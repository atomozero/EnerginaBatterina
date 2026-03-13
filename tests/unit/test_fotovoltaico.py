"""Test per il modulo Fotovoltaico."""

import json

import numpy as np
import pytest

from energina.moduli.fotovoltaico.modulo_fotovoltaico import ModuloFotovoltaico
from energina.moduli.fotovoltaico.pv_model import calcola_degradazione_annua


class TestPVModel:
    def test_degradazione_annua(self):
        deg = calcola_degradazione_annua(10000, 0.5, 25)
        assert len(deg) == 25
        assert deg[0]["anno"] == 1
        assert deg[0]["produzione_kwh"] == 10000  # anno 1 = base
        assert deg[0]["degradazione_cumulata_pct"] == 0
        assert deg[24]["produzione_kwh"] < 10000  # anno 25 degradato
        assert deg[24]["degradazione_cumulata_pct"] > 10

    def test_degradazione_zero(self):
        deg = calcola_degradazione_annua(10000, 0, 10)
        for d in deg:
            assert d["produzione_kwh"] == 10000


class TestModuloFotovoltaico:
    def test_produzione_pv(self, tmp_exchange_dir, output_meteo_fixture, salva_output_fixture):
        # Salva output meteo
        salva_output_fixture("meteo", output_meteo_fixture)

        config = {
            "progetto": {"nome": "test"},
            "meteo": {
                "localita": {
                    "latitudine": 41.9028,
                    "longitudine": 12.4964,
                    "altitudine": 21,
                },
            },
            "modulo": {
                "impianto": {
                    "potenza_nominale_kwp": 6.0,
                    "inclinazione_gradi": 30,
                    "azimut_gradi": 180,
                    "perdite_sistema_pct": 14.0,
                    "degradazione_annua_pct": 0.5,
                },
                "modulo": {
                    "coeff_temp_pmax_pct_c": -0.35,
                    "noct_c": 45,
                },
                "inverter": {
                    "efficienza_nominale_pct": 97.0,
                },
            },
        }

        modulo = ModuloFotovoltaico("fotovoltaico", config, tmp_exchange_dir)
        risultato = modulo.run()

        assert "serie_oraria" in risultato
        assert len(risultato["serie_oraria"]) == 8760

        riep = risultato["riepilogo"]
        # Per Roma 6kWp, produzione tipica 7000-10000 kWh/anno
        assert 3000 < riep["produzione_annua_kwh"] < 15000

        assert len(riep["produzione_mensile_kwh"]) == 12
        assert riep["ore_equivalenti"] > 500
        assert len(riep["produzione_per_anno"]) == 25
