"""Logica zone climatiche italiane per calcolo fabbisogno termico."""

import json
from pathlib import Path

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("edificio.zona_climatica")


def carica_zone_climatiche() -> dict:
    """Carica database zone climatiche."""
    for base in [Path.cwd(), Path(__file__).parents[4]]:
        path = base / "config" / "zone_climatiche.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {"zone": {}, "citta_gradi_giorno": {}}


def get_gradi_giorno(nome_citta: str, latitudine: float) -> int:
    """Ottieni gradi giorno per una citta.

    Args:
        nome_citta: Nome della citta.
        latitudine: Latitudine (fallback se citta non nel database).

    Returns:
        Gradi giorno.
    """
    db = carica_zone_climatiche()
    gg_db = db.get("citta_gradi_giorno", {})
    if nome_citta in gg_db:
        return gg_db[nome_citta]
    return int(max(600, min(3500, (latitudine - 36) * 200 + 800)))


def calcola_fabbisogno_riscaldamento(
    temp_aria: np.ndarray,
    superficie_mq: float,
    gradi_giorno: int,
    potenza_termica_kw_mq: float = 0.04,
    temp_setpoint: float = 20.0,
) -> np.ndarray:
    """Calcola fabbisogno riscaldamento orario.

    Args:
        temp_aria: Temperatura esterna oraria (C).
        superficie_mq: Superficie riscaldata (mq).
        gradi_giorno: Gradi giorno della localita.
        potenza_termica_kw_mq: Potenza termica specifica (kW/mq).
        temp_setpoint: Temperatura interna desiderata (C).

    Returns:
        Array fabbisogno termico orario (kWh_termici).
    """
    # Fabbisogno solo quando T_ext < T_setpoint
    delta_t = np.maximum(temp_setpoint - temp_aria, 0)

    # Normalizza rispetto ai gradi giorno
    if gradi_giorno > 0:
        fattore = superficie_mq * potenza_termica_kw_mq
        # Proporzionale al delta T
        fabbisogno = fattore * delta_t / 15.0  # 15C e' un delta T tipico
    else:
        fabbisogno = np.zeros_like(temp_aria)

    return fabbisogno


def calcola_fabbisogno_raffrescamento(
    temp_aria: np.ndarray,
    superficie_mq: float,
    potenza_frigorifera_kw_mq: float = 0.03,
    temp_setpoint: float = 26.0,
) -> np.ndarray:
    """Calcola fabbisogno raffrescamento orario.

    Args:
        temp_aria: Temperatura esterna oraria (C).
        superficie_mq: Superficie raffrescata (mq).
        potenza_frigorifera_kw_mq: Potenza frigorifera specifica (kW/mq).
        temp_setpoint: Temperatura interna desiderata (C).

    Returns:
        Array fabbisogno frigorifero orario (kWh_frigoriferi).
    """
    delta_t = np.maximum(temp_aria - temp_setpoint, 0)
    fattore = superficie_mq * potenza_frigorifera_kw_mq
    return fattore * delta_t / 10.0
