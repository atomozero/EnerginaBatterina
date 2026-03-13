"""Strategia batteria: massimizzazione autoconsumo."""

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("batteria.autoconsumo")


def simula_autoconsumo(
    immissione_kwh: np.ndarray,
    prelievo_kwh: np.ndarray,
    capacita_kwh: float,
    potenza_max_kw: float,
    soc_min_pct: float,
    soc_max_pct: float,
    eff_carica: float,
    eff_scarica: float,
    soc_iniziale_pct: float = 50.0,
) -> dict:
    """Simula batteria con strategia autoconsumo.

    Logica:
    - Quando c'e' surplus (immissione > 0): carica batteria
    - Quando c'e' deficit (prelievo > 0): scarica batteria
    - Priorita: autoconsumo massimo

    Args:
        immissione_kwh: Surplus orario da impianto PV (kWh).
        prelievo_kwh: Deficit orario dall'edificio (kWh).
        capacita_kwh: Capacita nominale batteria (kWh).
        potenza_max_kw: Potenza massima carica/scarica (kW).
        soc_min_pct: SOC minimo (%).
        soc_max_pct: SOC massimo (%).
        eff_carica: Efficienza carica (0-1).
        eff_scarica: Efficienza scarica (0-1).
        soc_iniziale_pct: SOC iniziale (%).

    Returns:
        Dict con arrays: soc_pct, energia_caricata_kwh, energia_scaricata_kwh,
        immissione_residua_kwh, prelievo_residuo_kwh.
    """
    n = len(immissione_kwh)
    soc_min = soc_min_pct / 100.0 * capacita_kwh
    soc_max = soc_max_pct / 100.0 * capacita_kwh
    soc = soc_iniziale_pct / 100.0 * capacita_kwh

    soc_arr = np.zeros(n)
    caricata = np.zeros(n)
    scaricata = np.zeros(n)
    imm_residua = np.zeros(n)
    prel_residuo = np.zeros(n)

    for i in range(n):
        surplus = immissione_kwh[i]
        deficit = prelievo_kwh[i]

        energia_car = 0.0
        energia_scar = 0.0

        if surplus > 0:
            # Carica batteria con surplus
            spazio = soc_max - soc
            max_car = min(surplus * eff_carica, spazio, potenza_max_kw)
            energia_car = max(max_car, 0)
            soc += energia_car
            imm_residua[i] = surplus - energia_car / eff_carica
        else:
            imm_residua[i] = 0

        if deficit > 0:
            # Scarica batteria per deficit
            disponibile = soc - soc_min
            max_scar = min(deficit / eff_scarica, disponibile, potenza_max_kw)
            energia_scar = max(max_scar, 0)
            soc -= energia_scar
            prel_residuo[i] = deficit - energia_scar * eff_scarica
        else:
            prel_residuo[i] = 0

        soc_arr[i] = soc / capacita_kwh * 100 if capacita_kwh > 0 else 0
        caricata[i] = energia_car
        scaricata[i] = energia_scar * eff_scarica

    return {
        "soc_pct": soc_arr,
        "energia_caricata_kwh": caricata,
        "energia_scaricata_kwh": scaricata,
        "immissione_residua_kwh": np.maximum(imm_residua, 0),
        "prelievo_residuo_kwh": np.maximum(prel_residuo, 0),
    }
