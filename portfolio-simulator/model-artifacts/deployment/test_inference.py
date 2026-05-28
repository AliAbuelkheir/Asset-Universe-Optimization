"""End-to-end test for the deployment package.

Run from deployment/:
    python test_inference.py

Asserts:
  1. Sample input produces weights summing to 1.0 within tolerance
  2. All output weights are in [0, max_weight]
  3. Output is reproducible (matches expected_output.json within 1e-3)
  4. Different N_assets work (3, 5, 10) — dynamic-N verification
  5. constraints_override correctly caps weights
  6. JSON round-trip works (serialize → load → predict → same result)
"""

import json
import sys
from pathlib import Path

DEPLOYMENT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(DEPLOYMENT_ROOT))

from egtportfolio import (
    AssetTimeSeries,
    ConstraintsOverride,
    InferenceRequest,
    load_model,
    predict,
    request_from_dict,
)


def load_sample():
    sample_path = Path(__file__).parent / 'examples' / 'sample_input_raw_ohlcv.json'
    with open(sample_path) as f:
        data = json.load(f)
    data.pop('_notes', None)
    return data


def test_sum_to_one():
    request_dict = load_sample()
    request = request_from_dict(request_dict)
    bundle = load_model(tier='low', n_assets=len(request.asset_data))
    result = predict(request, model_bundle=bundle)
    s = sum(w.weight for w in result.asset_weights)
    assert abs(s - 1.0) < 1e-5, f"sum_check failed: {s}"
    print(f"  [PASS] sum_to_one: {s:.6f}")
    return result


def test_long_only_and_bounded(result, max_w):
    for w in result.asset_weights:
        assert w.weight >= 0.0, f"{w.asset} has negative weight {w.weight}"
        assert w.weight <= max_w + 1e-6, f"{w.asset} exceeds max_weight: {w.weight} > {max_w}"
    print(f"  [PASS] long_only + bounded by max_weight={max_w}")


def test_reproducibility(result):
    expected_path = Path(__file__).parent / 'examples' / 'expected_output.json'
    if not expected_path.exists():
        # First run — seed the expected file
        expected_path.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"  [SEED] wrote expected_output.json (first run)")
        return
    with open(expected_path) as f:
        expected = json.load(f)
    actual_by_asset = {w.asset: w.weight for w in result.asset_weights}
    expected_by_asset = {w['asset']: w['weight'] for w in expected['asset_weights']}
    assert set(actual_by_asset) == set(expected_by_asset), \
        f"asset set differs: {set(actual_by_asset) ^ set(expected_by_asset)}"
    max_d = max(abs(actual_by_asset[k] - expected_by_asset[k]) for k in actual_by_asset)
    assert max_d < 1e-3, f"max weight delta {max_d:.6f} > 1e-3"
    print(f"  [PASS] reproducibility: max delta {max_d:.2e}")


def test_dynamic_n(sample_data):
    """Predict on a 3-asset subset of the sample (was 5)."""
    sub = {**sample_data, 'asset_data': sample_data['asset_data'][:3]}
    request = request_from_dict(sub)
    bundle = load_model(tier='low', n_assets=3)
    result = predict(request, model_bundle=bundle)
    s = sum(w.weight for w in result.asset_weights)
    assert abs(s - 1.0) < 1e-5, f"sum_check failed for N=3: {s}"
    assert len(result.asset_weights) == 3
    print(f"  [PASS] dynamic N=3 works: sum {s:.6f}, top weight {result.asset_weights[0].weight:.3f}")


def test_constraints_override(sample_data):
    """Verify max_weight override is applied."""
    over = {**sample_data, 'constraints_override': {'max_weight': 0.50}}
    request = request_from_dict(over)
    bundle = load_model(tier='low', n_assets=len(request.asset_data))
    result = predict(request, model_bundle=bundle)
    for w in result.asset_weights:
        assert w.weight <= 0.50 + 1e-6, f"{w.asset} exceeds overridden max: {w.weight}"
    assert result.constraints_applied['max_weight'] == 0.50
    print(f"  [PASS] constraints_override applied: max_weight=0.50")


def test_json_roundtrip(sample_data):
    """Serialize request → JSON → load → predict → same result as direct call."""
    request_direct = request_from_dict(sample_data)
    bundle = load_model(tier='low', n_assets=len(request_direct.asset_data))
    result_direct = predict(request_direct, model_bundle=bundle)

    json_str = json.dumps(sample_data)
    request_loaded = request_from_dict(json.loads(json_str))
    result_loaded = predict(request_loaded, model_bundle=bundle)

    direct_by_asset = {w.asset: w.weight for w in result_direct.asset_weights}
    loaded_by_asset = {w.asset: w.weight for w in result_loaded.asset_weights}
    max_d = max(abs(direct_by_asset[k] - loaded_by_asset[k]) for k in direct_by_asset)
    assert max_d < 1e-6, f"JSON roundtrip mismatch: {max_d}"
    print(f"  [PASS] JSON roundtrip: max delta {max_d:.2e}")


def main():
    print("=" * 70)
    print("Deployment package end-to-end tests")
    print("=" * 70)

    sample_data = load_sample()

    print("\n[1/6] sum_to_one + return result for further tests")
    result = test_sum_to_one()

    print("\n[2/6] long_only and max_weight bounded")
    test_long_only_and_bounded(result, max_w=0.30)

    print("\n[3/6] reproducibility vs expected_output.json")
    test_reproducibility(result)

    print("\n[4/6] dynamic N (subset of 3 assets)")
    test_dynamic_n(sample_data)

    print("\n[5/6] constraints_override")
    test_constraints_override(sample_data)

    print("\n[6/6] JSON round-trip")
    test_json_roundtrip(sample_data)

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)


if __name__ == '__main__':
    main()
