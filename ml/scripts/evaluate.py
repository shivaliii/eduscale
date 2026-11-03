"""
Evaluation script for trained DKT/AKT models.

Computes:
  - AUC (Area Under ROC Curve)
  - Accuracy
  - RMSE
  - Per-skill accuracy breakdown
  - Confusion matrix stats

Usage:
    python -m ml.scripts.evaluate --model dkt --checkpoint ml/checkpoints/dkt_best.pt
"""
import os
import json
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import (
    roc_auc_score, accuracy_score, f1_score,
    precision_score, recall_score, confusion_matrix,
)
from collections import defaultdict

from ml.models.dkt import DKTModel
from ml.models.akt import AKTModel


@torch.no_grad()
def detailed_evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    model_type: str,
    num_skills: int,
) -> dict:
    """Run detailed evaluation with per-skill metrics."""
    model.eval()
    all_preds = []
    all_targets = []
    all_skills = []

    for batch in loader:
        interaction_ids, skill_ids, response_ids, target_skills, target_corrects, seq_lengths, masks = [
            b.to(device) for b in batch
        ]

        if model_type == "dkt":
            predictions = model(interaction_ids, target_skills, seq_lengths)
        else:
            predictions = model(skill_ids, response_ids, target_skills, masks)

        # Loss mask
        loss_mask = ~masks.clone()
        for i in range(len(seq_lengths)):
            if seq_lengths[i] > 0:
                loss_mask[i, seq_lengths[i] - 1] = False

        if loss_mask.any():
            all_preds.append(predictions[loss_mask].cpu().numpy())
            all_targets.append(target_corrects[loss_mask].cpu().numpy())
            all_skills.append(target_skills[loss_mask].cpu().numpy())

    if not all_preds:
        return {"error": "No valid predictions"}

    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)
    skills = np.concatenate(all_skills)

    binary_preds = (preds >= 0.5).astype(float)

    # Overall metrics
    try:
        auc = roc_auc_score(targets, preds)
    except ValueError:
        auc = 0.5

    overall = {
        "auc": float(auc),
        "accuracy": float(accuracy_score(targets, binary_preds)),
        "precision": float(precision_score(targets, binary_preds, zero_division=0)),
        "recall": float(recall_score(targets, binary_preds, zero_division=0)),
        "f1": float(f1_score(targets, binary_preds, zero_division=0)),
        "rmse": float(np.sqrt(np.mean((preds - targets) ** 2))),
        "num_predictions": int(len(preds)),
    }

    # Confusion matrix
    cm = confusion_matrix(targets, binary_preds)
    if cm.shape == (2, 2):
        overall["true_negatives"] = int(cm[0, 0])
        overall["false_positives"] = int(cm[0, 1])
        overall["false_negatives"] = int(cm[1, 0])
        overall["true_positives"] = int(cm[1, 1])

    # Per-skill metrics
    per_skill = {}
    for skill_id in range(1, num_skills + 1):
        mask = skills == skill_id
        if mask.sum() < 2:
            continue

        skill_preds = preds[mask]
        skill_targets = targets[mask]
        skill_binary = (skill_preds >= 0.5).astype(float)

        try:
            skill_auc = roc_auc_score(skill_targets, skill_preds)
        except ValueError:
            skill_auc = 0.5

        per_skill[str(skill_id)] = {
            "auc": float(skill_auc),
            "accuracy": float(accuracy_score(skill_targets, skill_binary)),
            "num_samples": int(mask.sum()),
            "positive_rate": float(skill_targets.mean()),
        }

    return {
        "overall": overall,
        "per_skill": per_skill,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate DKT/AKT model")
    parser.add_argument("--model", choices=["dkt", "akt"], required=True)
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint .pt file")
    parser.add_argument("--data-dir", default="ml/data/processed")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    # Device
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    # Load checkpoint
    print(f"Loading checkpoint: {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    config = checkpoint["model_config"]
    model_type = checkpoint.get("model_type", args.model)

    # Create model
    if model_type == "dkt":
        model = DKTModel.from_config(config)
    else:
        model = AKTModel.from_config(config)

    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    print(f"Model: {model_type.upper()}")
    print(f"Config: {config}")
    print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Load test data
    test_path = os.path.join(args.data_dir, "test_sequences.pt")
    test_data = torch.load(test_path, weights_only=False)
    num_skills = test_data["num_skills"]

    dataset = TensorDataset(
        test_data["interaction_ids"],
        test_data["skill_ids"],
        test_data["response_ids"],
        test_data["target_skills"],
        test_data["target_corrects"],
        test_data["seq_lengths"],
        test_data["masks"],
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)

    # Evaluate
    print(f"\nEvaluating on {len(test_data['seq_lengths'])} test sequences...")
    results = detailed_evaluate(model, loader, device, model_type, num_skills)

    # Print results
    print(f"\n{'='*50}")
    print("Overall Metrics:")
    for k, v in results["overall"].items():
        if isinstance(v, float):
            print(f"  {k:20s}: {v:.4f}")
        else:
            print(f"  {k:20s}: {v}")

    print(f"\nPer-Skill Metrics ({len(results['per_skill'])} skills):")
    sorted_skills = sorted(
        results["per_skill"].items(),
        key=lambda x: x[1]["auc"],
        reverse=True,
    )
    print(f"  {'Skill':>6} | {'AUC':>8} | {'Accuracy':>10} | {'Samples':>8} | {'Pos Rate':>10}")
    print(f"  {'-'*52}")
    for skill_id, metrics in sorted_skills[:20]:  # Top 20
        print(
            f"  {skill_id:>6} | {metrics['auc']:8.4f} | {metrics['accuracy']:10.4f} | "
            f"{metrics['num_samples']:8d} | {metrics['positive_rate']:10.4f}"
        )
    print(f"{'='*50}")

    # Save results
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(
            "ml/experiments", f"{model_type}_evaluation_results.json"
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()

