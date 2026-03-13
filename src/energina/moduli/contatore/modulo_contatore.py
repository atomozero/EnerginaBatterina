"""Modulo Contatore - Bilancio energetico orario autoconsumo/immissione/prelievo."""

import numpy as np

from energina.core.base_modulo import BaseModulo
from energina.core.time_series import genera_indice_orario, serie_a_lista_dicts


class ModuloContatore(BaseModulo):
    """Calcola il bilancio energetico orario al punto di connessione.

    Per ogni ora:
    - autoconsumo = min(produzione, consumo)
    - immissione = max(produzione - consumo, 0)  # surplus in rete
    - prelievo = max(consumo - produzione, 0)     # deficit da rete
    """

    def get_dipendenze(self) -> list[str]:
        return ["fotovoltaico", "edificio"]

    def get_input_schema(self) -> dict:
        return {}

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["riepilogo"],
            "properties": {
                "riepilogo": {
                    "type": "object",
                    "required": ["autoconsumo_pct"],
                },
            },
        }

    def esegui(self) -> dict:
        # Carica dati upstream
        pv = self._input_dati.get("fotovoltaico", {})
        ed = self._input_dati.get("edificio", {})

        serie_pv = pv.get("serie_oraria", [])
        serie_ed = ed.get("serie_oraria", [])

        if not serie_pv or not serie_ed:
            raise ValueError("Dati fotovoltaico o edificio non disponibili")

        n = min(len(serie_pv), len(serie_ed))

        produzione = np.array(
            [h.get("energia_kwh", 0) for h in serie_pv[:n]], dtype=float
        )
        consumo = np.array(
            [h.get("consumo_kwh", 0) for h in serie_ed[:n]], dtype=float
        )

        # Bilancio energetico
        autoconsumo = np.minimum(produzione, consumo)
        immissione = np.maximum(produzione - consumo, 0)
        prelievo = np.maximum(consumo - produzione, 0)

        # Indicatori
        prod_totale = float(np.sum(produzione))
        cons_totale = float(np.sum(consumo))
        auto_totale = float(np.sum(autoconsumo))
        imm_totale = float(np.sum(immissione))
        prel_totale = float(np.sum(prelievo))

        autoconsumo_pct = (auto_totale / prod_totale * 100) if prod_totale > 0 else 0
        autosufficienza_pct = (auto_totale / cons_totale * 100) if cons_totale > 0 else 0

        # Anno dalla serie
        anno = 2023
        if serie_pv and "timestamp" in serie_pv[0]:
            try:
                anno = int(serie_pv[0]["timestamp"][:4])
            except (ValueError, IndexError):
                pass

        indice = genera_indice_orario(anno)[:n]
        serie = serie_a_lista_dicts(
            indice,
            produzione_kwh=produzione,
            consumo_kwh=consumo,
            autoconsumo_kwh=autoconsumo,
            immissione_kwh=immissione,
            prelievo_kwh=prelievo,
        )

        return {
            "metadata": {
                "produzione_annua_kwh": round(prod_totale, 1),
                "consumo_annuo_kwh": round(cons_totale, 1),
            },
            "serie_oraria": serie,
            "riepilogo": {
                "autoconsumo_kwh": round(auto_totale, 1),
                "immissione_kwh": round(imm_totale, 1),
                "prelievo_kwh": round(prel_totale, 1),
                "autoconsumo_pct": round(autoconsumo_pct, 1),
                "autosufficienza_pct": round(autosufficienza_pct, 1),
                "produzione_annua_kwh": round(prod_totale, 1),
                "consumo_annuo_kwh": round(cons_totale, 1),
            },
        }
