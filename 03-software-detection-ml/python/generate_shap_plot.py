"""Generate a SHAP summary plot for the trained model.

Produces `charts/06_shap_summary.png`. Loads the model artefact and the same
holdout split used in `analysis.py`. Feature names are anonymised to generic
labels for public publication (the underlying schema mirrors Danish CVR
registry features, but the labels in this plot are intentionally generic).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import shap
import xgboost as xgb
from sklearn.model_selection import train_test_split

from train import featurise, load

ART = Path(__file__).resolve().parent / "artifacts"
OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)


def anonymise_columns(columns: list[str]) -> list[str]:
    """Map real feature names to generic Feature A, B, C... grouped by family.

    Keeps the same ordering so SHAP values still align with the original
    column index, but the rendered axis labels carry no schema detail.
    """
    family_map: dict[str, str] = {}
    family_counter = ord("A")
    sub_counters: dict[str, int] = {}
    new_labels: list[str] = []

    for col in columns:
        # Extract the family prefix (before the first underscore-separated value)
        # Examples: "employee_band_5-9" -> "employee_band"
        #           "company_form_ApS"  -> "company_form"
        #           "founded_year"      -> "founded_year"
        parts = col.rsplit("_", 1)
        if len(parts) == 2 and not parts[0].endswith("year"):
            family = parts[0]
        else:
            family = col

        if family not in family_map:
            family_map[family] = chr(family_counter)
            family_counter += 1
            sub_counters[family] = 0

        # If the original was a one-hot (family_value), increment a sub-index
        if family != col:
            sub_counters[family] += 1
            new_labels.append(f"Feature {family_map[family]}{sub_counters[family]}")
        else:
            new_labels.append(f"Feature {family_map[family]}")

    return new_labels


def main() -> None:
    df = load()
    X, y = featurise(df)
    _, X_test, _, _ = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier()
    model.load_model(ART / "model.json")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # Anonymise feature names before passing to SHAP plot
    X_test_anon = X_test.copy()
    X_test_anon.columns = anonymise_columns(list(X_test.columns))

    plt.figure(figsize=(10, 7))
    shap.summary_plot(
        shap_values,
        X_test_anon,
        max_display=15,
        show=False,
        plot_size=None,
    )
    plt.title("SHAP feature impact on prediction (top 15)")
    plt.tight_layout()
    plt.savefig(OUT / "06_shap_summary.png", dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote SHAP plot to {OUT / '06_shap_summary.png'}")


if __name__ == "__main__":
    main()
