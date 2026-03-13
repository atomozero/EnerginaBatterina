"""Previsore prezzi energia multi-anno."""

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("previsione.prezzi")


def previsione_trend_lineare(
    prezzo_medio_anno1: float,
    escalation_pct: float,
    orizzonte_anni: int,
) -> list[dict]:
    """Previsione prezzi con trend lineare (escalation costante).

    Args:
        prezzo_medio_anno1: Prezzo medio energia anno 1 (EUR/MWh).
        escalation_pct: Escalation annua (%).
        orizzonte_anni: Orizzonte previsionale (anni).

    Returns:
        Lista dicts con anno e prezzo previsto.
    """
    previsioni = []
    for anno in range(1, orizzonte_anni + 1):
        fattore = (1 + escalation_pct / 100) ** (anno - 1)
        previsioni.append({
            "anno": anno,
            "prezzo_medio_eur_mwh": round(prezzo_medio_anno1 * fattore, 2),
        })
    return previsioni


def previsione_sarima(
    prezzi_storici_mensili: list[float],
    orizzonte_mesi: int = 300,
) -> list[dict]:
    """Previsione prezzi con modello SARIMA.

    Args:
        prezzi_storici_mensili: Serie storica prezzi mensili (EUR/MWh).
        orizzonte_mesi: Mesi da prevedere (default 300 = 25 anni).

    Returns:
        Lista dicts con mese e prezzo previsto.
    """
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        model = SARIMAX(
            prezzi_storici_mensili,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        risultato = model.fit(disp=False)
        forecast = risultato.forecast(steps=orizzonte_mesi)

        previsioni = []
        for i, val in enumerate(forecast):
            previsioni.append({
                "mese": i + 1,
                "prezzo_medio_eur_mwh": round(max(float(val), 10), 2),
            })
        return previsioni

    except (ImportError, Exception) as e:
        logger.warning(f"SARIMA non disponibile, fallback trend lineare: {e}")
        # Fallback: trend lineare basato su media storica
        media = np.mean(prezzi_storici_mensili) if prezzi_storici_mensili else 120
        return previsione_trend_lineare(media, 3.0, orizzonte_mesi // 12)
