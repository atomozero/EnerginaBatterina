"""Test di integrazione pipeline completa."""

from pathlib import Path

import pytest


class TestPipelineCompleta:
    """Test della pipeline end-to-end con dati sintetici."""

    @pytest.fixture
    def config_path(self):
        return Path(__file__).parent.parent / "fixtures" / "config_test.yaml"

    def test_pipeline_completa(self, config_path, tmp_path):
        """Esegui pipeline completa da config YAML a risultati."""
        from energina.core.direttore import Direttore

        # Override exchange dir per usare tmp
        direttore = Direttore(config_path)
        direttore.exchange_dir = tmp_path / "exchange"
        direttore.exchange_dir.mkdir()

        risultati = direttore.esegui()

        # Verifica che tutti i moduli abbiano prodotto risultati
        moduli_attesi = [
            "meteo", "pun", "fotovoltaico", "edificio",
            "contatore", "batteria", "incentivi", "economico",
            "previsione", "sensibilita", "report",
        ]
        for modulo in moduli_attesi:
            assert modulo in risultati, f"Modulo {modulo} mancante nei risultati"
            assert "_meta" in risultati[modulo]

        # Verifica indicatori economici presenti
        eco = risultati["economico"]
        assert "indicatori" in eco
        assert "flussi_cassa" in eco
        ind = eco["indicatori"]
        assert "npv_eur" in ind
        assert "irr_pct" in ind

        # Verifica contatore
        cont = risultati["contatore"]["riepilogo"]
        assert 0 <= cont["autoconsumo_pct"] <= 100

    def test_pipeline_resume(self, config_path, tmp_path):
        """Verifica che il resume da checkpoint funzioni."""
        from energina.core.direttore import Direttore

        direttore = Direttore(config_path)
        direttore.exchange_dir = tmp_path / "exchange"
        direttore.exchange_dir.mkdir()

        # Prima esecuzione
        risultati1 = direttore.esegui()

        # Resume (dovrebbe caricare da checkpoint)
        direttore2 = Direttore(config_path)
        direttore2.exchange_dir = tmp_path / "exchange"
        risultati2 = direttore2.esegui(resume=True)

        # I risultati devono essere equivalenti
        assert set(risultati1.keys()) == set(risultati2.keys())
