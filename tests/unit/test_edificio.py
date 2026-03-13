"""Test per il modulo Edificio."""

import numpy as np
import pytest

from energina.moduli.edificio.modulo_edificio import ModuloEdificio
from energina.moduli.edificio.profili_carico import genera_consumo_base
from energina.moduli.edificio.zona_climatica import (
    calcola_fabbisogno_raffrescamento,
    calcola_fabbisogno_riscaldamento,
    get_gradi_giorno,
)


class TestZonaClimatica:
    def test_gradi_giorno_roma(self):
        gg = get_gradi_giorno("Roma", 41.9)
        assert 1400 <= gg <= 1500

    def test_gradi_giorno_milano(self):
        gg = get_gradi_giorno("Milano", 45.5)
        assert 2300 <= gg <= 2500

    def test_riscaldamento_zero_estate(self):
        temp = np.full(24, 30.0)  # 30C = no riscaldamento
        fabb = calcola_fabbisogno_riscaldamento(temp, 120, 1415)
        assert np.all(fabb == 0)

    def test_riscaldamento_inverno(self):
        temp = np.full(24, 5.0)  # 5C = serve riscaldamento
        fabb = calcola_fabbisogno_riscaldamento(temp, 120, 1415)
        assert np.all(fabb > 0)

    def test_raffrescamento_zero_inverno(self):
        temp = np.full(24, 15.0)  # 15C = no raffrescamento
        fabb = calcola_fabbisogno_raffrescamento(temp, 120)
        assert np.all(fabb == 0)


class TestProfilCarico:
    def test_genera_consumo_residenziale(self):
        consumo = genera_consumo_base("residenziale", 2023, superficie_mq=120, n_occupanti=4)
        assert len(consumo) == 8760
        assert np.all(consumo >= 0)
        # Consumo annuo tipico residenziale ~1800-3000 kWh
        totale = np.sum(consumo)
        assert 1000 < totale < 5000


class TestModuloEdificio:
    def test_edificio_completo(self, tmp_exchange_dir, output_meteo_fixture, salva_output_fixture):
        salva_output_fixture("meteo", output_meteo_fixture)

        config = {
            "progetto": {"nome": "test"},
            "meteo": {"localita": {"latitudine": 41.9, "longitudine": 12.5, "nome": "Roma"}},
            "modulo": {
                "tipologia": "residenziale",
                "parametri": {"superficie_mq": 120, "n_occupanti": 4},
                "climatizzazione": {
                    "riscaldamento": "pompa_di_calore",
                    "raffrescamento": True,
                    "cop_medio": 3.5,
                    "eer_medio": 3.0,
                },
            },
        }

        modulo = ModuloEdificio("edificio", config, tmp_exchange_dir)
        risultato = modulo.run()

        riep = risultato["riepilogo"]
        assert riep["consumo_annuo_kwh"] > 0
        # Residenziale italiano tipico: 2000-4000 kWh con HVAC
        assert 1000 < riep["consumo_annuo_kwh"] < 8000
        assert len(riep["consumo_mensile_kwh"]) == 12
