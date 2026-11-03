"""
Training Pipeline for DKT and AKT Models

Supports:
  - DKT (LSTM-based) and AKT (attention-based) models
  - Student-level train/test split (from preprocessing)
  - Binary cross-entropy loss with masking for padded positions
  - Early stopping based on validation AUC
  - Checkpoint saving (best model + final model)
  - Training metrics logging (loss, AUC, accuracy per epoch)

Usage:
    python -m ml.scripts.train --model dkt --epochs 50 --batch-size 64
    python -m ml.scripts.train --model akt --epochs 50 --batch-size 64
    python -m ml.scripts.train --model dkt --generate-synthetic --epochs 20
"""
import os
import json
import time
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import roc_auc_score, accuracy_score
from pathlib import Path

from ml.models.dkt import DKTModel
from ml.models.akt import AKTModel


def create_dataloader(data: dict, batch_size: int, shuffle: bool = True) -> DataLoader:
    """Create a DataLoader from preprocessed tensor data."""
    dataset = TensorDataset(
        data["interaction_ids"],
        data["skill_ids"],
        data["response_ids"],
        data["target_skills"],
        data["target_corrects"],
        data["seq_lengths"],
        data["masks"],
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    model_type: str,
) -> float:
    """Train for one epoch. Returns average loss."""
    model.train()
    total_loss = 0.0
    num_batches = 0

    for batch in loader:
        interaction_ids, skill_ids, response_ids, target_skills, target_corrects, seq_lengths, masks = [
            b.to(device) for b in batch
        ]

        optimizer.zero_grad()

        if model_type == "dkt":
            predictions = model(interaction_ids, target_skills, seq_lengths)
        else:  # akt
            predictions = model(skill_ids, response_ids, target_skills, masks)

        # Create loss mask: exclude padded positions AND the last position
        # (which has no valid target)
        loss_mask = ~masks.clone()
        for i in range(len(seq_lengths)):
            if seq_lengths[i] > 0:
                loss_mask[i, seq_lengths[i] - 1] = False

        # Compute masked loss
        if loss_mask.any():
            masked_preds = predictions[loss_mask]
            masked_targets = target_corrects[loss_mask]
            loss = criterion(masked_preds, masked_targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()

        num_batches += 1

    return total_loss / max(num_batches, 1)


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    model_type: str,
) -> dict:
    """Evaluate model on a dataset. Returns metrics dict."""
    model.eval()
    all_preds = []
    all_targets = []
    total_loss = 0.0
    num_batches = 0

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
            masked_preds = predictions[loss_mask]
            masked_targets = target_corrects[loss_mask]
            loss = criterion(masked_preds, masked_targets)
            total_loss += loss.item()

            all_preds.append(masked_preds.cpu().numpy())
            all_targets.append(masked_targets.cpu().numpy())

        num_batches += 1

    if len(all_preds) == 0:
        return {"loss": 0.0, "auc": 0.5, "accuracy": 0.0, "rmse": 1.0}

    all_preds = np.concatenate(all_preds)
    all_targets = np.concatenate(all_targets)

    # Compute metrics
    try:
        auc = roc_auc_score(all_targets, all_preds)
    except ValueError:
        auc = 0.5  # All same class

    binary_preds = (all_preds >= 0.5).astype(float)
    accuracy = accuracy_score(all_targets, binary_preds)
    rmse = np.sqrt(np.mean((all_preds - all_targets) ** 2))

    return {
        "loss": total_loss / max(num_batches, 1),
        "auc": auc,
        "accuracy": accuracy,
        "rmse": rmse,
        "num_predictions": len(all_preds),
    }


def main():
    parser = argparse.ArgumentParser(description="Train DKT/AKT model")
    parser.add_argument("--model", choices=["dkt", "akt"], default="dkt",
                        help="Model type")
    parser.add_argument("--data-dir", default="ml/data/processed",
                        help="Processed data directory")
    parser.add_argument("--checkpoint-dir", default="ml/checkpoints",
                        help="Checkpoint save directory")
    parser.add_argument("--experiment-dir", default="ml/experiments",
                        help="Experiment logs directory")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-5, help="Weight decay")
    parser.add_argument("--embed-dim", type=int, default=64, help="Embedding dim")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Hidden dim (DKT)")
    parser.add_argument("--num-layers", type=int, default=1, help="Num LSTM/transformer layers")
    parser.add_argument("--dropout", type=float, default=0.2, help="Dropout rate")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    parser.add_argument("--device", default="auto", help="Device (auto/cpu/cuda)")
    parser.add_argument("--generate-synthetic", action="store_true",
                        help="Generate and preprocess synthetic data first")
    args = parser.parse_args()

    # Device
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    print(f"Using device: {device}")

    # Generate synthetic data if needed
    if args.generate_synthetic:
        print("Generating synthetic data for training...")
        from ml.scripts.preprocess_assistments import (
            generate_synthetic_data, student_split, create_tensors
        )
        sequences, num_skills, skill_map = generate_synthetic_data()
        train_seqs, test_seqs = student_split(sequences)
        train_data = create_tensors(train_seqs, num_skills)
        test_data = create_tensors(test_seqs, num_skills)

        os.makedirs(args.data_dir, exist_ok=True)
        torch.save(train_data, os.path.join(args.data_dir, "train_sequences.pt"))
        torch.save(test_data, os.path.join(args.data_dir, "test_sequences.pt"))
    else:
        # Load preprocessed data
        train_path = os.path.join(args.data_dir, "train_sequences.pt")
        test_path = os.path.join(args.data_dir, "test_sequences.pt")

        if not os.path.exists(train_path):
            print(f"ERROR: Processed data not found at {args.data_dir}/")
            print("Run preprocessing first:")
            print("  python -m ml.scripts.preprocess_assistments")
            print("Or use --generate-synthetic for synthetic data.")
            return

        print(f"Loading data from {args.data_dir}/...")
        train_data = torch.load(train_path, weights_only=False)
        test_data = torch.load(test_path, weights_only=False)

    num_skills = train_data["num_skills"]
    print(f"  Skills: {num_skills}")
    print(f"  Train sequences: {len(train_data['seq_lengths'])}")
    print(f"  Test sequences: {len(test_data['seq_lengths'])}")

    # Create data loaders
    train_loader = create_dataloader(train_data, args.batch_size, shuffle=True)
    test_loader = create_dataloader(test_data, args.batch_size, shuffle=False)

    # Create model
    if args.model == "dkt":
        model = DKTModel(
            num_skills=num_skills,
            embed_dim=args.embed_dim,
            hidden_dim=args.hidden_dim,
            num_layers=args.num_layers,
            dropout=args.dropout,
        )
    else:
        model = AKTModel(
            num_skills=num_skills,
            d_model=args.embed_dim,
            n_heads=4,
            n_layers=args.num_layers,
            d_ff=args.hidden_dim,
            dropout=args.dropout,
        )

    model = model.to(device)
    print(f"\n{args.model.upper()} Model:")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"  Config: {model.get_config()}")

    # Optimizer and loss
    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=5, verbose=True
    )
    criterion = nn.BCELoss()

    # Training loop
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    os.makedirs(args.experiment_dir, exist_ok=True)

    best_auc = 0.0
    patience_counter = 0
    history = []

    print(f"\nTraining for {args.epochs} epochs...\n")
    print(f"{'Epoch':>5} | {'Train Loss':>10} | {'Test Loss':>10} | {'Test AUC':>10} | {'Test Acc':>10} | {'Test RMSE':>10} | {'LR':>10}")
    print("-" * 80)

    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        # Train
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device, args.model)

        # Evaluate
        test_metrics = evaluate(model, test_loader, criterion, device, args.model)

        # Learning rate scheduling
        scheduler.step(test_metrics["auc"])
        current_lr = optimizer.param_groups[0]["lr"]

        # Log
        epoch_data = {
            "epoch": epoch,
            "train_loss": train_loss,
            **{f"test_{k}": v for k, v in test_metrics.items()},
            "lr": current_lr,
        }
        history.append(epoch_data)

        print(
            f"{epoch:5d} | {train_loss:10.4f} | {test_metrics['loss']:10.4f} | "
            f"{test_metrics['auc']:10.4f} | {test_metrics['accuracy']:10.4f} | "
            f"{test_metrics['rmse']:10.4f} | {current_lr:10.6f}"
        )

        # Save best model
        if test_metrics["auc"] > best_auc:
            best_auc = test_metrics["auc"]
            patience_counter = 0
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "model_config": model.get_config(),
                "model_type": args.model,
                "best_auc": best_auc,
                "test_metrics": test_metrics,
            }
            torch.save(
                checkpoint,
                os.path.join(args.checkpoint_dir, f"{args.model}_best.pt"),
            )
            print(f"  ★ New best AUC: {best_auc:.4f} — checkpoint saved")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"\nEarly stopping at epoch {epoch} (patience={args.patience})")
                break

    elapsed = time.time() - start_time

    # Save final model
    final_checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "model_config": model.get_config(),
        "model_type": args.model,
        "final_metrics": test_metrics,
    }
    torch.save(
        final_checkpoint,
        os.path.join(args.checkpoint_dir, f"{args.model}_final.pt"),
    )

    # Save training history
    experiment_log = {
        "model_type": args.model,
        "num_skills": num_skills,
        "model_config": model.get_config(),
        "training_args": vars(args),
        "best_auc": best_auc,
        "total_epochs": epoch,
        "training_time_seconds": elapsed,
        "history": history,
        "device": str(device),
    }

    log_path = os.path.join(args.experiment_dir, f"{args.model}_training_log.json")
    with open(log_path, "w") as f:
        json.dump(experiment_log, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Training complete!")
    print(f"  Model:         {args.model.upper()}")
    print(f"  Best AUC:      {best_auc:.4f}")
    print(f"  Total epochs:  {epoch}")
    print(f"  Training time: {elapsed:.1f}s")
    print(f"  Best checkpoint: {args.checkpoint_dir}/{args.model}_best.pt")
    print(f"  Training log:    {log_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

