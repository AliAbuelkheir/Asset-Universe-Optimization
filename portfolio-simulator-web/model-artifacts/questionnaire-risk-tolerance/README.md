# Questionnaire Risk-Tolerance Artifacts

This directory stores the source material for the questionnaire-based investor
risk-tolerance feature. The raw Random Forest pickle is wired into the FastAPI
simulator runtime through `ml-service/app/questionnaire.py`.

## Files

- `cl.py`: Google Colab training and analysis export.
- `karmapart.pdf`: questionnaire input schema and model-output mapping notes.
- `risk_tolerance_rf_model.pkl`: raw Random Forest risk-tolerance classifier.

## Raw Model Contract

The supplied pickle is a raw `sklearn.ensemble.RandomForestClassifier`, not the
dict-style artifact described in `karmapart.pdf`.

Expected inference feature vector, in exact order:

1. `age`
2. `Duration_Score`
3. `Expect_Score`
4. `Monitor_Score`
5. `gender_Male`
6. `Objective_Income`
7. `Objective_Growth`
8. `Purpose_Savings for Future`
9. `What are your savings objectives?_Health Care`

Number of features: 9.

## Output Mapping

- `0` -> `low` / Conservative
- `1` -> `medium` / Moderate
- `2` -> `high` / Aggressive

The simulator uses the predicted risk level as the input to the existing
historical simulation path. Portfolio results must remain described as
historical diagnostics, not guaranteed performance.

Note: the supplied pickle is missing the richer `feature_names` and `scaler`
metadata described in `karmapart.pdf`. Controlled-profile validation showed the
raw model expects the two objective one-hot columns as `Objective_Income` then
`Objective_Growth`; using the reverse order makes income-oriented conservative
profiles classify as aggressive.
