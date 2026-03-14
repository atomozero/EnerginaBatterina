"""Utility per gestione serie temporali orarie."""

import calendar
from datetime import datetime, timedelta

import numpy as np

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class _SimpleTimestamp:
    """Timestamp minimale come fallback senza pandas."""
    def __init__(self, dt: datetime):
        self._dt = dt

    def isoformat(self):
        return self._dt.isoformat()

    def to_pydatetime(self):
        return self._dt

    @property
    def hour(self):
        return self._dt.hour

    @property
    def month(self):
        return self._dt.month


class _SimpleDatetimeIndex:
    """DatetimeIndex minimale come fallback senza pandas."""
    def __init__(self, timestamps: list[datetime]):
        self._timestamps = timestamps
        self._wrapped = [_SimpleTimestamp(dt) for dt in timestamps]

    def __len__(self):
        return len(self._timestamps)

    def __iter__(self):
        return iter(self._wrapped)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return _SimpleDatetimeIndex(self._timestamps[key])
        return self._wrapped[key]


def genera_indice_orario(anno: int):
    """Genera indice orario per un anno intero (8760 o 8784 ore).

    Args:
        anno: Anno di riferimento.

    Returns:
        DatetimeIndex con frequenza oraria.
    """
    if HAS_PANDAS:
        inizio = pd.Timestamp(f"{anno}-01-01 00:00:00")
        fine = pd.Timestamp(f"{anno}-12-31 23:00:00")
        return pd.date_range(start=inizio, end=fine, freq="h")
    else:
        n = ore_anno(anno)
        base = datetime(anno, 1, 1)
        return _SimpleDatetimeIndex([base + timedelta(hours=i) for i in range(n)])


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
    indice, **colonne: np.ndarray
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
    if HAS_PANDAS:
        indice = genera_indice_orario(anno)
        serie = pd.Series(valori_orari[:len(indice)], index=indice)
        mensili = serie.resample("ME").sum()
        return [round(float(v), 2) for v in mensili.values]
    else:
        # Fallback senza pandas
        mensili = []
        idx = 0
        for mese in range(1, 13):
            giorni = calendar.monthrange(anno, mese)[1]
            ore_mese = giorni * 24
            fine = min(idx + ore_mese, len(valori_orari))
            mensili.append(round(float(np.sum(valori_orari[idx:fine])), 2))
            idx = fine
        return mensili
