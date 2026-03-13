"""Calcolo incentivi Ritiro Dedicato GSE."""

from energina.core.logging_config import get_logger

logger = get_logger("incentivi.ritiro_dedicato")

# Prezzi minimi garantiti 2024 (EUR/kWh) - fascia fino a 1.5 MW
# Fonte: delibera ARERA
PREZZI_MINIMI_GARANTITI = {
    "base": 0.04,  # prezzo minimo garantito base
    "solare": 0.04,
}


def calcola_ricavo_ritiro_dedicato(
    immissione_kwh: float,
    prezzo_medio_vendita_eur_kwh: float,
    prezzo_minimo_garantito: float = 0.04,
) -> dict:
    """Calcola ricavo annuo da Ritiro Dedicato.

    Il Ritiro Dedicato remunera l'energia immessa in rete al prezzo
    zonale orario, con garanzia di prezzo minimo.

    Args:
        immissione_kwh: Energia immessa in rete nell'anno (kWh).
        prezzo_medio_vendita_eur_kwh: Prezzo medio vendita (EUR/kWh).
        prezzo_minimo_garantito: Prezzo minimo garantito (EUR/kWh).

    Returns:
        Dict con ricavo e dettagli.
    """
    prezzo_effettivo = max(prezzo_medio_vendita_eur_kwh, prezzo_minimo_garantito)
    ricavo = immissione_kwh * prezzo_effettivo

    return {
        "immissione_kwh": round(immissione_kwh, 1),
        "prezzo_effettivo_eur_kwh": round(prezzo_effettivo, 4),
        "ricavo_annuo_eur": round(ricavo, 2),
        "applica_minimo_garantito": prezzo_medio_vendita_eur_kwh < prezzo_minimo_garantito,
    }
