"""
Knowledge Tracing Inference Server

Provides a FastAPI endpoint for real-time mastery prediction using
trained DKT or AKT models. Integrates with the main EduScale backend.

The backend calls this service when DEMO_MODE=false to get model-based
mastery estimates instead of the heuristic fallback.

Usage:
    python -m ml.scripts.inference_server --checkpoint ml/checkpoints/dkt_best.pt --port 8001
"""
import os
import json
import torch
import numpy as np
from typing import Optional
from pathlib import Path

from ml.models.dkt import DKTModel
from ml.models.akt import AKTModel


class KnowledgeTracingInference:
    """
    Inference wrapper for DKT/AKT models.

    Loads a trained checkpoint and provides methods to:
    1. Predict mastery for all skills given a student's interaction history
    2. Predict next-step correctness for a specific skill
    """

    def __init__(self, checkpoint_path: str, device: str = "auto"):
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Load checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model_type = checkpoint.get("model_type", "dkt")
        config = checkpoint["model_config"]
        self.num_skills = config["num_skills"]

        # Create and load model
        if self.model_type == "dkt":
            self.model = DKTModel.from_config(config)
        else:
            self.model = AKTModel.from_config(config)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model = self.model.to(self.device)
        self.model.eval()

        # Load skill map if available
        skill_map_path = os.path.join(
            os.path.dirname(checkpoint_path), "..", "data", "processed", "skill_map.json"
        )
        self.skill_map = {}
        if os.path.exists(skill_map_path):
            with open(skill_map_path) as f:
                self.skill_map = json.load(f)

        print(f"Loaded {self.model_type.upper()} model: {self.num_skills} skills, device={self.device}")

    @torch.no_grad()
    def predict_mastery(
        self,
        skill_sequence: list[int],
        correct_sequence: list[int],
    ) -> dict[int, float]:
        """
        Predict mastery probability for all skills given a student's
        interaction history.

        Args:
            skill_sequence: List of skill IDs (1-indexed) in temporal order.
            correct_sequence: List of 0/1 correctness values.

        Returns:
            Dict mapping skill_id → mastery_probability (0.0 to 1.0).
        """
        if not skill_sequence:
            return {i: 0.5 for i in range(1, self.num_skills + 1)}

        seq_len = len(skill_sequence)

        if self.model_type == "dkt":
            # Encode interactions: skill_id if wrong, skill_id + num_skills if correct
            interaction_ids = []
            for s, c in zip(skill_sequence, correct_sequence):
                interaction_ids.append(s + (self.num_skills if c == 1 else 0))

            ids_tensor = torch.tensor([interaction_ids], dtype=torch.long, device=self.device)
            lengths = torch.tensor([seq_len], dtype=torch.long)

            mastery = self.model.predict_mastery(ids_tensor, lengths)  # (1, num_skills)
        else:
            # AKT encoding
            skill_tensor = torch.tensor([skill_sequence], dtype=torch.long, device=self.device)
            response_tensor = torch.tensor(
                [[2 if c == 1 else 1 for c in correct_sequence]],
                dtype=torch.long,
                device=self.device,
            )
            mask = torch.zeros(1, seq_len, dtype=torch.bool, device=self.device)

            mastery = self.model.predict_mastery(skill_tensor, response_tensor, mask)

        # Convert to dict
        mastery_np = mastery[0].cpu().numpy()
        result = {}
        for i in range(self.num_skills):
            skill_id = i + 1
            result[skill_id] = float(np.clip(mastery_np[i], 0.0, 1.0))

        return result

    @torch.no_grad()
    def predict_next(
        self,
        skill_sequence: list[int],
        correct_sequence: list[int],
        target_skill: int,
    ) -> float:
        """
        Predict the probability of answering the next question correctly
        for a specific target skill.

        Args:
            skill_sequence: Past skill IDs.
            correct_sequence: Past correctness values.
            target_skill: The skill being tested next.

        Returns:
            Probability of correct response (0.0 to 1.0).
        """
        mastery = self.predict_mastery(skill_sequence, correct_sequence)
        return mastery.get(target_skill, 0.5)

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return {
            "model_type": self.model_type,
            "num_skills": self.num_skills,
            "device": str(self.device),
            "config": self.model.get_config(),
            "skill_map": self.skill_map,
            "parameters": sum(p.numel() for p in self.model.parameters()),
        }


# ─── FastAPI inference server ───────────────────────────────────────

def create_app(checkpoint_path: str, device: str = "auto"):
    """Create a FastAPI app for serving inference requests."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError:
        raise ImportError("FastAPI required: pip install fastapi uvicorn")

    app = FastAPI(
        title="EduScale Knowledge Tracing Inference",
        description="Real-time mastery prediction using DKT/AKT models",
        version="1.0.0",
    )

    # Load model at startup
    inference = KnowledgeTracingInference(checkpoint_path, device)

    class MasteryRequest(BaseModel):
        skill_sequence: list[int]
        correct_sequence: list[int]

    class NextPredictionRequest(BaseModel):
        skill_sequence: list[int]
        correct_sequence: list[int]
        target_skill: int

    @app.get("/health")
    def health():
        return {"status": "healthy", **inference.get_model_info()}

    @app.post("/predict/mastery")
    def predict_mastery(req: MasteryRequest):
        if len(req.skill_sequence) != len(req.correct_sequence):
            raise HTTPException(400, "skill_sequence and correct_sequence must have equal length")
        mastery = inference.predict_mastery(req.skill_sequence, req.correct_sequence)
        return {"mastery": mastery}

    @app.post("/predict/next")
    def predict_next(req: NextPredictionRequest):
        if len(req.skill_sequence) != len(req.correct_sequence):
            raise HTTPException(400, "skill_sequence and correct_sequence must have equal length")
        prob = inference.predict_next(
            req.skill_sequence, req.correct_sequence, req.target_skill
        )
        return {"target_skill": req.target_skill, "probability_correct": prob}

    return app


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    app = create_app(args.checkpoint, args.device)
    uvicorn.run(app, host="0.0.0.0", port=args.port)

