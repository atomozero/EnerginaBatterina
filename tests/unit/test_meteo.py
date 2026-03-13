"""Test per il modulo Meteo."""

import numpy as np
import pytest

from energina.moduli.meteo.modulo_meteo import ModuloMeteo


class TestModuloMeteo:
    def test_meteo_sintetico(self, tmp_exchange_dir, config_residenziale):
        config = config_residenziale.copy()
        config["modulo"] = config["meteo"]
        modulo = ModuloMeteo("meteo", config, tmp_exchange_dir)
        risultato = modulo.run()

        assert "_meta" in risultato
        assert risultato["_meta"]["modulo"] == "meteo"
        assert "metadata" in risultato
        assert "serie_oraria" in risultato
        assert "riepilogo" in risultato

        # Verifica lunghezza serie
        assert len(risultato["serie_oraria"]) == 8760

        # Verifica campi serie oraria
        prima_ora = risultato["serie_oraria"][0]
        assert "ghi" in prima_ora
        assert "dni" in prima_ora
        assert "dhi" in prima_ora
        assert "temp_aria" in prima_ora
        assert "vel_vento" in prima_ora

        # Verifica riepilogo
        riep = risultato["riepilogo"]
        assert riep["irradiazione_annua_kwh_mq"] > 0
        assert -10 < riep["temperatura_media_c"] < 40

    def test_meteo_zona_climatica_roma(self, tmp_exchange_dir, config_residenziale):
        config = config_residenziale.copy()
        config["modulo"] = config["meteo"]
        modulo = ModuloMeteo("meteo", config, tmp_exchange_dir)
        risultato = modulo.run()

        meta = risultato["metadata"]
        assert meta["zona_climatica"] in ["C", "D"]
        assert meta["gradi_giorno"] > 1000

    def test_output_salvato(self, tmp_exchange_dir, config_residenziale):
        config = config_residenziale.copy()
        config["modulo"] = config["meteo"]
        modulo = ModuloMeteo("meteo", config, tmp_exchange_dir)
        modulo.run()

        output_file = tmp_exchange_dir / "meteo_output.json"
        assert output_file.exists()
