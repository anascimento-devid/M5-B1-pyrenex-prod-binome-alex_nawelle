"""Métriques métier Prometheus — service backend.

En plus des métriques HTTP standard exposées par
``prometheus-fastapi-instrumentator``, on expose un compteur métier
des erreurs rencontrées lors des appels au service model.
"""
from __future__ import annotations

from prometheus_client import Counter


UPSTREAM_ERRORS_TOTAL = Counter(
    "pyrenex_backend_upstream_errors_total",
    "Nombre d'erreurs lors des appels du backend au service model.",
    labelnames=("error_type",),
)


def observe_upstream_error(error_type: str) -> None:
    """Enregistre une erreur lors d'un appel au service model.

    Args:
        error_type: Type d'erreur rencontré, par exemple
            ``unavailable`` ou ``model_error``.
    """
    UPSTREAM_ERRORS_TOTAL.labels(error_type=error_type).inc()