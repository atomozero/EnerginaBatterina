"""Previsore produzione PV multi-anno."""

from energina.core.logging_config import get_logger

logger = get_logger("previsione.produzione")


def previsione_con_degradazione(
    produzione_anno1_kwh: float,
    degradazione_annua_pct: float,
    orizzonte_anni: int,
) -> list[dict]:
    """Previsione produzione PV con degradazione lineare.

    Args:
        produzione_anno1_kwh: Produzione primo anno (kWh).
        degradazione_annua_pct: Degradazione annua (%).
        orizzonte_anni: Orizzonte previsionale (anni).

    Returns:
        Lista dicts con anno e produzione prevista.
    """
    previsioni = []
    for anno in range(1, orizzonte_anni + 1):
        fattore = (1 - degradazione_annua_pct / 100) ** (anno - 1)
        previsioni.append({
            "anno": anno,
            "produzione_kwh": round(produzione_anno1_kwh * fattore, 1),
            "degradazione_cumulata_pct": round((1 - fattore) * 100, 2),
        })
    return previsioni
