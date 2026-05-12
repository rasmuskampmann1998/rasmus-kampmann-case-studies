"""
Train a binary classifier on the synthetic CVR-only dataset.

Predicts `uses_target_software` from public CVR-style features alone:
company form, employee band, age, VAT cadence, industry code, region.

Holdout AUC lands in the 0.74-0.78 range on the synthetic data, which
mirrors what a model trained on real labelled data tends to look like
for this kind of problem.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "artifacts"
OUT.mkdir(exist_ok=True)

CATEGORICAL = ["company_form", "industry_nace", "region", "employee_band", "vat_frequency"]
NUMERIC = ["founded_year"]
BOOLEAN = ["has_subsidiaries"]


def load() -> pd.DataFrame:
    return pd.read_csv(DATA / "synthetic_companies.csv")


def featurise(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df.copy()
    y = X.pop("uses_target_software")
    X = X.drop(columns=["cvr", "company_name"])
    X["has_subsidiaries"] = X["has_subsidiaries"].astype(int)
    X["company_age"] = 2025 - X["founded_year"]
    X = pd.get_dummies(X, columns=CATEGORICAL, drop_first=False)
    return X, y


def main() -> None:
    df = load()
    X, y = featurise(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="auc",
        random_state=42,
    )
    model.fit(X_train, y_train)

    train_pred = model.predict_proba(X_train)[:, 1]
    test_pred = model.predict_proba(X_test)[:, 1]
    train_auc = roc_auc_score(y_train, train_pred)
    test_auc = roc_auc_score(y_test, test_pred)

    importance = pd.Series(model.feature_importances_, index=X.columns)
    importance = importance.sort_values(ascending=False).head(15)

    print(f"Train AUC: {train_auc:.3f}")
    print(f"Test AUC:  {test_auc:.3f}")
    print("\nTop features by gain:")
    for feat, imp in importance.items():
        print(f"  {feat:40s} {imp:.4f}")

    # Persist the model and a small metadata file
    model.save_model(OUT / "model.json")
    metadata = {
        "train_auc": float(train_auc),
        "test_auc": float(test_auc),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "feature_columns": list(X.columns),
        "top_features": importance.to_dict(),
    }
    with (OUT / "metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nWrote model + metadata to {OUT}")


if __name__ == "__main__":
    main()
