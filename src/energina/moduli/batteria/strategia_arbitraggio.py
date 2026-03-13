"""Strategia batteria: arbitraggio sui prezzi energia."""

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("batteria.arbitraggio")


def simula_arbitraggio(
    immissione_kwh: np.ndarray,
    prelievo_kwh: np.ndarray,
    prezzi_acquisto: np.ndarray,
    prezzi_vendita: np.ndarray,
    capacita_kwh: float,
    potenza_max_kw: float,
    soc_min_pct: float,
    soc_max_pct: float,
    eff_carica: float,
    eff_scarica: float,
    soc_iniziale_pct: float = 50.0,
) -> dict:
    """Simula batteria con strategia arbitraggio prezzi.

    Logica:
    - Prima soddisfa autoconsumo (come strategia base)
    - Poi: carica quando prezzo basso, scarica quando prezzo alto
    - Soglie basate su media giornaliera mobile

    Args:
        immissione_kwh: Surplus orario (kWh).
        prelievo_kwh: Deficit orario (kWh).
        prezzi_acquisto: Prezzo acquisto orario (EUR/kWh).
        prezzi_vendita: Prezzo vendita orario (EUR/kWh).
        capacita_kwh: Capacita batteria (kWh).
        potenza_max_kw: Potenza max carica/scarica (kW).
        soc_min_pct, soc_max_pct: Limiti SOC (%).
        eff_carica, eff_scarica: Efficienze (0-1).
        soc_iniziale_pct: SOC iniziale (%).

    Returns:
        Dict con arrays di risultato.
    """
    n = len(immissione_kwh)
    soc_min = soc_min_pct / 100.0 * capacita_kwh
    soc_max = soc_max_pct / 100.0 * capacita_kwh
    soc = soc_iniziale_pct / 100.0 * capacita_kwh
    rte = eff_carica * eff_scarica  # round-trip efficiency

    soc_arr = np.zeros(n)
    caricata = np.zeros(n)
    scaricata = np.zeros(n)
    imm_residua = np.zeros(n)
    prel_residuo = np.zeros(n)

    # Calcola soglie prezzo (media mobile 24h)
    kernel = np.ones(24) / 24
    media_mobile = np.convolve(prezzi_acquisto, kernel, mode="same")
    soglia_bassa = media_mobile * 0.85  # carica sotto 85% media
    soglia_alta = media_mobile * 1.15   # scarica sopra 115% media

    for i in range(n):
        surplus = immissione_kwh[i]
        deficit = prelievo_kwh[i]
        prezzo_acq = prezzi_acquisto[i]
        prezzo_ven = prezzi_vendita[i]

        energia_car = 0.0
        energia_scar = 0.0

        # 1. Autoconsumo prioritario: carica con surplus
        if surplus > 0:
            spazio = soc_max - soc
            max_car = min(surplus * eff_carica, spazio, potenza_max_kw)
            energia_car = max(max_car, 0)
            soc += energia_car
            surplus_residuo = surplus - energia_car / eff_carica
        else:
            surplus_residuo = 0

        # 2. Autoconsumo: scarica per deficit
        if deficit > 0:
            disponibile = soc - soc_min
            max_scar = min(deficit / eff_scarica, disponibile, potenza_max_kw)
            energia_scar = max(max_scar, 0)
            soc -= energia_scar
            deficit_residuo = deficit - energia_scar * eff_scarica
        else:
            deficit_residuo = 0

        # 3. Arbitraggio: carica da rete se prezzo basso
        if prezzo_acq < soglia_bassa[i] and surplus == 0:
            spazio = soc_max - soc
            potenza_disp = potenza_max_kw - energia_car
            max_car_arb = min(spazio, max(potenza_disp, 0))
            if max_car_arb > 0:
                costo_carica = prezzo_acq / eff_carica
                # Carica solo se conviene (prezzo basso * RTE < prezzo alto medio)
                if costo_carica < float(np.mean(prezzi_vendita)) * 0.9:
                    energia_car_arb = max_car_arb * eff_carica
                    soc += energia_car_arb
                    energia_car += energia_car_arb
                    deficit_residuo += max_car_arb  # acquisto da rete

        # 4. Arbitraggio: scarica in rete se prezzo alto
        if prezzo_ven > soglia_alta[i] and deficit == 0:
            disponibile = soc - soc_min
            potenza_disp = potenza_max_kw - energia_scar
            max_scar_arb = min(disponibile, max(potenza_disp, 0))
            if max_scar_arb > 0:
                ricavo = prezzo_ven * eff_scarica
                if ricavo > float(np.mean(prezzi_acquisto)) * rte:
                    soc -= max_scar_arb
                    energia_scar += max_scar_arb * eff_scarica
                    surplus_residuo += max_scar_arb * eff_scarica

        soc_arr[i] = soc / capacita_kwh * 100 if capacita_kwh > 0 else 0
        caricata[i] = energia_car
        scaricata[i] = energia_scar
        imm_residua[i] = max(surplus_residuo, 0)
        prel_residuo[i] = max(deficit_residuo, 0)

    return {
        "soc_pct": soc_arr,
        "energia_caricata_kwh": caricata,
        "energia_scaricata_kwh": scaricata,
        "immissione_residua_kwh": imm_residua,
        "prelievo_residuo_kwh": prel_residuo,
    }
