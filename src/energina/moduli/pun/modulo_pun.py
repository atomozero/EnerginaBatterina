"""Modulo PUN - Prezzi energia elettrica mercato italiano."""

import numpy as np

from energina.core.base_modulo import BaseModulo
from energina.core.time_series import (
    fascia_oraria,
    genera_indice_orario,
    is_feriale,
    serie_a_lista_dicts,
)
from energina.core.units import eur_mwh_to_eur_kwh


class ModuloPUN(BaseModulo):
    """Gestisce prezzi energia elettrica dal mercato italiano (GME/PUN).

    Produce serie oraria con PUN, prezzo acquisto (incl. oneri), prezzo vendita
    e fascia oraria ARERA (F1/F2/F3).
    """

    def get_dipendenze(self) -> list[str]:
        return []

    def get_input_schema(self) -> dict:
        return {}

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["metadata", "riepilogo"],
            "properties": {
                "metadata": {"type": "object"},
                "riepilogo": {"type": "object"},
            },
        }

    def esegui(self) -> dict:
        cfg = self.config.get("modulo", self.config.get("pun", {}))
        zona = cfg.get("zona_mercato", "CSUD")
        anno = cfg.get("anno", 2024)
        tariffa_acq = cfg.get("tariffa_acquisto", {})
        tariffa_ven = cfg.get("tariffa_vendita", {})

        # Oneri e tasse
        oneri = tariffa_acq.get("oneri_sistema_eur_kwh", 0.08)
        accise = tariffa_acq.get("accise_eur_kwh", 0.0227)
        iva_pct = tariffa_acq.get("iva_pct", 10.0)

        # Prezzo vendita minimo garantito (Ritiro Dedicato)
        prezzo_min_vendita = tariffa_ven.get("prezzo_minimo_garantito_eur_kwh", 0.04)

        # Tenta scaricamento da GME, fallback sintetico
        dati_prezzi = self._ottieni_prezzi(anno, zona)
        pun = dati_prezzi["pun_eur_mwh"]

        indice = genera_indice_orario(anno)
        n_ore = min(len(indice), len(pun))
        indice = indice[:n_ore]
        pun = pun[:n_ore]

        # Calcola prezzi acquisto e vendita
        pun_kwh = pun / 1000.0  # EUR/MWh -> EUR/kWh

        if tariffa_acq.get("tipo") == "fissa" and tariffa_acq.get("prezzo_fisso_eur_kwh"):
            prezzo_acquisto = np.full(n_ore, tariffa_acq["prezzo_fisso_eur_kwh"])
        else:
            # PUN indicizzata + oneri + accise + IVA
            prezzo_netto = pun_kwh + oneri + accise
            prezzo_acquisto = prezzo_netto * (1 + iva_pct / 100.0)

        # Prezzo vendita: PUN zonale - spread, minimo garantito
        prezzo_vendita = np.maximum(pun_kwh * 0.9, prezzo_min_vendita)

        # Fasce orarie
        fasce = []
        for ts in indice:
            dt = ts.to_pydatetime() if hasattr(ts, 'to_pydatetime') else ts._dt
            fasce.append(fascia_oraria(dt.hour, is_feriale(dt)))

        fasce_arr = np.array(fasce)

        # Medie per fascia
        media_f1 = float(np.mean(pun[fasce_arr == "F1"])) if np.any(fasce_arr == "F1") else 0
        media_f2 = float(np.mean(pun[fasce_arr == "F2"])) if np.any(fasce_arr == "F2") else 0
        media_f3 = float(np.mean(pun[fasce_arr == "F3"])) if np.any(fasce_arr == "F3") else 0

        serie = serie_a_lista_dicts(
            indice,
            pun_eur_mwh=pun,
            prezzo_acquisto_eur_kwh=prezzo_acquisto,
            prezzo_vendita_eur_kwh=prezzo_vendita,
            fascia_oraria=fasce_arr,
        )

        return {
            "metadata": {
                "zona_mercato": zona,
                "anno": anno,
                "tipo_tariffa": tariffa_acq.get("tipo", "pun_indicizzata"),
                "oneri_sistema_eur_kwh": oneri,
                "accise_eur_kwh": accise,
                "iva_pct": iva_pct,
            },
            "serie_oraria": serie,
            "riepilogo": {
                "pun_medio_eur_mwh": round(float(np.mean(pun)), 2),
                "pun_min_eur_mwh": round(float(np.min(pun)), 2),
                "pun_max_eur_mwh": round(float(np.max(pun)), 2),
                "prezzo_acquisto_medio_eur_kwh": round(float(np.mean(prezzo_acquisto)), 4),
                "prezzo_vendita_medio_eur_kwh": round(float(np.mean(prezzo_vendita)), 4),
                "media_per_fascia": {
                    "F1": round(media_f1, 2),
                    "F2": round(media_f2, 2),
                    "F3": round(media_f3, 2),
                },
            },
        }

    def _ottieni_prezzi(self, anno: int, zona: str) -> dict:
        """Ottieni prezzi PUN: cache -> GME -> sintetico."""
        # Per ora, fallback diretto a sintetico (evita dipendenze pandas)
        try:
            cache_dir = self.exchange_dir.parent / "cache"
            from energina.moduli.pun.pun_cache import carica_cache
            df = carica_cache(cache_dir, anno, zona)
            if df is not None:
                return {"pun_eur_mwh": df["pun_eur_mwh"].values}
        except Exception:
            pass

        try:
            from energina.moduli.pun.gme_client import scarica_prezzi_gme
            df = scarica_prezzi_gme(anno, zona)
            if df is not None:
                return {"pun_eur_mwh": df["pun_eur_mwh"].values}
        except Exception:
            pass

        self.logger.warning("Generazione prezzi PUN sintetici")
        return self._genera_sintetico(anno)

    def _genera_sintetico(self, anno: int) -> dict:
        """Genera prezzi PUN sintetici realistici."""
        n_ore = 8760
        ore = np.arange(n_ore)
        ora_giorno = ore % 24
        giorno_anno = ore / 24.0

        # Base ~120 EUR/MWh con stagionalita
        base = 120 + 30 * np.sin(2 * np.pi * (giorno_anno - 30) / 365)

        # Profilo giornaliero: picco diurno
        profilo_orario = np.array([
            0.80, 0.75, 0.72, 0.70, 0.72, 0.78,
            0.90, 1.05, 1.15, 1.18, 1.15, 1.12,
            1.08, 1.10, 1.12, 1.15, 1.18, 1.20,
            1.15, 1.10, 1.05, 1.00, 0.92, 0.85,
        ])

        pun = base * profilo_orario[ora_giorno]
        pun += np.random.normal(0, 10, n_ore)
        pun = np.clip(pun, 20, 500)

        return {"pun_eur_mwh": pun}
