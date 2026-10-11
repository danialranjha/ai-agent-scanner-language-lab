"""Offline pinned-classifier coverage and feature-attribution assay."""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace
from vendor.mcp_scrutiny.features import FEATURE_NAMES, extract_features, vectorise
from vendor.mcp_scrutiny.model import LogisticModel

ROOT = Path(__file__).resolve().parent
FRENCH_MARKER = re.compile(r"\bignorez (?:toutes )?les instructions (?:précédentes|precedentes|ci-dessus)\b", re.I)
METHODS = ("original", "french_marker_extension")

def verify_source():
    source = json.loads((ROOT / "artifacts/source.json").read_text())
    for item in source["files"]:
        data = (ROOT / item["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == item["git_blob"]
    return source

def load_model():
    model = LogisticModel.load(ROOT / "vendor/mcp_scrutiny/data/model.json")
    assert model.features == list(FEATURE_NAMES)
    assert len(model.features) == len(model.weights) == len(model.mean) == len(model.std) == 31
    return model

def measure(fixture, method, model):
    text = fixture["text"]
    tool = SimpleNamespace(name="fixture", description=text, input_schema={}, annotations={})
    features = extract_features(tool)
    baseline = dict(features)
    matches = [{"text": m.group(), "start": m.start(), "end": m.end()} for m in FRENCH_MARKER.finditer(text)]
    if method == "french_marker_extension":
        features["injection_markers"] += len(matches)
    elif method != "original":
        raise ValueError(method)
    vector = vectorise(features)
    score = model.predict_proba(vector)
    return {
        "id": fixture["id"], "role": fixture["role"], "language": fixture["language"],
        "text": text, "method": method, "features": features,
        "changed_features": [k for k in FEATURE_NAMES if features[k] != baseline[k]],
        "extension_matches": matches if method != "original" else [],
        "logit": model.decision(vector), "score": score,
        "threshold": model.threshold, "flagged": score >= model.threshold,
    }

def run():
    source = verify_source()
    model = load_model()
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    rows = [measure(f, method, model) for f in fixtures for method in METHODS]
    return {
        "scope": "Fixed harmless texts scored by a real logistic classifier. No LLM, tool execution, network, retraining or measured attack success.",
        "source_commit": source["commit"], "fixtures": len(fixtures), "observations": len(rows),
        "methods": list(METHODS), "rows": rows,
    }

def evidence(result):
    lines = ["# Exact classifier evidence", "", "Fixed fixture results; classifier verdicts only. No language model or tool ran.",
             "The diagnostic extension adds a French marker count with all other input features and all model parameters held fixed.",
             "Scores are model outputs, not calibrated attack probabilities. No sampling, uncertainty or population rate is implied.", "",
             "| Fixture | Role | Original markers | Original score / flag | Extended markers | Extended score / flag |",
             "|---|---|---:|---|---:|---|"]
    for a,b in zip(result["rows"][::2], result["rows"][1::2]):
        lines.append(f'| {a["id"]} | {a["role"]} | {a["features"]["injection_markers"]:g} | {a["score"]:.6f} / {a["flagged"]} | {b["features"]["injection_markers"]:g} | {b["score"]:.6f} / {b["flagged"]} |')
    lines += ["", f'{result["fixtures"]} chosen descriptions × 2 methods = {result["observations"]} records.',
              "The quoted example is benign by fixture design, so flagging it is a false positive in this tiny set.",
              "The paraphrase and Spanish examples show what this one-pattern extension leaves uncovered.",
              "Full text, all 31 features, changed feature names, exact scores and matching spans: [run.json](run.json)."]
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    result = run()
    (ROOT / "artifacts/run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "artifacts/evidence.md").write_text(evidence(result))
    for a,b in zip(result["rows"][::2], result["rows"][1::2]):
        print(a["id"], f'{a["score"]:.6f} -> {b["score"]:.6f}', a["flagged"], b["flagged"])
