"""Test per il core framework."""

import json
from pathlib import Path

import numpy as np
import pytest

from energina.core.exceptions import (
    ConfigError,
    DAGError,
    DipendenzaMancanteError,
    EnerginaError,
    InputValidationError,
    ModuloError,
    OutputValidationError,
)
from energina.core.json_io import carica_json, crea_meta, salva_json, valida_schema
from energina.core.time_series import (
    fascia_oraria,
    genera_indice_orario,
    is_feriale,
    ore_anno,
    raggruppa_mensile,
    serie_a_lista_dicts,
)
from energina.core.units import (
    eur_kwh_to_eur_mwh,
    eur_mwh_to_eur_kwh,
    kw_to_mw,
    kwh_to_mwh,
    mw_to_kw,
    mwh_to_kwh,
)


class TestExceptions:
    def test_gerarchia_eccezioni(self):
        assert issubclass(ConfigError, EnerginaError)
        assert issubclass(ModuloError, EnerginaError)
        assert issubclass(InputValidationError, ModuloError)
        assert issubclass(DAGError, EnerginaError)

    def test_modulo_error_format(self):
        e = ModuloError("meteo", "dati mancanti")
        assert "meteo" in str(e)
        assert "dati mancanti" in str(e)


class TestJsonIO:
    def test_salva_e_carica(self, tmp_path):
        dati = {"chiave": "valore", "numero": 42}
        path = tmp_path / "test.json"
        salva_json(dati, path)
        caricato = carica_json(path)
        assert caricato == dati

    def test_carica_file_inesistente(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            carica_json(tmp_path / "inesistente.json")

    def test_crea_meta(self):
        meta = crea_meta("meteo", "0.1.0", 1.23)
        assert meta["modulo"] == "meteo"
        assert meta["versione"] == "0.1.0"
        assert meta["durata_s"] == 1.23
        assert "timestamp_esecuzione" in meta

    def test_valida_schema_ok(self):
        schema = {"type": "object", "required": ["nome"]}
        dati = {"nome": "test"}
        valida_schema(dati, schema, "test_modulo")

    def test_valida_schema_input_fallito(self):
        schema = {"type": "object", "required": ["nome"]}
        with pytest.raises(InputValidationError):
            valida_schema({}, schema, "test_modulo", direzione="input")

    def test_valida_schema_output_fallito(self):
        schema = {"type": "object", "required": ["nome"]}
        with pytest.raises(OutputValidationError):
            valida_schema({}, schema, "test_modulo", direzione="output")


class TestTimeSeries:
    def test_genera_indice_orario_standard(self):
        idx = genera_indice_orario(2023)
        assert len(idx) == 8760

    def test_genera_indice_orario_bisestile(self):
        idx = genera_indice_orario(2024)
        assert len(idx) == 8784

    def test_ore_anno(self):
        assert ore_anno(2023) == 8760
        assert ore_anno(2024) == 8784

    def test_is_feriale(self):
        from datetime import datetime
        assert is_feriale(datetime(2023, 1, 2))  # lunedi
        assert not is_feriale(datetime(2023, 1, 1))  # domenica

    def test_fascia_oraria_f1(self):
        assert fascia_oraria(10, True) == "F1"
        assert fascia_oraria(18, True) == "F1"

    def test_fascia_oraria_f2(self):
        assert fascia_oraria(7, True) == "F2"
        assert fascia_oraria(20, True) == "F2"

    def test_fascia_oraria_f3(self):
        assert fascia_oraria(3, True) == "F3"
        assert fascia_oraria(12, False) == "F3"  # weekend

    def test_serie_a_lista_dicts(self):
        idx = genera_indice_orario(2023)[:3]
        valori = np.array([1.0, 2.0, 3.0])
        result = serie_a_lista_dicts(idx, test=valori)
        assert len(result) == 3
        assert result[0]["test"] == 1.0
        assert "timestamp" in result[0]

    def test_raggruppa_mensile(self):
        valori = np.ones(8760)
        mensili = raggruppa_mensile(valori, 2023)
        assert len(mensili) == 12
        assert sum(mensili) == pytest.approx(8760, abs=1)


class TestUnits:
    def test_kwh_mwh(self):
        assert kwh_to_mwh(1000) == 1.0
        assert mwh_to_kwh(1) == 1000.0

    def test_kw_mw(self):
        assert kw_to_mw(1000) == 1.0
        assert mw_to_kw(1) == 1000.0

    def test_eur_conversions(self):
        assert eur_mwh_to_eur_kwh(100) == 0.1
        assert eur_kwh_to_eur_mwh(0.1) == 100.0
