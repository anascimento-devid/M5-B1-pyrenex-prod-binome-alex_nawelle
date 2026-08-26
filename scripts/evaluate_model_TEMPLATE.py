"""Évaluation continue + tracking MLflow (SQUELETTE M5-B2 À COMPLÉTER).

À chaque release : recalcule les métriques cibles sur un jeu de référence
figé, **trace le run dans MLflow**, compare aux seuils, et **sort un code
retour non-zéro** si dégradation (→ bloque la release en CI).

Renommez ce fichier en `scripts/evaluate_model.py` une fois complété.
Mini-cours : `07_MLflow_tracking_essentiel.md` + `08_Evaluation_continue_seuils`.

Usage cible::

    python scripts/evaluate_model.py --freeze-baseline             # une fois, au gel du jeu
    python scripts/evaluate_model.py --release-tag v2.0.0
    python scripts/evaluate_model.py --release-tag bad --degrade   # test du rouge
    mlflow ui    # comparer les runs

⚠️ **Le piège central du brief.** La tentation est de comparer vos métriques à
la baseline holdout annoncée en M1 (`metrics_holdout` dans le `.json`). Ne le
faites pas : le holdout et votre jeu de référence n'ont ni la même taille ni la
même composition. Vous mesureriez l'écart entre **deux populations**, pas la
dégradation du **modèle** — et votre garde-fou se déclencherait tout seul.
La baseline du garde-fou, c'est le **golden run** : les métriques mesurées sur
**votre** jeu de référence, au moment où vous le gelez.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import joblib
import mlflow
import pandas as pd
from sklearn.metrics import f1_score, recall_score, roc_auc_score

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "services" / "model" / "models"
REFERENCE_SET = ROOT / "data" / "reference_set.csv"
REFERENCE_BASELINE = ROOT / "data" / "reference_baseline.json"

MODEL_NAME = os.environ.get("MODEL_NAME", "pyrenex_risk_v2_balanced")
MODEL_PATH = MODELS_DIR / f"{MODEL_NAME}.joblib"
META_PATH = MODELS_DIR / f"{MODEL_NAME}.json"

# TODO 1 — définir vos seuils (stratégie absolu / relatif / hybride).
#   Documentez-les ET justifiez-les dans evaluation_thresholds.md.
#   ⚠️ Une tolérance relative n'a de sens que si elle est **plus grande que le
#   bruit de mesure** de votre jeu de référence. Mesurez ce bruit (bootstrap,
#   cf. mini-cours 08) et prenez au moins 2 σ. Sous le bruit, le garde-fou se
#   déclenche sur du hasard et vous perdez confiance en lui.
THRESHOLDS: dict[str, dict[str, float]] = {
    # "f1_macro": {"absolute_min": ..., "max_drop_vs_baseline": ...},
}


def compute_metrics(model, df: pd.DataFrame, meta: dict) -> dict[str, float]:
    """Calcule les métriques cibles sur le jeu de référence."""

    feature_columns = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    target_mapping = meta["target_mapping"]

    X = df[feature_columns]
    y_true = df[meta["target_column"]].map(target_mapping)

    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]  # proba de la classe "défaut" (label 1)

    default_label = target_mapping["Charged Off"]

    return {
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        "f1_default": f1_score(y_true, y_pred, pos_label=default_label),
        "roc_auc": roc_auc_score(y_true, y_proba),
        "recall_default": recall_score(y_true, y_pred, pos_label=default_label),
    }


def check_thresholds(metrics: dict[str, float], baseline: dict) -> list[str]:
    """Retourne la liste des violations de seuil (vide = release OK)."""

    violations: list[str] = []
    baseline_metrics = baseline["metrics"]

    for name, rules in THRESHOLDS.items():
        value = metrics[name]
        golden = baseline_metrics[name]

        absolute_min = rules.get("absolute_min")
        if absolute_min is not None and value < absolute_min:
            violations.append(
                f"{name}={value:.4f} < plancher absolu {absolute_min:.4f}"
            )

        max_drop = rules.get("max_drop_vs_baseline")
        if max_drop is not None and (golden - value) > max_drop:
            violations.append(
                f"{name}={value:.4f} a baissé de {golden - value:.4f} vs golden "
                f"run {golden:.4f} (baisse max tolérée {max_drop:.4f})"
            )

    return violations


def load_baseline() -> dict:
    """Charge le golden run (baseline mesurée sur le jeu de référence)."""

    if not REFERENCE_BASELINE.exists():
        raise FileNotFoundError(
            f"{REFERENCE_BASELINE} introuvable. Gelez le golden run d'abord : "
            "python scripts/evaluate_model.py --freeze-baseline"
        )
    return json.loads(REFERENCE_BASELINE.read_text(encoding="utf-8"))


def freeze_baseline(model, df: pd.DataFrame, meta: dict) -> dict:
    """Mesure et gèle le golden run sur le jeu de référence."""

    baseline = {
        "model_version": meta["model_version"],
        "reference_set": REFERENCE_SET.name,
        "n_reference": len(df),
        "metrics": compute_metrics(model, df, meta),
    }
    REFERENCE_BASELINE.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-tag", default="dev")
    parser.add_argument("--degrade", action="store_true")
    parser.add_argument("--freeze-baseline", action="store_true")
    args = parser.parse_args()

    model = joblib.load(MODEL_PATH)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    df = pd.read_csv(REFERENCE_SET)

    if args.freeze_baseline:
        print(json.dumps(freeze_baseline(model, df, meta), indent=2))
        return 0

    if args.degrade:
        # TODO 4 — simuler un bug de preprocessing réaliste (ex. désaligner
        #   X et y) pour PROUVER que le rouge bloque bien la release.
        pass

    metrics = compute_metrics(model, df, meta)
    baseline = load_baseline()  # ← le golden run, PAS metrics_holdout
    violations = check_thresholds(metrics, baseline)

    # --- Bloc MLflow PRÉ-CÂBLÉ — complétez params + metrics ------------------
    mlflow.set_experiment("pyrenex-eval-continue")
    with mlflow.start_run(run_name=args.release_tag):
        mlflow.log_params(
            {
                "model_version": meta["model_version"],
                "release_tag": args.release_tag,
                # TODO 5 — ajouter reference_set, n_reference…
            }
        )
        mlflow.log_metrics(metrics)  # ← les 4 métriques tracées
        mlflow.set_tag("release_blocked", str(bool(violations)))
    # ------------------------------------------------------------------------

    print(json.dumps({"metrics": metrics, "violations": violations}, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
