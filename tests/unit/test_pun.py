"""Test per il modulo PUN."""

import numpy as np
import pytest

from energina.moduli.pun.modulo_pun import ModuloPUN


class TestModuloPUN:
    def test_pun_sintetico(self, tmp_exchange_dir):
        config = {
            "progetto": {"nome": "test"},
            "meteo": {"localita": {"latitudine": 41.9, "longitudine": 12.5}},
            "modulo": {
                "zona_mercato": "CSUD",
                "anno": 2023,
                "tariffa_acquisto": {
                    "tipo": "pun_indicizzata",
                    "oneri_sistema_eur_kwh": 0.08,
                    "accise_eur_kwh": 0.0227,
                    "iva_pct": 10.0,
                },
                "tariffa_vendita": {
                    "prezzo_minimo_garantito_eur_kwh": 0.04,
                },
            },
        }
        modulo = ModuloPUN("pun", config, tmp_exchange_dir)
        risultato = modulo.run()

        assert len(risultato["serie_oraria"]) == 8760

        # Verifica campi
        prima_ora = risultato["serie_oraria"][0]
        assert "pun_eur_mwh" in prima_ora
        assert "prezzo_acquisto_eur_kwh" in prima_ora
        assert "prezzo_vendita_eur_kwh" in prima_ora
        assert "fascia_oraria" in prima_ora
        assert prima_ora["fascia_oraria"] in ("F1", "F2", "F3")

        # Prezzi ragionevoli
        riep = risultato["riepilogo"]
        assert 50 < riep["pun_medio_eur_mwh"] < 300
        assert riep["prezzo_acquisto_medio_eur_kwh"] > 0
        assert riep["prezzo_vendita_medio_eur_kwh"] > 0
        assert riep["prezzo_acquisto_medio_eur_kwh"] > riep["prezzo_vendita_medio_eur_kwh"]

    def test_fasce_orarie(self, tmp_exchange_dir):
        config = {
            "progetto": {"nome": "test"},
            "meteo": {"localita": {}},
            "modulo": {"zona_mercato": "CSUD", "anno": 2023},
        }
        modulo = ModuloPUN("pun", config, tmp_exchange_dir)
        risultato = modulo.run()

        riep = risultato["riepilogo"]
        medie = riep["media_per_fascia"]
        assert "F1" in medie
        assert "F2" in medie
        assert "F3" in medie
        # F1 dovrebbe essere piu alta di F3
        assert medie["F1"] > medie["F3"]
