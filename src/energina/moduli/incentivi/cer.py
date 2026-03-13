"""Calcolo incentivi Comunita Energetiche Rinnovabili (CER)."""

from energina.core.logging_config import get_logger

logger = get_logger("incentivi.cer")

# Tariffe incentivanti CER (D.M. 24/01/2024 - decreto CACER)
# Per impianti <= 200 kWp
TARIFFA_INCENTIVANTE_BASE = 0.11  # EUR/kWh sull'energia condivisa


def calcola_incentivo_cer(
    energia_condivisa_kwh: float,
    potenza_impianto_kwp: float,
    tariffa_incentivante: float = TARIFFA_INCENTIVANTE_BASE,
) -> dict:
    """Calcola incentivo annuo CER.

    L'incentivo CER si applica all'energia condivisa virtualmente,
    cioe' il minimo tra immissione e prelievo degli altri membri
    nella stessa cabina primaria.

    Per semplificazione, l'energia condivisa e' stimata come quota
    dell'autoconsumo.

    Args:
        energia_condivisa_kwh: Energia condivisa nella CER (kWh/anno).
        potenza_impianto_kwp: Potenza impianto (kWp).
        tariffa_incentivante: Tariffa incentivante (EUR/kWh).

    Returns:
        Dict con incentivo e dettagli.
    """
    # La tariffa varia per taglia impianto
    if potenza_impianto_kwp <= 200:
        tariffa = tariffa_incentivante
    elif potenza_impianto_kwp <= 600:
        tariffa = tariffa_incentivante * 0.9  # riduzione per taglie maggiori
    else:
        tariffa = tariffa_incentivante * 0.8

    incentivo = energia_condivisa_kwh * tariffa

    return {
        "energia_condivisa_kwh": round(energia_condivisa_kwh, 1),
        "tariffa_applicata_eur_kwh": round(tariffa, 4),
        "incentivo_annuo_eur": round(incentivo, 2),
        "durata_incentivo_anni": 20,
    }
