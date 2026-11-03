"""
Deep Knowledge Tracing (DKT) Model

Based on: Piech et al., "Deep Knowledge Tracing" (NeurIPS 2015)

Architecture:
  - Input: one-hot encoded (skill_id, correctness) pairs → embedding
  - LSTM processes the student interaction sequence
  - Output: predicted probability of correct response for each skill at each step

This implementation uses:
  - Learnable skill embeddings instead of raw one-hot vectors
  - Separate embeddings for correct vs incorrect responses
  - LSTM with dropout for regularization
  - Sigmoid output for binary cross-entropy loss
"""
import torch
import torch.nn as nn
from typing import Optional


class DKTModel(nn.Module):
    """Deep Knowledge Tracing with LSTM backbone."""

    def __init__(
        self,
        num_skills: int,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 1,
        dropout: float = 0.2,
    ):
        """
        Args:
            num_skills: Number of unique skills/knowledge components.
            embed_dim: Dimension of skill+response embeddings.
            hidden_dim: LSTM hidden state dimension.
            num_layers: Number of LSTM layers.
            dropout: Dropout rate applied between LSTM layers (if num_layers > 1)
                     and on the final output projection.
        """
        super().__init__()
        self.num_skills = num_skills
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # Embedding: 2 * num_skills inputs (skill_id for wrong, skill_id + num_skills for correct)
        self.interaction_embedding = nn.Embedding(
            num_embeddings=2 * num_skills,
            embedding_dim=embed_dim,
            padding_idx=0,
        )

        # LSTM backbone
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Output projection: hidden state → per-skill prediction
        self.output_dropout = nn.Dropout(dropout)
        self.output_layer = nn.Linear(hidden_dim, num_skills)

    def forward(
        self,
        interaction_ids: torch.Tensor,
        target_skill_ids: torch.Tensor,
        seq_lengths: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            interaction_ids: (batch, seq_len) — encoded as:
                skill_id if incorrect, skill_id + num_skills if correct.
                0 = padding.
            target_skill_ids: (batch, seq_len) — the skill being tested at
                each next step. Used to select the relevant output dimension.
            seq_lengths: (batch,) — actual sequence lengths for packing.

        Returns:
            predictions: (batch, seq_len) — predicted P(correct) for the
                target skill at each step.
        """
        # Embed interactions
        embedded = self.interaction_embedding(interaction_ids)  # (B, T, E)

        # Pack if lengths provided, for efficiency
        if seq_lengths is not None:
            packed = nn.utils.rnn.pack_padded_sequence(
                embedded, seq_lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            lstm_out, _ = self.lstm(packed)
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(
                lstm_out, batch_first=True
            )
        else:
            lstm_out, _ = self.lstm(embedded)  # (B, T, H)

        # Project to per-skill predictions
        lstm_out = self.output_dropout(lstm_out)
        all_skill_preds = torch.sigmoid(self.output_layer(lstm_out))  # (B, T, num_skills)

        # Select prediction for the target skill at each step
        # target_skill_ids: (B, T) → (B, T, 1) for gather
        target_ids = target_skill_ids.unsqueeze(-1).clamp(0, self.num_skills - 1)
        predictions = all_skill_preds.gather(dim=2, index=target_ids).squeeze(-1)  # (B, T)

        return predictions

    def predict_mastery(
        self,
        interaction_ids: torch.Tensor,
        seq_lengths: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Predict mastery probability for ALL skills after processing
        the student's interaction sequence.

        Args:
            interaction_ids: (batch, seq_len) — encoded interactions.
            seq_lengths: (batch,) — actual sequence lengths.

        Returns:
            mastery: (batch, num_skills) — P(correct) for each skill
                based on the final hidden state.
        """
        embedded = self.interaction_embedding(interaction_ids)

        if seq_lengths is not None:
            packed = nn.utils.rnn.pack_padded_sequence(
                embedded, seq_lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            lstm_out, (h_n, _) = self.lstm(packed)
        else:
            _, (h_n, _) = self.lstm(embedded)

        # Use the final hidden state from the last layer
        final_hidden = h_n[-1]  # (B, H)
        final_hidden = self.output_dropout(final_hidden)
        mastery = torch.sigmoid(self.output_layer(final_hidden))  # (B, num_skills)

        return mastery

    def get_config(self) -> dict:
        """Return model configuration for serialization."""
        return {
            "num_skills": self.num_skills,
            "embed_dim": self.interaction_embedding.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "dropout": self.output_dropout.p,
        }

    @classmethod
    def from_config(cls, config: dict) -> "DKTModel":
        """Create model from configuration dict."""
        return cls(
            num_skills=config["num_skills"],
            embed_dim=config["embed_dim"],
            hidden_dim=config["hidden_dim"],
            num_layers=config["num_layers"],
            dropout=config["dropout"],
        )

