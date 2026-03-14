"""Generatore profili di carico bottom-up per edifici."""

import json
from pathlib import Path

import numpy as np

from energina.core.logging_config import get_logger
from energina.core.time_series import genera_indice_orario, is_feriale

logger = get_logger("edificio.profili_carico")


def carica_profilo(tipologia: str) -> dict:
    """Carica profilo di carico dal file di configurazione.

    Args:
        tipologia: Tipo edificio (residenziale, ufficio, industriale).

    Returns:
        Dizionario con profilo giornaliero e fattori mensili.
    """
    for base in [Path.cwd(), Path(__file__).parents[4]]:
        path = base / "config" / "profili_carico" / f"{tipologia}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)

    logger.warning(f"Profilo '{tipologia}' non trovato, uso default residenziale")
    return _profilo_default_residenziale()


def genera_consumo_base(
    tipologia: str,
    anno: int,
    consumo_annuo_kwh: float | None = None,
    superficie_mq: float = 120,
    n_occupanti: int = 4,
) -> np.ndarray:
    """Genera profilo consumo elettrico base (senza HVAC) ora per ora.

    Args:
        tipologia: Tipo edificio.
        anno: Anno di riferimento.
        consumo_annuo_kwh: Consumo annuo obiettivo. Se None, calcolato dal profilo.
        superficie_mq: Superficie edificio (mq).
        n_occupanti: Numero occupanti.

    Returns:
        Array con consumo orario (kWh), 8760 elementi.
    """
    profilo = carica_profilo(tipologia)

    # Determina consumo annuo base
    if consumo_annuo_kwh is not None:
        base_annuo = consumo_annuo_kwh
    elif tipologia == "residenziale":
        base_annuo = profilo.get("consumo_base_annuo_kwh", 1800)
        # Scala per occupanti
        base_annuo *= (0.7 + 0.15 * n_occupanti)
    else:
        kwh_mq = profilo.get("consumo_base_annuo_kwh_per_mq", 30)
        base_annuo = kwh_mq * superficie_mq

    # Profili giornalieri normalizzati
    prof_norm = profilo.get("profilo_giornaliero_normalizzato", {})
    prof_feriale = np.array(prof_norm.get("feriale", [1/24]*24))
    prof_festivo = np.array(prof_norm.get("festivo", prof_feriale))

    # Normalizza a somma 1
    prof_feriale = prof_feriale / prof_feriale.sum()
    prof_festivo = prof_festivo / prof_festivo.sum()

    # Fattori mensili
    fattori = profilo.get("fattori_mensili", {})
    fattori_mese = np.array(fattori.get("valori", [1.0]*12))
    # Normalizza a media 1
    fattori_mese = fattori_mese / fattori_mese.mean()

    # Genera serie oraria
    indice = genera_indice_orario(anno)
    n_ore = len(indice)
    consumo = np.zeros(n_ore)

    consumo_giornaliero_medio = base_annuo / 365.0

    for i, ts in enumerate(indice):
        dt = ts.to_pydatetime()
        mese = dt.month - 1  # 0-indexed
        ora = dt.hour

        fattore_mese = fattori_mese[mese]
        if is_feriale(dt):
            fattore_ora = prof_feriale[ora]
        else:
            fattore_ora = prof_festivo[ora]

        consumo[i] = consumo_giornaliero_medio * fattore_mese * fattore_ora

    # Aggiungi rumore realistico (+-5%)
    rumore = 1 + np.random.normal(0, 0.05, n_ore)
    consumo *= np.maximum(rumore, 0.5)

    return consumo


def _profilo_default_residenziale() -> dict:
    """Profilo residenziale di fallback."""
    return {
        "tipologia": "residenziale",
        "consumo_base_annuo_kwh": 1800,
        "profilo_giornaliero_normalizzato": {
            "feriale": [
                0.020, 0.015, 0.012, 0.012, 0.012, 0.015,
                0.030, 0.065, 0.060, 0.040, 0.035, 0.035,
                0.055, 0.060, 0.040, 0.035, 0.035, 0.045,
                0.065, 0.080, 0.085, 0.075, 0.055, 0.030,
            ],
            "festivo": [
                0.020, 0.015, 0.012, 0.012, 0.012, 0.012,
                0.020, 0.040, 0.060, 0.065, 0.065, 0.065,
                0.070, 0.055, 0.045, 0.040, 0.040, 0.050,
                0.060, 0.070, 0.075, 0.070, 0.055, 0.030,
            ],
        },
        "fattori_mensili": {
            "valori": [1.05, 0.95, 0.90, 0.85, 0.85, 0.90,
                       0.95, 0.95, 0.90, 0.95, 1.00, 1.10],
        },
    }
