"""Direttore - Orchestratore DAG dei moduli EnerginaBatterina."""

from collections import deque
from pathlib import Path

import yaml

from energina.core.base_modulo import BaseModulo
from energina.core.exceptions import ConfigError, DAGError
from energina.core.json_io import carica_json, salva_json
from energina.core.logging_config import get_logger, setup_logging

# Import di tutti i moduli
from energina.moduli.meteo.modulo_meteo import ModuloMeteo
from energina.moduli.pun.modulo_pun import ModuloPUN
from energina.moduli.fotovoltaico.modulo_fotovoltaico import ModuloFotovoltaico
from energina.moduli.edificio.modulo_edificio import ModuloEdificio
from energina.moduli.contatore.modulo_contatore import ModuloContatore
from energina.moduli.batteria.modulo_batteria import ModuloBatteria
from energina.moduli.incentivi.modulo_incentivi import ModuloIncentivi
from energina.moduli.economico.modulo_economico import ModuloEconomico
from energina.moduli.previsione.modulo_previsione import ModuloPrevisione
from energina.moduli.sensibilita.modulo_sensibilita import ModuloSensibilita
from energina.moduli.report.modulo_report import ModuloReport

logger = get_logger("direttore")

# Registro moduli disponibili
REGISTRO_MODULI: dict[str, type[BaseModulo]] = {
    "meteo": ModuloMeteo,
    "pun": ModuloPUN,
    "fotovoltaico": ModuloFotovoltaico,
    "edificio": ModuloEdificio,
    "contatore": ModuloContatore,
    "batteria": ModuloBatteria,
    "incentivi": ModuloIncentivi,
    "economico": ModuloEconomico,
    "previsione": ModuloPrevisione,
    "sensibilita": ModuloSensibilita,
    "report": ModuloReport,
}


class Direttore:
    """Orchestratore della pipeline EnerginaBatterina.

    - Legge config.yaml
    - Istanzia i moduli necessari
    - Costruisce DAG delle dipendenze
    - Esegue in ordine topologico (Kahn's algorithm)
    - Gestisce checkpoint per resume
    """

    def __init__(self, config_path: Path):
        """Inizializza il Direttore.

        Args:
            config_path: Percorso del file di configurazione YAML.
        """
        self.config_path = Path(config_path)
        self.config = self._carica_config()
        self.exchange_dir = self._setup_exchange_dir()
        self.moduli: dict[str, BaseModulo] = {}
        self.risultati: dict[str, dict] = {}

    def _carica_config(self) -> dict:
        """Carica e valida la configurazione."""
        if not self.config_path.exists():
            raise ConfigError(f"File di configurazione non trovato: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ConfigError("Il file di configurazione deve essere un dizionario YAML")

        return config

    def _setup_exchange_dir(self) -> Path:
        """Crea directory di scambio per i JSON inter-modulo."""
        base = self.config_path.parent
        exchange = base / "data" / "exchange"
        exchange.mkdir(parents=True, exist_ok=True)
        return exchange

    def _istanzia_moduli(self) -> None:
        """Istanzia tutti i moduli configurati."""
        for nome, classe_modulo in REGISTRO_MODULI.items():
            config_modulo = self.config.get(nome, {})
            # Passa anche configurazione globale
            config_completa = {
                "progetto": self.config.get("progetto", {}),
                "modulo": config_modulo,
            }
            # Aggiungi config meteo a tutti (per localita)
            if nome != "meteo":
                config_completa["meteo"] = self.config.get("meteo", {})

            self.moduli[nome] = classe_modulo(nome, config_completa, self.exchange_dir)
            logger.debug(f"Modulo istanziato: {nome}")

    def _ordine_topologico(self) -> list[str]:
        """Calcola ordine di esecuzione con algoritmo di Kahn.

        Returns:
            Lista ordinata di nomi moduli.

        Raises:
            DAGError: Se il grafo ha cicli.
        """
        # Costruisci grafo
        grafo: dict[str, set[str]] = {}
        in_degree: dict[str, int] = {}

        for nome, modulo in self.moduli.items():
            if nome not in grafo:
                grafo[nome] = set()
                in_degree[nome] = 0

            for dep in modulo.get_dipendenze():
                if dep not in self.moduli:
                    logger.warning(
                        f"Modulo '{nome}' dipende da '{dep}' che non e' registrato"
                    )
                    continue
                if dep not in grafo:
                    grafo[dep] = set()
                    in_degree[dep] = 0
                grafo[dep].add(nome)
                in_degree[nome] = in_degree.get(nome, 0) + 1

        # Kahn's algorithm
        coda = deque([n for n, d in in_degree.items() if d == 0])
        ordine = []

        while coda:
            nodo = coda.popleft()
            ordine.append(nodo)
            for vicino in grafo.get(nodo, set()):
                in_degree[vicino] -= 1
                if in_degree[vicino] == 0:
                    coda.append(vicino)

        if len(ordine) != len(self.moduli):
            eseguiti = set(ordine)
            mancanti = set(self.moduli.keys()) - eseguiti
            raise DAGError(f"Ciclo nel grafo delle dipendenze. Moduli non raggiungibili: {mancanti}")

        return ordine

    def _carica_checkpoint(self) -> set[str]:
        """Carica checkpoint di moduli gia completati.

        Returns:
            Set di nomi moduli gia completati.
        """
        checkpoint_path = self.exchange_dir / "_checkpoint.json"
        if checkpoint_path.exists():
            data = carica_json(checkpoint_path)
            completati = set(data.get("completati", []))
            logger.info(f"Checkpoint trovato: {len(completati)} moduli gia completati")
            return completati
        return set()

    def _salva_checkpoint(self, completati: set[str]) -> None:
        """Salva checkpoint dei moduli completati."""
        checkpoint_path = self.exchange_dir / "_checkpoint.json"
        salva_json({"completati": sorted(completati)}, checkpoint_path)

    def esegui(self, resume: bool = False) -> dict[str, dict]:
        """Esegui l'intera pipeline.

        Args:
            resume: Se True, riprende da checkpoint.

        Returns:
            Dizionario con risultati di tutti i moduli.
        """
        setup_logging(self.config.get("logging", {}).get("livello", "INFO"))
        logger.info("=== EnerginaBatterina - Avvio Pipeline ===")
        logger.info(f"Progetto: {self.config.get('progetto', {}).get('nome', 'N/D')}")

        self._istanzia_moduli()
        ordine = self._ordine_topologico()
        logger.info(f"Ordine esecuzione: {' -> '.join(ordine)}")

        completati = self._carica_checkpoint() if resume else set()

        for nome in ordine:
            if nome in completati:
                logger.info(f"Modulo '{nome}' gia completato (checkpoint), skip")
                # Carica risultato dal file
                output_path = self.exchange_dir / f"{nome}_output.json"
                if output_path.exists():
                    self.risultati[nome] = carica_json(output_path)
                continue

            modulo = self.moduli[nome]
            try:
                risultato = modulo.run()
                self.risultati[nome] = risultato
                completati.add(nome)
                self._salva_checkpoint(completati)
            except Exception as e:
                logger.error(f"Pipeline interrotta al modulo '{nome}': {e}")
                raise

        logger.info("=== Pipeline completata con successo ===")
        return self.risultati
