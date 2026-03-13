"""Modulo Batteria - Simulatore accumulo con strategie di dispatch."""

import numpy as np

from energina.core.base_modulo import BaseModulo
from energina.core.time_series import genera_indice_orario, serie_a_lista_dicts
from energina.moduli.batteria.degradazione import calcola_cicli_equivalenti, degradazione_lineare
from energina.moduli.batteria.strategia_autoconsumo import simula_autoconsumo


class ModuloBatteria(BaseModulo):
    """Simula accumulo elettrochimico con diverse strategie.

    Strategie disponibili:
    - autoconsumo: massimizza autoconsumo (carica surplus, scarica deficit)
    - arbitraggio: compra basso, vendi alto basato su prezzi PUN
    - ibrida: autoconsumo prioritario, poi arbitraggio
    """

    def get_dipendenze(self) -> list[str]:
        return ["contatore", "pun"]

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
        cfg_batt = self.config.get("modulo", self.config.get("batteria", {}))

        if not cfg_batt.get("abilitata", True):
            return self._output_senza_batteria()

        specifiche = cfg_batt.get("specifiche", {})
        capacita = specifiche.get("capacita_nominale_kwh", 10.0)
        potenza_max = specifiche.get("potenza_max_kw", capacita / 2)
        soc_min = specifiche.get("soc_min_pct", 10.0)
        soc_max = specifiche.get("soc_max_pct", 90.0)
        eff_car = specifiche.get("efficienza_carica_pct", 95.0) / 100
        eff_scar = specifiche.get("efficienza_scarica_pct", 95.0) / 100
        chimica = specifiche.get("chimica", "LFP")
        strategia_nome = cfg_batt.get("strategia", "autoconsumo")

        cfg_degr = cfg_batt.get("degradazione", {})
        cicli_vita = cfg_degr.get("cicli_vita", 6000)
        cap_fine_vita = cfg_degr.get("capacita_fine_vita_pct", 80.0)

        # Carica dati upstream
        contatore = self._input_dati.get("contatore", {})
        pun = self._input_dati.get("pun", {})

        serie_cont = contatore.get("serie_oraria", [])
        serie_pun = pun.get("serie_oraria", [])

        n = min(len(serie_cont), len(serie_pun)) if serie_pun else len(serie_cont)

        immissione = np.array(
            [h.get("immissione_kwh", 0) for h in serie_cont[:n]], dtype=float
        )
        prelievo = np.array(
            [h.get("prelievo_kwh", 0) for h in serie_cont[:n]], dtype=float
        )

        # Simulazione strategia
        if strategia_nome == "arbitraggio" and serie_pun:
            from energina.moduli.batteria.strategia_arbitraggio import simula_arbitraggio
            prezzi_acq = np.array(
                [h.get("prezzo_acquisto_eur_kwh", 0.2) for h in serie_pun[:n]], dtype=float
            )
            prezzi_ven = np.array(
                [h.get("prezzo_vendita_eur_kwh", 0.1) for h in serie_pun[:n]], dtype=float
            )
            ris = simula_arbitraggio(
                immissione, prelievo, prezzi_acq, prezzi_ven,
                capacita, potenza_max, soc_min, soc_max, eff_car, eff_scar,
            )
        elif strategia_nome == "ibrida" and serie_pun:
            # Ibrida = autoconsumo con leggero arbitraggio
            from energina.moduli.batteria.strategia_arbitraggio import simula_arbitraggio
            prezzi_acq = np.array(
                [h.get("prezzo_acquisto_eur_kwh", 0.2) for h in serie_pun[:n]], dtype=float
            )
            prezzi_ven = np.array(
                [h.get("prezzo_vendita_eur_kwh", 0.1) for h in serie_pun[:n]], dtype=float
            )
            ris = simula_arbitraggio(
                immissione, prelievo, prezzi_acq, prezzi_ven,
                capacita, potenza_max, soc_min, soc_max, eff_car, eff_scar,
            )
        else:
            ris = simula_autoconsumo(
                immissione, prelievo,
                capacita, potenza_max, soc_min, soc_max, eff_car, eff_scar,
            )

        # Cicli equivalenti e degradazione
        cicli_eq = calcola_cicli_equivalenti(ris["energia_caricata_kwh"], capacita)
        rte = eff_car * eff_scar
        vita_utile = self.config.get("progetto", {}).get("vita_utile_anni", 25)
        degr = degradazione_lineare(cicli_eq, cicli_vita, cap_fine_vita, vita_utile)

        # Anno
        anno = 2023
        if serie_cont and "timestamp" in serie_cont[0]:
            try:
                anno = int(serie_cont[0]["timestamp"][:4])
            except (ValueError, IndexError):
                pass

        indice = genera_indice_orario(anno)[:n]
        serie = serie_a_lista_dicts(
            indice,
            soc_pct=ris["soc_pct"],
            energia_caricata_kwh=ris["energia_caricata_kwh"],
            energia_scaricata_kwh=ris["energia_scaricata_kwh"],
            immissione_residua_kwh=ris["immissione_residua_kwh"],
            prelievo_residuo_kwh=ris["prelievo_residuo_kwh"],
        )

        return {
            "metadata": {
                "capacita_nominale_kwh": capacita,
                "potenza_max_kw": potenza_max,
                "chimica": chimica,
                "strategia": strategia_nome,
            },
            "serie_oraria": serie,
            "riepilogo": {
                "cicli_equivalenti": round(cicli_eq, 1),
                "rte_medio": round(rte, 3),
                "energia_caricata_totale_kwh": round(float(np.sum(ris["energia_caricata_kwh"])), 1),
                "energia_scaricata_totale_kwh": round(float(np.sum(ris["energia_scaricata_kwh"])), 1),
                "immissione_post_batteria_kwh": round(float(np.sum(ris["immissione_residua_kwh"])), 1),
                "prelievo_post_batteria_kwh": round(float(np.sum(ris["prelievo_residuo_kwh"])), 1),
                "flussi_energetici_rivisti": {
                    "immissione_kwh": round(float(np.sum(ris["immissione_residua_kwh"])), 1),
                    "prelievo_kwh": round(float(np.sum(ris["prelievo_residuo_kwh"])), 1),
                },
                "degradazione": {
                    "capacita_fine_anno_pct": [d["capacita_residua_pct"] for d in degr],
                },
            },
        }

    def _output_senza_batteria(self) -> dict:
        """Output quando batteria non abilitata."""
        contatore = self._input_dati.get("contatore", {})
        riep_cont = contatore.get("riepilogo", {})

        return {
            "metadata": {"abilitata": False},
            "serie_oraria": [],
            "riepilogo": {
                "cicli_equivalenti": 0,
                "rte_medio": 0,
                "energia_caricata_totale_kwh": 0,
                "energia_scaricata_totale_kwh": 0,
                "immissione_post_batteria_kwh": riep_cont.get("immissione_kwh", 0),
                "prelievo_post_batteria_kwh": riep_cont.get("prelievo_kwh", 0),
                "flussi_energetici_rivisti": {
                    "immissione_kwh": riep_cont.get("immissione_kwh", 0),
                    "prelievo_kwh": riep_cont.get("prelievo_kwh", 0),
                },
                "degradazione": {"capacita_fine_anno_pct": []},
            },
        }
