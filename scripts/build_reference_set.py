"""Construit le jeu de référence M5-B2 à partir du holdout M1.

Tire un échantillon **équilibré** (250 `Charged Off` / 250 `Fully Paid`)
depuis `data/lending_club_holdout.csv` (le holdout complet du M1-B1, 6000
lignes, ~18,4 % de défauts), avec une seed fixe pour que le tirage soit
reproductible — cf. justification du choix « équilibré » dans
`evaluation_thresholds_TEMPLATE.md`.

⚠️ À lancer une seule fois : le jeu de référence produit doit ensuite rester
figé et versionné (`data/reference_set.csv`). Si on le relance, on obtient
exactement le même fichier (seed fixe) — relancer ne sert donc qu'à
documenter/reproduire la recette, pas à en générer un nouveau à chaque fois.

Usage::

    python scripts/build_reference_set.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
HOLDOUT_PATH = ROOT / "data" / "lending_club_holdout.csv"
REFERENCE_SET_PATH = ROOT / "data" / "reference_set.csv"

SEED = 42
N_PER_CLASS = 250
TARGET_COLUMN = "loan_status"
CLASSES = ("Charged Off", "Fully Paid")


def build_reference_set(holdout: pd.DataFrame) -> pd.DataFrame:
    """Tire un échantillon équilibré {N_PER_CLASS} par classe, mélangé."""
    samples = [
        holdout[holdout[TARGET_COLUMN] == cls].sample(n=N_PER_CLASS, random_state=SEED)
        for cls in CLASSES
    ]
    return pd.concat(samples).sample(frac=1, random_state=SEED).reset_index(drop=True)


def main() -> None:
    holdout = pd.read_csv(HOLDOUT_PATH)
    reference_set = build_reference_set(holdout)

    reference_set.to_csv(REFERENCE_SET_PATH, index=False)

    counts = reference_set[TARGET_COLUMN].value_counts().to_dict()
    print(f"Holdout source : {len(holdout)} lignes ({HOLDOUT_PATH})")
    print(f"Jeu de référence écrit : {len(reference_set)} lignes {counts}")
    print(f"→ {REFERENCE_SET_PATH}")


if __name__ == "__main__":
    main()
