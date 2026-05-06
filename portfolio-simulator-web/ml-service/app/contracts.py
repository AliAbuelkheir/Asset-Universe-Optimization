from __future__ import annotations

RISK_TOLERANCE_MODEL_CONTRACT = [
    "Model artifact file format and loader code.",
    "Python and package versions required for inference.",
    "Exact questionnaire input feature names, types, ranges, and missing-value rules.",
    "Output schema: risk score, class label, and probabilities if available.",
    "Mapping from model output to low, medium, and high risk levels.",
    "One sample input JSON and expected output JSON.",
]

WEIGHT_OPTIMIZER_MODEL_CONTRACT = [
    "Model artifact file or files and loader code.",
    "Python and package versions required for inference.",
    "Required input schema: selected assets, month context, historical returns, risk group, and constraints.",
    "Whether the model expects raw features, asset IDs, returns history, or tensors.",
    "Output weight schema and whether weights are ordered by asset ID or input order.",
    "Cash, shorting, min weight, max weight, and leverage constraints.",
    "Rebalance assumption and forward holding-period assumption.",
    "One sample input JSON or CSV and expected output JSON or CSV.",
]

