"""
Attentive Knowledge Tracing (AKT) Model

Based on: Ghosh et al., "Context-Aware Attentive Knowledge Tracing" (KDD 2020)

Architecture:
  - Skill embeddings + response embeddings
  - Multi-head self-attention over the interaction sequence
  - Context-aware attention between current query and past interactions
  - Monotonic attention mechanism to respect temporal ordering
  - Output: predicted probability of correct response

This is a simplified but functional AKT implementation suitable for
the EduScale platform's knowledge tracing needs.
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for sequence position information."""

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class MonotonicAttention(nn.Module):
    """
    Causal (monotonic) scaled dot-product attention.
    Ensures each position can only attend to previous positions,
    respecting the temporal order of student interactions.
    """

    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_k = d_model // n_heads
        self.n_heads = n_heads

        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        B, T, _ = query.shape

        # Project and reshape to (B, n_heads, T, d_k)
        q = self.W_q(query).view(B, T, self.n_heads, self.d_k).transpose(1, 2)
        k = self.W_k(key).view(B, -1, self.n_heads, self.d_k).transpose(1, 2)
        v = self.W_v(value).view(B, -1, self.n_heads, self.d_k).transpose(1, 2)

        # Scaled dot-product attention
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)

        # Causal mask: prevent attending to future positions
        causal_mask = torch.triu(
            torch.ones(T, k.size(2), device=query.device, dtype=torch.bool), diagonal=1
        )
        scores = scores.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float("-inf"))

        # Padding mask
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1).unsqueeze(2), float("-inf"))

        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # Attend to values
        context = torch.matmul(attn_weights, v)  # (B, n_heads, T, d_k)
        context = context.transpose(1, 2).contiguous().view(B, T, -1)

        return self.W_o(context)


class AKTBlock(nn.Module):
    """Single AKT transformer block with attention + FFN."""

    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.attention = MonotonicAttention(d_model, n_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(
        self, x: torch.Tensor, mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        # Self-attention with residual
        attn_out = self.attention(x, x, x, mask)
        x = self.norm1(x + attn_out)

        # Feed-forward with residual
        ffn_out = self.ffn(x)
        x = self.norm2(x + ffn_out)

        return x


class AKTModel(nn.Module):
    """
    Attentive Knowledge Tracing model.

    Uses transformer-style self-attention with monotonic (causal) masking
    to model student learning trajectories.
    """

    def __init__(
        self,
        num_skills: int,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ff: int = 128,
        max_seq_len: int = 200,
        dropout: float = 0.2,
    ):
        """
        Args:
            num_skills: Number of unique skills/knowledge components.
            d_model: Model embedding dimension.
            n_heads: Number of attention heads.
            n_layers: Number of transformer blocks.
            d_ff: Feed-forward hidden dimension.
            max_seq_len: Maximum sequence length.
            dropout: Dropout rate.
        """
        super().__init__()
        self.num_skills = num_skills
        self.d_model = d_model

        # Embeddings
        self.skill_embedding = nn.Embedding(num_skills + 1, d_model, padding_idx=0)
        self.response_embedding = nn.Embedding(3, d_model, padding_idx=0)  # 0=pad, 1=wrong, 2=correct
        self.interaction_proj = nn.Linear(2 * d_model, d_model)

        # Positional encoding
        self.pos_encoding = PositionalEncoding(d_model, max_seq_len, dropout)

        # Transformer blocks
        self.blocks = nn.ModuleList(
            [AKTBlock(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)]
        )

        # Output projection
        self.output_dropout = nn.Dropout(dropout)
        self.output_layer = nn.Linear(d_model, num_skills)

    def forward(
        self,
        skill_ids: torch.Tensor,
        response_ids: torch.Tensor,
        target_skill_ids: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            skill_ids: (batch, seq_len) — skill ID at each step (1-indexed, 0=pad).
            response_ids: (batch, seq_len) — 0=pad, 1=incorrect, 2=correct.
            target_skill_ids: (batch, seq_len) — skill tested at next step.
            padding_mask: (batch, seq_len) — True where padded.

        Returns:
            predictions: (batch, seq_len) — P(correct) for target skill.
        """
        # Embed skills and responses
        skill_emb = self.skill_embedding(skill_ids)  # (B, T, D)
        resp_emb = self.response_embedding(response_ids)  # (B, T, D)

        # Combine skill + response into interaction embedding
        interaction = self.interaction_proj(
            torch.cat([skill_emb, resp_emb], dim=-1)
        )  # (B, T, D)

        # Add positional encoding
        x = self.pos_encoding(interaction)

        # Process through transformer blocks
        for block in self.blocks:
            x = block(x, padding_mask)

        # Project to per-skill predictions
        x = self.output_dropout(x)
        all_preds = torch.sigmoid(self.output_layer(x))  # (B, T, num_skills)

        # Select prediction for target skill
        target_ids = target_skill_ids.unsqueeze(-1).clamp(0, self.num_skills - 1)
        predictions = all_preds.gather(dim=2, index=target_ids).squeeze(-1)  # (B, T)

        return predictions

    def predict_mastery(
        self,
        skill_ids: torch.Tensor,
        response_ids: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Predict mastery for all skills after processing the interaction sequence.

        Returns:
            mastery: (batch, num_skills) — P(correct) for each skill.
        """
        skill_emb = self.skill_embedding(skill_ids)
        resp_emb = self.response_embedding(response_ids)
        interaction = self.interaction_proj(torch.cat([skill_emb, resp_emb], dim=-1))
        x = self.pos_encoding(interaction)

        for block in self.blocks:
            x = block(x, padding_mask)

        # Use the last non-padded position's output
        if padding_mask is not None:
            # Find last valid position for each sequence
            seq_lengths = (~padding_mask).sum(dim=1).clamp(min=1)  # (B,)
            batch_idx = torch.arange(x.size(0), device=x.device)
            last_hidden = x[batch_idx, seq_lengths - 1]  # (B, D)
        else:
            last_hidden = x[:, -1, :]  # (B, D)

        last_hidden = self.output_dropout(last_hidden)
        mastery = torch.sigmoid(self.output_layer(last_hidden))  # (B, num_skills)

        return mastery

    def get_config(self) -> dict:
        """Return model configuration for serialization."""
        return {
            "num_skills": self.num_skills,
            "d_model": self.d_model,
            "n_heads": self.blocks[0].attention.n_heads,
            "n_layers": len(self.blocks),
            "d_ff": self.blocks[0].ffn[0].out_features,
            "max_seq_len": self.pos_encoding.pe.size(1),
            "dropout": self.output_dropout.p,
        }

    @classmethod
    def from_config(cls, config: dict) -> "AKTModel":
        """Create model from configuration dict."""
        return cls(
            num_skills=config["num_skills"],
            d_model=config["d_model"],
            n_heads=config["n_heads"],
            n_layers=config["n_layers"],
            d_ff=config["d_ff"],
            max_seq_len=config["max_seq_len"],
            dropout=config["dropout"],
        )

