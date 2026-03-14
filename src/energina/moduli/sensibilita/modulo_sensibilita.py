"""Modulo Sensibilita - Analisi what-if e sweep parametri."""

from energina.core.base_modulo import BaseModulo
from energina.moduli.sensibilita.scenario_runner import (
    esegui_sweep_parametro,
    genera_variazioni_percentuali,
)


class ModuloSensibilita(BaseModulo):
    """Analisi di sensibilita: variazione parametri e impatto su NPV/IRR.

    Supporta:
    - Sweep percentuale (es. costo PV +/-30%)
    - Sweep valori assoluti (es. potenza 3/6/9 kWp)
    - Tornado diagram data
    """

    def get_dipendenze(self) -> list[str]:
        return ["economico", "incentivi", "contatore", "fotovoltaico"]

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
        cfg_sens = self.config.get("modulo", self.config.get("sensibilita", {}))
        variabili = cfg_sens.get("variabili", [])

        economico = self._input_dati.get("economico", {})
        indicatori = economico.get("indicatori", {})
        flussi = economico.get("flussi_cassa", [])
        meta = economico.get("metadata", {})

        # Costruisci dati base per lo scenario runner
        flussi_base = self._costruisci_base(economico)

        risultati_sweep = []
        tornado_data = []

        for var in variabili:
            nome = var.get("nome", "")
            if not nome:
                continue

            # Genera valori da testare
            if "valori" in var:
                valori = var["valori"]
            else:
                valore_base = self._get_valore_base(nome, flussi_base)
                min_pct = var.get("min_pct", -20)
                max_pct = var.get("max_pct", 20)
                passi = var.get("passi", 5)
                valori = genera_variazioni_percentuali(valore_base, min_pct, max_pct, passi)

            # Esegui sweep
            risultati = esegui_sweep_parametro(
                config_base=self.config,
                flussi_base=flussi_base,
                nome_variabile=nome,
                valori=valori,
            )
            risultati_sweep.append({
                "variabile": nome,
                "risultati": risultati,
            })

            # Dati per tornado diagram (min e max NPV)
            npvs = [r["npv_eur"] for r in risultati if r["npv_eur"] is not None]
            if npvs:
                tornado_data.append({
                    "variabile": nome,
                    "npv_min_eur": min(npvs),
                    "npv_max_eur": max(npvs),
                    "npv_range_eur": max(npvs) - min(npvs),
                })

        # Ordina tornado per range (piu influente prima)
        tornado_data.sort(key=lambda x: x["npv_range_eur"], reverse=True)

        return {
            "metadata": {
                "n_variabili": len(variabili),
                "npv_base_eur": indicatori.get("npv_eur", 0),
            },
            "riepilogo": {
                "scenari": risultati_sweep,
                "tornado": tornado_data,
            },
        }

    def _costruisci_base(self, economico: dict) -> dict:
        """Costruisci dati base per scenario runner dagli output economici."""
        indicatori = economico.get("indicatori", {})
        meta = economico.get("metadata", {})

        cfg_eco = self.config.get("modulo", self.config.get("economico", {}))
        cfg_inv = cfg_eco.get("investimento", {})
        cfg_costi = cfg_eco.get("costi_esercizio", {})
        cfg_param = cfg_eco.get("parametri", {})

        costo_pv = cfg_inv.get("costo_pv_eur", 9000)
        costo_batt = cfg_inv.get("costo_batteria_eur", 6000)
        costo_inst = cfg_inv.get("costo_installazione_eur", 2000)

        # Incentivi per anno
        incentivi = self._input_dati.get("incentivi", {})
        incentivi_per_anno = incentivi.get("riepilogo", {}).get("incentivi_per_anno", [
            {"anno": i, "incentivo_totale_eur": 0} for i in range(1, 26)
        ])

        # Dati reali da moduli upstream
        pv_data = self._input_dati.get("fotovoltaico", {})
        cont_data = self._input_dati.get("contatore", {})
        potenza_kwp = pv_data.get("metadata", {}).get("potenza_nominale_kwp", 6.0)
        capacita_kwh = cfg_inv.get("capacita_batteria_kwh", 10.0)
        # Prova anche dalla config batteria
        cfg_batt = self.config.get("modulo", self.config.get("batteria", {}))
        if isinstance(cfg_batt, dict):
            spec_batt = cfg_batt.get("specifiche", {})
            if spec_batt.get("capacita_nominale_kwh"):
                capacita_kwh = spec_batt["capacita_nominale_kwh"]

        return {
            "investimento_totale": meta.get("investimento_totale_eur", 17500),
            "risparmio_autoconsumo": indicatori.get("risparmio_autoconsumo_anno1_eur", 0),
            "ricavo_vendita": indicatori.get("ricavo_vendita_anno1_eur", 0),
            "incentivi_per_anno": incentivi_per_anno,
            "costi_esercizio": cfg_costi.get("manutenzione_annua_eur", 200) + cfg_costi.get("assicurazione_annua_eur", 100),
            "vita_utile": cfg_param.get("vita_utile_anni", 25),
            "tasso_sconto": cfg_param.get("tasso_sconto_pct", 5.0) / 100,
            "escalation": cfg_param.get("escalation_prezzo_energia_pct", 3.0),
            "inflazione": cfg_param.get("inflazione_pct", 2.0),
            "degradazione": 0.5,
            "costo_pv": costo_pv,
            "costo_batteria": costo_batt,
            "costo_installazione": costo_inst,
            "costo_altro": costo_batt + costo_inst,
            "costo_pv_per_kwp": costo_pv / potenza_kwp if potenza_kwp > 0 else 1500,
            "costo_batt_per_kwh": costo_batt / capacita_kwh if capacita_kwh > 0 else 600,
            "prezzo_energia_base": 0.25,
            "potenza_base_kwp": potenza_kwp,
            "capacita_base_kwh": capacita_kwh,
        }

    def _get_valore_base(self, nome: str, flussi_base: dict) -> float:
        """Ottieni valore base per una variabile."""
        mapping = {
            "costo_pv_eur": flussi_base.get("costo_pv", 9000),
            "costo_batteria_eur": flussi_base.get("costo_batteria", 6000),
            "prezzo_energia": flussi_base.get("prezzo_energia_base", 0.25),
            "tasso_sconto": flussi_base.get("tasso_sconto", 0.05) * 100,
            "potenza_nominale_kwp": flussi_base.get("potenza_base_kwp", 6.0),
            "capacita_nominale_kwh": flussi_base.get("capacita_base_kwh", 10.0),
        }
        return mapping.get(nome, 1.0)
