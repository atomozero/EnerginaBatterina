"""Modulo Report - Generazione PDF professionale con grafici e tabelle."""

from pathlib import Path

from energina.core.base_modulo import BaseModulo
from energina.moduli.report.grafici import (
    grafico_autoconsumo_pie,
    grafico_bilancio_mensile,
    grafico_flussi_cassa,
    grafico_tornado,
)
from energina.moduli.report.template_pdf import genera_pdf


class ModuloReport(BaseModulo):
    """Genera report PDF professionale con tutti i risultati dell'analisi.

    Sezioni:
    - Sommario progetto
    - Dati meteo e localita
    - Produzione fotovoltaica
    - Consumi edificio
    - Bilancio energetico
    - Accumulo batteria
    - Analisi economica
    - Previsioni
    - Sensibilita
    """

    def get_dipendenze(self) -> list[str]:
        return ["economico", "previsione", "sensibilita"]

    def get_input_schema(self) -> dict:
        return {}

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["riepilogo"],
            "properties": {
                "riepilogo": {"type": "object"},
            },
        }

    def esegui(self) -> dict:
        output_dir = self.exchange_dir.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        grafici_dir = output_dir / "grafici"
        grafici_dir.mkdir(parents=True, exist_ok=True)

        # Raccogli dati da tutti i moduli
        meteo = self._input_dati.get("meteo", {})
        pv = self._input_dati.get("fotovoltaico", {})
        edificio = self._input_dati.get("edificio", {})
        contatore = self._input_dati.get("contatore", {})
        batteria = self._input_dati.get("batteria", {})
        incentivi = self._input_dati.get("incentivi", {})
        economico = self._input_dati.get("economico", {})
        previsione = self._input_dati.get("previsione", {})
        sensibilita = self._input_dati.get("sensibilita", {})

        progetto = self.config.get("progetto", {})
        titolo = f"Report - {progetto.get('nome', 'Impianto PV')}"

        # Genera grafici
        grafici_paths = self._genera_grafici(
            pv, edificio, contatore, economico, sensibilita, grafici_dir
        )

        # Costruisci sezioni
        sezioni = self._costruisci_sezioni(
            meteo, pv, edificio, contatore, batteria,
            incentivi, economico, previsione, sensibilita,
        )

        # Genera PDF
        pdf_path = output_dir / "report_energina.pdf"
        risultato_path = genera_pdf(titolo, sezioni, grafici_paths, pdf_path)

        return {
            "metadata": {
                "formato": "pdf",
                "n_sezioni": len(sezioni),
                "n_grafici": len(grafici_paths),
            },
            "riepilogo": {
                "percorso_report": str(risultato_path),
                "percorso_grafici": [str(p) for p in grafici_paths],
            },
        }

    def _genera_grafici(self, pv, edificio, contatore, economico, sensibilita, grafici_dir):
        """Genera tutti i grafici."""
        paths = []

        # Bilancio mensile
        riep_pv = pv.get("riepilogo", {})
        riep_ed = edificio.get("riepilogo", {})
        prod_mensile = riep_pv.get("produzione_mensile_kwh", [0]*12)
        cons_mensile = riep_ed.get("consumo_mensile_kwh", [0]*12)
        if prod_mensile and cons_mensile:
            p = grafico_bilancio_mensile(
                prod_mensile, cons_mensile,
                grafici_dir / "bilancio_mensile.png",
            )
            paths.append(p)

        # Autoconsumo pie
        riep_cont = contatore.get("riepilogo", {})
        auto = riep_cont.get("autoconsumo_kwh", 0)
        imm = riep_cont.get("immissione_kwh", 0)
        prel = riep_cont.get("prelievo_kwh", 0)
        if auto > 0 or imm > 0:
            p = grafico_autoconsumo_pie(
                auto, imm, prel,
                grafici_dir / "autoconsumo_pie.png",
            )
            paths.append(p)

        # Flussi di cassa
        flussi = economico.get("flussi_cassa", [])
        if flussi:
            p = grafico_flussi_cassa(flussi, grafici_dir / "flussi_cassa.png")
            paths.append(p)

        # Tornado
        tornado = sensibilita.get("riepilogo", {}).get("tornado", [])
        npv_base = sensibilita.get("metadata", {}).get("npv_base_eur", 0)
        if tornado:
            p = grafico_tornado(tornado, npv_base, grafici_dir / "tornado.png")
            paths.append(p)

        return paths

    def _costruisci_sezioni(
        self, meteo, pv, edificio, contatore, batteria,
        incentivi, economico, previsione, sensibilita,
    ) -> list[dict]:
        """Costruisci sezioni del report."""
        sezioni = []

        # Sommario
        riep_eco = economico.get("indicatori", {})
        riep_cont = contatore.get("riepilogo", {})
        sezioni.append({
            "titolo": "Sommario Risultati",
            "testo": [
                f"Produzione annua: {riep_cont.get('produzione_annua_kwh', 'N/D')} kWh",
                f"Consumo annuo: {riep_cont.get('consumo_annuo_kwh', 'N/D')} kWh",
                f"Autoconsumo: {riep_cont.get('autoconsumo_pct', 'N/D')}%",
                f"NPV: {riep_eco.get('npv_eur', 'N/D')} EUR",
                f"IRR: {riep_eco.get('irr_pct', 'N/D')}%",
                f"Payback: {riep_eco.get('payback_semplice_anni', 'N/D')} anni",
            ],
        })

        # Dati meteo
        riep_meteo = meteo.get("riepilogo", {})
        meta_meteo = meteo.get("metadata", {})
        sezioni.append({
            "titolo": "Dati Meteorologici",
            "testo": [
                f"Localita: {meta_meteo.get('nome_localita', 'N/D')}",
                f"Zona climatica: {meta_meteo.get('zona_climatica', 'N/D')} "
                f"(GG: {meta_meteo.get('gradi_giorno', 'N/D')})",
                f"Irradiazione annua: {riep_meteo.get('irradiazione_annua_kwh_mq', 'N/D')} kWh/mq",
                f"Temperatura media: {riep_meteo.get('temperatura_media_c', 'N/D')} C",
            ],
        })

        # Produzione PV
        riep_pv = pv.get("riepilogo", {})
        meta_pv = pv.get("metadata", {})
        sezioni.append({
            "titolo": "Produzione Fotovoltaica",
            "testo": [
                f"Potenza nominale: {meta_pv.get('potenza_nominale_kwp', 'N/D')} kWp",
                f"Produzione anno 1: {riep_pv.get('produzione_annua_kwh', 'N/D')} kWh",
                f"Ore equivalenti: {riep_pv.get('ore_equivalenti', 'N/D')} h",
            ],
            "tabella": {
                "righe": [["Mese", "Produzione (kWh)"]] + [
                    [m, str(round(v, 0))]
                    for m, v in zip(
                        ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                         "Lug", "Ago", "Set", "Ott", "Nov", "Dic"],
                        riep_pv.get("produzione_mensile_kwh", [0]*12),
                    )
                ],
            },
        })

        # Bilancio energetico
        sezioni.append({
            "titolo": "Bilancio Energetico",
            "testo": [
                f"Autoconsumo: {riep_cont.get('autoconsumo_kwh', 'N/D')} kWh "
                f"({riep_cont.get('autoconsumo_pct', 'N/D')}%)",
                f"Immissione in rete: {riep_cont.get('immissione_kwh', 'N/D')} kWh",
                f"Prelievo da rete: {riep_cont.get('prelievo_kwh', 'N/D')} kWh",
                f"Autosufficienza: {riep_cont.get('autosufficienza_pct', 'N/D')}%",
            ],
        })

        # Batteria
        riep_batt = batteria.get("riepilogo", {})
        meta_batt = batteria.get("metadata", {})
        if meta_batt.get("abilitata", True) and meta_batt.get("capacita_nominale_kwh", 0) > 0:
            sezioni.append({
                "titolo": "Accumulo Batteria",
                "testo": [
                    f"Capacita: {meta_batt.get('capacita_nominale_kwh', 'N/D')} kWh "
                    f"({meta_batt.get('chimica', 'N/D')})",
                    f"Strategia: {meta_batt.get('strategia', 'N/D')}",
                    f"Cicli equivalenti/anno: {riep_batt.get('cicli_equivalenti', 'N/D')}",
                    f"Immissione post-batteria: "
                    f"{riep_batt.get('immissione_post_batteria_kwh', 'N/D')} kWh",
                    f"Prelievo post-batteria: "
                    f"{riep_batt.get('prelievo_post_batteria_kwh', 'N/D')} kWh",
                ],
            })

        # Analisi economica
        meta_eco = economico.get("metadata", {})
        sezioni.append({
            "titolo": "Analisi Economica",
            "testo": [
                f"Investimento totale: {meta_eco.get('investimento_totale_eur', 'N/D')} EUR",
                f"Tasso di sconto: {meta_eco.get('tasso_sconto_pct', 'N/D')}%",
            ],
            "tabella": {
                "righe": [
                    ["Indicatore", "Valore"],
                    ["NPV", f"{riep_eco.get('npv_eur', 'N/D')} EUR"],
                    ["IRR", f"{riep_eco.get('irr_pct', 'N/D')}%"],
                    ["Payback semplice", f"{riep_eco.get('payback_semplice_anni', 'N/D')} anni"],
                    ["Payback attualizzato", f"{riep_eco.get('payback_attualizzato_anni', 'N/D')} anni"],
                    ["ROI", f"{riep_eco.get('roi_pct', 'N/D')}%"],
                    ["LCOE", f"{riep_eco.get('lcoe_eur_kwh', 'N/D')} EUR/kWh"],
                ],
            },
        })

        # Incentivi
        riep_inc = incentivi.get("riepilogo", {})
        detr = riep_inc.get("detrazione_fiscale", {})
        rd = riep_inc.get("ritiro_dedicato", {})
        testi_inc = []
        if detr.get("abilitata"):
            testi_inc.append(
                f"Detrazione fiscale: {detr.get('rata_annua_eur', 0)} EUR/anno "
                f"per {detr.get('anni_detrazione', 0)} anni"
            )
        if rd.get("abilitato"):
            testi_inc.append(
                f"Ritiro Dedicato: {rd.get('ricavo_annuo_eur', 0)} EUR/anno"
            )
        if testi_inc:
            sezioni.append({
                "titolo": "Incentivi",
                "testo": testi_inc,
            })

        return sezioni
