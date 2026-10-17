"""Pinned local ONNX MiniLM encoder. No runtime downloads or remote embedding API."""

import json
from pathlib import Path

import numpy as np

from relaydesk_api.common import digest, file_hash

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FILES = ("model.onnx", "tokenizer.json")


def validate_vector(value):
    array = np.asarray(value, dtype=np.float32)
    if (
        array.shape != (384,)
        or not np.isfinite(array).all()
        or not np.isclose(np.linalg.norm(array), 1, atol=0.002)
    ):
        raise ValueError("Invalid normalized 384-dimensional vector")
    return array


class Encoder:
    def __init__(self, directory="var/models/relaydesk-minilm"):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        root = Path(directory)
        manifest = json.loads((root / "manifest.json").read_text())
        if (
            manifest["repository"] != MODEL
            or set(manifest["files"]) != set(FILES)
            or manifest["dimension"] != 384
        ):
            raise ValueError("Unsupported embedding manifest")
        for filename, expected in manifest["files"].items():
            if file_hash(root / filename) != expected:
                raise ValueError("Model artifact hash mismatch")
        self.manifest = manifest
        self.fingerprint = digest(manifest)
        self.tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
        self.tokenizer.no_truncation()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(root / "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.inputs = {i.name for i in self.session.get_inputs()}

    def chunks(self, text):
        encoded = self.tokenizer.encode(text, add_special_tokens=False)
        offsets = encoded.offsets
        if not offsets:
            return [(0, len(text), text)]
        result = []
        for i in range(0, len(offsets), 220):
            start = 0 if i == 0 else offsets[i][0]
            end = len(text) if i + 220 >= len(offsets) else offsets[i + 220][0]
            result.append((start, end, text[start:end]))
        return result

    def encode(self, texts):
        output = []
        for offset in range(0, len(texts), 16):
            group = texts[offset : offset + 16]
            encoded = [self.tokenizer.encode(text) for text in group]
            if any(len(e.ids) > 256 for e in encoded):
                raise ValueError("Chunk exceeds model token allowance")
            width = max(len(e.ids) for e in encoded)
            ids = np.zeros((len(group), width), dtype=np.int64)
            mask = np.zeros_like(ids)
            types = np.zeros_like(ids)
            for i, e in enumerate(encoded):
                ids[i, : len(e.ids)] = e.ids
                mask[i, : len(e.ids)] = e.attention_mask
                types[i, : len(e.ids)] = e.type_ids
            feeds = {
                k: v
                for k, v in {
                    "input_ids": ids,
                    "attention_mask": mask,
                    "token_type_ids": types,
                }.items()
                if k in self.inputs
            }
            hidden = self.session.run(None, feeds)[0]
            if hidden.ndim != 3:
                raise ValueError("Unexpected encoder output")
            vectors = (hidden * mask[:, :, None]).sum(axis=1) / mask.sum(axis=1)[:, None]
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            if (norms == 0).any():
                raise ValueError("Zero embedding")
            output.extend(validate_vector(v) for v in vectors / norms)
        return output

    def query(self, text):
        chunks = self.chunks(text)
        values = self.encode([c[2] for c in chunks])
        vector = np.mean(values, axis=0)
        return validate_vector(vector / np.linalg.norm(vector))
