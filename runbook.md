# Runbook d'astreinte — Pyrenex Prod

> Pour l'équipe SRE Pyrenex. 4 procédures : **déclenchement → actions → qui
> appeler → ce qu'on NE fait PAS**. Pas besoin de connaître le ML pour
> l'exécuter — sauf procédure 3, qui implique l'équipe data/ML par nature.

---

## 1. Service KO (un conteneur down)

**Déclenchement** :
- `docker compose ps` montre un service `exited` ou `unhealthy`, **ou**
- panel Grafana « Vie » : RPS à 0 / service à `DOWN` (rouge) pendant plus
  de 30 s (healthcheck `model`/`backend` : intervalle 10 s, 3 échecs
  consécutifs avant bascule `unhealthy`).

**Actions** :
1. `docker compose logs --tail=100 <service>` — lire l'erreur (crash au
   démarrage ? artefact modèle manquant ? port déjà utilisé ?).
2. `docker compose restart <service>`.
3. Si le service redémarré dépend d'un autre (`backend` dépend de `model`,
   `frontend` dépend de `backend`) : vérifier d'abord que la dépendance est
   `healthy` avant de rediagnostiquer le service en aval.
4. Si toujours KO après 2 tentatives de restart → escalade.

**Qui appeler** : astreinte SRE Pyrenex (niveau 1). Si pas résolu sous
15 min → équipe dev Pyrenex (Alex / Nawelle).

**On NE fait PAS** : `docker compose down -v` (détruit les volumes —
perte des données Grafana/Prometheus).

---

## 2. Latence p95 dégradée

**Déclenchement** : panel « Vitesse — p95 » (service `model`) > **300 ms**
sur une fenêtre glissante de 5 min. *(Seuil basé sur la baseline observée
en recette : p95 ~50-90 ms sur des payloads standards — 300 ms représente
déjà ~3-5x la baseline, marge volontaire contre le bruit de mesure.)*

**Actions** :
1. Regarder le RPS sur la même période : latence dégradée + RPS élevé =
   probable charge (pic de trafic légitime) ; latence dégradée + RPS
   normal/faible = problème côté service.
2. `docker stats` — vérifier CPU/mémoire des conteneurs `model` et
   `backend` (le modèle scikit-learn est CPU-bound).
3. `docker compose logs model backend --tail=200` — chercher des timeouts
   ou des retries `httpx` côté `backend`.
4. Vérifier s'il y a eu un déploiement récent (`git log --oneline -5`,
   dernier tag GHCR) corrélé dans le temps avec la dégradation.

**Qui appeler** : astreinte SRE Pyrenex (niveau 1). Si corrélée à un
déploiement récent → escalade directe équipe dev (déclenche la
procédure 4, rollback).

**On NE fait PAS** :
- Redéployer une version non testée en espérant que ça règle le problème.
- Augmenter à chaud les ressources allouées sans avoir identifié la cause
  (masque le symptôme, pas la régression).

---

## 3. Métrique modèle qui s'écarte (distribution des prédictions anormale)

**Déclenchement** : panel « Comportement — prédictions » : la part de
prédictions `classe=1` (défaut) dépasse **50 % sur une fenêtre de 15 min**,
alors que la baseline observée en recette est ~10-20 %. *(Ce panel montre
CE QUE le modèle prédit en ce moment, pas s'il prédit juste — mesurer la
performance réelle du modèle, c'est le rôle de l'évaluation continue
M5-B2, pas de cette procédure.)*

**Actions** :
1. Vérifier qu'il ne s'agit pas d'un pic de trafic légitime (ex. campagne
   commerciale ciblant un profil de risque particulier) plutôt qu'un
   incident.
2. `GET /info` sur le service `model` — confirmer que la version/le
   fichier de modèle chargé est bien celui attendu (pas de bascule
   accidentelle sur un mauvais artefact après un déploiement).
3. `docker compose logs backend --tail=200` — chercher des erreurs de
   mapping de features (valeurs par défaut ou manquantes envoyées telles
   quelles au modèle, qui peuvent biaiser fortement le score).
4. Ne PAS tenter d'évaluer ici si le modèle « a raison » (accuracy,
   recall…) — hors périmètre de cette procédure.

**Qui appeler** : escalade directe équipe data/ML Pyrenex (Alex / Nawelle)
— ce n'est pas un incident infra pur, ça touche au comportement du modèle.

**On NE fait PAS** :
- Modifier les seuils de décision métier en prod à chaud sans validation.
- Désactiver le modèle / servir une réponse par défaut sans en informer
  Sophie Léger si l'impact est visible côté client.

---

## 4. Rollback de release

**Déclenchement** : une régression confirmée est corrélée temporellement à
un déploiement récent (hausse du taux d'erreur 5xx, latence dégradée, ou
comportement modèle anormal juste après un push/tag).

**Actions** :
1. Identifier le tag stable précédent : `git tag --list` (ou historique
   des images `ghcr.io/<repo>-<service>:<tag>` dans l'onglet Packages
   GitHub).
2. Repointer le déploiement sur les images du tag stable :
   `docker pull ghcr.io/<repo>-<service>:<tag_precedent>` pour chaque
   service concerné, puis redémarrer.
3. Vérifier que les 3 healthchecks repassent `healthy` et que les panels
   Grafana reviennent à la normale.
4. Ouvrir un post-mortem sans blâme pour documenter la cause avant tout
   nouveau déploiement.

**Qui appeler** : équipe dev Pyrenex (Alex / Nawelle) — valide le tag à
restaurer. Informer Sophie Léger si l'incident a eu un impact visible côté
client.

**On NE fait PAS** :
- Corriger en urgence sur la version cassée directement en prod (hotfix
  non testé).
- Supprimer les images/tags de la version cassée avant d'avoir fait le
  post-mortem (perd la trace nécessaire à l'investigation).
