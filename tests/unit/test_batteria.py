"""Test per il modulo Batteria."""

import numpy as np
import pytest

from energina.moduli.batteria.degradazione import (
    calcola_cicli_equivalenti,
    degradazione_lineare,
)
from energina.moduli.batteria.strategia_autoconsumo import simula_autoconsumo


class TestDegradazione:
    def test_degradazione_lineare_lfp(self):
        deg = degradazione_lineare(
            cicli_equivalenti_anno=300,
            cicli_vita=6000,
            capacita_fine_vita_pct=80.0,
            vita_utile_anni=25,
        )
        assert len(deg) == 25
        assert deg[0]["capacita_residua_pct"] > 99
        # A 6000 cicli -> 80%, a 300/anno -> 20 anni
        assert deg[19]["capacita_residua_pct"] == pytest.approx(80.0, abs=1)

    def test_cicli_equivalenti(self):
        caricata = np.array([5.0, 3.0, 2.0])  # 10 kWh totali
        cicli = calcola_cicli_equivalenti(caricata, 10.0)
        assert cicli == 1.0


class TestStrategiaAutoconsumo:
    def test_carica_da_surplus(self):
        immissione = np.array([5.0, 0.0, 0.0])
        prelievo = np.array([0.0, 3.0, 0.0])

        ris = simula_autoconsumo(
            immissione, prelievo,
            capacita_kwh=10.0,
            potenza_max_kw=5.0,
            soc_min_pct=10.0,
            soc_max_pct=90.0,
            eff_carica=1.0,  # efficienza 100% per semplicita test
            eff_scarica=1.0,
        )

        # Dopo carica, SOC deve salire
        assert ris["soc_pct"][0] > 50  # partenza 50%
        assert ris["energia_caricata_kwh"][0] > 0

        # Dopo scarica per deficit
        assert ris["energia_scaricata_kwh"][1] > 0
        assert ris["prelievo_residuo_kwh"][1] < prelievo[1]

    def test_rispetta_limiti_soc(self):
        # Tanto surplus, poco spazio
        immissione = np.array([100.0])
        prelievo = np.array([0.0])

        ris = simula_autoconsumo(
            immissione, prelievo,
            capacita_kwh=10.0,
            potenza_max_kw=5.0,
            soc_min_pct=10.0,
            soc_max_pct=90.0,
            eff_carica=1.0,
            eff_scarica=1.0,
            soc_iniziale_pct=85.0,
        )

        # SOC non deve superare soc_max (90%)
        assert ris["soc_pct"][0] <= 90.0 + 0.1

    def test_no_surplus_no_carica(self):
        immissione = np.zeros(10)
        prelievo = np.zeros(10)

        ris = simula_autoconsumo(
            immissione, prelievo,
            capacita_kwh=10.0,
            potenza_max_kw=5.0,
            soc_min_pct=10.0,
            soc_max_pct=90.0,
            eff_carica=0.95,
            eff_scarica=0.95,
        )

        assert np.all(ris["energia_caricata_kwh"] == 0)
        assert np.all(ris["energia_scaricata_kwh"] == 0)
