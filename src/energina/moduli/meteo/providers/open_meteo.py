"""Provider dati meteo da Open-Meteo API (gratuita, senza API key)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from energina.core.exceptions import APIError
from energina.core.logging_config import get_logger

logger = get_logger("meteo.open_meteo")

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


def scarica_meteo_anno(
    latitudine: float,
    longitudine: float,
    anno: int,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Scarica dati meteo orari da Open-Meteo per un anno intero.

    Args:
        latitudine: Latitudine in gradi decimali.
        longitudine: Longitudine in gradi decimali.
        anno: Anno di riferimento.
        cache_dir: Directory per cache locale.

    Returns:
        DataFrame con colonne: timestamp, ghi, dni, dhi, temp_aria, vel_vento,
        umidita_rel, copertura_nubi.
    """
    # Controlla cache
    if cache_dir is not None:
        cache_file = (
            cache_dir / f"open_meteo_{latitudine:.4f}_{longitudine:.4f}_{anno}.parquet"
        )
        if cache_file.exists():
            logger.info(f"Dati meteo da cache: {cache_file}")
            return pd.read_parquet(cache_file)

    logger.info(f"Scaricamento meteo Open-Meteo per ({latitudine}, {longitudine}), anno {anno}")

    params = {
        "latitude": latitudine,
        "longitude": longitudine,
        "start_date": f"{anno}-01-01",
        "end_date": f"{anno}-12-31",
        "hourly": ",".join([
            "shortwave_radiation",
            "direct_normal_irradiance",
            "diffuse_radiation",
            "temperature_2m",
            "windspeed_10m",
            "relativehumidity_2m",
            "cloudcover",
        ]),
        "timezone": "UTC",
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise APIError("Open-Meteo", f"Errore scaricamento: {e}") from e

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise APIError("Open-Meteo", f"Risposta non valida: {e}") from e

    hourly = data.get("hourly", {})
    if not hourly or "time" not in hourly:
        raise APIError("Open-Meteo", "Nessun dato orario nella risposta")

    df = pd.DataFrame({
        "timestamp": pd.to_datetime(hourly["time"]),
        "ghi": hourly.get("shortwave_radiation", []),
        "dni": hourly.get("direct_normal_irradiance", []),
        "dhi": hourly.get("diffuse_radiation", []),
        "temp_aria": hourly.get("temperature_2m", []),
        "vel_vento": hourly.get("windspeed_10m", []),
        "umidita_rel": hourly.get("relativehumidity_2m", []),
        "copertura_nubi": hourly.get("cloudcover", []),
    })

    # Riempi NaN con interpolazione
    df = df.fillna(method="ffill").fillna(method="bfill").fillna(0)

    # Salva in cache
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file, index=False)
        logger.info(f"Meteo salvato in cache: {cache_file}")

    return df
