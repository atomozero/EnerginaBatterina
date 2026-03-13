"""Costruttore flussi di cassa per analisi investimento PV+batteria."""

from energina.core.logging_config import get_logger

logger = get_logger("economico.flussi_cassa")


def costruisci_flussi_cassa(
    investimento_totale: float,
    risparmio_autoconsumo_anno1: float,
    ricavo_vendita_anno1: float,
    incentivi_per_anno: list[dict],
    costi_esercizio_annui: float,
    vita_utile_anni: int,
    escalation_prezzo_pct: float = 3.0,
    inflazione_pct: float = 2.0,
    degradazione_produzione_pct: float = 0.5,
    costo_sostituzione_inverter: float = 0,
    anno_sostituzione_inverter: int = 0,
) -> list[dict]:
    """Costruisce tabella flussi di cassa anno per anno.

    Args:
        investimento_totale: Investimento iniziale (EUR, positivo).
        risparmio_autoconsumo_anno1: Risparmio da autoconsumo anno 1 (EUR).
        ricavo_vendita_anno1: Ricavo vendita energia anno 1 (EUR).
        incentivi_per_anno: Lista dicts con incentivo_totale_eur per anno.
        costi_esercizio_annui: Costi O&M anno 1 (EUR).
        vita_utile_anni: Durata analisi (anni).
        escalation_prezzo_pct: Aumento annuo prezzo energia (%).
        inflazione_pct: Inflazione annua (%).
        degradazione_produzione_pct: Degradazione produzione PV annua (%).
        costo_sostituzione_inverter: Costo sostituzione inverter (EUR).
        anno_sostituzione_inverter: Anno sostituzione (0 = mai).

    Returns:
        Lista di dicts con dettaglio flussi per ogni anno.
    """
    flussi = []
    flusso_cumulato = -investimento_totale

    # Anno 0: investimento
    flussi.append({
        "anno": 0,
        "investimento_eur": -investimento_totale,
        "risparmio_autoconsumo_eur": 0,
        "ricavo_vendita_eur": 0,
        "incentivi_eur": 0,
        "costi_esercizio_eur": 0,
        "costi_straordinari_eur": 0,
        "flusso_netto_eur": -investimento_totale,
        "flusso_cumulato_eur": flusso_cumulato,
    })

    for anno in range(1, vita_utile_anni + 1):
        # Escalation prezzi energia
        fattore_prezzo = (1 + escalation_prezzo_pct / 100) ** (anno - 1)
        # Degradazione produzione
        fattore_prod = (1 - degradazione_produzione_pct / 100) ** (anno - 1)
        # Inflazione costi
        fattore_inflazione = (1 + inflazione_pct / 100) ** (anno - 1)

        risparmio = risparmio_autoconsumo_anno1 * fattore_prezzo * fattore_prod
        ricavo = ricavo_vendita_anno1 * fattore_prezzo * fattore_prod

        # Incentivi dall'array
        incentivo = 0.0
        if anno <= len(incentivi_per_anno):
            incentivo = incentivi_per_anno[anno - 1].get("incentivo_totale_eur", 0)

        costi = costi_esercizio_annui * fattore_inflazione

        # Costi straordinari
        costi_straord = 0.0
        if anno_sostituzione_inverter > 0 and anno == anno_sostituzione_inverter:
            costi_straord = costo_sostituzione_inverter

        flusso_netto = risparmio + ricavo + incentivo - costi - costi_straord
        flusso_cumulato += flusso_netto

        flussi.append({
            "anno": anno,
            "investimento_eur": 0,
            "risparmio_autoconsumo_eur": round(risparmio, 2),
            "ricavo_vendita_eur": round(ricavo, 2),
            "incentivi_eur": round(incentivo, 2),
            "costi_esercizio_eur": round(costi, 2),
            "costi_straordinari_eur": round(costi_straord, 2),
            "flusso_netto_eur": round(flusso_netto, 2),
            "flusso_cumulato_eur": round(flusso_cumulato, 2),
        })

    return flussi
