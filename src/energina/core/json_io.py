"""I/O JSON con validazione schema per comunicazione inter-modulo."""

import json
from datetime import datetime, timezone
from pathlib import Path

from energina.core.exceptions import InputValidationError, OutputValidationError

try:
    from jsonschema import ValidationError, validate
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
from energina.core.logging_config import get_logger

logger = get_logger("json_io")

# Schema base condiviso da tutti gli output dei moduli
SCHEMA_OUTPUT_BASE = {
    "type": "object",
    "required": ["_meta"],
    "properties": {
        "_meta": {
            "type": "object",
            "required": ["modulo", "versione", "timestamp_esecuzione"],
            "properties": {
                "modulo": {"type": "string"},
                "versione": {"type": "string"},
                "timestamp_esecuzione": {"type": "string"},
                "durata_s": {"type": "number"},
            },
        },
    },
}


def carica_json(path: Path) -> dict:
    """Carica un file JSON.

    Args:
        path: Percorso del file.

    Returns:
        Contenuto del file come dizionario.

    Raises:
        FileNotFoundError: Se il file non esiste.
    """
    logger.debug(f"Caricamento JSON: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def salva_json(dati: dict, path: Path, indent: int = 2) -> None:
    """Salva dati in formato JSON.

    Args:
        dati: Dizionario da salvare.
        path: Percorso di destinazione.
        indent: Indentazione (default 2).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=indent, ensure_ascii=False, default=str)
    logger.debug(f"Salvato JSON: {path}")


def valida_schema(dati: dict, schema: dict, modulo: str, direzione: str = "output") -> None:
    """Valida dati contro uno schema JSON.

    Args:
        dati: Dati da validare.
        schema: Schema JSON.
        modulo: Nome del modulo (per errori).
        direzione: "input" o "output".

    Raises:
        InputValidationError: Se validazione input fallisce.
        OutputValidationError: Se validazione output fallisce.
    """
    if not HAS_JSONSCHEMA:
        logger.debug("jsonschema non disponibile, validazione saltata")
        return

    try:
        validate(instance=dati, schema=schema)
    except ValidationError as e:
        msg = f"Validazione {direzione} fallita: {e.message}"
        if direzione == "input":
            raise InputValidationError(modulo, msg) from e
        else:
            raise OutputValidationError(modulo, msg) from e


def crea_meta(modulo: str, versione: str, durata_s: float) -> dict:
    """Crea blocco _meta standard per output modulo.

    Args:
        modulo: Nome del modulo.
        versione: Versione del modulo.
        durata_s: Durata esecuzione in secondi.

    Returns:
        Dizionario _meta.
    """
    return {
        "modulo": modulo,
        "versione": versione,
        "timestamp_esecuzione": datetime.now(timezone.utc).isoformat(),
        "durata_s": round(durata_s, 3),
    }
