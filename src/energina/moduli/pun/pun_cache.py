"""Cache locale per prezzi PUN storici."""

from pathlib import Path

import pandas as pd

from energina.core.logging_config import get_logger

logger = get_logger("pun.cache")


def salva_cache(df: pd.DataFrame, cache_dir: Path, anno: int, zona: str) -> None:
    """Salva prezzi in cache locale."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"pun_{zona}_{anno}.parquet"
    df.to_parquet(path, index=False)
    logger.info(f"Prezzi salvati in cache: {path}")


def carica_cache(cache_dir: Path, anno: int, zona: str) -> pd.DataFrame | None:
    """Carica prezzi da cache locale."""
    path = cache_dir / f"pun_{zona}_{anno}.parquet"
    if path.exists():
        logger.info(f"Prezzi caricati da cache: {path}")
        return pd.read_parquet(path)
    return None
