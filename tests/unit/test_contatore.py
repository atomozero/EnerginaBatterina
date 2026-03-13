"""Test per il modulo Contatore."""

import json

import numpy as np
import pytest

from energina.moduli.contatore.modulo_contatore import ModuloContatore


class TestModuloContatore:
    def _crea_output_pv(self, n=8760):
        """Crea output PV sintetico."""
        from datetime import datetime, timedelta
        base = datetime(2023, 1, 1)
        serie = []
        for i in range(n):
            ts = base + timedelta(hours=i)
            ora = ts.hour
            # Produzione PV solo di giorno
            if 6 <= ora <= 20:
                pot = max(0, 4.0 * np.sin(np.pi * (ora - 6) / 14))
            else:
                pot = 0
            serie.append({
                "timestamp": ts.isoformat(),
                "potenza_ac_kw": round(pot, 2),
                "energia_kwh": round(pot, 2),
                "temp_cella_c": 25.0,
            })
        return {
            "_meta": {"modulo": "fotovoltaico", "versione": "0.1.0",
                      "timestamp_esecuzione": "2023-01-01", "durata_s": 0.1},
            "metadata": {"potenza_nominale_kwp": 6.0},
            "serie_oraria": serie,
            "riepilogo": {"produzione_annua_kwh": 8000},
        }

    def _crea_output_edificio(self, n=8760):
        """Crea output edificio sintetico."""
        from datetime import datetime, timedelta
        base = datetime(2023, 1, 1)
        serie = []
        consumo_giornaliero = 7.5  # kWh/giorno ~ 2740 kWh/anno
        for i in range(n):
            ts = base + timedelta(hours=i)
            ora = ts.hour
            # Profilo con picco sera
            profilo = [0.1, 0.1, 0.1, 0.1, 0.1, 0.15,
                       0.2, 0.4, 0.35, 0.25, 0.2, 0.2,
                       0.3, 0.35, 0.25, 0.2, 0.2, 0.3,
                       0.45, 0.5, 0.55, 0.45, 0.3, 0.15]
            consumo = consumo_giornaliero * profilo[ora] / sum(profilo)
            serie.append({
                "timestamp": ts.isoformat(),
                "consumo_kwh": round(consumo, 3),
                "consumo_base_kwh": round(consumo * 0.7, 3),
                "consumo_hvac_kwh": round(consumo * 0.3, 3),
            })
        return {
            "_meta": {"modulo": "edificio", "versione": "0.1.0",
                      "timestamp_esecuzione": "2023-01-01", "durata_s": 0.1},
            "metadata": {"tipologia": "residenziale"},
            "serie_oraria": serie,
            "riepilogo": {"consumo_annuo_kwh": 2740},
        }

    def test_bilancio_energetico(self, tmp_exchange_dir, salva_output_fixture):
        output_pv = self._crea_output_pv()
        output_ed = self._crea_output_edificio()
        salva_output_fixture("fotovoltaico", output_pv)
        salva_output_fixture("edificio", output_ed)

        config = {
            "progetto": {"nome": "test"},
            "meteo": {"localita": {}},
            "modulo": {"tipo": "bidirezionale"},
        }

        modulo = ModuloContatore("contatore", config, tmp_exchange_dir)
        risultato = modulo.run()

        riep = risultato["riepilogo"]
        assert riep["autoconsumo_kwh"] > 0
        assert riep["immissione_kwh"] >= 0
        assert riep["prelievo_kwh"] >= 0
        assert 0 <= riep["autoconsumo_pct"] <= 100
        assert 0 <= riep["autosufficienza_pct"] <= 100

        # Verifica bilancio: autoconsumo + immissione = produzione
        prod = riep["produzione_annua_kwh"]
        assert riep["autoconsumo_kwh"] + riep["immissione_kwh"] == pytest.approx(prod, abs=1)

        # autoconsumo + prelievo = consumo
        cons = riep["consumo_annuo_kwh"]
        assert riep["autoconsumo_kwh"] + riep["prelievo_kwh"] == pytest.approx(cons, abs=1)
