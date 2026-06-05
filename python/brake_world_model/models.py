from __future__ import annotations

import torch
from torch import nn


class SequenceWorldModel(nn.Module):
    def __init__(
        self,
        input_size: int = 4,
        hidden_size: int = 64,
        output_size: int = 2,
        num_layers: int = 1,
        dropout: float = 0.0,
        recurrent: str = "lstm",
    ):
        super().__init__()
        recurrent = recurrent.lower()
        rnn_cls = {"lstm": nn.LSTM, "gru": nn.GRU}.get(recurrent)
        if rnn_cls is None:
            raise ValueError("recurrent must be 'lstm' or 'gru'")

        self.recurrent = recurrent
        self.rnn = rnn_cls(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.rnn(x)
        return self.head(out[:, -1, :])

