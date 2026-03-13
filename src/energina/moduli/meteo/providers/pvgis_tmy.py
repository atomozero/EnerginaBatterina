"""Provider dati meteo da PVGIS Typical Meteorological Year (TMY)."""

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from energina.core.exceptions import APIError
from energina.core.logging_config import get_logger

logger = get_logger("meteo.pvgis_tmy")

PVGIS_TMY_URL = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"


def scarica_tmy(
    latitudine: float,
    longitudine: float,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Scarica dati TMY da PVGIS.

    Args:
        latitudine: Latitudine in gradi decimali.
        longitudine: Longitudine in gradi decimali.
        cache_dir: Directory per cache locale.

    Returns:
        DataFrame con 8760 righe e colonne:
        - ghi (W/m2), dni (W/m2), dhi (W/m2)
        - temp_aria (C), vel_vento (m/s), umidita_rel (%)
    """
    # Controlla cache
    if cache_dir is not None:
        cache_file = cache_dir / f"pvgis_tmy_{latitudine:.4f}_{longitudine:.4f}.parquet"
        if cache_file.exists():
            logger.info(f"TMY da cache: {cache_file}")
            return pd.read_parquet(cache_file)

    logger.info(f"Scaricamento TMY da PVGIS per ({latitudine}, {longitudine})")

    params = {
        "lat": latitudine,
        "lon": longitudine,
        "outputformat": "json",
    }

    try:
        resp = requests.get(PVGIS_TMY_URL, params=params, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise APIError("PVGIS", f"Errore scaricamento TMY: {e}") from e

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise APIError("PVGIS", f"Risposta non valida: {e}") from e

    records = data.get("outputs", {}).get("tmy_hourly", [])
    if not records:
        raise APIError("PVGIS", "Nessun dato TMY nella risposta")

    df = pd.DataFrame(records)

    # Rinomina colonne PVGIS -> nostre convenzioni
    col_map = {
        "G(h)": "ghi",
        "Gb(n)": "dni",
        "Gd(h)": "dhi",
        "T2m": "temp_aria",
        "WS10m": "vel_vento",
        "RH": "umidita_rel",
    }
    df = df.rename(columns=col_map)

    # Parsing timestamp - PVGIS usa formato "20050101:0010"
    if "time(UTC)" in df.columns:
        df["timestamp"] = pd.to_datetime(df["time(UTC)"], format="%Y%m%d:%H%M")
        df = df.drop(columns=["time(UTC)"])

    # Mantieni solo colonne che ci servono
    colonne_utili = ["timestamp", "ghi", "dni", "dhi", "temp_aria", "vel_vento", "umidita_rel"]
    colonne_presenti = [c for c in colonne_utili if c in df.columns]
    df = df[colonne_presenti]

    # Forza 8760 righe (anno non bisestile)
    if len(df) > 8760:
        df = df.iloc[:8760]

    # Salva in cache
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file, index=False)
        logger.info(f"TMY salvato in cache: {cache_file}")

    return df
