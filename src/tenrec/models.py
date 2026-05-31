import torch
from torch import nn


def append_numeric_features(parts: list[torch.Tensor], numeric_features: torch.Tensor | None) -> list[torch.Tensor]:
    if numeric_features is not None:
        parts.append(numeric_features)
    return parts


class FieldWiseLogisticRegression(nn.Module):
    """True categorical LR: one scalar lookup per field value plus a global bias."""

    def __init__(
        self,
        vocab_sizes: dict[str, int],
        feature_columns: list[str],
        numeric_features: list[str] | None = None,
    ):
        super().__init__()
        self.feature_columns = list(feature_columns)
        self.numeric_features = list(numeric_features or [])
        self.uses_numeric_features = bool(self.numeric_features)
        self.weights = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], 1)
                for column in self.feature_columns
            }
        )
        self.numeric_weights = (
            nn.Linear(len(self.numeric_features), 1, bias=False)
            if self.numeric_features
            else None
        )
        self.bias = nn.Parameter(torch.zeros(1))
        self.reset_parameters()

    def reset_parameters(self):
        for embedding in self.weights.values():
            nn.init.zeros_(embedding.weight)
        if self.numeric_weights is not None:
            nn.init.zeros_(self.numeric_weights.weight)

    def forward(
        self,
        features: dict[str, torch.Tensor],
        numeric_features: torch.Tensor | None = None,
    ) -> torch.Tensor:
        logits = self.bias.expand_as(features[self.feature_columns[0]].float())
        for column in self.feature_columns:
            logits = logits + self.weights[column](features[column]).squeeze(-1)
        if self.numeric_weights is not None:
            if numeric_features is None:
                raise ValueError("LR requires numeric_features")
            logits = logits + self.numeric_weights(numeric_features).squeeze(-1)
        return logits


class CtrMLP(nn.Module):
    def __init__(
        self,
        vocab_sizes: dict[str, int],
        feature_columns: list[str],
        embedding_dim: int,
        hidden_dims: list[int],
        dropout: float = 0.0,
        numeric_features: list[str] | None = None,
    ):
        super().__init__()
        self.feature_columns = list(feature_columns)
        self.numeric_features = list(numeric_features or [])
        self.uses_numeric_features = bool(self.numeric_features)
        self.embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], embedding_dim)
                for column in self.feature_columns
            }
        )
        layers = []
        input_dim = embedding_dim * len(self.feature_columns) + len(self.numeric_features)
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            input_dim = hidden_dim
        layers.append(nn.Linear(input_dim, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(
        self,
        features: dict[str, torch.Tensor],
        numeric_features: torch.Tensor | None = None,
    ) -> torch.Tensor:
        embeddings = [self.embeddings[column](features[column]) for column in self.feature_columns]
        if self.numeric_features and numeric_features is None:
            raise ValueError("MLP requires numeric_features")
        x = torch.cat(append_numeric_features(embeddings, numeric_features), dim=1)
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
        numeric_features: list[str] | None = None,
    ):
        super().__init__()
        self.feature_columns = list(feature_columns)
        self.numeric_features = list(numeric_features or [])
        self.uses_numeric_features = bool(self.numeric_features)
        self.embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], embedding_dim)
                for column in self.feature_columns
            }
        )
        input_dim = embedding_dim * len(self.feature_columns) + len(self.numeric_features)
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

    def forward(
        self,
        features: dict[str, torch.Tensor],
        numeric_features: torch.Tensor | None = None,
    ) -> torch.Tensor:
        embeddings = [self.embeddings[column](features[column]) for column in self.feature_columns]
        if self.numeric_features and numeric_features is None:
            raise ValueError("DCN-v2 requires numeric_features")
        x0 = torch.cat(append_numeric_features(embeddings, numeric_features), dim=1)
        cross = x0
        for layer in self.cross_layers:
            cross = layer(x0, cross)
        deep = self.deep(x0)
        combined = torch.cat([cross, deep], dim=1)
        return self.output(combined).squeeze(-1)


class Din(nn.Module):
    requires_sequence_features = True

    def __init__(
        self,
        vocab_sizes: dict[str, int],
        feature_columns: list[str],
        embedding_dim: int,
        attention_hidden_dims: list[int],
        deep_hidden_dims: list[int],
        dropout: float = 0.0,
        output_bias_init: float = 0.0,
        padding_index: int = 1,
        hist_mode: str = "attention",
        numeric_features: list[str] | None = None,
    ):
        super().__init__()
        if hist_mode not in ("attention", "meanpool", "none"):
            raise ValueError(
                f"DIN hist_mode must be attention/meanpool/none, got {hist_mode!r}"
            )
        self.feature_columns = list(feature_columns)
        self.numeric_features = list(numeric_features or [])
        self.uses_numeric_features = bool(self.numeric_features)
        self.embedding_dim = int(embedding_dim)
        self.padding_index = int(padding_index)
        self.hist_mode = str(hist_mode)
        self.target_embedding = nn.Embedding(vocab_sizes["item_id"], embedding_dim)
        self.hist_embedding = self.target_embedding
        self.profile_columns = [
            column for column in self.feature_columns if column != "item_id"
        ]
        self.profile_embeddings = nn.ModuleDict(
            {
                column: nn.Embedding(vocab_sizes[column], embedding_dim)
                for column in self.profile_columns
            }
        )
        self.attention_mlp = make_mlp(
            input_dim=embedding_dim * 4,
            hidden_dims=attention_hidden_dims,
            dropout=dropout,
            output_dim=1,
        )
        has_interest = self.hist_mode != "none"
        deep_input_dim = embedding_dim * ((2 if has_interest else 1) + len(self.profile_columns)) + len(self.numeric_features)
        self.deep = make_mlp(
            input_dim=deep_input_dim,
            hidden_dims=deep_hidden_dims,
            dropout=dropout,
            output_dim=1,
        )
        self.output_bias_init = float(output_bias_init)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.normal_(self.target_embedding.weight, mean=0.0, std=0.01)
        for embedding in self.profile_embeddings.values():
            nn.init.normal_(embedding.weight, mean=0.0, std=0.01)
        for module in list(self.attention_mlp) + list(self.deep):
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
        final_layer = self.deep[-1]
        if isinstance(final_layer, nn.Linear):
            nn.init.constant_(final_layer.bias, self.output_bias_init)

    def _hist_item_tensor(self, sequence_features: dict[str, torch.Tensor]) -> torch.Tensor:
        if "hist_item" not in sequence_features:
            raise ValueError("DIN requires sequence_features['hist_item']")
        return sequence_features["hist_item"]

    def attention_weights(
        self,
        features: dict[str, torch.Tensor],
        sequence_features: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        hist_items = self._hist_item_tensor(sequence_features)
        target_emb = self.target_embedding(features["item_id"])
        hist_emb = self.hist_embedding(hist_items)
        target_expanded = target_emb.unsqueeze(1).expand_as(hist_emb)
        attention_input = torch.cat(
            [
                target_expanded,
                hist_emb,
                target_expanded * hist_emb,
                target_expanded - hist_emb,
            ],
            dim=-1,
        )
        raw_weights = self.attention_mlp(attention_input).squeeze(-1)
        non_padding = hist_items.ne(self.padding_index).to(raw_weights.dtype)
        return raw_weights * non_padding

    def user_interest_vector(
        self,
        features: dict[str, torch.Tensor],
        sequence_features: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        hist_items = self._hist_item_tensor(sequence_features)
        hist_emb = self.hist_embedding(hist_items)
        if self.hist_mode == "meanpool":
            non_padding = hist_items.ne(self.padding_index).to(hist_emb.dtype).unsqueeze(-1)
            summed = torch.sum(hist_emb * non_padding, dim=1)
            count = non_padding.sum(dim=1).clamp(min=1.0)
            return summed / count
        weights = self.attention_weights(features, sequence_features)
        return torch.sum(weights.unsqueeze(-1) * hist_emb, dim=1)

    def logit_from_user_interest(
        self,
        features: dict[str, torch.Tensor],
        user_interest: torch.Tensor | None,
        numeric_features: torch.Tensor | None = None,
    ) -> torch.Tensor:
        target_emb = self.target_embedding(features["item_id"])
        profile_embs = [
            self.profile_embeddings[column](features[column])
            for column in self.profile_columns
        ]
        interest_parts = [user_interest] if user_interest is not None else []
        x = torch.cat(
            append_numeric_features(interest_parts + [target_emb] + profile_embs, numeric_features),
            dim=1,
        )
        return self.deep(x).squeeze(-1)

    def forward(
        self,
        features: dict[str, torch.Tensor],
        sequence_features: dict[str, torch.Tensor] | None = None,
        numeric_features: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if sequence_features is None:
            raise ValueError("DIN forward requires sequence_features")
        if self.uses_numeric_features and numeric_features is None:
            raise ValueError("DIN requires numeric_features")
        if self.hist_mode == "none":
            user_interest = None
        else:
            user_interest = self.user_interest_vector(features, sequence_features)
        return self.logit_from_user_interest(features, user_interest, numeric_features)


def build_model(
    model_config: dict,
    vocab_sizes: dict[str, int],
    feature_columns: list[str],
    numeric_features: list[str] | None = None,
) -> nn.Module:
    model_name = model_config["name"]
    if model_name == "lr":
        return FieldWiseLogisticRegression(
            vocab_sizes=vocab_sizes,
            feature_columns=feature_columns,
            numeric_features=numeric_features,
        )
    if model_name == "mlp":
        return CtrMLP(
            vocab_sizes=vocab_sizes,
            feature_columns=feature_columns,
            embedding_dim=int(model_config["mlp"]["embedding_dim"]),
            hidden_dims=[int(value) for value in model_config["mlp"]["hidden_dims"]],
            dropout=float(model_config["mlp"].get("dropout", 0.0)),
            numeric_features=numeric_features,
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
            numeric_features=numeric_features,
        )
    if model_name == "din":
        return Din(
            vocab_sizes=vocab_sizes,
            feature_columns=feature_columns,
            embedding_dim=int(model_config["din"]["embedding_dim"]),
            attention_hidden_dims=[
                int(value) for value in model_config["din"]["attention_hidden_dims"]
            ],
            deep_hidden_dims=[int(value) for value in model_config["din"]["deep_hidden_dims"]],
            dropout=float(model_config["din"].get("dropout", 0.0)),
            output_bias_init=float(model_config["din"].get("output_bias_init", 0.0)),
            padding_index=int(model_config["din"].get("padding_index", 1)),
            hist_mode=str(model_config["din"].get("hist_mode", "attention")),
            numeric_features=numeric_features,
        )
    raise ValueError(f"Unsupported model name: {model_name}")
