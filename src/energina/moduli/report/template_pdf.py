"""Template PDF corporate EnerginaBatterina - Layout professionale."""

from datetime import datetime
from pathlib import Path

from energina.core.logging_config import get_logger

logger = get_logger("report.template_pdf")

# Palette corporate
NAVY = "#1B2A4A"
TEAL = "#0D7377"
GOLD = "#C8A951"
SLATE = "#4A5568"
LIGHT_BG = "#F7F8FA"
WHITE = "#FFFFFF"
DARK_TEXT = "#1A202C"
MID_TEXT = "#4A5568"
LIGHT_LINE = "#E2E8F0"
SUCCESS = "#2F855A"
DANGER = "#C53030"


def genera_pdf(
    titolo: str,
    sezioni: list[dict],
    grafici_paths: list[Path],
    output_path: Path,
) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            Frame,
            Image,
            NextPageTemplate,
            PageBreak,
            PageTemplate,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
            BaseDocTemplate,
        )
        from reportlab.graphics.shapes import Drawing, Line, Rect
        from reportlab.graphics import renderPDF
    except ImportError:
        logger.warning("ReportLab non disponibile, generazione report testuale")
        return _genera_report_testuale(titolo, sezioni, output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    W, H = A4

    # --- Stili ---
    styles = _crea_stili()

    # --- Documento ---
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.8 * cm,
        bottomMargin=2.2 * cm,
    )

    elementi = []

    # === COVER PAGE ===
    elementi += _crea_cover(titolo, sezioni, styles, W, H)
    elementi.append(PageBreak())

    # === EXECUTIVE SUMMARY (KPI cards) ===
    elementi += _crea_executive_summary(sezioni, styles)
    elementi.append(PageBreak())

    # === SEZIONI CONTENUTO ===
    for i, sez in enumerate(sezioni):
        tipo = sez.get("tipo", "standard")
        if tipo == "kpi":
            continue  # gia' nel summary

        elementi += _crea_sezione(sez, styles, i)

    # === GRAFICI ===
    for grafico_path in grafici_paths:
        if grafico_path.exists():
            elementi.append(PageBreak())
            nome = grafico_path.stem.replace("_", " ").title()
            elementi += _crea_intestazione_sezione(nome, styles)
            elementi.append(Spacer(1, 8 * mm))
            img_w = 15.6 * cm
            img_h = 8.8 * cm
            img = Image(str(grafico_path), width=img_w, height=img_h)
            elementi.append(img)
            elementi.append(Spacer(1, 6 * mm))

    # === FOOTER / DISCLAIMER ===
    elementi.append(Spacer(1, 15 * mm))
    elementi += _crea_disclaimer(styles)

    doc.build(elementi, onFirstPage=_pagina_cover, onLaterPages=_pagina_standard)
    logger.info(f"Report PDF generato: {output_path}")
    return output_path


def _crea_stili():
    """Stili tipografici corporate."""
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors

    base_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", fontName=bold_font, fontSize=28,
            leading=34, textColor=colors.HexColor(WHITE),
            alignment=TA_LEFT, spaceAfter=6,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", fontName=base_font, fontSize=13,
            leading=18, textColor=colors.HexColor("#CBD5E0"),
            alignment=TA_LEFT, spaceAfter=4,
        ),
        "cover_date": ParagraphStyle(
            "CoverDate", fontName=base_font, fontSize=10,
            leading=14, textColor=colors.HexColor(GOLD),
            alignment=TA_LEFT,
        ),
        "section_title": ParagraphStyle(
            "SectionTitle", fontName=bold_font, fontSize=15,
            leading=20, textColor=colors.HexColor(NAVY),
            spaceBefore=0, spaceAfter=2,
        ),
        "section_number": ParagraphStyle(
            "SectionNumber", fontName=bold_font, fontSize=11,
            leading=14, textColor=colors.HexColor(TEAL),
            spaceBefore=0, spaceAfter=0,
        ),
        "body": ParagraphStyle(
            "Body", fontName=base_font, fontSize=9.5,
            leading=14, textColor=colors.HexColor(DARK_TEXT),
            alignment=TA_LEFT, spaceAfter=3,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold", fontName=bold_font, fontSize=9.5,
            leading=14, textColor=colors.HexColor(DARK_TEXT),
            alignment=TA_LEFT, spaceAfter=3,
        ),
        "kpi_value": ParagraphStyle(
            "KPIValue", fontName=bold_font, fontSize=20,
            leading=24, textColor=colors.HexColor(NAVY),
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "KPILabel", fontName=base_font, fontSize=8,
            leading=11, textColor=colors.HexColor(MID_TEXT),
            alignment=TA_CENTER,
        ),
        "kpi_unit": ParagraphStyle(
            "KPIUnit", fontName=base_font, fontSize=9,
            leading=12, textColor=colors.HexColor(TEAL),
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", fontName=bold_font, fontSize=8.5,
            leading=12, textColor=colors.HexColor(WHITE),
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", fontName=base_font, fontSize=8.5,
            leading=12, textColor=colors.HexColor(DARK_TEXT),
            alignment=TA_LEFT,
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight", fontName=base_font, fontSize=8.5,
            leading=12, textColor=colors.HexColor(DARK_TEXT),
            alignment=TA_RIGHT,
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer", fontName=base_font, fontSize=7,
            leading=10, textColor=colors.HexColor(MID_TEXT),
            alignment=TA_LEFT,
        ),
        "graph_title": ParagraphStyle(
            "GraphTitle", fontName=bold_font, fontSize=13,
            leading=17, textColor=colors.HexColor(NAVY),
            alignment=TA_LEFT, spaceAfter=2,
        ),
    }


# ============================================================
#  Cover Page
# ============================================================

def _crea_cover(titolo, sezioni, styles, W, H):
    """Costruisce elementi per la cover page (il background e' in onFirstPage)."""
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
    from reportlab.lib import colors

    elementi = []
    # Lo spazio dall'alto e' gestito dal callback _pagina_cover
    # che disegna il rettangolo navy. Qui mettiamo solo spaziatura
    # per posizionare il testo nella zona navy.
    elementi.append(Spacer(1, 6.5 * cm))

    # Titolo progetto - estrai dal titolo
    nome_progetto = titolo.replace("Report - ", "")
    elementi.append(Paragraph(nome_progetto, styles["cover_title"]))
    elementi.append(Spacer(1, 3 * mm))

    elementi.append(Paragraph(
        "Analisi Tecnico-Economica Impianto Fotovoltaico con Accumulo",
        styles["cover_subtitle"],
    ))
    elementi.append(Spacer(1, 5 * mm))

    data_str = datetime.now().strftime("%d %B %Y").replace(
        "January", "Gennaio").replace("February", "Febbraio").replace(
        "March", "Marzo").replace("April", "Aprile").replace(
        "May", "Maggio").replace("June", "Giugno").replace(
        "July", "Luglio").replace("August", "Agosto").replace(
        "September", "Settembre").replace("October", "Ottobre").replace(
        "November", "Novembre").replace("December", "Dicembre")
    elementi.append(Paragraph(f"Data: {data_str}", styles["cover_date"]))

    # Spazio per arrivare alla zona bianca inferiore
    elementi.append(Spacer(1, 5.5 * cm))

    # Mini-riepilogo KPI sulla cover
    kpi_sez = _trova_sezione(sezioni, "Sommario Risultati")
    eco_sez = _trova_sezione(sezioni, "Analisi Economica")
    if kpi_sez:
        kpi_data = _estrai_kpi_cover(kpi_sez, eco_sez)
        if kpi_data:
            elementi += _crea_kpi_strip(kpi_data, styles)

    return elementi


def _estrai_kpi_cover(kpi_sez, eco_sez):
    """Estrai dati KPI per la cover."""
    dati = []
    testi = kpi_sez.get("testo", [])
    for t in testi:
        if "Produzione annua:" in t:
            val = t.split(":")[1].strip().replace(" kWh", "")
            dati.append(("Produzione", val, "kWh/anno"))
        elif "Autoconsumo:" in t and "%" in t:
            val = t.split(":")[1].strip().replace("%", "")
            dati.append(("Autoconsumo", val, "%"))
        elif "NPV:" in t:
            val = t.split(":")[1].strip().replace(" EUR", "")
            dati.append(("NPV", val, "EUR"))
        elif "Payback:" in t:
            val = t.split(":")[1].strip().replace(" anni", "")
            dati.append(("Payback", val, "anni"))
    return dati[:4]  # max 4 KPI


def _crea_kpi_strip(kpi_data, styles):
    """Crea striscia orizzontale di KPI cards."""
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm

    cells = []
    for label, value, unit in kpi_data:
        cell_content = [
            [Paragraph(f"<b>{value}</b>", styles["kpi_value"])],
            [Paragraph(unit, styles["kpi_unit"])],
            [Paragraph(label.upper(), styles["kpi_label"])],
        ]
        inner = Table(cell_content, colWidths=[3.8 * cm])
        inner.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        cells.append(inner)

    n = len(cells)
    col_w = 4.0 * cm
    t = Table([cells], colWidths=[col_w] * n)
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(WHITE)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(LIGHT_LINE)),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.HexColor(LIGHT_LINE)),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return [t, Spacer(1, 5 * mm)]


# ============================================================
#  Executive Summary
# ============================================================

def _crea_executive_summary(sezioni, styles):
    """Pagina con KPI grandi + tabella indicatori."""
    from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm

    elementi = []
    elementi += _crea_intestazione_sezione("Executive Summary", styles)
    elementi.append(Spacer(1, 5 * mm))

    kpi_sez = _trova_sezione(sezioni, "Sommario Risultati")
    if kpi_sez:
        kpi_data = _estrai_kpi_cover(kpi_sez, None)
        if kpi_data:
            # KPI grandi con box colorati
            elementi += _crea_kpi_box_grandi(kpi_data, styles)
            elementi.append(Spacer(1, 8 * mm))

    # Tabella indicatori economici
    eco_sez = _trova_sezione(sezioni, "Analisi Economica")
    if eco_sez and "tabella" in eco_sez:
        elementi.append(Paragraph("Indicatori Economici", styles["body_bold"]))
        elementi.append(Spacer(1, 3 * mm))
        righe = eco_sez["tabella"]["righe"]
        elementi.append(_crea_tabella_corporate(righe, styles))
        elementi.append(Spacer(1, 6 * mm))

    # Tabella incentivi
    inc_sez = _trova_sezione(sezioni, "Incentivi")
    if inc_sez:
        elementi.append(Paragraph("Incentivi Attivi", styles["body_bold"]))
        elementi.append(Spacer(1, 3 * mm))
        for t in inc_sez.get("testo", []):
            elementi.append(Paragraph(f"\u2022  {t}", styles["body"]))

    return elementi


def _crea_kpi_box_grandi(kpi_data, styles):
    """KPI boxes grandi per executive summary."""
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle

    box_colors = [TEAL, NAVY, SUCCESS, GOLD]
    cells = []
    for i, (label, value, unit) in enumerate(kpi_data):
        bg = box_colors[i % len(box_colors)]
        val_style = ParagraphStyle(
            f"KPIBig{i}", fontName="Helvetica-Bold", fontSize=22,
            leading=26, textColor=colors.HexColor(WHITE), alignment=TA_CENTER,
        )
        unit_style = ParagraphStyle(
            f"KPIBigUnit{i}", fontName="Helvetica", fontSize=9,
            leading=12, textColor=colors.HexColor("#E2E8F0"), alignment=TA_CENTER,
        )
        lbl_style = ParagraphStyle(
            f"KPIBigLbl{i}", fontName="Helvetica-Bold", fontSize=7.5,
            leading=10, textColor=colors.HexColor("#E2E8F0"), alignment=TA_CENTER,
        )
        inner = Table([
            [Paragraph(label.upper(), lbl_style)],
            [Paragraph(f"<b>{value}</b>", val_style)],
            [Paragraph(unit, unit_style)],
        ], colWidths=[3.6 * cm])
        inner.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
            ("TOPPADDING", (0, 0), (0, 0), 10),
            ("BOTTOMPADDING", (0, -1), (0, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        cells.append(inner)

    n = len(cells)
    col_w = 3.8 * cm
    t = Table([cells], colWidths=[col_w] * n)
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [t]


# ============================================================
#  Sezioni Contenuto
# ============================================================

def _crea_intestazione_sezione(titolo, styles, numero=None):
    """Crea intestazione sezione con linea accent."""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm

    elementi = []

    if numero is not None:
        elementi.append(Paragraph(f"{numero:02d}", styles["section_number"]))

    elementi.append(Paragraph(titolo, styles["section_title"]))

    # Linea accent teal
    line_data = [["",""]]
    line = Table(line_data, colWidths=[3.5 * cm, 13 * cm])
    line.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (0, 0), 2.5, colors.HexColor(TEAL)),
        ("LINEBELOW", (1, 0), (1, 0), 0.5, colors.HexColor(LIGHT_LINE)),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    elementi.append(line)
    elementi.append(Spacer(1, 4 * mm))
    return elementi


def _crea_sezione(sez, styles, idx):
    """Crea una sezione di contenuto."""
    from reportlab.platypus import Spacer, Paragraph
    from reportlab.lib.units import mm

    elementi = []
    titolo = sez.get("titolo", "")

    # Skip sezioni gia' gestite nell'executive summary
    if titolo in ("Sommario Risultati", "Analisi Economica", "Incentivi"):
        return []

    elementi += _crea_intestazione_sezione(titolo, styles, idx + 1)

    # Contenuto testuale con bullet eleganti
    for paragrafo in sez.get("testo", []):
        # Separa label: valore
        if ":" in paragrafo and not paragrafo.startswith("("):
            parts = paragrafo.split(":", 1)
            testo_fmt = f"<b>{parts[0]}:</b>{parts[1]}"
        else:
            testo_fmt = paragrafo
        elementi.append(Paragraph(testo_fmt, styles["body"]))
        elementi.append(Spacer(1, 1.5 * mm))

    # Tabella
    if "tabella" in sez:
        righe = sez["tabella"].get("righe", [])
        if righe:
            elementi.append(Spacer(1, 3 * mm))
            elementi.append(_crea_tabella_corporate(righe, styles))

    elementi.append(Spacer(1, 8 * mm))
    return elementi


def _crea_tabella_corporate(righe, styles):
    """Tabella con stile corporate elegante."""
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm

    if not righe:
        return Spacer(1, 1)

    # Converti in Paragraph per controllo stile
    formatted = []
    for i, riga in enumerate(righe):
        if i == 0:
            formatted.append([
                Paragraph(str(c), styles["table_header"]) for c in riga
            ])
        else:
            cells = []
            for j, c in enumerate(riga):
                s = styles["table_cell_right"] if j > 0 else styles["table_cell"]
                cells.append(Paragraph(str(c), s))
            formatted.append(cells)

    n_cols = len(righe[0]) if righe else 2
    if n_cols == 2:
        col_widths = [6 * cm, 5.5 * cm]
    else:
        w = 16 * cm / n_cols
        col_widths = [w] * n_cols

    t = Table(formatted, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(WHITE)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        # Righe alternate
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor(WHITE), colors.HexColor(LIGHT_BG)]),
        # Bordi sottili
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor(TEAL)),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, colors.HexColor(LIGHT_LINE)),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor(NAVY)),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        # Allineamento
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# ============================================================
#  Page callbacks (header/footer)
# ============================================================

def _pagina_cover(canvas, doc):
    """Disegna sfondo cover page."""
    canvas.saveState()
    from reportlab.lib.pagesizes import A4
    W, H = A4

    # Rettangolo navy grande (parte superiore ~55%)
    canvas.setFillColor(colors_hex(NAVY))
    canvas.rect(0, H * 0.4, W, H * 0.6, fill=1, stroke=0)

    # Accento teal sottile
    canvas.setFillColor(colors_hex(TEAL))
    canvas.rect(0, H * 0.4, W, 4, fill=1, stroke=0)

    # Linea gold decorativa
    canvas.setStrokeColor(colors_hex(GOLD))
    canvas.setLineWidth(1.2)
    canvas.line(2.2 * 28.35, H * 0.4 + 25, 8 * 28.35, H * 0.4 + 25)

    # Brand badge in alto a sinistra
    canvas.setFillColor(colors_hex(GOLD))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(2.2 * 28.35, H - 1.5 * 28.35, "ENERGINA BATTERINA")

    canvas.setFillColor(colors_hex("#CBD5E0"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(2.2 * 28.35, H - 1.9 * 28.35, "ENERGY ANALYTICS PLATFORM")

    # Footer cover
    canvas.setFillColor(colors_hex(MID_TEXT))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        2.2 * 28.35, 1.2 * 28.35,
        "Documento generato automaticamente da EnerginaBatterina v0.1.0"
    )
    canvas.drawRightString(
        W - 2.2 * 28.35, 1.2 * 28.35,
        f"Confidenziale"
    )

    canvas.restoreState()


def _pagina_standard(canvas, doc):
    """Header e footer per pagine standard."""
    canvas.saveState()
    from reportlab.lib.pagesizes import A4  # noqa: F811
    W, H = A4

    # Header: linea teal + brand
    canvas.setStrokeColor(colors_hex(TEAL))
    canvas.setLineWidth(1.5)
    canvas.line(2.2 * 28.35, H - 1.6 * 28.35, W - 2.2 * 28.35, H - 1.6 * 28.35)

    canvas.setFillColor(colors_hex(NAVY))
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(2.2 * 28.35, H - 1.4 * 28.35, "ENERGINA BATTERINA")

    canvas.setFillColor(colors_hex(MID_TEXT))
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(
        W - 2.2 * 28.35, H - 1.4 * 28.35,
        "Analisi Tecnico-Economica"
    )

    # Footer: linea + pagina
    canvas.setStrokeColor(colors_hex(LIGHT_LINE))
    canvas.setLineWidth(0.5)
    canvas.line(2.2 * 28.35, 1.6 * 28.35, W - 2.2 * 28.35, 1.6 * 28.35)

    canvas.setFillColor(colors_hex(MID_TEXT))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        2.2 * 28.35, 1.0 * 28.35,
        datetime.now().strftime("%d/%m/%Y")
    )
    canvas.drawCentredString(W / 2, 1.0 * 28.35, "Confidenziale")
    canvas.drawRightString(
        W - 2.2 * 28.35, 1.0 * 28.35,
        f"Pagina {doc.page}"
    )

    canvas.restoreState()


# ============================================================
#  Disclaimer
# ============================================================

def _crea_disclaimer(styles):
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm

    elementi = []
    line_data = [[""]]
    line = Table(line_data, colWidths=[16.6 * cm])
    line.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.5, colors.HexColor(LIGHT_LINE)),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementi.append(line)
    elementi.append(Spacer(1, 3 * mm))
    elementi.append(Paragraph(
        "I risultati presentati sono basati su modelli di simulazione e dati sintetici/storici. "
        "I valori effettivi di produzione, consumo e ritorno economico possono variare "
        "in funzione delle condizioni meteorologiche reali, dei prezzi di mercato e delle "
        "condizioni operative dell'impianto. Questo documento ha finalita' puramente indicativa "
        "e non costituisce consulenza finanziaria o tecnica vincolante.",
        styles["disclaimer"],
    ))
    return elementi


# ============================================================
#  Utility
# ============================================================

def _trova_sezione(sezioni, titolo):
    for s in sezioni:
        if s.get("titolo") == titolo:
            return s
    return None


def colors_hex(hex_str):
    """Converte hex string in colore ReportLab."""
    from reportlab.lib.colors import HexColor
    return HexColor(hex_str)


# ============================================================
#  Fallback testo
# ============================================================

def _genera_report_testuale(
    titolo: str, sezioni: list[dict], output_path: Path
) -> Path:
    output_txt = output_path.with_suffix(".txt")
    output_txt.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"{'=' * 60}", f"  {titolo}", f"{'=' * 60}", ""]

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
