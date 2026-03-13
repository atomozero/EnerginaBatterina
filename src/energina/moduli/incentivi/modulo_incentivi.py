"""Modulo Incentivi - Incentivi italiani per fotovoltaico e accumulo."""

from energina.core.base_modulo import BaseModulo
from energina.moduli.incentivi.cer import calcola_incentivo_cer
from energina.moduli.incentivi.ritiro_dedicato import calcola_ricavo_ritiro_dedicato


class ModuloIncentivi(BaseModulo):
    """Calcola incentivi italiani applicabili all'impianto.

    Incentivi supportati:
    - Detrazione fiscale 50% (ristrutturazione edilizia)
    - Ritiro Dedicato GSE
    - Comunita Energetiche Rinnovabili (CER)
    """

    def get_dipendenze(self) -> list[str]:
        return ["contatore", "batteria"]

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
        cfg_inc = self.config.get("modulo", self.config.get("incentivi", {}))
        cfg_eco = self.config.get("modulo", {})  # per costi investimento

        contatore = self._input_dati.get("contatore", {})
        batteria = self._input_dati.get("batteria", {})
        riep_cont = contatore.get("riepilogo", {})
        riep_batt = batteria.get("riepilogo", {})

        # Dati energetici post-batteria
        flussi = riep_batt.get("flussi_energetici_rivisti", {})
        immissione = flussi.get("immissione_kwh", riep_cont.get("immissione_kwh", 0))
        autoconsumo = riep_cont.get("autoconsumo_kwh", 0)

        risultato = {
            "detrazione_fiscale": {},
            "ritiro_dedicato": {},
            "cer": {},
        }

        totale_incentivi_anno1 = 0.0
        incentivi_per_anno = []

        # 1. Detrazione fiscale 50%
        cfg_detr = cfg_inc.get("detrazione_fiscale", {})
        if cfg_detr.get("abilitata", True):
            # Cerca costi investimento nella configurazione
            cfg_economico = self.config.get("progetto", {})
            # Prova a leggere da config originale
            investimento_totale = 0
            for key in ["costo_pv_eur", "costo_batteria_eur", "costo_installazione_eur",
                         "costo_progettazione_eur"]:
                investimento_totale += cfg_inc.get(key, 0)

            # Se non trovato, usa default ragionevoli
            if investimento_totale == 0:
                investimento_totale = 17500  # stima default

            aliquota = cfg_detr.get("aliquota_pct", 50.0) / 100
            anni = cfg_detr.get("anni_detrazione", 10)
            tetto = cfg_detr.get("tetto_spesa_eur", 96000)

            spesa_detraibile = min(investimento_totale, tetto)
            detrazione_totale = spesa_detraibile * aliquota
            rata_annua = detrazione_totale / anni

            risultato["detrazione_fiscale"] = {
                "abilitata": True,
                "investimento_totale_eur": round(investimento_totale, 2),
                "spesa_detraibile_eur": round(spesa_detraibile, 2),
                "aliquota_pct": cfg_detr.get("aliquota_pct", 50.0),
                "detrazione_totale_eur": round(detrazione_totale, 2),
                "rata_annua_eur": round(rata_annua, 2),
                "anni_detrazione": anni,
            }
            totale_incentivi_anno1 += rata_annua
        else:
            risultato["detrazione_fiscale"] = {"abilitata": False}

        # 2. Ritiro Dedicato
        cfg_rd = cfg_inc.get("ritiro_dedicato", {})
        if cfg_rd.get("abilitato", True) and immissione > 0:
            # Usa prezzo medio vendita dal PUN
            pun = self._input_dati.get("pun", {})
            prezzo_vendita = pun.get("riepilogo", {}).get("prezzo_vendita_medio_eur_kwh", 0.08)
            prezzo_min = cfg_rd.get("prezzo_minimo_garantito_eur_kwh", 0.04)

            rd = calcola_ricavo_ritiro_dedicato(immissione, prezzo_vendita, prezzo_min)
            risultato["ritiro_dedicato"] = {"abilitato": True, **rd}
            totale_incentivi_anno1 += rd["ricavo_annuo_eur"]
        else:
            risultato["ritiro_dedicato"] = {"abilitato": False}

        # 3. CER
        cfg_cer = cfg_inc.get("cer", {})
        if cfg_cer.get("abilitata", False):
            tariffa = cfg_cer.get("tariffa_incentivante_eur_kwh", 0.11)
            # Energia condivisa stimata come % dell'autoconsumo
            energia_condivisa = autoconsumo * 0.5  # stima conservativa

            pv_meta = self._input_dati.get("fotovoltaico", {}).get("metadata", {})
            potenza_kwp = pv_meta.get("potenza_nominale_kwp", 6.0)

            cer = calcola_incentivo_cer(energia_condivisa, potenza_kwp, tariffa)
            risultato["cer"] = {"abilitata": True, **cer}
            totale_incentivi_anno1 += cer["incentivo_annuo_eur"]
        else:
            risultato["cer"] = {"abilitata": False}

        # Costruisci profilo incentivi per anno
        vita_utile = 25
        detr_anni = risultato["detrazione_fiscale"].get("anni_detrazione", 0)
        detr_rata = risultato["detrazione_fiscale"].get("rata_annua_eur", 0)
        rd_annuo = risultato["ritiro_dedicato"].get("ricavo_annuo_eur", 0)
        cer_annuo = risultato["cer"].get("incentivo_annuo_eur", 0)
        cer_durata = risultato["cer"].get("durata_incentivo_anni", 20)

        for anno in range(1, vita_utile + 1):
            tot = 0
            if anno <= detr_anni:
                tot += detr_rata
            tot += rd_annuo  # RD per tutta la vita
            if anno <= cer_durata:
                tot += cer_annuo
            incentivi_per_anno.append({
                "anno": anno,
                "incentivo_totale_eur": round(tot, 2),
            })

        return {
            "metadata": {
                "incentivi_attivi": [
                    k for k, v in risultato.items()
                    if isinstance(v, dict) and v.get("abilitata", v.get("abilitato", False))
                ],
            },
            "riepilogo": {
                **risultato,
                "totale_incentivi_anno1_eur": round(totale_incentivi_anno1, 2),
                "incentivi_per_anno": incentivi_per_anno,
            },
        }
