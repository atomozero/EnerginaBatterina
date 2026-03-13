"""Analisi finanziaria investimento: NPV, IRR, payback, LCOE."""

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("economico.analisi")


def calcola_npv(flussi_cassa: list[float], tasso_sconto: float) -> float:
    """Calcola Net Present Value.

    Args:
        flussi_cassa: Lista flussi di cassa (anno 0 = investimento negativo).
        tasso_sconto: Tasso di sconto annuo (es. 0.05 per 5%).

    Returns:
        NPV in EUR.
    """
    try:
        import numpy_financial as npf
        return float(npf.npv(tasso_sconto, flussi_cassa))
    except ImportError:
        npv = 0.0
        for t, cf in enumerate(flussi_cassa):
            npv += cf / (1 + tasso_sconto) ** t
        return npv


def calcola_irr(flussi_cassa: list[float]) -> float | None:
    """Calcola Internal Rate of Return.

    Args:
        flussi_cassa: Lista flussi di cassa.

    Returns:
        IRR come decimale (es. 0.08 per 8%), o None se non calcolabile.
    """
    try:
        import numpy_financial as npf
        irr = float(npf.irr(flussi_cassa))
        if np.isnan(irr) or np.isinf(irr):
            return None
        return irr
    except (ImportError, ValueError):
        return None


def calcola_payback_semplice(flussi_cassa: list[float]) -> float | None:
    """Calcola payback period semplice (non attualizzato).

    Args:
        flussi_cassa: Lista flussi di cassa.

    Returns:
        Anni per recuperare l'investimento, o None se mai recuperato.
    """
    cumulato = 0.0
    for t, cf in enumerate(flussi_cassa):
        cumulato += cf
        if cumulato >= 0 and t > 0:
            # Interpolazione lineare nell'anno di payback
            cumulato_prec = cumulato - cf
            if cf > 0:
                fraz = -cumulato_prec / cf
                return t - 1 + fraz
            return float(t)
    return None


def calcola_payback_attualizzato(
    flussi_cassa: list[float], tasso_sconto: float
) -> float | None:
    """Calcola payback period attualizzato.

    Args:
        flussi_cassa: Lista flussi di cassa.
        tasso_sconto: Tasso di sconto.

    Returns:
        Anni per payback attualizzato, o None.
    """
    cumulato = 0.0
    for t, cf in enumerate(flussi_cassa):
        cf_att = cf / (1 + tasso_sconto) ** t
        cumulato += cf_att
        if cumulato >= 0 and t > 0:
            cumulato_prec = cumulato - cf_att
            if cf_att > 0:
                fraz = -cumulato_prec / cf_att
                return t - 1 + fraz
            return float(t)
    return None


def calcola_lcoe(
    investimento_totale: float,
    costi_om_annui: float,
    produzione_annua_kwh: list[float],
    tasso_sconto: float,
) -> float:
    """Calcola Levelized Cost of Energy.

    LCOE = (somma costi attualizzati) / (somma energia attualizzata)

    Args:
        investimento_totale: Investimento iniziale (EUR).
        costi_om_annui: Costi O&M annui (EUR).
        produzione_annua_kwh: Produzione per ogni anno (kWh).
        tasso_sconto: Tasso di sconto.

    Returns:
        LCOE in EUR/kWh.
    """
    costi_att = investimento_totale
    energia_att = 0.0

    for t, prod in enumerate(produzione_annua_kwh, start=1):
        fattore = (1 + tasso_sconto) ** t
        costi_att += costi_om_annui / fattore
        energia_att += prod / fattore

    if energia_att > 0:
        return costi_att / energia_att
    return 0.0


def calcola_roi(investimento: float, guadagno_netto: float) -> float:
    """Calcola Return on Investment.

    Args:
        investimento: Investimento totale (EUR).
        guadagno_netto: Guadagno netto totale su vita utile (EUR).

    Returns:
        ROI come percentuale.
    """
    if investimento > 0:
        return (guadagno_netto / investimento) * 100
    return 0.0
