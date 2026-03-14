"""Grafici matplotlib premium per report corporate EnerginaBatterina."""

from pathlib import Path

import numpy as np

from energina.core.logging_config import get_logger

logger = get_logger("report.grafici")

# Palette corporate
NAVY = "#1B2A4A"
NAVY_LIGHT = "#2D3F5F"
TEAL = "#0D7377"
TEAL_LIGHT = "#14A3A8"
GOLD = "#C8A951"
GOLD_LIGHT = "#E0C76A"
SLATE = "#4A5568"
LIGHT_BG = "#F7F8FA"
SUCCESS = "#2F855A"
SUCCESS_LIGHT = "#48BB78"
DANGER = "#C53030"
DANGER_LIGHT = "#FC8181"
CORAL = "#E05252"
SKY = "#3B82F6"
SKY_LIGHT = "#93C5FD"
WARM_GRAY = "#718096"


def _setup_style():
    """Stile corporate premium per matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    plt.rcParams.update({
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "axes.edgecolor": "#E2E8F0",
        "axes.linewidth": 0.6,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.titlepad": 16,
        "axes.labelsize": 9,
        "axes.labelcolor": SLATE,
        "axes.labelpad": 10,
        "xtick.color": WARM_GRAY,
        "ytick.color": WARM_GRAY,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,
        "grid.color": "#EDF2F7",
        "grid.linewidth": 0.5,
        "grid.alpha": 1.0,
        "legend.fontsize": 8.5,
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.edgecolor": "#E2E8F0",
        "legend.fancybox": True,
        "legend.borderpad": 0.8,
        "legend.handlelength": 1.5,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "figure.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.2,
        "savefig.facecolor": WHITE,
    })
    return plt


WHITE = "#FFFFFF"


def _brand_footer(fig):
    """Brand sottile in basso a destra."""
    fig.text(
        0.98, 0.008, "ENERGINA BATTERINA",
        fontsize=5.5, color="#CBD5E0", alpha=0.5,
        ha="right", va="bottom",
        fontfamily="sans-serif", fontweight="bold",
    )


def _format_eur(val):
    """Formatta valore in EUR con separatori."""
    if abs(val) >= 1000:
        return f"{val:,.0f}".replace(",", ".")
    return f"{val:.0f}"


# ============================================================
#  1. BILANCIO MENSILE
# ============================================================

def grafico_bilancio_mensile(
    produzione_mensile: list[float],
    consumo_mensile: list[float],
    output_path: Path,
) -> Path:
    """Bilancio mensile con barre affiancate e linea bilancio netto."""
    plt = _setup_style()

    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
            "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    x = np.arange(len(mesi))
    w = 0.35
    bilancio = [p - c for p, c in zip(produzione_mensile, consumo_mensile)]

    fig, ax = plt.subplots(figsize=(12, 5.5))

    # Barre
    ax.bar(x - w / 2, produzione_mensile, w,
           label="Produzione PV", color=GOLD, zorder=3)
    ax.bar(x + w / 2, consumo_mensile, w,
           label="Consumo Edificio", color=NAVY, alpha=0.82, zorder=3)

    # Linea bilancio netto su asse secondario
    ax2 = ax.twinx()
    ax2.plot(x, bilancio, color=TEAL, linewidth=2, marker="D",
             markersize=5, markerfacecolor=WHITE, markeredgecolor=TEAL,
             markeredgewidth=1.5, label="Bilancio Netto", zorder=5)
    ax2.axhline(y=0, color=TEAL, linewidth=0.6, linestyle=":", alpha=0.5)
    ax2.set_ylabel("Bilancio Netto (kWh)", color=TEAL, fontsize=9)
    ax2.tick_params(axis="y", colors=TEAL, labelsize=8)
    ax2.spines["right"].set_color(TEAL)
    ax2.spines["right"].set_linewidth(0.8)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)

    # Etichette produzione
    max_val = max(max(produzione_mensile), max(consumo_mensile))
    for i, v in enumerate(produzione_mensile):
        if v > 0:
            ax.text(i - w / 2, v + max_val * 0.015, f"{v:.0f}",
                    ha="center", va="bottom", fontsize=6.5, color=SLATE,
                    fontweight="bold")

    ax.set_xlabel("")
    ax.set_ylabel("Energia (kWh)")
    ax.set_title("Bilancio Energetico Mensile")
    ax.set_xticks(x)
    ax.set_xticklabels(mesi)
    ax.set_xlim(-0.6, 11.6)
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legenda combinata
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2,
              loc="upper left", ncols=3, borderaxespad=1.2)

    _brand_footer(fig)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


# ============================================================
#  2. DONUT AUTOCONSUMO
# ============================================================

def grafico_autoconsumo_pie(
    autoconsumo_kwh: float,
    immissione_kwh: float,
    prelievo_kwh: float,
    output_path: Path,
) -> Path:
    """Donut chart elegante con breakdown flussi energetici."""
    plt = _setup_style()

    raw = [
        ("Autoconsumo", autoconsumo_kwh, TEAL),
        ("Immissione in rete", immissione_kwh, GOLD),
        ("Prelievo da rete", prelievo_kwh, NAVY),
    ]
    filtered = [(l, s, c) for l, s, c in raw if s > 0]
    if not filtered:
        filtered = [("Nessun dato", 1, SLATE)]

    labels, sizes, palette = zip(*filtered)
    totale = sum(sizes)

    fig, ax = plt.subplots(figsize=(7, 6.5))

    # Anello esterno
    wedges, _, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=palette,
        autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
        startangle=90,
        pctdistance=0.80,
        wedgeprops={"width": 0.38, "edgecolor": WHITE, "linewidth": 2.5},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
        at.set_color(WHITE)

    # Centro
    ax.text(0, 0.08, f"{totale:,.0f}", ha="center", va="center",
            fontsize=22, fontweight="bold", color=NAVY)
    ax.text(0, -0.08, "kWh", ha="center", va="center",
            fontsize=9, color=WARM_GRAY)

    # Legenda con valori
    legend_labels = [f"{l}  ({s:,.0f} kWh)" for l, s in zip(labels, sizes)]
    legend = ax.legend(
        wedges, legend_labels,
        loc="lower center", ncols=min(len(labels), 3),
        frameon=True, fontsize=8.5,
        bbox_to_anchor=(0.5, -0.04),
        handlelength=1.2,
    )
    legend.get_frame().set_edgecolor("#E2E8F0")

    ax.set_title("Ripartizione Flussi Energetici", pad=20, fontsize=14)

    _brand_footer(fig)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


# ============================================================
#  3. FLUSSI DI CASSA
# ============================================================

def grafico_flussi_cassa(
    flussi_cassa: list[dict],
    output_path: Path,
) -> Path:
    """Flussi di cassa: area cumulata + barre annuali."""
    plt = _setup_style()

    anni = [f["anno"] for f in flussi_cassa]
    cumulati = [f["flusso_cumulato_eur"] for f in flussi_cassa]
    netti = [f["flusso_netto_eur"] for f in flussi_cassa]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 7),
        gridspec_kw={"height_ratios": [2.5, 1], "hspace": 0.28},
    )

    # --- Superiore: cumulato ---
    # Area fill sfumata
    pos = [max(0, v) for v in cumulati]
    neg = [min(0, v) for v in cumulati]
    ax1.fill_between(anni, 0, pos, alpha=0.08, color=SUCCESS, zorder=2)
    ax1.fill_between(anni, neg, 0, alpha=0.08, color=DANGER, zorder=2)

    # Linea principale
    ax1.plot(anni, cumulati, color=NAVY, linewidth=2.5, zorder=4,
             solid_capstyle="round")
    # Punti
    ax1.scatter(anni, cumulati, color=NAVY, s=18, zorder=5,
                edgecolors=WHITE, linewidths=1)

    ax1.axhline(y=0, color=WARM_GRAY, linewidth=0.7, zorder=1)

    # Payback
    for i in range(1, len(cumulati)):
        if cumulati[i - 1] < 0 <= cumulati[i]:
            frac = -cumulati[i - 1] / (cumulati[i] - cumulati[i - 1])
            pb = anni[i - 1] + frac
            ax1.axvline(x=pb, color=TEAL, linewidth=1.5,
                        linestyle="--", alpha=0.6, zorder=3)
            # Badge payback
            ax1.annotate(
                f" Payback  {pb:.1f} anni ",
                xy=(pb, 0),
                xytext=(pb + 2, min(cumulati) * 0.25),
                fontsize=8, color=WHITE, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4", facecolor=TEAL,
                          edgecolor="none", alpha=0.9),
                arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.2),
                ha="left", va="center",
            )
            break

    # Valore finale
    final_color = SUCCESS if cumulati[-1] >= 0 else DANGER
    ax1.annotate(
        f" {_format_eur(cumulati[-1])} EUR ",
        xy=(anni[-1], cumulati[-1]),
        xytext=(-8, 12), textcoords="offset points",
        fontsize=9, fontweight="bold", color=WHITE,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=final_color,
                  edgecolor="none", alpha=0.9),
        ha="right", va="bottom",
    )

    ax1.set_ylabel("Flusso Cumulato (EUR)")
    ax1.set_title("Analisi Flussi di Cassa", fontsize=14)
    ax1.grid(axis="y", zorder=0)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # --- Inferiore: barre netti ---
    for i, (anno, netto) in enumerate(zip(anni, netti)):
        c = SUCCESS if netto >= 0 else DANGER
        ax2.bar(anno, netto, color=c, width=0.7, zorder=3, alpha=0.8)

    ax2.axhline(y=0, color=WARM_GRAY, linewidth=0.5, zorder=1)
    ax2.set_xlabel("Anno")
    ax2.set_ylabel("Flusso Netto (EUR)")
    ax2.grid(axis="y", zorder=0)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Formato asse Y con separatori
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: _format_eur(x)))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: _format_eur(x)))

    _brand_footer(fig)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


# ============================================================
#  4. TORNADO SENSIBILITA
# ============================================================

def grafico_tornado(
    tornado_data: list[dict],
    npv_base: float,
    output_path: Path,
) -> Path:
    """Tornado diagram con barre separate e label chiare."""
    plt = _setup_style()

    if not tornado_data:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "Nessun dato disponibile",
                ha="center", va="center", fontsize=13, color=SLATE)
        ax.set_axis_off()
        fig.savefig(output_path)
        plt.close(fig)
        return output_path

    label_map = {
        "potenza_nominale_kwp": "Potenza PV",
        "prezzo_energia": "Prezzo Energia",
        "capacita_nominale_kwh": "Capacita Batteria",
        "costo_pv_eur": "Costo PV",
        "costo_batteria_eur": "Costo Batteria",
        "tasso_sconto": "Tasso di Sconto",
    }

    labels = [label_map.get(d["variabile"], d["variabile"]) for d in tornado_data]
    npv_min = np.array([d["npv_min_eur"] for d in tornado_data])
    npv_max = np.array([d["npv_max_eur"] for d in tornado_data])

    n = len(labels)
    fig, ax = plt.subplots(figsize=(12, max(3.5, n * 1.3 + 1.5)))
    y = np.arange(n)
    bar_h = 0.5

    # Calcola margini per le etichette
    val_range = max(abs(npv_min.min() - npv_base), abs(npv_max.max() - npv_base))
    margin = val_range * 0.12

    for i in range(n):
        delta_pos = npv_max[i] - npv_base
        delta_neg = npv_min[i] - npv_base

        # Barra positiva (verso destra)
        if delta_pos > 0:
            ax.barh(i, delta_pos, left=npv_base, height=bar_h,
                    color=TEAL, alpha=0.85, zorder=3)
        elif delta_pos < 0:
            ax.barh(i, delta_pos, left=npv_base, height=bar_h,
                    color=CORAL, alpha=0.85, zorder=3)

        # Barra negativa (verso sinistra)
        if delta_neg < 0:
            ax.barh(i, delta_neg, left=npv_base, height=bar_h,
                    color=CORAL, alpha=0.85, zorder=3)
        elif delta_neg > 0:
            ax.barh(i, delta_neg, left=npv_base, height=bar_h,
                    color=TEAL, alpha=0.85, zorder=3)

        # Etichette valori esterne
        ax.text(npv_min[i] - margin * 0.3, i,
                _format_eur(npv_min[i]),
                ha="right", va="center", fontsize=8, color=DANGER,
                fontweight="bold")
        ax.text(npv_max[i] + margin * 0.3, i,
                _format_eur(npv_max[i]),
                ha="left", va="center", fontsize=8, color=SUCCESS,
                fontweight="bold")

    # Linea base NPV
    ax.axvline(x=npv_base, color=NAVY, linewidth=1.8, linestyle="-", zorder=4)

    # Etichetta NPV base in alto
    ax.text(npv_base, -0.7,
            f"NPV base: {_format_eur(npv_base)} EUR",
            ha="center", va="bottom", fontsize=9, color=NAVY,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=LIGHT_BG,
                      edgecolor=NAVY, linewidth=0.5))

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10, fontweight="bold")
    ax.set_xlabel("NPV (EUR)")
    ax.set_title("Analisi di Sensibilita", fontsize=14)
    ax.grid(axis="x", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.invert_yaxis()

    # Margini X per label
    x_min = min(npv_min.min(), npv_base) - margin * 2
    x_max = max(npv_max.max(), npv_base) + margin * 2
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(n - 0.5, -1.0)

    ax.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: _format_eur(x)))

    _brand_footer(fig)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


# ============================================================
#  5. HEATMAP ANNUALE (CARPET PLOT)
# ============================================================

def grafico_heatmap_annuale(
    serie_contatore: list[dict],
    serie_pv: list[dict],
    output_path: Path,
) -> Path:
    """Carpet plot 365x24: produzione PV, consumo e bilancio netto ora per ora."""
    plt = _setup_style()
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.dates as mdates

    n_ore = len(serie_contatore)
    n_giorni = n_ore // 24
    if n_giorni < 2:
        return output_path

    # Estrai dati
    produzione = np.array([h.get("produzione_kwh", 0) for h in serie_contatore[:n_giorni * 24]])
    consumo = np.array([h.get("consumo_kwh", 0) for h in serie_contatore[:n_giorni * 24]])
    bilancio = produzione - consumo

    # Reshape in matrice giorni x ore
    prod_mat = produzione.reshape(n_giorni, 24)
    cons_mat = consumo.reshape(n_giorni, 24)
    bil_mat = bilancio.reshape(n_giorni, 24)

    # Crea figure con 3 subplot
    fig, axes = plt.subplots(3, 1, figsize=(14, 10),
                              gridspec_kw={"hspace": 0.35})

    mesi_labels = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    # Posizioni approssimative dei mesi (inizio mese, giorni cumulati)
    giorni_mese = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    mesi_pos = np.cumsum([0] + giorni_mese[:-1])

    ore_labels = ["00", "04", "08", "12", "16", "20"]
    ore_pos = [0, 4, 8, 12, 16, 20]

    # --- 1. Produzione PV ---
    cmap_prod = LinearSegmentedColormap.from_list(
        "pv_prod", [NAVY, TEAL_LIGHT, GOLD_LIGHT, GOLD, "#FF8C00"], N=256)
    im1 = axes[0].imshow(
        prod_mat.T, aspect="auto", origin="lower",
        cmap=cmap_prod, interpolation="bilinear",
        extent=[0, n_giorni, 0, 24],
    )
    axes[0].set_title("Produzione Fotovoltaica (kWh)", fontsize=12, pad=10)
    cb1 = fig.colorbar(im1, ax=axes[0], pad=0.02, aspect=25, shrink=0.85)
    cb1.set_label("kWh", fontsize=8)
    cb1.ax.tick_params(labelsize=7)

    # --- 2. Consumo Edificio ---
    cmap_cons = LinearSegmentedColormap.from_list(
        "consumo", [LIGHT_BG, SKY_LIGHT, SKY, NAVY_LIGHT, NAVY], N=256)
    im2 = axes[1].imshow(
        cons_mat.T, aspect="auto", origin="lower",
        cmap=cmap_cons, interpolation="bilinear",
        extent=[0, n_giorni, 0, 24],
    )
    axes[1].set_title("Consumo Edificio (kWh)", fontsize=12, pad=10)
    cb2 = fig.colorbar(im2, ax=axes[1], pad=0.02, aspect=25, shrink=0.85)
    cb2.set_label("kWh", fontsize=8)
    cb2.ax.tick_params(labelsize=7)

    # --- 3. Bilancio Netto ---
    vmax = max(abs(bil_mat.min()), abs(bil_mat.max()))
    cmap_bil = LinearSegmentedColormap.from_list(
        "bilancio", [DANGER, DANGER_LIGHT, WHITE, SUCCESS_LIGHT, SUCCESS], N=256)
    im3 = axes[2].imshow(
        bil_mat.T, aspect="auto", origin="lower",
        cmap=cmap_bil, interpolation="bilinear",
        vmin=-vmax, vmax=vmax,
        extent=[0, n_giorni, 0, 24],
    )
    axes[2].set_title("Bilancio Netto: Produzione - Consumo (kWh)", fontsize=12, pad=10)
    cb3 = fig.colorbar(im3, ax=axes[2], pad=0.02, aspect=25, shrink=0.85)
    cb3.set_label("kWh", fontsize=8)
    cb3.ax.tick_params(labelsize=7)

    # Stile comune
    for ax in axes:
        ax.set_yticks(ore_pos)
        ax.set_yticklabels(ore_labels)
        ax.set_ylabel("Ora", fontsize=9)
        # Mesi sull'asse X
        valid_pos = [p for p in mesi_pos if p < n_giorni]
        valid_labels = mesi_labels[:len(valid_pos)]
        ax.set_xticks(valid_pos)
        ax.set_xticklabels(valid_labels, fontsize=8)
        ax.tick_params(axis="both", which="both", length=0)
        # Linee verticali sottili per i mesi
        for mp in valid_pos[1:]:
            ax.axvline(x=mp, color=WHITE, linewidth=0.3, alpha=0.5)

    axes[2].set_xlabel("Mese")

    fig.suptitle("Profilo Energetico Annuale  -  365 giorni x 24 ore",
                 fontsize=15, fontweight="bold", color=NAVY, y=0.98)

    _brand_footer(fig)
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


# ============================================================
#  6. PROFILO GIORNALIERO TIPO
# ============================================================

def grafico_produzione_giornaliera(
    serie_oraria: list[dict],
    giorno_idx: int,
    output_path: Path,
) -> Path:
    """Profilo giornaliero produzione vs consumo con area autoconsumo."""
    plt = _setup_style()

    start = giorno_idx * 24
    end = start + 24
    if end > len(serie_oraria):
        end = len(serie_oraria)
        start = max(0, end - 24)

    ore = list(range(24))
    prod = [serie_oraria[i].get("produzione_kwh", 0) for i in range(start, end)]
    cons = [serie_oraria[i].get("consumo_kwh", 0) for i in range(start, end)]
    auto = [serie_oraria[i].get("autoconsumo_kwh", 0) for i in range(start, end)]

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.fill_between(ore, 0, prod, alpha=0.12, color=GOLD, zorder=2)
    ax.fill_between(ore, 0, auto, alpha=0.25, color=TEAL, zorder=2,
                     label="Autoconsumo")
    ax.plot(ore, prod, color=GOLD, linewidth=2.5, label="Produzione PV",
            zorder=3, solid_capstyle="round")
    ax.plot(ore, cons, color=NAVY, linewidth=2.5, label="Consumo",
            zorder=3, solid_capstyle="round")

    ax.set_xlabel("Ora del giorno")
    ax.set_ylabel("Energia (kWh)")
    ax.set_title("Profilo Giornaliero Tipo")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], fontsize=7.5)
    ax.legend(loc="upper right")
    ax.grid(zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _brand_footer(fig)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
