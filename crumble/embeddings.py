# SPDX-License-Identifier: Apache-2.0
"""Versioned embedding providers. Demo descriptors are not a fashion AI model."""

import importlib.metadata
import threading

import numpy as np
from PIL import Image

from .util import digest

FASHION_REPO = "Marqo/marqo-fashionSigLIP"
FASHION_REVISION = "c56244cc94f92419e8369fa71efdaf403b124ce8"


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    if v.ndim != 2 or not np.isfinite(v).all():
        raise ValueError("Encoder returned invalid vectors")
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    if (norms <= 1e-12).any():
        raise ValueError("Encoder returned a zero vector")
    return v / norms


class Encoder:
    def __init__(self, name="demo", device="cpu"):
        if name not in ("demo", "fashion"):
            raise ValueError("Encoder must be demo or fashion")
        self.name, self.device = name, device
        self.dim = 192 if name == "demo" else 768
        self.spec = {"provider": name, "implementation": "crumble-embedding/1", "dim": self.dim}
        if name == "fashion":
            self.spec.update(
                repo=FASHION_REPO,
                revision=FASHION_REVISION,
                open_clip=importlib.metadata.version("open_clip_torch"),
            )
        self.id = digest(self.spec)
        self.lock = threading.RLock()
        self.model = None

    def load(self):
        if self.name == "demo" or self.model is not None:
            return
        import open_clip
        import torch
        from huggingface_hub import snapshot_download

        folder = snapshot_download(
            FASHION_REPO,
            revision=FASHION_REVISION,
            allow_patterns=[
                "open_clip_config.json",
                "open_clip_model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
            ],
        )
        torch.set_num_threads(4)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "local-dir:" + folder, device=self.device, precision="fp32", weights_only=True
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer("local-dir:" + folder)

    def images(self, images):
        with self.lock:
            self.load()
            if not images:
                return np.empty((0, self.dim), np.float32)
            if self.name == "demo":
                vectors = [
                    np.asarray(
                        im.convert("RGB").resize((8, 8), Image.Resampling.LANCZOS), dtype=np.float32
                    ).reshape(-1)
                    / 255
                    for im in images
                ]
                return unit(vectors)
            import torch

            batch = torch.stack([self.preprocess(im) for im in images]).to(self.device)
            with torch.inference_mode():
                v = self.model.encode_image(batch, normalize=True).float().cpu().numpy()
            return unit(v)

    def texts(self, texts):
        if self.name != "fashion":
            raise ValueError("Text and visual-part inference require --encoder fashion")
        with self.lock:
            self.load()
            import torch

            with torch.inference_mode():
                v = (
                    self.model.encode_text(self.tokenizer(texts).to(self.device), normalize=True)
                    .float()
                    .cpu()
                    .numpy()
                )
            return unit(v)

    def parts(self, image):
        """Zero-shot proposals. Margins are ranking heuristics, not probabilities."""
        prompts = {
            "neckline": ["square neck", "v neck", "crew neck", "halter neck", "off shoulder"],
            "sleeve_length": ["sleeveless", "short sleeves", "long sleeves", "three quarter sleeves"],
            "sleeve_shape": ["plain sleeves", "puff sleeves", "bell sleeves", "balloon sleeves"],
            "pattern": ["plain solid", "floral print", "stripes", "polka dots", "gingham"],
        }
        image_v = self.images([image])[0]
        fields = {}
        for key, values in prompts.items():
            t = self.texts(["a garment with " + v for v in values])
            scores = t @ image_v
            order = np.argsort(-scores)
            best, other = (int(x) for x in order[:2])
            margin = float(scores[best] - scores[other])
            fields[key] = {
                "state": "inferred" if margin >= 0.025 else "unknown",
                "values": [values[best]] if margin >= 0.025 else [],
                "source": self.id,
                "note": "Uncalibrated visual proposal; check the selected garment.",
                "margin": margin,
            }
        return fields
