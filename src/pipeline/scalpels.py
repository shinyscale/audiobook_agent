"""
Unified loader for DeBERTa-v3-small scalpel models.

Four fine-tuned classification models replace specific LLM calls:
- Compass: moral valence (5 classes)
- Beacon: narrator/POV (4 classes)
- Cluster: alias grouping (2 classes)
- Echo: character active vs mentioned (2 classes)

All share identical architecture: DeBERTa encoder → mean pooling → dropout → linear → class_bias.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Registry of all scalpel models with their configurations
SCALPEL_REGISTRY = {
    "compass": {
        "num_classes": 5,
        "max_length": 512,
        "base_model": "microsoft/deberta-v3-small",
        "labels": {
            0: "protagonist",
            1: "antagonist",
            2: "morally_ambiguous",
            3: "victim",
            4: "neutral",
        },
    },
    "beacon": {
        "num_classes": 4,
        "max_length": 512,
        "base_model": "microsoft/deberta-v3-small",
        "head": "mlp",
        "labels": {
            0: "first_person",
            1: "third_person",
            2: "third_person_omniscient",
            3: "epistolary",
        },
    },
    "cluster": {
        "num_classes": 2,
        "max_length": 256,
        "base_model": "microsoft/deberta-v3-small",
        "labels": {0: "different_person", 1: "same_person"},
    },
    "echo": {
        "num_classes": 2,
        "max_length": 256,
        "base_model": "microsoft/deberta-v3-small",
        "labels": {0: "mentioned", 1: "active"},
    },
    "voice": {
        "num_classes": 2,
        "max_length": 512,
        "base_model": "microsoft/deberta-v3-base",
        "pooling": "attention",
        "labels": {0: "non_speaker", 1: "speaker"},
    },
    "scope": {
        "num_classes": 5,
        "max_length": 512,
        "base_model": "microsoft/deberta-v3-small",
        "labels": {
            0: "single_narrator",       # Non-nested: one narrator throughout
            1: "frame_narrator",        # Outer/frame narrator (e.g., Walton, Lockwood)
            2: "inner_narrator",        # Primary inner narrator (e.g., Victor, Nelly Dean)
            3: "deep_narrator",         # Deeply embedded narrator (e.g., Creature)
            4: "omniscient_interlude",  # Third-person omniscient section in mixed narrative
        },
    },
}

# Models directory relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = _PROJECT_ROOT / "models"


def _torch_available() -> bool:
    """Check if torch and transformers are installed."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401

        return True
    except ImportError:
        return False


def scalpel_available(name: str) -> bool:
    """Check if a scalpel model is available (torch installed + model file exists)."""
    if name not in SCALPEL_REGISTRY:
        return False
    if not _torch_available():
        return False
    model_path = MODELS_DIR / f"{name}_model" / f"{name}_model.pt"
    return model_path.exists()


class ScalpelModel:
    """
    DeBERTa-v3-small encoder + classification head.

    Architecture matches train.py exactly:
        encoder(input_ids, attention_mask) → last_hidden_state
        → mean pooling (with attention mask)
        → dropout(0.1)
        → linear(hidden_size, num_classes)
        → + class_bias
        → argmax
    """

    def __init__(self, name: str, device: str = "cpu"):
        import torch
        import torch.nn as nn
        from transformers import AutoModel, AutoTokenizer

        if name not in SCALPEL_REGISTRY:
            raise ValueError(f"Unknown scalpel model: {name}. Available: {list(SCALPEL_REGISTRY.keys())}")

        config = SCALPEL_REGISTRY[name]
        model_path = MODELS_DIR / f"{name}_model" / f"{name}_model.pt"

        if not model_path.exists():
            raise FileNotFoundError(f"Scalpel model not found: {model_path}")

        self.name = name
        self.device = device
        self.num_classes = config["num_classes"]
        self.max_length = config["max_length"]
        self.labels = config["labels"]

        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)

        # Base model name from registry (default: deberta-v3-small)
        base_model = config.get("base_model", "microsoft/deberta-v3-small")

        # Use bundled tokenizer files from the model directory (avoids HuggingFace download)
        model_dir = MODELS_DIR / f"{name}_model"
        tokenizer_json = model_dir / "tokenizer.json"
        if tokenizer_json.exists():
            self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(base_model)

        # Initialize encoder architecture, then load weights from checkpoint
        from transformers import AutoConfig
        encoder_config = AutoConfig.from_pretrained(base_model)
        self.encoder = AutoModel.from_config(encoder_config)
        hidden_size = encoder_config.hidden_size

        # Pooling type (default: mean)
        self.pooling_type = config.get("pooling", "mean")

        # Classification head
        self.dropout = nn.Dropout(0.1)
        if self.pooling_type == "attention":
            self.pool_attn = nn.Linear(hidden_size, 1)

        self.head_type = config.get("head", "linear")
        if self.head_type == "mlp":
            # 2-layer MLP head: hidden_size -> hidden_size//4 -> num_classes (GELU)
            self.hidden = nn.Linear(hidden_size, hidden_size // 4)
            self.classifier = nn.Linear(hidden_size // 4, self.num_classes)
        else:
            self.classifier = nn.Linear(hidden_size, self.num_classes)
        self.class_bias = nn.Parameter(torch.zeros(self.num_classes))

        # Load weights from checkpoint state dict
        # Keys: class_bias, encoder.*, classifier.weight, classifier.bias
        encoder_state = {}
        classifier_state = {}
        pool_attn_state = {}
        hidden_state = {}
        class_bias = None

        for key, value in checkpoint["model_state_dict"].items():
            if key.startswith("encoder."):
                encoder_state[key[len("encoder."):]] = value
            elif key.startswith("classifier."):
                classifier_state[key[len("classifier."):]] = value
            elif key.startswith("pool_attn."):
                pool_attn_state[key[len("pool_attn."):]] = value
            elif key.startswith("hidden."):
                hidden_state[key[len("hidden."):]] = value
            elif key == "class_bias":
                class_bias = value

        self.encoder.load_state_dict(encoder_state)
        self.classifier.load_state_dict(classifier_state)
        if self.pooling_type == "attention" and pool_attn_state:
            self.pool_attn.load_state_dict(pool_attn_state)
        if self.head_type == "mlp" and hidden_state:
            self.hidden.load_state_dict(hidden_state)
        # Prefer top-level class_bias (bfloat16 trained value), fall back to state_dict
        if checkpoint.get("class_bias") is not None:
            self.class_bias.data = checkpoint["class_bias"].float()
        elif class_bias is not None:
            self.class_bias.data = class_bias.float()

        # Move to device and set eval mode
        self.encoder.to(device).eval()
        self.classifier.to(device).eval()
        if self.pooling_type == "attention":
            self.pool_attn.to(device).eval()
        if self.head_type == "mlp":
            self.hidden.to(device).eval()
        self.class_bias = self.class_bias.to(device)

        logger.info(f"Loaded scalpel model '{name}' ({self.num_classes} classes, max_length={self.max_length})")

    def predict(self, text: str) -> tuple[str, float]:
        """
        Predict class for a single text input.

        Args:
            text: Input text (will be truncated to max_length tokens)

        Returns:
            (label, confidence) tuple
        """
        import torch

        inputs = self.tokenizer(
            text,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.encoder(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
            )
            hidden = outputs.last_hidden_state

            if self.pooling_type == "attention":
                # Attention pooling: learned weighted sum over tokens
                scores = self.pool_attn(hidden).squeeze(-1)  # [B, L]
                scores = scores.masked_fill(inputs["attention_mask"] == 0, float("-inf"))
                weights = torch.softmax(scores, dim=-1)  # [B, L]
                pooled = (weights.unsqueeze(-1) * hidden).sum(dim=1)  # [B, H]
            else:
                # Mean pooling over non-padding tokens
                mask = inputs["attention_mask"].unsqueeze(-1).float()
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)

            # Classification head
            pooled = self.dropout(pooled)
            if self.head_type == "mlp":
                import torch.nn.functional as F
                hidden = F.gelu(self.hidden(pooled))
                hidden = self.dropout(hidden)
                logits = self.classifier(hidden) + self.class_bias
            else:
                logits = self.classifier(pooled) + self.class_bias

            probs = torch.softmax(logits, dim=-1)
            pred_idx = probs.argmax(dim=-1).item()
            confidence = probs[0, pred_idx].item()

        return self.labels[pred_idx], confidence

    def predict_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        """
        Predict classes for a batch of texts.

        Args:
            texts: List of input texts

        Returns:
            List of (label, confidence) tuples
        """
        import torch

        if not texts:
            return []

        inputs = self.tokenizer(
            texts,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.encoder(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
            )
            hidden = outputs.last_hidden_state

            if self.pooling_type == "attention":
                scores = self.pool_attn(hidden).squeeze(-1)
                scores = scores.masked_fill(inputs["attention_mask"] == 0, float("-inf"))
                weights = torch.softmax(scores, dim=-1)
                pooled = (weights.unsqueeze(-1) * hidden).sum(dim=1)
            else:
                mask = inputs["attention_mask"].unsqueeze(-1).float()
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)

            pooled = self.dropout(pooled)
            if self.head_type == "mlp":
                import torch.nn.functional as F
                hidden = F.gelu(self.hidden(pooled))
                hidden = self.dropout(hidden)
                logits = self.classifier(hidden) + self.class_bias
            else:
                logits = self.classifier(pooled) + self.class_bias

            probs = torch.softmax(logits, dim=-1)
            pred_indices = probs.argmax(dim=-1)
            confidences = probs.gather(1, pred_indices.unsqueeze(1)).squeeze(1)

        results = []
        for i in range(len(texts)):
            label = self.labels[pred_indices[i].item()]
            conf = confidences[i].item()
            results.append((label, conf))

        return results


class ScalpelLoader:
    """
    Singleton lazy-loader for scalpel models.

    Models are loaded on first use and cached for subsequent calls.
    """

    _instance: Optional["ScalpelLoader"] = None
    _models: dict[str, ScalpelModel]

    def __new__(cls) -> "ScalpelLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models = {}
        return cls._instance

    def get(self, name: str) -> ScalpelModel:
        """Get a scalpel model, loading it if necessary."""
        if name not in self._models:
            self._models[name] = ScalpelModel(name)
        return self._models[name]

    def predict(self, name: str, text: str) -> tuple[str, float]:
        """Predict using a named scalpel model."""
        return self.get(name).predict(text)

    def predict_batch(self, name: str, texts: list[str]) -> list[tuple[str, float]]:
        """Batch predict using a named scalpel model."""
        return self.get(name).predict_batch(texts)

    def unload(self, name: str) -> None:
        """Unload a model to free memory."""
        if name in self._models:
            del self._models[name]
            logger.info(f"Unloaded scalpel model '{name}'")

    def unload_all(self) -> None:
        """Unload all models."""
        self._models.clear()
        logger.info("Unloaded all scalpel models")
