"""ML Platform — revenue prediction + explainability.

CatBoost is the target model, but all modules degrade gracefully to a
dependency-free linear/heuristic model so prediction, training, and
explainability run (and are testable) without CatBoost/SHAP installed.
"""
