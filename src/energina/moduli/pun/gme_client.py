"""Client per dati prezzi energia dal GME (Gestore Mercati Energetici)."""

from datetime import date, datetime

import numpy as np
import pandas as pd

from energina.core.exceptions import APIError
from energina.core.logging_config import get_logger

logger = get_logger("pun.gme_client")


def scarica_prezzi_gme(
    anno: int,
    zona: str = "CSUD",
) -> pd.DataFrame:
    """Scarica prezzi PUN orari dal GME tramite mercati-energetici.

    Args:
        anno: Anno di riferimento.
        zona: Zona di mercato (CNOR, CSUD, NORD, SUD, SICI, SARD).

    Returns:
        DataFrame con colonne: timestamp, pun_eur_mwh.
    """
    try:
        from mercati_energetici import MGP

        mgp = MGP()
        inizio = date(anno, 1, 1)
        fine = date(anno, 12, 31)

        logger.info(f"Scaricamento prezzi GME {zona} per {anno}")
        df = mgp.prezzi(inizio, fine, zona=zona)

        if df is None or df.empty:
            raise APIError("GME", f"Nessun dato per {zona}/{anno}")

        # Normalizza colonne
        df = df.reset_index()
        if "Data" in df.columns and "Ora" in df.columns:
            df["timestamp"] = pd.to_datetime(df["Data"]) + pd.to_timedelta(
                df["Ora"] - 1, unit="h"
            )
        elif "datetime" in df.columns:
            df["timestamp"] = pd.to_datetime(df["datetime"])

        # Cerca colonna prezzo
        col_prezzo = None
        for c in df.columns:
            if "pun" in c.lower() or "prezzo" in c.lower() or zona in c:
                col_prezzo = c
                break
        if col_prezzo is None:
            # Usa prima colonna numerica
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                col_prezzo = numeric_cols[0]
            else:
                raise APIError("GME", "Colonna prezzo non trovata nella risposta")

        return pd.DataFrame({
            "timestamp": df["timestamp"],
            "pun_eur_mwh": df[col_prezzo].astype(float),
        })

    except ImportError:
        logger.warning("Libreria mercati-energetici non installata, uso fallback sintetico")
        return None
    except Exception as e:
        logger.warning(f"Errore GME, uso fallback sintetico: {e}")
        return None
