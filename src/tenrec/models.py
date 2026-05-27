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


def make_mlp(input_dim: int, hidden_dims: list[int], dropout: float, output_dim: int) -> nn.Sequential:
    layers = []
    current_dim = input_dim
    for hidden_dim in hidden_dims:
        layers.append(nn.Linear(current_dim, hidden_dim))
        layers.append(nn.ReLU())
        if dropout > 0:
            layers.append(nn.Dropout(dropout))
        current_dim = hidden_dim
    layers.append(nn.Linear(current_dim, output_dim))
    return nn.Sequential(*layers)


class DeepFM(nn.Module):
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
        self.linear_embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], 1)
                for column in self.feature_columns
            }
        )
        self.fm_embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], embedding_dim)
                for column in self.feature_columns
            }
        )
        self.bias = nn.Parameter(torch.zeros(1))
        input_dim = embedding_dim * len(self.feature_columns)
        self.deep = make_mlp(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=dropout,
            output_dim=1,
        )
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for embedding in self.linear_embeddings.values():
            nn.init.zeros_(embedding.weight)
        for embedding in self.fm_embeddings.values():
            nn.init.normal_(embedding.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.bias)

    def forward(self, features: dict[str, torch.Tensor]) -> torch.Tensor:
        first_order = self.bias.expand_as(features[self.feature_columns[0]].float())
        shared_embeddings = []
        for column in self.feature_columns:
            first_order = first_order + self.linear_embeddings[column](features[column]).squeeze(-1)
            shared_embeddings.append(self.fm_embeddings[column](features[column]))
        stacked_embeddings = torch.stack(shared_embeddings, dim=1)
        summed_embeddings = torch.sum(stacked_embeddings, dim=1)
        squared_sum = summed_embeddings * summed_embeddings
        sum_squared = torch.sum(stacked_embeddings * stacked_embeddings, dim=1)
        second_order = 0.5 * torch.sum(squared_sum - sum_squared, dim=1)
        deep_input = torch.flatten(stacked_embeddings, start_dim=1)
        deep_logit = self.deep(deep_input).squeeze(-1)
        return first_order + second_order + deep_logit


class DcnV2CrossLayer(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(input_dim, input_dim))
        self.bias = nn.Parameter(torch.zeros(input_dim))
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.normal_(self.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.bias)

    def forward(self, x0: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        projected = torch.matmul(x, self.weight) + self.bias
        return x0 * projected + x


class DcnV2(nn.Module):
    def __init__(
        self,
        vocab_sizes: dict[str, int],
        feature_columns: list[str],
        embedding_dim: int,
        cross_layers: int,
        deep_hidden_dims: list[int],
        dropout: float = 0.0,
        output_bias_init: float = 0.0,
    ):
        super().__init__()
        self.feature_columns = list(feature_columns)
        self.embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], embedding_dim)
                for column in self.feature_columns
            }
        )
        input_dim = embedding_dim * len(self.feature_columns)
        self.cross_layers = nn.ModuleList(
            [DcnV2CrossLayer(input_dim=input_dim) for _ in range(cross_layers)]
        )
        self.deep = make_mlp(
            input_dim=input_dim,
            hidden_dims=deep_hidden_dims,
            dropout=dropout,
            output_dim=deep_hidden_dims[-1] if deep_hidden_dims else input_dim,
        )
        deep_output_dim = deep_hidden_dims[-1] if deep_hidden_dims else input_dim
        self.output = nn.Linear(input_dim + deep_output_dim, 1)
        self.output_bias_init = float(output_bias_init)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for embedding in self.embeddings.values():
            nn.init.normal_(embedding.weight, mean=0.0, std=0.01)
        for layer in self.deep:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)
        nn.init.xavier_uniform_(self.output.weight)
        nn.init.constant_(self.output.bias, self.output_bias_init)

    def forward(self, features: dict[str, torch.Tensor]) -> torch.Tensor:
        embeddings = [self.embeddings[column](features[column]) for column in self.feature_columns]
        x0 = torch.cat(embeddings, dim=1)
        cross = x0
        for layer in self.cross_layers:
            cross = layer(x0, cross)
        deep = self.deep(x0)
        combined = torch.cat([cross, deep], dim=1)
        return self.output(combined).squeeze(-1)


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
    if model_name == "deepfm":
        return DeepFM(
            vocab_sizes=vocab_sizes,
            feature_columns=feature_columns,
            embedding_dim=int(model_config["deepfm"]["embedding_dim"]),
            hidden_dims=[int(value) for value in model_config["deepfm"]["hidden_dims"]],
            dropout=float(model_config["deepfm"].get("dropout", 0.0)),
        )
    if model_name == "dcnv2":
        return DcnV2(
            vocab_sizes=vocab_sizes,
            feature_columns=feature_columns,
            embedding_dim=int(model_config["dcnv2"]["embedding_dim"]),
            cross_layers=int(model_config["dcnv2"]["cross_layers"]),
            deep_hidden_dims=[int(value) for value in model_config["dcnv2"]["deep_hidden_dims"]],
            dropout=float(model_config["dcnv2"].get("dropout", 0.0)),
            output_bias_init=float(model_config["dcnv2"].get("output_bias_init", 0.0)),
        )
    raise ValueError(f"Unsupported model name: {model_name}")
