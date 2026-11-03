"""
ASSISTments 2009-2010 Dataset Preprocessing

Downloads (if needed) and preprocesses the ASSISTments skill-builder dataset
for use with DKT and AKT models.

Input:  ml/data/skill_builder_data.csv (raw ASSISTments export)
Output: ml/data/processed/
        ├── train_sequences.pt    (student interaction sequences — train split)
        ├── test_sequences.pt     (student interaction sequences — test split)
        ├── skill_map.json        (skill_name → skill_id mapping)
        └── metadata.json         (dataset statistics)

Usage:
    python -m ml.scripts.preprocess_assistments [--data-dir ml/data]
"""
import os
import json
import argparse
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from sklearn.model_selection import train_test_split


def load_assistments(data_dir: str) -> pd.DataFrame:
    """Load raw ASSISTments skill-builder dataset."""
    csv_path = os.path.join(data_dir, "skill_builder_data.csv")

    if not os.path.exists(csv_path):
        print(f"ERROR: Dataset not found at {csv_path}")
        print()
        print("Please download the ASSISTments 2009-2010 skill-builder dataset:")
        print("  1. Visit https://sites.google.com/site/assistmaborern/dataset")
        print("  2. Download 'skill_builder_data.csv'")
        print(f"  3. Place it in: {data_dir}/")
        print()
        print("Alternatively, run with --generate-synthetic to create synthetic data.")
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path, encoding="latin-1", low_memory=False)
    print(f"  Raw records: {len(df):,}")
    return df


def preprocess(df: pd.DataFrame, min_interactions: int = 5, max_seq_len: int = 200):
    """
    Preprocess ASSISTments data into student interaction sequences.

    Steps:
    1. Select relevant columns
    2. Drop rows with missing skill_id or correct values
    3. Filter students with too few interactions
    4. Encode skill IDs to contiguous integers (1-indexed, 0 = padding)
    5. Sort by student and order_id (temporal order)
    6. Group into per-student sequences
    7. Truncate/split long sequences
    """
    print("Preprocessing...")

    # Select and clean columns
    required_cols = ["user_id", "skill_id", "correct"]
    optional_cols = ["order_id", "skill_name"]

    available = [c for c in required_cols + optional_cols if c in df.columns]
    df = df[available].copy()

    # Drop missing values
    df = df.dropna(subset=["user_id", "skill_id", "correct"])
    df["correct"] = df["correct"].astype(int).clip(0, 1)
    df["user_id"] = df["user_id"].astype(int)
    df["skill_id"] = df["skill_id"].astype(int)

    print(f"  After cleaning: {len(df):,} interactions")

    # Filter students with too few interactions
    student_counts = df.groupby("user_id").size()
    valid_students = student_counts[student_counts >= min_interactions].index
    df = df[df["user_id"].isin(valid_students)]
    print(f"  Students with ≥{min_interactions} interactions: {len(valid_students):,}")
    print(f"  Interactions after filtering: {len(df):,}")

    # Encode skill IDs to contiguous integers (1-indexed, 0 reserved for padding)
    unique_skills = sorted(df["skill_id"].unique())
    skill_to_idx = {s: i + 1 for i, s in enumerate(unique_skills)}
    num_skills = len(unique_skills)
    df["skill_idx"] = df["skill_id"].map(skill_to_idx)

    print(f"  Unique skills: {num_skills}")

    # Build skill name map if available
    skill_map = {}
    if "skill_name" in df.columns:
        for _, row in df[["skill_id", "skill_name"]].drop_duplicates().iterrows():
            sid = int(row["skill_id"])
            if sid in skill_to_idx:
                skill_map[str(skill_to_idx[sid])] = str(row["skill_name"])

    # Sort by student and temporal order
    if "order_id" in df.columns:
        df = df.sort_values(["user_id", "order_id"])
    else:
        df = df.sort_values("user_id")

    # Group into per-student sequences
    sequences = []
    for user_id, group in df.groupby("user_id"):
        skills = group["skill_idx"].values
        corrects = group["correct"].values

        # Split long sequences into chunks
        for start in range(0, len(skills), max_seq_len):
            end = min(start + max_seq_len, len(skills))
            chunk_skills = skills[start:end]
            chunk_corrects = corrects[start:end]

            if len(chunk_skills) >= min_interactions:
                sequences.append({
                    "user_id": int(user_id),
                    "skill_ids": chunk_skills.tolist(),
                    "corrects": chunk_corrects.tolist(),
                    "length": len(chunk_skills),
                })

    print(f"  Total sequences: {len(sequences):,}")

    return sequences, num_skills, skill_map


def generate_synthetic_data(
    num_students: int = 500,
    num_skills: int = 20,
    min_seq: int = 10,
    max_seq: int = 100,
    seed: int = 42,
):
    """
    Generate synthetic student interaction data for development/testing.
    NOT a substitute for real ASSISTments data.
    """
    print("Generating synthetic data (for development only)...")
    rng = np.random.RandomState(seed)
    sequences = []

    for student_id in range(num_students):
        seq_len = rng.randint(min_seq, max_seq + 1)

        # Student has varying mastery per skill
        student_mastery = rng.beta(2, 3, size=num_skills)

        skills = rng.randint(1, num_skills + 1, size=seq_len)
        corrects = []
        for s in skills:
            # Probability of correct answer based on mastery
            p = student_mastery[s - 1]
            # Simple learning effect: mastery increases slightly with practice
            student_mastery[s - 1] = min(1.0, p + 0.02)
            corrects.append(int(rng.random() < p))

        sequences.append({
            "user_id": student_id,
            "skill_ids": skills.tolist(),
            "corrects": corrects,
            "length": seq_len,
        })

    skill_map = {str(i): f"Skill_{i}" for i in range(1, num_skills + 1)}
    print(f"  Generated {num_students} students, {num_skills} skills")

    return sequences, num_skills, skill_map


def create_tensors(sequences: list, num_skills: int, max_seq_len: int = 200):
    """
    Convert sequence dicts to padded PyTorch tensors.

    Returns dict with:
        - interaction_ids: (N, max_len) — skill_idx if wrong, skill_idx + num_skills if correct
        - skill_ids: (N, max_len) — skill index at each step (1-indexed)
        - response_ids: (N, max_len) — 0=pad, 1=wrong, 2=correct
        - target_skills: (N, max_len) — next skill (shifted by 1 for prediction)
        - target_corrects: (N, max_len) — next correctness (shifted)
        - seq_lengths: (N,) — actual lengths
        - masks: (N, max_len) — True where padded
    """
    N = len(sequences)
    max_len = min(max(s["length"] for s in sequences), max_seq_len)

    interaction_ids = torch.zeros(N, max_len, dtype=torch.long)
    skill_ids = torch.zeros(N, max_len, dtype=torch.long)
    response_ids = torch.zeros(N, max_len, dtype=torch.long)
    target_skills = torch.zeros(N, max_len, dtype=torch.long)
    target_corrects = torch.zeros(N, max_len, dtype=torch.float)
    seq_lengths = torch.zeros(N, dtype=torch.long)
    masks = torch.ones(N, max_len, dtype=torch.bool)  # True = padded

    for i, seq in enumerate(sequences):
        L = min(seq["length"], max_len)
        skills = seq["skill_ids"][:L]
        corrects = seq["corrects"][:L]

        for t in range(L):
            s = skills[t]
            c = corrects[t]

            # DKT-style interaction ID
            interaction_ids[i, t] = s + (num_skills if c == 1 else 0)

            # AKT-style separate encodings
            skill_ids[i, t] = s
            response_ids[i, t] = 2 if c == 1 else 1  # 2=correct, 1=wrong

            # Target is the NEXT step's skill and correctness
            if t < L - 1:
                target_skills[i, t] = skills[t + 1]
                target_corrects[i, t] = float(corrects[t + 1])

            masks[i, t] = False

        # For the last position, target is invalid (masked out during loss)
        seq_lengths[i] = L

    return {
        "interaction_ids": interaction_ids,
        "skill_ids": skill_ids,
        "response_ids": response_ids,
        "target_skills": target_skills,
        "target_corrects": target_corrects,
        "seq_lengths": seq_lengths,
        "masks": masks,
        "num_skills": num_skills,
    }


def student_split(sequences: list, test_size: float = 0.2, seed: int = 42):
    """
    Student-level train/test split.
    Ensures no student appears in both train and test sets.
    """
    user_ids = list(set(s["user_id"] for s in sequences))
    train_users, test_users = train_test_split(
        user_ids, test_size=test_size, random_state=seed
    )
    train_users = set(train_users)
    test_users = set(test_users)

    train_seqs = [s for s in sequences if s["user_id"] in train_users]
    test_seqs = [s for s in sequences if s["user_id"] in test_users]

    print(f"  Train: {len(train_seqs)} sequences ({len(train_users)} students)")
    print(f"  Test:  {len(test_seqs)} sequences ({len(test_users)} students)")

    return train_seqs, test_seqs


def main():
    parser = argparse.ArgumentParser(description="Preprocess ASSISTments dataset")
    parser.add_argument("--data-dir", default="ml/data", help="Data directory")
    parser.add_argument("--min-interactions", type=int, default=5,
                        help="Minimum interactions per student")
    parser.add_argument("--max-seq-len", type=int, default=200,
                        help="Maximum sequence length")
    parser.add_argument("--test-size", type=float, default=0.2,
                        help="Test set fraction")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--generate-synthetic", action="store_true",
                        help="Generate synthetic data instead of loading ASSISTments")
    args = parser.parse_args()

    # Load or generate data
    if args.generate_synthetic:
        sequences, num_skills, skill_map = generate_synthetic_data(seed=args.seed)
    else:
        df = load_assistments(args.data_dir)
        sequences, num_skills, skill_map = preprocess(
            df,
            min_interactions=args.min_interactions,
            max_seq_len=args.max_seq_len,
        )

    # Student-level split
    train_seqs, test_seqs = student_split(sequences, args.test_size, args.seed)

    # Convert to tensors
    print("Creating tensors...")
    train_data = create_tensors(train_seqs, num_skills, args.max_seq_len)
    test_data = create_tensors(test_seqs, num_skills, args.max_seq_len)

    # Save
    output_dir = os.path.join(args.data_dir, "processed")
    os.makedirs(output_dir, exist_ok=True)

    torch.save(train_data, os.path.join(output_dir, "train_sequences.pt"))
    torch.save(test_data, os.path.join(output_dir, "test_sequences.pt"))

    with open(os.path.join(output_dir, "skill_map.json"), "w") as f:
        json.dump(skill_map, f, indent=2)

    metadata = {
        "num_skills": num_skills,
        "num_train_sequences": len(train_seqs),
        "num_test_sequences": len(test_seqs),
        "max_seq_len": args.max_seq_len,
        "min_interactions": args.min_interactions,
        "test_size": args.test_size,
        "seed": args.seed,
        "is_synthetic": args.generate_synthetic,
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved to {output_dir}/")
    print(f"  train_sequences.pt: {len(train_seqs)} sequences")
    print(f"  test_sequences.pt:  {len(test_seqs)} sequences")
    print(f"  skill_map.json:     {num_skills} skills")
    print(f"  metadata.json:      dataset statistics")
    print("\nDone!")


if __name__ == "__main__":
    main()

