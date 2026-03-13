"""Esecutore scenari per analisi di sensibilita."""

import copy

import numpy as np

from energina.core.logging_config import get_logger
from energina.moduli.economico.analisi_investimento import calcola_irr, calcola_npv
from energina.moduli.economico.flussi_cassa import costruisci_flussi_cassa

logger = get_logger("sensibilita.runner")


def esegui_sweep_parametro(
    config_base: dict,
    flussi_base: dict,
    nome_variabile: str,
    valori: list[float],
) -> list[dict]:
    """Esegui sweep di un parametro e ricalcola indicatori economici.

    Args:
        config_base: Configurazione base dell'analisi.
        flussi_base: Dati base per calcolo flussi (investimento, risparmio, etc).
        nome_variabile: Nome della variabile da variare.
        valori: Lista di valori da testare.

    Returns:
        Lista dicts con valore, NPV, IRR per ogni scenario.
    """
    risultati = []

    for valore in valori:
        # Crea copia e modifica parametro
        dati = copy.deepcopy(flussi_base)
        dati = _applica_variazione(dati, nome_variabile, valore)

        # Ricalcola flussi di cassa
        flussi = costruisci_flussi_cassa(
            investimento_totale=dati["investimento_totale"],
            risparmio_autoconsumo_anno1=dati["risparmio_autoconsumo"],
            ricavo_vendita_anno1=dati["ricavo_vendita"],
            incentivi_per_anno=dati["incentivi_per_anno"],
            costi_esercizio_annui=dati["costi_esercizio"],
            vita_utile_anni=dati["vita_utile"],
            escalation_prezzo_pct=dati.get("escalation", 3.0),
            inflazione_pct=dati.get("inflazione", 2.0),
            degradazione_produzione_pct=dati.get("degradazione", 0.5),
        )

        flussi_netti = [f["flusso_netto_eur"] for f in flussi]
        tasso = dati.get("tasso_sconto", 0.05)

        npv = calcola_npv(flussi_netti, tasso)
        irr = calcola_irr(flussi_netti)

        risultati.append({
            "variabile": nome_variabile,
            "valore": valore,
            "npv_eur": round(npv, 2),
            "irr_pct": round(irr * 100, 2) if irr is not None else None,
        })

    return risultati


def _applica_variazione(dati: dict, nome: str, valore: float) -> dict:
    """Applica variazione di un parametro ai dati base."""
    if nome == "costo_pv_eur":
        dati["investimento_totale"] = (
            valore
            + dati.get("costo_batteria", 0)
            + dati.get("costo_installazione", 0)
        )
    elif nome == "costo_batteria_eur":
        dati["investimento_totale"] = (
            dati.get("costo_pv", 0)
            + valore
            + dati.get("costo_installazione", 0)
        )
    elif nome == "prezzo_energia":
        # Scala risparmio e ricavi proporzionalmente
        fattore = valore / dati.get("prezzo_energia_base", 0.25)
        dati["risparmio_autoconsumo"] *= fattore
        dati["ricavo_vendita"] *= fattore
    elif nome == "potenza_nominale_kwp":
        fattore = valore / dati.get("potenza_base_kwp", 6.0)
        dati["risparmio_autoconsumo"] *= min(fattore, 1.5)  # limita a saturazione
        dati["ricavo_vendita"] *= fattore
        dati["investimento_totale"] = dati.get("costo_pv_per_kwp", 1500) * valore + dati.get("costo_altro", 8000)
    elif nome == "capacita_nominale_kwh":
        if valore == 0:
            dati["investimento_totale"] = dati.get("costo_pv", 9000) + dati.get("costo_installazione", 2000)
        else:
            dati["investimento_totale"] = (
                dati.get("costo_pv", 9000)
                + dati.get("costo_batt_per_kwh", 600) * valore
                + dati.get("costo_installazione", 2000)
            )
    elif nome == "tasso_sconto":
        dati["tasso_sconto"] = valore / 100.0

    return dati


def genera_variazioni_percentuali(
    valore_base: float,
    min_pct: float,
    max_pct: float,
    passi: int,
) -> list[float]:
    """Genera lista di valori come variazioni percentuali del base.

    Args:
        valore_base: Valore di riferimento.
        min_pct: Variazione minima (es. -30 per -30%).
        max_pct: Variazione massima (es. +30 per +30%).
        passi: Numero di passi.

    Returns:
        Lista di valori.
    """
    percentuali = np.linspace(min_pct, max_pct, passi)
    return [round(valore_base * (1 + p / 100), 2) for p in percentuali]
