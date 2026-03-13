"""Generazione grafici matplotlib per il report PDF."""

from pathlib import Path

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("report.grafici")

# Colori tema EnerginaBatterina
COLORI = {
    "solare": "#FFB300",
    "consumo": "#E53935",
    "autoconsumo": "#43A047",
    "immissione": "#1E88E5",
    "prelievo": "#8E24AA",
    "batteria_carica": "#00ACC1",
    "batteria_scarica": "#F4511E",
    "npv_positivo": "#2E7D32",
    "npv_negativo": "#C62828",
}


def grafico_bilancio_mensile(
    produzione_mensile: list[float],
    consumo_mensile: list[float],
    output_path: Path,
) -> Path:
    """Grafico a barre produzione vs consumo mensile."""
    import matplotlib.pyplot as plt

    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
            "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    x = np.arange(len(mesi))
    w = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - w/2, produzione_mensile, w, label="Produzione PV",
           color=COLORI["solare"], edgecolor="white")
    ax.bar(x + w/2, consumo_mensile, w, label="Consumo",
           color=COLORI["consumo"], edgecolor="white")

    ax.set_xlabel("Mese")
    ax.set_ylabel("Energia (kWh)")
    ax.set_title("Bilancio Energetico Mensile")
    ax.set_xticks(x)
    ax.set_xticklabels(mesi)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.debug(f"Grafico bilancio mensile salvato: {output_path}")
    return output_path


def grafico_autoconsumo_pie(
    autoconsumo_kwh: float,
    immissione_kwh: float,
    prelievo_kwh: float,
    output_path: Path,
) -> Path:
    """Grafico a torta autoconsumo/immissione/prelievo."""
    import matplotlib.pyplot as plt

    labels = ["Autoconsumo", "Immissione\nin rete", "Prelievo\nda rete"]
    sizes = [autoconsumo_kwh, immissione_kwh, prelievo_kwh]
    colors = [COLORI["autoconsumo"], COLORI["immissione"], COLORI["prelievo"]]

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, textprops={"fontsize": 11},
    )
    ax.set_title("Ripartizione Flussi Energetici")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def grafico_flussi_cassa(
    flussi_cassa: list[dict],
    output_path: Path,
) -> Path:
    """Grafico flussi di cassa cumulati."""
    import matplotlib.pyplot as plt

    anni = [f["anno"] for f in flussi_cassa]
    cumulati = [f["flusso_cumulato_eur"] for f in flussi_cassa]

    fig, ax = plt.subplots(figsize=(10, 5))

    colori = [COLORI["npv_positivo"] if v >= 0 else COLORI["npv_negativo"] for v in cumulati]
    ax.bar(anni, cumulati, color=colori, edgecolor="white", width=0.8)
    ax.axhline(y=0, color="black", linewidth=0.8)

    ax.set_xlabel("Anno")
    ax.set_ylabel("Flusso Cumulato (EUR)")
    ax.set_title("Flussi di Cassa Cumulati")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def grafico_tornado(
    tornado_data: list[dict],
    npv_base: float,
    output_path: Path,
) -> Path:
    """Tornado diagram per analisi sensibilita."""
    import matplotlib.pyplot as plt

    if not tornado_data:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Nessun dato disponibile", ha="center", va="center")
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        return output_path

    labels = [d["variabile"] for d in tornado_data]
    npv_min = [d["npv_min_eur"] for d in tornado_data]
    npv_max = [d["npv_max_eur"] for d in tornado_data]

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.8)))
    y = np.arange(len(labels))

    for i, (label, nmin, nmax) in enumerate(zip(labels, npv_min, npv_max)):
        ax.barh(i, nmax - npv_base, left=npv_base, height=0.6,
                color=COLORI["npv_positivo"], alpha=0.7)
        ax.barh(i, nmin - npv_base, left=npv_base, height=0.6,
                color=COLORI["npv_negativo"], alpha=0.7)

    ax.axvline(x=npv_base, color="black", linewidth=1.2, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("NPV (EUR)")
    ax.set_title("Analisi di Sensibilita - Tornado Diagram")
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def grafico_produzione_giornaliera(
    serie_oraria: list[dict],
    giorno_idx: int,
    output_path: Path,
) -> Path:
    """Grafico produzione PV vs consumo per un giorno tipo."""
    import matplotlib.pyplot as plt

    start = giorno_idx * 24
    end = start + 24
    if end > len(serie_oraria):
        end = len(serie_oraria)
        start = max(0, end - 24)

    ore = list(range(24))
    prod = [serie_oraria[i].get("produzione_kwh", 0) for i in range(start, end)]
    cons = [serie_oraria[i].get("consumo_kwh", 0) for i in range(start, end)]
    auto = [serie_oraria[i].get("autoconsumo_kwh", 0) for i in range(start, end)]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ore, prod, color=COLORI["solare"], linewidth=2, label="Produzione PV")
    ax.plot(ore, cons, color=COLORI["consumo"], linewidth=2, label="Consumo")
    ax.fill_between(ore, 0, auto, alpha=0.3, color=COLORI["autoconsumo"],
                     label="Autoconsumo")

    ax.set_xlabel("Ora")
    ax.set_ylabel("Energia (kWh)")
    ax.set_title("Profilo Giornaliero Tipo")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
