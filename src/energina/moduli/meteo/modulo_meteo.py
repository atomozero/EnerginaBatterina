"""Modulo Meteo - Centralizza dati meteorologici per tutti i moduli downstream."""

import json
from pathlib import Path

import numpy as np

from energina.core.base_modulo import BaseModulo
from energina.core.time_series import genera_indice_orario, serie_a_lista_dicts


class ModuloMeteo(BaseModulo):
    """Scarica/genera dati meteo orari (irradianza, temperatura, vento).

    Sorgenti supportate:
    - pvgis_tmy: Dati TMY da PVGIS (anno tipico, gratis)
    - open_meteo: Dati storici da Open-Meteo (anno specifico, gratis)
    - sintetico: Dati sintetici per test (nessuna API)
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
                "metadata": {
                    "type": "object",
                    "required": ["latitudine", "longitudine"],
                },
                "riepilogo": {"type": "object"},
            },
        }

    def esegui(self) -> dict:
        cfg_meteo = self.config.get("modulo", self.config.get("meteo", {}))
        localita = cfg_meteo.get("localita", {})
        lat = localita.get("latitudine", 41.9)
        lon = localita.get("longitudine", 12.5)
        alt = localita.get("altitudine", 0)
        nome_loc = localita.get("nome", "Sconosciuta")
        sorgente = cfg_meteo.get("sorgente_dati", "sintetico")
        anno = cfg_meteo.get("anno", 2023)

        cache_dir = self.exchange_dir.parent / "cache"

        if sorgente == "pvgis_tmy":
            dati = self._carica_pvgis(lat, lon, cache_dir)
        elif sorgente == "open_meteo":
            dati = self._carica_open_meteo(lat, lon, anno, cache_dir)
        else:
            dati = self._genera_sintetico(lat, anno)

        # Assicurati che abbiamo tutte le colonne necessarie
        for col in ["ghi", "dni", "dhi", "temp_aria", "vel_vento"]:
            if col not in dati:
                dati[col] = np.zeros(len(dati.get("ghi", [])))
        if "copertura_nubi" not in dati:
            ghi = dati["ghi"]
            dhi = dati["dhi"]
            with np.errstate(divide="ignore", invalid="ignore"):
                kt = np.where(ghi > 50, dhi / ghi, 0.5)
            dati["copertura_nubi"] = np.clip(kt * 100, 0, 100)

        # Determina zona climatica
        zona, gradi_giorno = self._determina_zona_climatica(nome_loc, lat)

        # Riepilogo
        ghi = dati["ghi"]
        temp = dati["temp_aria"]
        vento = dati["vel_vento"]
        ghi_annuo = float(np.sum(ghi) / 1000.0)  # kWh/m2
        temp_media = float(np.mean(temp))

        # Crea serie oraria
        anno_idx = anno if sorgente != "pvgis_tmy" else 2023
        indice = genera_indice_orario(anno_idx)
        n_ore = min(len(indice), len(ghi))
        indice = indice[:n_ore]

        serie = serie_a_lista_dicts(
            indice,
            ghi=ghi[:n_ore],
            dni=dati["dni"][:n_ore],
            dhi=dati["dhi"][:n_ore],
            temp_aria=temp[:n_ore],
            vel_vento=vento[:n_ore],
            copertura_nubi=dati["copertura_nubi"][:n_ore],
        )

        return {
            "metadata": {
                "latitudine": lat,
                "longitudine": lon,
                "altitudine": alt,
                "nome_localita": nome_loc,
                "sorgente_dati": sorgente,
                "zona_climatica": zona,
                "gradi_giorno": gradi_giorno,
            },
            "serie_oraria": serie,
            "riepilogo": {
                "irradiazione_annua_kwh_mq": round(ghi_annuo, 1),
                "temperatura_media_c": round(temp_media, 1),
                "temperatura_min_c": round(float(np.min(temp[:n_ore])), 1),
                "temperatura_max_c": round(float(np.max(temp[:n_ore])), 1),
                "vel_vento_media_ms": round(float(np.mean(vento[:n_ore])), 1),
            },
        }

    def _carica_pvgis(self, lat: float, lon: float, cache_dir: Path):
        from energina.moduli.meteo.providers.pvgis_tmy import scarica_tmy
        df = scarica_tmy(lat, lon, cache_dir)
        # Converti DataFrame in dict di arrays
        return {col: df[col].values for col in df.columns if col != "timestamp"}

    def _carica_open_meteo(self, lat: float, lon: float, anno: int, cache_dir: Path):
        from energina.moduli.meteo.providers.open_meteo import scarica_meteo_anno
        df = scarica_meteo_anno(lat, lon, anno, cache_dir)
        return {col: df[col].values for col in df.columns if col != "timestamp"}

    def _genera_sintetico(self, lat: float, anno: int) -> dict[str, np.ndarray]:
        """Genera dati meteo sintetici per test."""
        self.logger.info("Generazione dati meteo sintetici")
        n_ore = 8760
        ore = np.arange(n_ore)
        giorno_anno = ore / 24.0

        # GHI sintetico con stagionalita e ciclo giornaliero
        ora_giorno = ore % 24
        declinazione = 23.45 * np.sin(np.radians((360 / 365) * (giorno_anno - 81)))
        elevazione_solare = np.maximum(
            0, np.sin(np.radians(lat)) * np.sin(np.radians(declinazione))
            + np.cos(np.radians(lat)) * np.cos(np.radians(declinazione))
            * np.cos(np.radians(15 * (ora_giorno - 12)))
        )
        ghi = 1000 * elevazione_solare * (0.75 + 0.1 * np.random.random(n_ore))
        ghi = np.maximum(ghi, 0)

        # DNI e DHI stimati
        kt = np.where(ghi > 0, 0.6 + 0.15 * np.random.random(n_ore), 0)
        dhi = ghi * (1 - kt) * 0.8
        cos_zenith = np.maximum(elevazione_solare, 0.01)
        dni = np.where(cos_zenith > 0.05, (ghi - dhi) / cos_zenith, 0)
        dni = np.clip(dni, 0, 1200)

        # Temperatura con stagionalita
        temp_base = 15 + 10 * np.sin(np.radians((360 / 365) * (giorno_anno - 100)))
        temp_giorno = 3 * np.sin(np.radians(15 * (ora_giorno - 6)))
        temp_aria = temp_base + temp_giorno + np.random.normal(0, 1.5, n_ore)

        # Vento
        vel_vento = np.abs(np.random.normal(3, 1.5, n_ore))

        # Copertura nubi
        copertura = np.clip(np.random.normal(40, 25, n_ore), 0, 100)

        return {
            "ghi": ghi,
            "dni": dni,
            "dhi": dhi,
            "temp_aria": temp_aria,
            "vel_vento": vel_vento,
            "copertura_nubi": copertura,
        }

    def _determina_zona_climatica(
        self, nome_localita: str, lat: float
    ) -> tuple[str, int]:
        """Determina zona climatica e gradi giorno."""
        for base in [Path.cwd(), Path(__file__).parents[4]]:
            candidate = base / "config" / "zone_climatiche.json"
            if candidate.exists():
                try:
                    with open(candidate, encoding="utf-8") as f:
                        zone_data = json.load(f)

                    gg_db = zone_data.get("citta_gradi_giorno", {})
                    if nome_localita in gg_db:
                        gradi_giorno = gg_db[nome_localita]
                    else:
                        gradi_giorno = int(max(600, min(3500, (lat - 36) * 200 + 800)))

                    zone = zone_data.get("zone", {})
                    zona = "D"
                    for lettera, info in zone.items():
                        if info["gradi_giorno_min"] <= gradi_giorno <= info["gradi_giorno_max"]:
                            zona = lettera
                            break

                    return zona, gradi_giorno
                except (json.JSONDecodeError, KeyError):
                    break

        # Fallback: stima da latitudine
        gradi_giorno = int(max(600, min(3500, (lat - 36) * 200 + 800)))
        if gradi_giorno <= 600:
            zona = "A"
        elif gradi_giorno <= 900:
            zona = "B"
        elif gradi_giorno <= 1400:
            zona = "C"
        elif gradi_giorno <= 2100:
            zona = "D"
        elif gradi_giorno <= 3000:
            zona = "E"
        else:
            zona = "F"
        return zona, gradi_giorno
