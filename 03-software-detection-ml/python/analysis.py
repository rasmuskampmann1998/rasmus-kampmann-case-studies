"""
Produce five charts for the software-detection case study.

Runs after `train.py` (which produces the model artefact).

Charts:
  01_feature_importance.png   top-15 features by gain
  02_roc_curve.png            ROC on holdout
  03_confusion_matrix.png     confusion matrix at 0.5 threshold
  04_calibration.png          probability calibration
  05_score_distribution.png   predicted probability distribution by true class
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import calibration_curve
from sklearn.metrics import confusion_matrix, roc_curve
from sklearn.model_selection import train_test_split

from train import featurise, load

ART = Path(__file__).resolve().parent / "artifacts"
OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)

LIME = "#9DEB6E"
BLACK = "#0A0A0A"
GREEN_MID = "#2D6A4F"
GREY = "#94A3B8"


def main() -> None:
    df = load()
    X, y = featurise(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier()
    model.load_model(ART / "model.json")
    test_pred = model.predict_proba(X_test)[:, 1]
    test_class = (test_pred > 0.5).astype(int)

    # 1. Feature importance
    importance = pd.Series(model.feature_importances_, index=X.columns)
    top = importance.sort_values(ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top.index, top.values, color=LIME, edgecolor=BLACK)
    ax.invert_yaxis()
    ax.set_xlabel("Importance (gain)")
    ax.set_title("Top-15 features driving the model")
    plt.tight_layout()
    plt.savefig(OUT / "01_feature_importance.png", dpi=140)
    plt.close()

    # 2. ROC
    fpr, tpr, _ = roc_curve(y_test, test_pred)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(fpr, tpr, color=LIME, lw=2.5)
    ax.plot([0, 1], [0, 1], color=GREY, ls="--")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve on holdout (5,000-row synthetic dataset)")
    plt.tight_layout()
    plt.savefig(OUT / "02_roc_curve.png", dpi=140)
    plt.close()

    # 3. Confusion matrix
    cm = confusion_matrix(y_test, test_class)
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.imshow(cm, cmap="Greens")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    fontsize=18, fontweight="bold",
                    color=BLACK if cm[i, j] < cm.max() / 2 else "white")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["No", "Yes"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["No", "Yes"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion matrix (threshold = 0.5)")
    plt.tight_layout()
    plt.savefig(OUT / "03_confusion_matrix.png", dpi=140)
    plt.close()

    # 4. Calibration
    frac_pos, mean_pred = calibration_curve(y_test, test_pred, n_bins=10)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(mean_pred, frac_pos, color=LIME, marker="o", lw=2.5)
    ax.plot([0, 1], [0, 1], color=GREY, ls="--")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration plot")
    plt.tight_layout()
    plt.savefig(OUT / "04_calibration.png", dpi=140)
    plt.close()

    # 5. Score distribution by true class
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(test_pred[y_test == 0], bins=30, alpha=0.7, label="Actual: No", color=GREY)
    ax.hist(test_pred[y_test == 1], bins=30, alpha=0.7, label="Actual: Yes", color=LIME, edgecolor=BLACK)
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Count")
    ax.set_title("Predicted-probability distribution, by true class")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "05_score_distribution.png", dpi=140)
    plt.close()

    print(f"Wrote 5 charts to {OUT}")


if __name__ == "__main__":
    main()
