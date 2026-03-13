"""Modulo Economico - Analisi finanziaria NPV, IRR, payback, LCOE."""

from energina.core.base_modulo import BaseModulo
from energina.moduli.economico.analisi_investimento import (
    calcola_irr,
    calcola_lcoe,
    calcola_npv,
    calcola_payback_attualizzato,
    calcola_payback_semplice,
    calcola_roi,
)
from energina.moduli.economico.flussi_cassa import costruisci_flussi_cassa


class ModuloEconomico(BaseModulo):
    """Analisi economica completa dell'investimento PV+batteria.

    Calcola: NPV, IRR, payback semplice e attualizzato, ROI, LCOE.
    Costruisce tabella flussi di cassa su vita utile.
    """

    def get_dipendenze(self) -> list[str]:
        return ["contatore", "batteria", "incentivi", "pun"]

    def get_input_schema(self) -> dict:
        return {}

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["indicatori", "flussi_cassa"],
            "properties": {
                "indicatori": {"type": "object"},
                "flussi_cassa": {"type": "array"},
            },
        }

    def esegui(self) -> dict:
        cfg_eco = self.config.get("modulo", self.config.get("economico", {}))
        cfg_inv = cfg_eco.get("investimento", {})
        cfg_costi = cfg_eco.get("costi_esercizio", {})
        cfg_param = cfg_eco.get("parametri", {})

        # Investimento
        costo_pv = cfg_inv.get("costo_pv_eur", 9000)
        costo_batt = cfg_inv.get("costo_batteria_eur", 6000)
        costo_inst = cfg_inv.get("costo_installazione_eur", 2000)
        costo_prog = cfg_inv.get("costo_progettazione_eur", 500)
        investimento_totale = costo_pv + costo_batt + costo_inst + costo_prog

        # Costi esercizio
        manutenzione = cfg_costi.get("manutenzione_annua_eur", 200)
        assicurazione = cfg_costi.get("assicurazione_annua_eur", 100)
        costi_esercizio = manutenzione + assicurazione

        # Sostituzione inverter
        anno_sost_inv = cfg_costi.get("sostituzione_inverter_anno", 12)
        costo_inv = cfg_costi.get("costo_inverter_eur", 1500)

        # Parametri finanziari
        tasso_sconto = cfg_param.get("tasso_sconto_pct", 5.0) / 100
        vita_utile = cfg_param.get("vita_utile_anni", 25)
        inflazione = cfg_param.get("inflazione_pct", 2.0)
        escalation = cfg_param.get("escalation_prezzo_energia_pct", 3.0)

        # Dati upstream
        contatore = self._input_dati.get("contatore", {})
        batteria = self._input_dati.get("batteria", {})
        incentivi = self._input_dati.get("incentivi", {})
        pun = self._input_dati.get("pun", {})

        riep_cont = contatore.get("riepilogo", {})
        riep_batt = batteria.get("riepilogo", {})
        riep_inc = incentivi.get("riepilogo", {})
        riep_pun = pun.get("riepilogo", {})

        # Flussi energetici (post-batteria se disponibili)
        flussi_en = riep_batt.get("flussi_energetici_rivisti", {})
        autoconsumo_kwh = riep_cont.get("autoconsumo_kwh", 0)
        immissione_kwh = flussi_en.get("immissione_kwh", riep_cont.get("immissione_kwh", 0))
        prelievo_kwh = flussi_en.get("prelievo_kwh", riep_cont.get("prelievo_kwh", 0))

        # Aggiunta autoconsumo dalla batteria
        energia_scaricata = riep_batt.get("energia_scaricata_totale_kwh", 0)
        autoconsumo_totale = autoconsumo_kwh + energia_scaricata

        # Prezzi
        prezzo_acquisto = riep_pun.get("prezzo_acquisto_medio_eur_kwh", 0.25)
        prezzo_vendita = riep_pun.get("prezzo_vendita_medio_eur_kwh", 0.08)

        # Calcolo risparmio e ricavi anno 1
        risparmio_autoconsumo = autoconsumo_totale * prezzo_acquisto
        ricavo_vendita = immissione_kwh * prezzo_vendita

        # Incentivi per anno
        incentivi_per_anno = riep_inc.get("incentivi_per_anno", [
            {"anno": i, "incentivo_totale_eur": 0} for i in range(1, vita_utile + 1)
        ])

        # Degradazione
        degr = riep_batt.get("degradazione", {})
        pv_meta = self._input_dati.get("fotovoltaico", {}).get("riepilogo", {})
        degradazione_pv = pv_meta.get("produzione_per_anno", [])
        if degradazione_pv:
            deg_pct = 0.5  # default
        else:
            deg_pct = 0.5

        # Costruisci flussi di cassa
        flussi = costruisci_flussi_cassa(
            investimento_totale=investimento_totale,
            risparmio_autoconsumo_anno1=risparmio_autoconsumo,
            ricavo_vendita_anno1=ricavo_vendita,
            incentivi_per_anno=incentivi_per_anno,
            costi_esercizio_annui=costi_esercizio,
            vita_utile_anni=vita_utile,
            escalation_prezzo_pct=escalation,
            inflazione_pct=inflazione,
            degradazione_produzione_pct=deg_pct,
            costo_sostituzione_inverter=costo_inv,
            anno_sostituzione_inverter=anno_sost_inv,
        )

        # Array flussi netti per calcoli
        flussi_netti = [f["flusso_netto_eur"] for f in flussi]

        # Indicatori
        npv = calcola_npv(flussi_netti, tasso_sconto)
        irr = calcola_irr(flussi_netti)
        payback = calcola_payback_semplice(flussi_netti)
        payback_att = calcola_payback_attualizzato(flussi_netti, tasso_sconto)

        guadagno_netto = sum(flussi_netti)
        roi = calcola_roi(investimento_totale, guadagno_netto)

        # LCOE
        prod_annue = []
        produzione_anno1 = riep_cont.get("produzione_annua_kwh", 0)
        for anno in range(1, vita_utile + 1):
            fattore = (1 - deg_pct / 100) ** (anno - 1)
            prod_annue.append(produzione_anno1 * fattore)

        lcoe = calcola_lcoe(investimento_totale, costi_esercizio, prod_annue, tasso_sconto)

        return {
            "metadata": {
                "investimento_totale_eur": investimento_totale,
                "tasso_sconto_pct": tasso_sconto * 100,
                "vita_utile_anni": vita_utile,
            },
            "indicatori": {
                "npv_eur": round(npv, 2),
                "irr_pct": round(irr * 100, 2) if irr is not None else None,
                "payback_semplice_anni": round(payback, 1) if payback is not None else None,
                "payback_attualizzato_anni": round(payback_att, 1) if payback_att is not None else None,
                "roi_pct": round(roi, 1),
                "lcoe_eur_kwh": round(lcoe, 4),
                "risparmio_autoconsumo_anno1_eur": round(risparmio_autoconsumo, 2),
                "ricavo_vendita_anno1_eur": round(ricavo_vendita, 2),
            },
            "flussi_cassa": flussi,
        }
