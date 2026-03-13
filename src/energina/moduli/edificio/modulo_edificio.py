"""Modulo Edificio - Profili consumo edificio ora per ora."""

import numpy as np

from energina.core.base_modulo import BaseModulo
from energina.core.time_series import genera_indice_orario, raggruppa_mensile, serie_a_lista_dicts
from energina.moduli.edificio.profili_carico import genera_consumo_base
from energina.moduli.edificio.zona_climatica import (
    calcola_fabbisogno_raffrescamento,
    calcola_fabbisogno_riscaldamento,
    get_gradi_giorno,
)


class ModuloEdificio(BaseModulo):
    """Genera profilo consumo elettrico orario dell'edificio.

    Combina carico base (elettrodomestici, illuminazione) con HVAC
    (pompa di calore / condizionatore) basato su dati meteo.
    """

    def get_dipendenze(self) -> list[str]:
        return ["meteo"]

    def get_input_schema(self) -> dict:
        return {}

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["riepilogo"],
            "properties": {
                "riepilogo": {
                    "type": "object",
                    "required": ["consumo_annuo_kwh"],
                },
            },
        }

    def esegui(self) -> dict:
        cfg_ed = self.config.get("modulo", self.config.get("edificio", {}))
        cfg_meteo = self.config.get("meteo", {})
        localita = cfg_meteo.get("localita", {})

        tipologia = cfg_ed.get("tipologia", "residenziale")
        parametri = cfg_ed.get("parametri", {})
        hvac_cfg = cfg_ed.get("climatizzazione", {})

        superficie = parametri.get("superficie_mq", 120)
        n_occupanti = parametri.get("n_occupanti", 4)
        consumo_annuo_spec = parametri.get("consumo_annuo_kwh")
        nome_citta = localita.get("nome", "Roma")
        lat = localita.get("latitudine", 41.9)

        # Gradi giorno
        gradi_giorno = get_gradi_giorno(nome_citta, lat)

        # Carica dati meteo per temperatura
        meteo = self._input_dati.get("meteo", {})
        serie_meteo = meteo.get("serie_oraria", [])
        anno = 2023
        if serie_meteo and "timestamp" in serie_meteo[0]:
            try:
                anno = int(serie_meteo[0]["timestamp"][:4])
            except (ValueError, IndexError):
                pass

        n = len(serie_meteo) if serie_meteo else 8760
        temp_aria = np.array(
            [h.get("temp_aria", 15) for h in serie_meteo], dtype=float
        ) if serie_meteo else np.full(n, 15.0)

        # Consumo base (senza HVAC)
        consumo_base = genera_consumo_base(
            tipologia=tipologia,
            anno=anno,
            consumo_annuo_kwh=consumo_annuo_spec,
            superficie_mq=superficie,
            n_occupanti=n_occupanti,
        )

        # Adatta lunghezza
        n = min(n, len(consumo_base), len(temp_aria))
        consumo_base = consumo_base[:n]
        temp_aria = temp_aria[:n]

        # HVAC
        consumo_hvac = np.zeros(n)

        # Riscaldamento elettrico (pompa di calore)
        riscaldamento = hvac_cfg.get("riscaldamento", "pompa_di_calore")
        if riscaldamento == "pompa_di_calore":
            cop = hvac_cfg.get("cop_medio", 3.5)
            hvac_cfg_risc = hvac_cfg.get("riscaldamento_cfg", {})
            temp_set = hvac_cfg_risc.get("temperatura_setpoint_c", 20)
            pot_kw_mq = hvac_cfg_risc.get("potenza_termica_kw_per_mq", 0.04)

            fabbisogno_term = calcola_fabbisogno_riscaldamento(
                temp_aria, superficie, gradi_giorno,
                potenza_termica_kw_mq=pot_kw_mq,
                temp_setpoint=temp_set,
            )
            consumo_hvac += fabbisogno_term / cop

        # Raffrescamento
        if hvac_cfg.get("raffrescamento", True):
            eer = hvac_cfg.get("eer_medio", 3.0)
            hvac_cfg_raff = hvac_cfg.get("raffrescamento_cfg", {})
            temp_set_raff = hvac_cfg_raff.get("temperatura_setpoint_c", 26)
            pot_kw_mq_raff = hvac_cfg_raff.get("potenza_frigorifera_kw_per_mq", 0.03)

            fabbisogno_frig = calcola_fabbisogno_raffrescamento(
                temp_aria, superficie,
                potenza_frigorifera_kw_mq=pot_kw_mq_raff,
                temp_setpoint=temp_set_raff,
            )
            consumo_hvac += fabbisogno_frig / eer

        # Consumo totale
        consumo_totale = consumo_base + consumo_hvac

        # Riepilogo
        consumo_annuo = float(np.sum(consumo_totale))
        picco_potenza = float(np.max(consumo_totale))
        consumo_mensile = raggruppa_mensile(consumo_totale, anno)

        # Serie oraria
        indice = genera_indice_orario(anno)[:n]
        serie = serie_a_lista_dicts(
            indice,
            consumo_kwh=consumo_totale,
            consumo_base_kwh=consumo_base,
            consumo_hvac_kwh=consumo_hvac,
        )

        return {
            "metadata": {
                "tipologia": tipologia,
                "superficie_mq": superficie,
                "n_occupanti": n_occupanti,
                "gradi_giorno": gradi_giorno,
                "riscaldamento": riscaldamento,
                "raffrescamento": hvac_cfg.get("raffrescamento", True),
            },
            "serie_oraria": serie,
            "riepilogo": {
                "consumo_annuo_kwh": round(consumo_annuo, 1),
                "consumo_base_annuo_kwh": round(float(np.sum(consumo_base)), 1),
                "consumo_hvac_annuo_kwh": round(float(np.sum(consumo_hvac)), 1),
                "picco_potenza_kw": round(picco_potenza, 2),
                "consumo_mensile_kwh": consumo_mensile,
            },
        }
