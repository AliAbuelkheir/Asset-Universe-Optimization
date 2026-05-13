"""End-to-end demo: load sample_input_raw_ohlcv.json -> predict -> print weights.

Run from the deployment/ folder:

    python examples/run_example.py

Expected: prints a table of asset -> weight (5 entries), summing to ~1.0.
The exact weights are saved to examples/expected_output.json on first run,
then verified against on subsequent runs.
"""

import json
import sys
from pathlib import Path

# Make egtportfolio importable when run from deployment/
DEPLOYMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOYMENT_ROOT))

from egtportfolio import load_model, predict, request_from_dict


def main():
    sample_path = Path(__file__).parent / 'sample_input_raw_ohlcv.json'
    expected_path = Path(__file__).parent / 'expected_output.json'

    with open(sample_path) as f:
        request_dict = json.load(f)
    # Strip the documentation '_notes' field if present
    request_dict.pop('_notes', None)

    request = request_from_dict(request_dict)
    print(f"Loaded request: tier={request.tier}, target={request.target_month}, "
          f"n_assets={len(request.asset_data)}")

    bundle = load_model(tier=request.tier, n_assets=len(request.asset_data))
    print(f"Loaded {request.tier} set-based model (max_weight={bundle.max_weight}, "
          f"min_weight={bundle.min_weight}, dirichlet_prior={bundle.dirichlet_prior})")

    response = predict(request, model_bundle=bundle)
    print(f"\nDecision date: {response.decision_date}")
    print(f"Target month:  {response.target_month}")
    print(f"Sum check:     {response.sum_check:.6f}\n")
    print(f"  {'Asset':<25s} {'Weight':>8s}")
    print(f"  {'-' * 35}")
    for w in response.asset_weights:
        bar = '#' * int(w.weight * 30)
        print(f"  {w.asset:<25s} {w.weight:>7.1%}  {bar}")

    # Save expected output for regression testing
    if not expected_path.exists():
        expected_path.write_text(json.dumps(response.to_dict(), indent=2))
        print(f"\nSaved expected output -> {expected_path}")
    else:
        # Compare on subsequent runs
        with open(expected_path) as f:
            expected = json.load(f)
        deltas = []
        for actual, exp in zip(
            sorted(response.asset_weights, key=lambda x: x.asset),
            sorted(expected['asset_weights'], key=lambda x: x['asset']),
        ):
            d = abs(actual.weight - exp['weight'])
            deltas.append(d)
        max_delta = max(deltas)
        print(f"\nMax weight delta vs expected: {max_delta:.2e}")
        if max_delta > 1e-3:
            print("  WARNING: output deviated from expected by more than 1e-3")
        else:
            print("  OK — reproducible within 1e-3 tolerance")


if __name__ == '__main__':
    main()
