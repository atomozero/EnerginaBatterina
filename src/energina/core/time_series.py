"""Utility per gestione serie temporali orarie."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def genera_indice_orario(anno: int) -> pd.DatetimeIndex:
    """Genera indice orario per un anno intero (8760 o 8784 ore).

    Args:
        anno: Anno di riferimento.

    Returns:
        DatetimeIndex con frequenza oraria.
    """
    inizio = pd.Timestamp(f"{anno}-01-01 00:00:00")
    fine = pd.Timestamp(f"{anno}-12-31 23:00:00")
    return pd.date_range(start=inizio, end=fine, freq="h")


def ore_anno(anno: int) -> int:
    """Numero di ore in un anno (8760 o 8784 per bisestile)."""
    inizio = datetime(anno, 1, 1)
    fine = datetime(anno + 1, 1, 1)
    return int((fine - inizio).total_seconds() / 3600)


def is_feriale(dt: datetime) -> bool:
    """Verifica se una data e' feriale (lun-ven)."""
    return dt.weekday() < 5


def fascia_oraria(ora: int, feriale: bool) -> str:
    """Determina fascia oraria ARERA (F1/F2/F3).

    F1: lun-ven 8-19
    F2: lun-ven 7-8,19-23; sab 7-23
    F3: lun-sab 23-7; dom e festivi tutto il giorno

    Args:
        ora: Ora del giorno (0-23).
        feriale: True se giorno feriale (lun-ven).

    Returns:
        "F1", "F2" o "F3".
    """
    if feriale:
        if 8 <= ora < 19:
            return "F1"
        elif 7 <= ora < 23:
            return "F2"
        else:
            return "F3"
    else:
        return "F3"


def serie_a_lista_dicts(
    indice: pd.DatetimeIndex, **colonne: np.ndarray
) -> list[dict]:
    """Converte serie orarie in lista di dizionari per output JSON.

    Args:
        indice: Indice temporale.
        **colonne: Arrays con i dati (stessa lunghezza di indice).

    Returns:
        Lista di dizionari con "timestamp" + colonne.
    """
    risultato = []
    for i, ts in enumerate(indice):
        riga = {"timestamp": ts.isoformat()}
        for nome, valori in colonne.items():
            val = valori[i]
            if isinstance(val, (np.floating, float)):
                riga[nome] = round(float(val), 4)
            elif isinstance(val, (np.integer, int)):
                riga[nome] = int(val)
            else:
                riga[nome] = val
        risultato.append(riga)
    return risultato


def raggruppa_mensile(valori_orari: np.ndarray, anno: int) -> list[float]:
    """Aggrega valori orari in somme mensili.

    Args:
        valori_orari: Array con un valore per ogni ora dell'anno.
        anno: Anno di riferimento.

    Returns:
        Lista di 12 valori (uno per mese).
    """
    indice = genera_indice_orario(anno)
    serie = pd.Series(valori_orari, index=indice)
    mensili = serie.resample("ME").sum()
    return [round(float(v), 2) for v in mensili.values]
