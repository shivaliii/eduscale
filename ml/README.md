# EduScale ML — Knowledge Tracing
# DKT and AKT model implementations for student knowledge estimation

This directory contains the machine learning pipeline for knowledge tracing.

## Structure

```
ml/
├── README.md                    # This file
├── requirements.txt             # ML-specific dependencies
├── models/
│   ├── __init__.py
│   ├── dkt.py                   # Deep Knowledge Tracing (DKT) model
│   └── akt.py                   # Attentive Knowledge Tracing (AKT) model
├── scripts/
│   ├── preprocess_assistments.py # ASSISTments data preprocessing
│   ├── train.py                  # Training pipeline
│   ├── evaluate.py               # Evaluation metrics
│   └── inference_server.py       # FastAPI inference endpoint
├── data/                         # Raw and processed datasets (gitignored)
├── checkpoints/                  # Trained model weights (gitignored)
└── experiments/                  # Training logs and results
```

## Dataset: ASSISTments 2009-2010

Download from: https://sites.google.com/site/assistmaborern/dataset

Place the file `skill_builder_data.csv` in `ml/data/`.

### Preprocessing

```bash
python -m ml.scripts.preprocess_assistments
```

This will:
1. Load the raw ASSISTments skill-builder dataset
2. Filter students with ≥ 5 interactions
3. Encode skill IDs to contiguous indices
4. Create student-level train/test split (80/20)
5. Save processed sequences to `ml/data/processed/`

### Training

```bash
# Train DKT model
python -m ml.scripts.train --model dkt --epochs 50 --batch-size 64

# Train AKT model
python -m ml.scripts.train --model akt --epochs 50 --batch-size 64
```

### Evaluation Metrics

- AUC (Area Under ROC Curve)
- Accuracy
- RMSE
- Per-skill accuracy breakdown

### Integration with Backend

Set `DEMO_MODE=false` and `KT_MODEL_PATH=ml/checkpoints/dkt_best.pt` in `.env` to use
the trained DKT model for mastery estimation instead of the heuristic fallback.

