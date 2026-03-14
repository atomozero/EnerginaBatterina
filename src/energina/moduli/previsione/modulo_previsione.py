"""Modulo Previsione - Forecasting multi-anno prezzi e produzione."""

from energina.core.base_modulo import BaseModulo
from energina.moduli.previsione.previsore_prezzi import previsione_trend_lineare
from energina.moduli.previsione.previsore_produzione import previsione_con_degradazione


class ModuloPrevisione(BaseModulo):
    """Genera previsioni multi-anno per prezzi energia e produzione PV.

    Metodi disponibili:
    - Prezzi: trend_lineare, sarima
    - Produzione: degradazione lineare, sarima
    """

    def get_dipendenze(self) -> list[str]:
        return ["economico", "pun", "contatore", "fotovoltaico"]

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
        cfg_prev = self.config.get("modulo", self.config.get("previsione", {}))
        orizzonte = cfg_prev.get("orizzonte_anni", 25)
        metodo_prezzi = cfg_prev.get("metodo_prezzi", "trend_lineare")
        metodo_produzione = cfg_prev.get("metodo_produzione", "degradazione")

        # Dati da upstream
        economico = self._input_dati.get("economico", {})
        pun = self._input_dati.get("pun", {})
        contatore = self._input_dati.get("contatore", {})

        # Prezzo medio anno 1
        riep_pun = pun.get("riepilogo", {})
        prezzo_medio = riep_pun.get("pun_medio_eur_mwh", 120)

        # Escalation dalla config economica
        cfg_eco = self.config.get("modulo", {}).get("parametri", {})
        escalation = cfg_eco.get("escalation_prezzo_energia_pct", 3.0)
        # Se non trovato, cerca in config globale
        if escalation == 3.0:
            eco_glob = self.config.get("progetto", {})
            escalation = eco_glob.get("escalation_prezzo_energia_pct", 3.0)

        # Previsione prezzi
        if metodo_prezzi == "sarima":
            from energina.moduli.previsione.previsore_prezzi import previsione_sarima
            # Usa prezzi orari come base (aggregati mensilmente)
            serie_pun = pun.get("serie_oraria", [])
            if serie_pun:
                import numpy as np
                prezzi = [h.get("pun_eur_mwh", 120) for h in serie_pun]
                # Aggrega in mensili (media)
                n_mesi = len(prezzi) // (24 * 30)
                mensili = []
                for m in range(max(n_mesi, 1)):
                    start = m * 24 * 30
                    end = min(start + 24 * 30, len(prezzi))
                    mensili.append(float(np.mean(prezzi[start:end])))
                prev_prezzi = previsione_sarima(mensili, orizzonte * 12)
            else:
                prev_prezzi = previsione_trend_lineare(prezzo_medio, escalation, orizzonte)
        else:
            prev_prezzi = previsione_trend_lineare(prezzo_medio, escalation, orizzonte)

        # Previsione produzione
        riep_cont = contatore.get("riepilogo", {})
        prod_anno1 = riep_cont.get("produzione_annua_kwh", 0)
        if prod_anno1 == 0:
            # Fallback da fotovoltaico
            pv = self._input_dati.get("fotovoltaico", {})
            prod_anno1 = pv.get("riepilogo", {}).get("produzione_annua_kwh", 0)

        degradazione_pv = 0.5  # default
        pv_meta = self._input_dati.get("fotovoltaico", {}).get("metadata", {})
        degradazione_pv = pv_meta.get("degradazione_annua_pct", 0.5)

        prev_produzione = previsione_con_degradazione(prod_anno1, degradazione_pv, orizzonte)

        return {
            "metadata": {
                "orizzonte_anni": orizzonte,
                "metodo_prezzi": metodo_prezzi,
                "metodo_produzione": metodo_produzione,
            },
            "riepilogo": {
                "previsione_prezzi": prev_prezzi,
                "previsione_produzione": prev_produzione,
                "produzione_totale_vita_utile_kwh": round(
                    sum(p["produzione_kwh"] for p in prev_produzione), 0
                ),
            },
        }
