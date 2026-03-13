"""Configurazione logging gerarchico per EnerginaBatterina."""

import logging
import sys
from pathlib import Path


def setup_logging(livello: str = "INFO", log_file: Path | None = None) -> logging.Logger:
    """Configura logging gerarchico.

    Args:
        livello: Livello di log (DEBUG, INFO, WARNING, ERROR).
        log_file: Path opzionale per log su file.

    Returns:
        Logger root del progetto.
    """
    logger = logging.getLogger("energina")
    logger.setLevel(getattr(logging, livello.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(nome_modulo: str) -> logging.Logger:
    """Ottieni logger per un modulo specifico.

    Args:
        nome_modulo: Nome del modulo (es. "meteo", "fotovoltaico").

    Returns:
        Logger con namespace gerarchico.
    """
    return logging.getLogger(f"energina.{nome_modulo}")
