"""Eccezioni custom per EnerginaBatterina."""


class EnerginaError(Exception):
    """Eccezione base per tutti gli errori del progetto."""


class ConfigError(EnerginaError):
    """Errore nella configurazione."""


class ModuloError(EnerginaError):
    """Errore generico di un modulo."""

    def __init__(self, modulo: str, messaggio: str):
        self.modulo = modulo
        super().__init__(f"[{modulo}] {messaggio}")


class InputValidationError(ModuloError):
    """Input non valido per un modulo."""


class OutputValidationError(ModuloError):
    """Output non valido prodotto da un modulo."""


class DipendenzaMancanteError(ModuloError):
    """Output di un modulo upstream non trovato."""


class APIError(EnerginaError):
    """Errore nella comunicazione con API esterna."""

    def __init__(self, servizio: str, messaggio: str):
        self.servizio = servizio
        super().__init__(f"API [{servizio}]: {messaggio}")


class DAGError(EnerginaError):
    """Errore nel grafo delle dipendenze (ciclo, nodo mancante)."""
