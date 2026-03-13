"""Configurazione pytest e fixtures condivise."""

import json
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def tmp_exchange_dir(tmp_path):
    """Directory temporanea per scambio JSON inter-modulo."""
    exchange = tmp_path / "exchange"
    exchange.mkdir()
    return exchange


@pytest.fixture
def config_residenziale():
    """Configurazione base residenziale per test."""
    return {
        "progetto": {
            "nome": "Test Residenziale",
            "vita_utile_anni": 25,
        },
        "meteo": {
            "localita": {
                "latitudine": 41.9028,
                "longitudine": 12.4964,
                "altitudine": 21,
                "nome": "Roma",
            },
            "sorgente_dati": "sintetico",
            "anno": 2023,
        },
        "modulo": {},
    }


@pytest.fixture
def output_meteo_fixture():
    """Output di esempio del modulo meteo."""
    np.random.seed(42)
    n = 8760
    ore = np.arange(n)
    ora = ore % 24
    giorno = ore / 24.0

    # GHI sintetico
    elev = np.maximum(0, np.sin(np.radians(15 * (ora - 6))) *
                      np.cos(np.radians(23.45 * np.sin(np.radians(360/365 * (giorno - 81))))))
    ghi = (800 * elev * (0.8 + 0.1 * np.random.random(n))).tolist()
    temp = (15 + 10 * np.sin(np.radians(360/365 * (giorno - 100))) +
            3 * np.sin(np.radians(15 * (ora - 6))) +
            np.random.normal(0, 1, n)).tolist()
    vento = np.abs(np.random.normal(3, 1, n)).tolist()

    serie = []
    for i in range(n):
        serie.append({
            "timestamp": f"2023-01-01T{i:05d}".replace(
                f"T{i:05d}", f"T00:00:00"
            ),  # semplificato
            "ghi": round(max(ghi[i], 0), 1),
            "dni": round(max(ghi[i] * 0.7, 0), 1),
            "dhi": round(max(ghi[i] * 0.3, 0), 1),
            "temp_aria": round(temp[i], 1),
            "vel_vento": round(vento[i], 1),
            "copertura_nubi": round(np.random.uniform(0, 100), 0),
        })

    # Fix timestamp
    from datetime import datetime, timedelta
    base = datetime(2023, 1, 1)
    for i, s in enumerate(serie):
        s["timestamp"] = (base + timedelta(hours=i)).isoformat()

    return {
        "_meta": {
            "modulo": "meteo",
            "versione": "0.1.0",
            "timestamp_esecuzione": "2023-01-01T00:00:00",
            "durata_s": 0.1,
        },
        "metadata": {
            "latitudine": 41.9028,
            "longitudine": 12.4964,
            "altitudine": 21,
            "nome_localita": "Roma",
            "sorgente_dati": "sintetico",
            "zona_climatica": "D",
            "gradi_giorno": 1415,
        },
        "serie_oraria": serie,
        "riepilogo": {
            "irradiazione_annua_kwh_mq": 1500.0,
            "temperatura_media_c": 15.5,
            "temperatura_min_c": -2.0,
            "temperatura_max_c": 38.0,
            "vel_vento_media_ms": 3.0,
        },
    }


@pytest.fixture
def output_pun_fixture():
    """Output di esempio del modulo PUN."""
    np.random.seed(42)
    n = 8760
    ore = np.arange(n)
    ora = ore % 24

    profilo = np.array([
        0.80, 0.75, 0.72, 0.70, 0.72, 0.78,
        0.90, 1.05, 1.15, 1.18, 1.15, 1.12,
        1.08, 1.10, 1.12, 1.15, 1.18, 1.20,
        1.15, 1.10, 1.05, 1.00, 0.92, 0.85,
    ])
    pun = 120 * profilo[ora] + np.random.normal(0, 5, n)
    pun = np.clip(pun, 20, 500)

    from datetime import datetime, timedelta
    base = datetime(2023, 1, 1)

    serie = []
    for i in range(n):
        ts = base + timedelta(hours=i)
        serie.append({
            "timestamp": ts.isoformat(),
            "pun_eur_mwh": round(float(pun[i]), 2),
            "prezzo_acquisto_eur_kwh": round(float(pun[i] / 1000 + 0.10) * 1.10, 4),
            "prezzo_vendita_eur_kwh": round(float(pun[i] / 1000 * 0.9), 4),
            "fascia_oraria": "F1" if 8 <= ts.hour < 19 and ts.weekday() < 5 else "F3",
        })

    return {
        "_meta": {"modulo": "pun", "versione": "0.1.0",
                  "timestamp_esecuzione": "2023-01-01T00:00:00", "durata_s": 0.1},
        "metadata": {"zona_mercato": "CSUD", "anno": 2023},
        "serie_oraria": serie,
        "riepilogo": {
            "pun_medio_eur_mwh": 120.0,
            "pun_min_eur_mwh": 60.0,
            "pun_max_eur_mwh": 200.0,
            "prezzo_acquisto_medio_eur_kwh": 0.25,
            "prezzo_vendita_medio_eur_kwh": 0.10,
            "media_per_fascia": {"F1": 135.0, "F2": 115.0, "F3": 90.0},
        },
    }


@pytest.fixture
def salva_output_fixture(tmp_exchange_dir):
    """Helper per salvare output fixture nella exchange dir."""
    def _salva(nome_modulo: str, dati: dict):
        path = tmp_exchange_dir / f"{nome_modulo}_output.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, default=str)
        return path
    return _salva
