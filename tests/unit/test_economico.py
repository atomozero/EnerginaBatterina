"""Test per il modulo Economico."""

import pytest

from energina.moduli.economico.analisi_investimento import (
    calcola_irr,
    calcola_lcoe,
    calcola_npv,
    calcola_payback_semplice,
    calcola_roi,
)
from energina.moduli.economico.flussi_cassa import costruisci_flussi_cassa


class TestAnalisiInvestimento:
    def test_npv_positivo(self):
        # Investimento 10000 con flussi da 2000/anno per 10 anni
        flussi = [-10000] + [2000] * 10
        npv = calcola_npv(flussi, 0.05)
        assert npv > 0  # investimento profittevole

    def test_npv_negativo(self):
        flussi = [-10000] + [500] * 10
        npv = calcola_npv(flussi, 0.05)
        assert npv < 0

    def test_npv_tasso_zero(self):
        flussi = [-1000] + [200] * 10
        npv = calcola_npv(flussi, 0)
        assert npv == pytest.approx(1000, abs=1)

    def test_irr(self):
        flussi = [-10000] + [2000] * 10
        irr = calcola_irr(flussi)
        assert irr is not None
        assert 0.05 < irr < 0.20

    def test_payback(self):
        flussi = [-10000] + [2000] * 10
        pb = calcola_payback_semplice(flussi)
        assert pb is not None
        assert 4 < pb < 6  # ~5 anni

    def test_payback_mai_recuperato(self):
        flussi = [-10000] + [100] * 5
        pb = calcola_payback_semplice(flussi)
        assert pb is None

    def test_roi(self):
        roi = calcola_roi(10000, 5000)
        assert roi == 50.0

    def test_lcoe(self):
        lcoe = calcola_lcoe(
            investimento_totale=17500,
            costi_om_annui=300,
            produzione_annua_kwh=[8000 * (1 - 0.005) ** i for i in range(25)],
            tasso_sconto=0.05,
        )
        assert 0.05 < lcoe < 0.30  # range ragionevole per PV residenziale


class TestFlussiCassa:
    def test_flussi_base(self):
        incentivi = [{"anno": i, "incentivo_totale_eur": 875} for i in range(1, 11)]
        incentivi += [{"anno": i, "incentivo_totale_eur": 0} for i in range(11, 26)]

        flussi = costruisci_flussi_cassa(
            investimento_totale=17500,
            risparmio_autoconsumo_anno1=1500,
            ricavo_vendita_anno1=300,
            incentivi_per_anno=incentivi,
            costi_esercizio_annui=300,
            vita_utile_anni=25,
        )

        assert len(flussi) == 26  # anno 0 + 25 anni
        assert flussi[0]["flusso_netto_eur"] == -17500
        assert flussi[0]["flusso_cumulato_eur"] == -17500
        assert flussi[1]["flusso_netto_eur"] > 0  # primo anno positivo

    def test_flussi_cumulati_crescenti(self):
        incentivi = [{"anno": i, "incentivo_totale_eur": 500} for i in range(1, 26)]
        flussi = costruisci_flussi_cassa(
            investimento_totale=10000,
            risparmio_autoconsumo_anno1=1000,
            ricavo_vendita_anno1=200,
            incentivi_per_anno=incentivi,
            costi_esercizio_annui=200,
            vita_utile_anni=25,
        )
        # I flussi cumulati devono crescere (flussi netti positivi)
        for i in range(2, len(flussi)):
            assert flussi[i]["flusso_cumulato_eur"] > flussi[i-1]["flusso_cumulato_eur"]
