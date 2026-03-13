"""Classe base astratta per tutti i moduli EnerginaBatterina."""

import time
from abc import ABC, abstractmethod
from pathlib import Path

from energina.core.exceptions import DipendenzaMancanteError
from energina.core.json_io import carica_json, crea_meta, salva_json, valida_schema
from energina.core.logging_config import get_logger


class BaseModulo(ABC):
    """Classe base per tutti i moduli della piattaforma.

    Ogni modulo:
    - Ha un nome univoco
    - Riceve configurazione dal Direttore
    - Legge input da exchange_dir (output di moduli upstream)
    - Produce output JSON in exchange_dir
    - Implementa validazione input/output tramite schema JSON
    """

    VERSIONE = "0.1.0"

    def __init__(self, nome: str, config: dict, exchange_dir: Path):
        """Inizializza il modulo.

        Args:
            nome: Nome univoco del modulo.
            config: Configurazione specifica del modulo (da config.yaml).
            exchange_dir: Directory per I/O JSON inter-modulo.
        """
        self.nome = nome
        self.config = config
        self.exchange_dir = Path(exchange_dir)
        self.logger = get_logger(nome)
        self._stato = "inizializzato"
        self._input_dati: dict = {}

    @abstractmethod
    def esegui(self) -> dict:
        """Logica principale del modulo.

        Returns:
            Dizionario con output del modulo (metadata, serie_oraria, riepilogo).
        """

    @abstractmethod
    def get_input_schema(self) -> dict:
        """Schema JSON per validazione input.

        Returns:
            Schema JSON (dict vuoto se il modulo non ha input da upstream).
        """

    @abstractmethod
    def get_output_schema(self) -> dict:
        """Schema JSON per validazione output.

        Returns:
            Schema JSON per l'output del modulo.
        """

    def get_dipendenze(self) -> list[str]:
        """Lista dei moduli da cui questo modulo dipende.

        Override nelle sottoclassi se il modulo ha dipendenze.

        Returns:
            Lista di nomi moduli upstream.
        """
        return []

    def carica_input(self, dati: dict) -> None:
        """Valida e carica dati di input.

        Args:
            dati: Dizionario con input (config + output upstream).
        """
        schema = self.get_input_schema()
        if schema:
            valida_schema(dati, schema, self.nome, direzione="input")
        self._input_dati = dati
        self.logger.debug("Input caricato e validato")

    def carica_output_upstream(self, nome_upstream: str) -> dict:
        """Carica output JSON di un modulo upstream.

        Args:
            nome_upstream: Nome del modulo upstream.

        Returns:
            Contenuto del file output del modulo upstream.

        Raises:
            DipendenzaMancanteError: Se il file non esiste.
        """
        path = self.exchange_dir / f"{nome_upstream}_output.json"
        if not path.exists():
            raise DipendenzaMancanteError(
                self.nome,
                f"Output di '{nome_upstream}' non trovato: {path}",
            )
        return carica_json(path)

    def salva_output(self, dati: dict) -> Path:
        """Valida e salva output JSON.

        Args:
            dati: Output del modulo.

        Returns:
            Path del file salvato.
        """
        schema = self.get_output_schema()
        if schema:
            valida_schema(dati, schema, self.nome, direzione="output")
        path = self.exchange_dir / f"{self.nome}_output.json"
        salva_json(dati, path)
        self.logger.info(f"Output salvato: {path}")
        return path

    def run(self) -> dict:
        """Esegui il modulo: prepara input -> esegui -> salva output.

        Returns:
            Output completo del modulo con _meta.
        """
        self._stato = "in_esecuzione"
        self.logger.info(f"=== Avvio modulo: {self.nome} ===")

        t0 = time.time()
        try:
            # Carica output dei moduli upstream
            for dep in self.get_dipendenze():
                upstream = self.carica_output_upstream(dep)
                self._input_dati[dep] = upstream

            risultato = self.esegui()

            durata = time.time() - t0
            risultato["_meta"] = crea_meta(self.nome, self.VERSIONE, durata)

            self.salva_output(risultato)
            self._stato = "completato"
            self.logger.info(f"=== Modulo {self.nome} completato in {durata:.1f}s ===")
            return risultato

        except Exception as e:
            self._stato = "errore"
            self.logger.error(f"Errore nel modulo {self.nome}: {e}")
            raise

    def status(self) -> dict:
        """Stato corrente del modulo.

        Returns:
            Dizionario con nome, stato, versione.
        """
        return {
            "nome": self.nome,
            "stato": self._stato,
            "versione": self.VERSIONE,
        }
