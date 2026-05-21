"""egtportfolio — Egyptian Tier-Based Portfolio Allocator

Quickstart:
    from egtportfolio import predict, load_model

    bundle = load_model(tier='low', n_assets=7)  # pre-load for repeated calls
    result = predict({
        'tier': 'low',
        'target_month': '2025-08',
        'asset_data': [...],   # see schemas.AssetTimeSeries
    }, model_bundle=bundle)

    for w in result.asset_weights:
        print(f'{w.asset}: {w.weight:.1%}')
"""

from .inference import predict
from .loader import load_model, ModelBundle, TIER_MAX_WEIGHT, TIER_MIN_WEIGHT
from .schemas import (
    AssetTimeSeries,
    AssetWeight,
    ConstraintsOverride,
    InferenceRequest,
    InferenceResponse,
    request_from_dict,
)

__version__ = '0.1.0'

__all__ = [
    'predict',
    'load_model', 'ModelBundle',
    'AssetTimeSeries', 'AssetWeight', 'ConstraintsOverride',
    'InferenceRequest', 'InferenceResponse', 'request_from_dict',
    'TIER_MAX_WEIGHT', 'TIER_MIN_WEIGHT',
    '__version__',
]
