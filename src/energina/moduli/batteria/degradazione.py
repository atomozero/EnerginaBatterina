"""Modello di degradazione batteria."""

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("batteria.degradazione")


def degradazione_lineare(
    cicli_equivalenti_anno: float,
    cicli_vita: int,
    capacita_fine_vita_pct: float,
    vita_utile_anni: int,
) -> list[dict]:
    """Modello degradazione lineare basato su cicli.

    Args:
        cicli_equivalenti_anno: Cicli equivalenti per anno.
        cicli_vita: Cicli totali a fine vita (es. 6000 per LFP).
        capacita_fine_vita_pct: Capacita residua a fine vita (%).
        vita_utile_anni: Anni di vita utile.

    Returns:
        Lista dicts con anno, capacita_residua_pct, cicli_cumulati.
    """
    degradazione_per_ciclo = (100 - capacita_fine_vita_pct) / cicli_vita
    risultati = []

    for anno in range(1, vita_utile_anni + 1):
        cicli_cumulati = cicli_equivalenti_anno * anno
        perdita = min(degradazione_per_ciclo * cicli_cumulati, 100 - capacita_fine_vita_pct)
        capacita = max(100 - perdita, capacita_fine_vita_pct)

        risultati.append({
            "anno": anno,
            "capacita_residua_pct": round(capacita, 2),
            "cicli_cumulati": round(cicli_cumulati, 0),
        })

    return risultati


def calcola_cicli_equivalenti(
    energia_caricata_kwh: np.ndarray,
    capacita_nominale_kwh: float,
) -> float:
    """Calcola cicli equivalenti dall'energia caricata.

    Un ciclo equivalente = una carica completa della capacita nominale.

    Args:
        energia_caricata_kwh: Array energia caricata per ogni ora.
        capacita_nominale_kwh: Capacita nominale batteria.

    Returns:
        Numero di cicli equivalenti.
    """
    if capacita_nominale_kwh <= 0:
        return 0.0
    energia_totale = float(np.sum(energia_caricata_kwh))
    return energia_totale / capacita_nominale_kwh
