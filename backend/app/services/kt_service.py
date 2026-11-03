"""
Knowledge Tracing Service

Bridges the ML models (DKT/AKT) with the backend API.
When DEMO_MODE=false and a trained model checkpoint exists,
uses the ML model for mastery prediction.
Otherwise, falls back to the heuristic mastery calculation.

This service is called by quiz_service after each quiz submission
to update student mastery scores based on the model's predictions.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global inference instance (lazy-loaded)
_inference_instance = None
_inference_initialized = False


def _get_inference():
    """Lazy-load the inference model."""
    global _inference_instance, _inference_initialized

    if _inference_initialized:
        return _inference_instance

    _inference_initialized = True

    # Check if we should use ML model
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if demo_mode:
        logger.info("DEMO_MODE=true — using heuristic mastery (no ML model)")
        return None

    # Look for checkpoint
    checkpoint_path = os.getenv(
        "KT_MODEL_PATH",
        os.path.join("ml", "checkpoints", "dkt_best.pt"),
    )

    if not os.path.exists(checkpoint_path):
        logger.warning(f"KT checkpoint not found at {checkpoint_path} — falling back to heuristic")
        return None

    try:
        from ml.scripts.inference_server import KnowledgeTracingInference
        _inference_instance = KnowledgeTracingInference(
            checkpoint_path=checkpoint_path,
            device=os.getenv("KT_DEVICE", "cpu"),
        )
        logger.info(f"Loaded KT model from {checkpoint_path}")
        return _inference_instance
    except Exception as e:
        logger.error(f"Failed to load KT model: {e}")
        return None


def predict_mastery(
    skill_sequence: list[int],
    correct_sequence: list[int],
    num_skills: int,
) -> Optional[dict[int, float]]:
    """
    Predict mastery for all skills using the trained model.

    Returns None if no model is available (caller should use heuristic).

    Args:
        skill_sequence: List of skill IDs (1-indexed) attempted by the student.
        correct_sequence: List of 0/1 correctness values for each attempt.
        num_skills: Total number of skills.

    Returns:
        Dict mapping skill_id → mastery score (0.0 to 1.0), or None.
    """
    inference = _get_inference()
    if inference is None:
        return None

    try:
        return inference.predict_mastery(skill_sequence, correct_sequence)
    except Exception as e:
        logger.error(f"Mastery prediction failed: {e}")
        return None


def predict_next_correctness(
    skill_sequence: list[int],
    correct_sequence: list[int],
    target_skill: int,
) -> Optional[float]:
    """
    Predict probability of answering the next question correctly.

    Returns None if no model is available.
    """
    inference = _get_inference()
    if inference is None:
        return None

    try:
        return inference.predict_next(
            skill_sequence, correct_sequence, target_skill
        )
    except Exception as e:
        logger.error(f"Next-step prediction failed: {e}")
        return None


def get_model_info() -> dict:
    """Get information about the loaded model, or fallback status."""
    inference = _get_inference()
    if inference is None:
        return {
            "model_type": "heuristic",
            "status": "No ML model loaded — using heuristic mastery",
            "demo_mode": os.getenv("DEMO_MODE", "true"),
        }
    return inference.get_model_info()

