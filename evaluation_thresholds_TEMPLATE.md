# Seuils d'évaluation continue — Pyrenex scoring v2 (À COMPLÉTER)

> Doit être lisible par Sophie Léger (Lead Data) et le DPO. **Chaque seuil
> est justifié** par une raison chiffrée. Renommez en `evaluation_thresholds.md`.

Stratégie retenue (absolu / relatif / **hybride**) : _à choisir et justifier_.
Jeu de référence : `data/reference_set.csv` (sous-échantillon figé du holdout M1).

## Composition du jeu de référence

Le jeu de référence (500 lignes) est tiré du holdout M1
(`data/lending_club_holdout.csv`, 6000 lignes, 18,4 % de défauts) par
tirage stratifié **équilibré (250 `Charged Off` / 250 `Fully Paid`)**, seed
fixe `42`, plutôt que représentatif de la prod (~18 % de défauts, soit ~90
défauts sur 500). Recette reproductible : `scripts/build_reference_set.py`.

**Justification** : le coût métier d'une erreur n'est pas symétrique — un
défaut non détecté (faux négatif) fait perdre le capital prêté à Pyrenex,
alors qu'un faux positif ne coûte qu'un manque à gagner sur les intérêts.
`recall_default` est donc la métrique la plus critique de ce garde-fou
(c'est justement la faiblesse documentée du modèle v1 : `recall=0.05`,
95 % des défauts non détectés). Un jeu équilibré donne 250 défauts pour
mesurer cette métrique au lieu de ~90 en échantillon représentatif — un
signal nettement moins bruité, donc un seuil de tolérance plus resserré
et plus utile. Contrepartie assumée : le F1 macro/ROC-AUC mesurés ici ne
sont pas directement comparables à la distribution réelle de prod — ce
n'est pas leur rôle, seul le golden run sur ce même jeu arbitre les
releases.

## Deux baselines, à ne pas confondre

| | Mesurée sur | Sert à |
|---|---|---|
| **Baseline communiquée** (`metrics_holdout`) | le holdout M1 complet | ce qu'on a annoncé au client |
| **Golden run** (`data/reference_baseline.json`) | **votre** jeu de référence, au gel | **arbitrer les releases** |

⚠️ Le garde-fou compare au **golden run**, jamais à la baseline communiquée :
les deux jeux n'ont ni la même taille ni la même composition, donc l'écart
entre eux mesure une **différence de population**, pas une dégradation du
modèle.

| Métrique | Golden run | Plancher absolu | Baisse max vs golden run | Justification |
|---|---|---|---|---|
| F1 macro | _…_ | _…_ | _…_ | _… (pourquoi ce seuil ?)_ |
| ROC-AUC | _…_ | _…_ | _…_ | _…_ |
| Recall défaut | _…_ | _…_ | _…_ | _…_ |

> **Comment dimensionner la colonne « baisse max »** : mesurez le bruit de
> votre jeu de référence (bootstrap, cf. mini-cours 08), et prenez **au moins
> 2 σ**. Une tolérance sous le bruit se déclenche toute seule. Reportez ici le
> σ mesuré — c'est ce qui rend le seuil défendable devant Sophie Léger.

| Métrique | σ bootstrap mesuré | 2 σ | Tolérance retenue |
|---|---|---|---|
| F1 macro | _…_ | _…_ | _…_ |
| ROC-AUC | _…_ | _…_ | _…_ |
| Recall défaut | _…_ | _…_ | _…_ |

## Procédure de mise à jour des seuils

- **Qui** : _…_
- **Quand** : _…_
- **Comment** : _… (garder `THRESHOLDS` dans le script ET ce fichier cohérents ;
  si le jeu de référence change, **regeler le golden run** — `--freeze-baseline`)_