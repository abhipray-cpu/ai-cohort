"""Explicit trusted CPU encoder provisioning; no remote model code is executed."""

import argparse
import json
import shutil
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from relaydesk_api.common import file_hash, now
from relaydesk_api.embeddings import MODEL, Encoder


def provision(destination):
    root = Path(destination)
    if root.exists():
        raise ValueError("Use a new model directory; never overwrite a pin")
    revision = HfApi().model_info(MODEL).sha
    root.mkdir(parents=True)
    for remote, filename in [
        ("onnx/model.onnx", "model.onnx"),
        ("tokenizer.json", "tokenizer.json"),
    ]:
        path = hf_hub_download(MODEL, remote, revision=revision)
        shutil.copyfile(path, root / filename)
    manifest = {
        "repository": MODEL,
        "revision": revision,
        "dimension": 384,
        "precision": "float32",
        "pooling": "attention-mask mean then L2 normalization",
        "chunk_tokens": 220,
        "created_at": now(),
        "files": {name: file_hash(root / name) for name in ["model.onnx", "tokenizer.json"]},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    encoder = Encoder(root)
    encoder.encode(["Technical investigation memory."])
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", default="var/models/relaydesk-minilm")
    provision(parser.parse_args().destination)
