"""Modello fotovoltaico basato su pvlib."""

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("fotovoltaico.pv_model")


def simula_produzione_pv(
    ghi: np.ndarray,
    dni: np.ndarray,
    dhi: np.ndarray,
    temp_aria: np.ndarray,
    vel_vento: np.ndarray,
    latitudine: float,
    longitudine: float,
    altitudine: float,
    potenza_kwp: float,
    inclinazione: float,
    azimut: float,
    perdite_pct: float = 14.0,
    coeff_temp: float = -0.0035,
    noct: float = 45.0,
    efficienza_inverter: float = 0.97,
    anno: int = 2023,
) -> dict:
    """Simula produzione PV oraria usando pvlib.

    Args:
        ghi: Irradianza globale orizzontale (W/m2), array 8760.
        dni: Irradianza diretta normale (W/m2).
        dhi: Irradianza diffusa orizzontale (W/m2).
        temp_aria: Temperatura aria (C).
        vel_vento: Velocita vento (m/s).
        latitudine, longitudine, altitudine: Posizione impianto.
        potenza_kwp: Potenza nominale impianto (kWp).
        inclinazione: Inclinazione moduli (gradi).
        azimut: Orientamento (180=Sud, 90=Est, 270=Ovest).
        perdite_pct: Perdite di sistema (%).
        coeff_temp: Coefficiente temperatura potenza (%/C, negativo).
        noct: Temperatura nominale cella operativa (C).
        efficienza_inverter: Efficienza inverter (0-1).
        anno: Anno per indice temporale.

    Returns:
        Dict con potenza_ac_kw, energia_kwh, temp_cella arrays.
    """
    try:
        return _simula_con_pvlib(
            ghi, dni, dhi, temp_aria, vel_vento,
            latitudine, longitudine, altitudine,
            potenza_kwp, inclinazione, azimut,
            perdite_pct, coeff_temp, noct, efficienza_inverter, anno,
        )
    except ImportError:
        logger.warning("pvlib non disponibile, uso modello semplificato")
        return _simula_semplificato(
            ghi, temp_aria, vel_vento,
            potenza_kwp, inclinazione, latitudine,
            perdite_pct, coeff_temp, noct, efficienza_inverter,
        )


def _simula_con_pvlib(
    ghi, dni, dhi, temp_aria, vel_vento,
    latitudine, longitudine, altitudine,
    potenza_kwp, inclinazione, azimut,
    perdite_pct, coeff_temp, noct, efficienza_inverter, anno,
):
    """Simulazione completa con pvlib."""
    import pandas as pd
    import pvlib

    n_ore = len(ghi)
    indice = pd.date_range(f"{anno}-01-01", periods=n_ore, freq="h", tz="UTC")

    location = pvlib.location.Location(
        latitude=latitudine,
        longitude=longitudine,
        altitude=altitudine,
    )

    # Posizione solare
    solar_pos = location.get_solarposition(indice)

    # Irradianza sul piano inclinato (POA)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=inclinazione,
        surface_azimuth=azimut,
        solar_zenith=solar_pos["apparent_zenith"],
        solar_azimuth=solar_pos["azimuth"],
        dni=dni,
        ghi=ghi,
        dhi=dhi,
    )
    poa_global = poa["poa_global"].fillna(0).values
    poa_global = np.maximum(poa_global, 0)

    # Temperatura cella (modello NOCT)
    temp_cella = temp_aria + (noct - 20) / 800 * poa_global

    # Potenza DC con correzione temperatura
    eff_temp = 1 + coeff_temp * (temp_cella - 25)
    potenza_dc_kw = potenza_kwp * (poa_global / 1000.0) * eff_temp

    # Perdite di sistema
    potenza_dc_kw *= (1 - perdite_pct / 100.0)

    # Conversione AC
    potenza_ac_kw = potenza_dc_kw * efficienza_inverter

    # Non puo essere negativa
    potenza_ac_kw = np.maximum(potenza_ac_kw, 0)

    # Energia = potenza * 1h
    energia_kwh = potenza_ac_kw.copy()

    return {
        "potenza_ac_kw": potenza_ac_kw,
        "energia_kwh": energia_kwh,
        "temp_cella_c": temp_cella,
        "poa_global": poa_global,
    }


def _simula_semplificato(
    ghi, temp_aria, vel_vento,
    potenza_kwp, inclinazione, latitudine,
    perdite_pct, coeff_temp, noct, efficienza_inverter,
):
    """Modello semplificato senza pvlib."""
    logger.info("Simulazione PV con modello semplificato")

    # Fattore inclinazione approssimato
    lat_rad = np.radians(latitudine)
    tilt_rad = np.radians(inclinazione)
    fattore_tilt = 1 + 0.1 * np.cos(tilt_rad - lat_rad)

    poa_global = ghi * fattore_tilt
    poa_global = np.maximum(poa_global, 0)

    # Temperatura cella
    temp_cella = temp_aria + (noct - 20) / 800 * poa_global

    # Potenza con correzione temperatura
    eff_temp = 1 + coeff_temp * (temp_cella - 25)
    potenza_dc_kw = potenza_kwp * (poa_global / 1000.0) * eff_temp
    potenza_dc_kw *= (1 - perdite_pct / 100.0)
    potenza_ac_kw = np.maximum(potenza_dc_kw * efficienza_inverter, 0)
    energia_kwh = potenza_ac_kw.copy()

    return {
        "potenza_ac_kw": potenza_ac_kw,
        "energia_kwh": energia_kwh,
        "temp_cella_c": temp_cella,
        "poa_global": poa_global,
    }


def calcola_degradazione_annua(
    produzione_anno1_kwh: float,
    degradazione_annua_pct: float,
    vita_utile_anni: int,
) -> list[dict]:
    """Calcola produzione per ogni anno con degradazione.

    Args:
        produzione_anno1_kwh: Produzione primo anno.
        degradazione_annua_pct: Degradazione annua (%).
        vita_utile_anni: Vita utile in anni.

    Returns:
        Lista dicts con anno, produzione_kwh, degradazione_cumulata_pct.
    """
    risultati = []
    for anno in range(1, vita_utile_anni + 1):
        fattore = (1 - degradazione_annua_pct / 100.0) ** (anno - 1)
        risultati.append({
            "anno": anno,
            "produzione_kwh": round(produzione_anno1_kwh * fattore, 1),
            "degradazione_cumulata_pct": round((1 - fattore) * 100, 2),
        })
    return risultati
