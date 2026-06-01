# Questionnaire Risk-Tolerance Artifacts

This directory stores the runtime artifacts for the questionnaire-based
investor risk-tolerance feature. The CatBoost pickle is wired into the FastAPI
simulator runtime through `ml-service/app/questionnaire.py`.

## Files

- `catboost_undersampling_risk_model.pkl`: CatBoost risk-tolerance classifier.
- `contract.json`: runtime feature-order and checksum contract.

Source/provenance files live under
`docs/artifact-provenance/questionnaire-risk-tolerance/`.

## Raw Model Contract

The supplied pickle is a `catboost.CatBoostClassifier`. The simulator accepts
the deployment model inputs directly instead of reconstructing the original
survey answers.

Expected inference feature vector, in exact order:

1. `age`
2. `Gender_Score`
3. `Stock_Score`
4. `Duration_Score`
5. `Expect_Score`
6. `Monitor_Score`
7. `Objective_Score`
8. `Avenue_Score`
9. `Factor_Returns`
10. `Factor_Risk`
11. `Purpose_Savings for Future`
12. `Purpose_Wealth Creation`
13. `What are your savings objectives?_Health Care`
14. `What are your savings objectives?_Retirement Plan`

Number of features: 14.

The training export reports observed ages from `18` through `38`. Runtime
inference clamps submitted ages to this range before passing them to the model.

## Output Mapping

- `0` -> `low` / Conservative
- `1` -> `medium` / Moderate
- `2` -> `high` / Aggressive

The simulator uses the predicted risk level as the input to the existing
historical simulation path. Portfolio results must remain described as
historical diagnostics, not guaranteed performance.
