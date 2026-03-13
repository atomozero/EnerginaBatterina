"""Template e layout PDF con ReportLab."""

from pathlib import Path

from energina.core.logging_config import get_logger

logger = get_logger("report.template_pdf")


def genera_pdf(
    titolo: str,
    sezioni: list[dict],
    grafici_paths: list[Path],
    output_path: Path,
) -> Path:
    """Genera report PDF con ReportLab.

    Args:
        titolo: Titolo del report.
        sezioni: Lista di sezioni con contenuto testuale e tabelle.
        grafici_paths: Lista di percorsi ai grafici PNG.
        output_path: Percorso file PDF di output.

    Returns:
        Path del PDF generato.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        logger.warning("ReportLab non disponibile, generazione report testuale")
        return _genera_report_testuale(titolo, sezioni, output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    style_titolo = ParagraphStyle(
        "TitoloReport",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=30,
        textColor=colors.HexColor("#1565C0"),
    )
    style_h2 = ParagraphStyle(
        "Sezione",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#2E7D32"),
    )
    style_body = styles["Normal"]
    style_body.fontSize = 10
    style_body.leading = 14

    elementi = []

    # Titolo
    elementi.append(Paragraph(titolo, style_titolo))
    elementi.append(Spacer(1, 10))

    # Sezioni
    for sez in sezioni:
        elementi.append(Paragraph(sez.get("titolo", ""), style_h2))

        # Testo
        for paragrafo in sez.get("testo", []):
            elementi.append(Paragraph(paragrafo, style_body))
            elementi.append(Spacer(1, 5))

        # Tabella
        if "tabella" in sez:
            tab = sez["tabella"]
            dati_tab = tab.get("righe", [])
            if dati_tab:
                t = Table(dati_tab, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#F5F5F5")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                elementi.append(t)
                elementi.append(Spacer(1, 10))

    # Grafici
    for grafico_path in grafici_paths:
        if grafico_path.exists():
            elementi.append(PageBreak())
            nome = grafico_path.stem.replace("_", " ").title()
            elementi.append(Paragraph(nome, style_h2))
            img = Image(str(grafico_path), width=16 * cm, height=9 * cm)
            elementi.append(img)
            elementi.append(Spacer(1, 10))

    doc.build(elementi)
    logger.info(f"Report PDF generato: {output_path}")
    return output_path


def _genera_report_testuale(
    titolo: str, sezioni: list[dict], output_path: Path
) -> Path:
    """Fallback: genera report come file di testo."""
    output_txt = output_path.with_suffix(".txt")
    output_txt.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"{'='*60}", f"  {titolo}", f"{'='*60}", ""]

    for sez in sezioni:
        lines.append(f"\n--- {sez.get('titolo', '')} ---")
        for p in sez.get("testo", []):
            lines.append(p)
        if "tabella" in sez:
            for riga in sez["tabella"].get("righe", []):
                lines.append("  |  ".join(str(c) for c in riga))
        lines.append("")

    output_txt.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Report testuale generato: {output_txt}")
    return output_txt
