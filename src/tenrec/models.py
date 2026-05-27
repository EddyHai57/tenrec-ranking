import torch
from torch import nn


class FieldWiseLogisticRegression(nn.Module):
    """True categorical LR: one scalar lookup per field value plus a global bias."""

    def __init__(self, vocab_sizes: dict[str, int], feature_columns: list[str]):
        super().__init__()
        self.feature_columns = list(feature_columns)
        self.weights = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], 1)
                for column in self.feature_columns
            }
        )
        self.bias = nn.Parameter(torch.zeros(1))
        self.reset_parameters()

    def reset_parameters(self):
        for embedding in self.weights.values():
            nn.init.zeros_(embedding.weight)

    def forward(self, features: dict[str, torch.Tensor]) -> torch.Tensor:
        logits = self.bias.expand_as(features[self.feature_columns[0]].float())
        for column in self.feature_columns:
            logits = logits + self.weights[column](features[column]).squeeze(-1)
        return logits


class CtrMLP(nn.Module):
    def __init__(
        self,
        vocab_sizes: dict[str, int],
        feature_columns: list[str],
        embedding_dim: int,
        hidden_dims: list[int],
        dropout: float = 0.0,
    ):
        super().__init__()
        self.feature_columns = list(feature_columns)
        self.embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], embedding_dim)
                for column in self.feature_columns
            }
        )
        layers = []
        input_dim = embedding_dim * len(self.feature_columns)
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            input_dim = hidden_dim
        layers.append(nn.Linear(input_dim, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, features: dict[str, torch.Tensor]) -> torch.Tensor:
        embeddings = [self.embeddings[column](features[column]) for column in self.feature_columns]
        x = torch.cat(embeddings, dim=1)
        return self.mlp(x).squeeze(-1)


def build_model(model_config: dict, vocab_sizes: dict[str, int], feature_columns: list[str]) -> nn.Module:
    model_name = model_config["name"]
    if model_name == "lr":
        return FieldWiseLogisticRegression(vocab_sizes=vocab_sizes, feature_columns=feature_columns)
    if model_name == "mlp":
        return CtrMLP(
            vocab_sizes=vocab_sizes,
            feature_columns=feature_columns,
            embedding_dim=int(model_config["mlp"]["embedding_dim"]),
            hidden_dims=[int(value) for value in model_config["mlp"]["hidden_dims"]],
            dropout=float(model_config["mlp"].get("dropout", 0.0)),
        )
    raise ValueError(f"Unsupported model name: {model_name}")
