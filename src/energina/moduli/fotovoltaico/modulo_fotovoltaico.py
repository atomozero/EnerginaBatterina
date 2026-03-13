"""Modulo Fotovoltaico - Simulazione produzione PV ora per ora."""

import numpy as np

from energina.core.base_modulo import BaseModulo
from energina.core.time_series import genera_indice_orario, raggruppa_mensile, serie_a_lista_dicts
from energina.moduli.fotovoltaico.pv_model import calcola_degradazione_annua, simula_produzione_pv


class ModuloFotovoltaico(BaseModulo):
    """Simula produzione fotovoltaica oraria con pvlib.

    Dipende da Modulo Meteo per dati irradianza e temperatura.
    Produce serie oraria potenza AC e energia, con degradazione multi-anno.
    """

    def get_dipendenze(self) -> list[str]:
        return ["meteo"]

    def get_input_schema(self) -> dict:
        return {}

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["metadata", "riepilogo"],
            "properties": {
                "metadata": {"type": "object"},
                "riepilogo": {
                    "type": "object",
                    "required": ["produzione_annua_kwh"],
                },
            },
        }

    def esegui(self) -> dict:
        cfg_pv = self.config.get("modulo", self.config.get("fotovoltaico", {}))
        cfg_meteo = self.config.get("meteo", {})
        localita = cfg_meteo.get("localita", {})

        impianto = cfg_pv.get("impianto", {})
        modulo = cfg_pv.get("modulo", {})
        inverter = cfg_pv.get("inverter", {})

        lat = localita.get("latitudine", 41.9)
        lon = localita.get("longitudine", 12.5)
        alt = localita.get("altitudine", 0)
        potenza_kwp = impianto.get("potenza_nominale_kwp", 6.0)
        inclinazione = impianto.get("inclinazione_gradi", 30)
        azimut = impianto.get("azimut_gradi", 180)
        perdite = impianto.get("perdite_sistema_pct", 14.0)
        degradazione = impianto.get("degradazione_annua_pct", 0.5)
        coeff_temp = modulo.get("coeff_temp_pmax_pct_c", -0.35) / 100.0
        noct = modulo.get("noct_c", 45)
        eff_inv = inverter.get("efficienza_nominale_pct", 97.0) / 100.0
        vita_utile = self.config.get("progetto", {}).get("vita_utile_anni", 25)

        # Carica dati meteo
        meteo = self._input_dati.get("meteo", {})
        serie_meteo = meteo.get("serie_oraria", [])

        if not serie_meteo:
            raise ValueError("Dati meteo non disponibili")

        n = len(serie_meteo)
        ghi = np.array([h.get("ghi", 0) for h in serie_meteo], dtype=float)
        dni = np.array([h.get("dni", 0) for h in serie_meteo], dtype=float)
        dhi = np.array([h.get("dhi", 0) for h in serie_meteo], dtype=float)
        temp_aria = np.array([h.get("temp_aria", 20) for h in serie_meteo], dtype=float)
        vel_vento = np.array([h.get("vel_vento", 2) for h in serie_meteo], dtype=float)

        # Determina anno dalla serie meteo
        anno = 2023
        if serie_meteo and "timestamp" in serie_meteo[0]:
            try:
                anno = int(serie_meteo[0]["timestamp"][:4])
            except (ValueError, IndexError):
                pass

        # Simulazione
        risultato_pv = simula_produzione_pv(
            ghi=ghi, dni=dni, dhi=dhi,
            temp_aria=temp_aria, vel_vento=vel_vento,
            latitudine=lat, longitudine=lon, altitudine=alt,
            potenza_kwp=potenza_kwp,
            inclinazione=inclinazione, azimut=azimut,
            perdite_pct=perdite, coeff_temp=coeff_temp,
            noct=noct, efficienza_inverter=eff_inv,
            anno=anno,
        )

        potenza_ac = risultato_pv["potenza_ac_kw"]
        energia = risultato_pv["energia_kwh"]
        temp_cella = risultato_pv["temp_cella_c"]

        produzione_annua = float(np.sum(energia))
        ore_eq = produzione_annua / potenza_kwp if potenza_kwp > 0 else 0
        prod_mensile = raggruppa_mensile(energia, anno)

        # Degradazione multi-anno
        prod_per_anno = calcola_degradazione_annua(
            produzione_annua, degradazione, vita_utile
        )

        # Serie oraria output
        indice = genera_indice_orario(anno)[:n]
        serie = serie_a_lista_dicts(
            indice,
            potenza_ac_kw=potenza_ac,
            energia_kwh=energia,
            temp_cella_c=temp_cella,
        )

        return {
            "metadata": {
                "potenza_nominale_kwp": potenza_kwp,
                "inclinazione_gradi": inclinazione,
                "azimut_gradi": azimut,
                "perdite_sistema_pct": perdite,
                "degradazione_annua_pct": degradazione,
            },
            "serie_oraria": serie,
            "riepilogo": {
                "produzione_annua_kwh": round(produzione_annua, 1),
                "ore_equivalenti": round(ore_eq, 0),
                "produzione_mensile_kwh": prod_mensile,
                "picco_potenza_kw": round(float(np.max(potenza_ac)), 2),
                "produzione_specifica_kwh_kwp": round(ore_eq, 0),
                "produzione_per_anno": prod_per_anno,
            },
        }
