import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from utils.assets import get_logo_path


# ── Paleta (negro/gris oscuro) ───────────────────────────────────────────
COLOR_NEGRO       = colors.HexColor("#1a1a1a")
COLOR_GRIS_OSCURO = colors.HexColor("#2d2d2d")
COLOR_GRIS_MEDIO  = colors.HexColor("#555555")
COLOR_GRIS_CLARO  = colors.HexColor("#e8e8e8")
COLOR_GRIS_FONDO  = colors.HexColor("#f5f5f5")
COLOR_LINEA       = colors.HexColor("#cccccc")
COLOR_FILA_PAR    = colors.HexColor("#f9f9f9")
COLOR_FILA_IMPAR  = colors.white

COLOR_TOTAL_BG    = colors.HexColor("#1a1a1a")
COLOR_TOTAL_FG    = colors.white

COLOR_VERDE       = colors.HexColor("#1a6e3a")
COLOR_VERDE_BG    = colors.HexColor("#e8f5ee")
COLOR_ROJO        = colors.HexColor("#a92222")
COLOR_ROJO_BG     = colors.HexColor("#fbeaea")
COLOR_NARANJA     = colors.HexColor("#7d4e00")
COLOR_NARANJA_BG  = colors.HexColor("#fff3cd")


# ── Helpers ──────────────────────────────────────────────────────────────
def _fmt_moneda(valor):
    try:
        resultado = f"${float(valor):,.2f}"
    except Exception:
        resultado = "$0.00"
    return resultado


def _fmt_fecha(valor):
    resultado = "—"
    if valor:
        try:
            resultado = datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            resultado = str(valor)
    return resultado


def _fmt_fecha_hora(valor):
    resultado = "—"
    if valor:
        try:
            dt        = datetime.strptime(str(valor)[:16], "%Y-%m-%d %H:%M")
            resultado = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            resultado = _fmt_fecha(valor)
    return resultado


def _label_tipo(tipo):
    return "Pago de Cuota" if tipo == "pago_cuota" else "Otros Pagos"


def _label_mes(mes):
    return mes.capitalize() if mes else "—"


def _construir_pagina(canvas_obj, doc):
    canvas_obj.saveState()
    ancho, alto = A4
    margen = 1.1 * cm

    # Borde exterior negro fino
    canvas_obj.setStrokeColor(COLOR_NEGRO)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.rect(margen, margen, ancho - 2 * margen, alto - 2 * margen)

    # Franja superior negra
    canvas_obj.setFillColor(COLOR_NEGRO)
    canvas_obj.setStrokeColor(colors.transparent)
    canvas_obj.rect(margen, alto - margen - 0.55 * cm,
                    ancho - 2 * margen, 0.55 * cm, fill=1, stroke=0)

    # Franja inferior negra con número de página
    canvas_obj.rect(margen, margen,
                    ancho - 2 * margen, 0.55 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.drawCentredString(ancho / 2, margen + 0.14 * cm,
                                  f"Club Siglo XXI  —  Recibo N° {doc._recibo_id}")
    canvas_obj.restoreState()


# ── Generador principal ──────────────────────────────────────────────────
def generar_pdf_recibo(recibo: dict, ruta_salida: str = None) -> str:
    resultado_ruta = ruta_salida
    if resultado_ruta is None:
        fd, resultado_ruta = tempfile.mkstemp(
            suffix=".pdf", prefix=f"recibo_{recibo.get('id', 'x')}_"
        )
        os.close(fd)

    doc = SimpleDocTemplate(
        resultado_ruta,
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.6 * cm,
        bottomMargin=2.4 * cm,
    )
    doc._recibo_id = recibo.get("id") or "—"

    styles  = getSampleStyleSheet()
    ancho_u = A4[0] - 4.4 * cm

    # ── Estilos ───────────────────────────────────────────────────────────
    def _e(nombre, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(nombre, parent=base, **kw)

    es_titulo      = _e("titulo",  fontSize=20, fontName="Helvetica-Bold",
                         alignment=TA_CENTER, textColor=COLOR_NEGRO,
                         spaceAfter=2, leading=24)
    es_club        = _e("club",    fontSize=11, fontName="Helvetica-Bold",
                         alignment=TA_CENTER, textColor=COLOR_GRIS_OSCURO)
    es_meta        = _e("meta",    fontSize=8.5, alignment=TA_CENTER,
                         textColor=COLOR_GRIS_MEDIO, leading=13)
    es_seccion     = _e("sec",     fontSize=10, fontName="Helvetica-Bold",
                         textColor=COLOR_NEGRO, spaceBefore=12, spaceAfter=4)
    es_lbl         = _e("lbl",     fontSize=9,  fontName="Helvetica-Bold",
                         textColor=COLOR_GRIS_OSCURO, leading=12)
    es_val         = _e("val",     fontSize=9,  leading=12,
                         textColor=colors.HexColor("#333333"))
    es_der         = _e("der",     fontSize=9,  leading=12,
                         alignment=TA_RIGHT,
                         textColor=colors.HexColor("#333333"))
    es_total_l     = _e("tl",      fontSize=10, fontName="Helvetica-Bold",
                         textColor=COLOR_TOTAL_FG, leading=13)
    es_total_v     = _e("tv",      fontSize=10, fontName="Helvetica-Bold",
                         textColor=COLOR_TOTAL_FG, leading=13, alignment=TA_RIGHT)
    es_abonado_l   = _e("abl",     fontSize=9,  fontName="Helvetica-Bold",
                         textColor=COLOR_VERDE, leading=13)
    es_abonado_v   = _e("abv",     fontSize=9,  fontName="Helvetica-Bold",
                         textColor=COLOR_VERDE, leading=13, alignment=TA_RIGHT)
    es_saldo_l     = _e("sdl",     fontSize=9,  fontName="Helvetica-Bold",
                         textColor=COLOR_ROJO, leading=13)
    es_saldo_v     = _e("sdv",     fontSize=9,  fontName="Helvetica-Bold",
                         textColor=COLOR_ROJO, leading=13, alignment=TA_RIGHT)
    es_badge       = _e("badge",   fontSize=8,  fontName="Helvetica-Bold",
                         textColor=COLOR_NARANJA, alignment=TA_CENTER)
    es_footer      = _e("foot",    fontSize=8,  alignment=TA_CENTER,
                         textColor=COLOR_GRIS_MEDIO, leading=13)

    def P(txt, est=None):
        return Paragraph(str(txt) if txt is not None else "—", est or es_val)

    story = []

    # ── LOGO ──────────────────────────────────────────────────────────────
    logo_path = get_logo_path()
    if os.path.exists(logo_path):
        logo        = Image(logo_path, width=3 * cm, height=2 * cm, kind="proportional")
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 4))

    # ── ENCABEZADO ────────────────────────────────────────────────────────
    story.append(Paragraph("Recibo de Pago", es_titulo))
    story.append(Paragraph("Club Siglo XXI", es_club))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_NEGRO))
    story.append(Spacer(1, 6))

    # Barra de metadatos
    fecha_emision = _fmt_fecha_hora(
        recibo.get("fecha_emision") or datetime.today().strftime("%Y-%m-%d %H:%M"))
    emitido_por   = recibo.get("emitido_por") or "—"
    recibo_id     = recibo.get("id") or "—"

    meta = Table(
        [[P(f"<b>N° Recibo:</b> {recibo_id}", es_meta),
          P(f"<b>Emisión:</b> {fecha_emision}", es_meta),
          P(f"<b>Emitido por:</b> {emitido_por}", es_meta)]],
        colWidths=[ancho_u / 3] * 3
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), COLOR_GRIS_CLARO),
        ("BOX",           (0,0), (-1,-1), 0.5, COLOR_LINEA),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 12))

    # ── DATOS ─────────────────────────────────────────────────────────────
    monto         = float(recibo.get("monto")     or 0)
    descuento     = float(recibo.get("descuento") or 0)
    mora          = float(recibo.get("mora")      or 0)
    monto_pagado  = recibo.get("monto_pagado")

    # FIX: no usar "or 1" — 0 es falsy, lo pisaría
    pc_raw        = recibo.get("pago_completo")
    pago_completo = int(pc_raw) if pc_raw is not None else 1

    total_recibo  = monto - descuento + mora
    es_parcial    = (pago_completo == 0 and monto_pagado is not None)
    abonado_real  = float(monto_pagado) if es_parcial else total_recibo
    saldo_deuda   = total_recibo - abonado_real if es_parcial else 0.0

    tipo_pago     = recibo.get("tipo_pago", "")
    mes_pago      = recibo.get("mes_pago", "")

    # Badge pago parcial
    if es_parcial:
        badge = Table(
            [[P("  ⚠  PAGO PARCIAL  ", es_badge)]],
            colWidths=[ancho_u]
        )
        badge.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), COLOR_NARANJA_BG),
            ("BOX",           (0,0), (-1,-1), 0.8, COLOR_NARANJA),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(badge)
        story.append(Spacer(1, 8))

    # ── TABLA PRINCIPAL ───────────────────────────────────────────────────
    story.append(Paragraph("Detalles del Pago", es_seccion))

    col_w = [ancho_u * 0.30, ancho_u * 0.45, ancho_u * 0.25]

    def fila(lbl, val, imp=""):
        return [P(lbl, es_lbl), P(val), P(imp, es_der)]

    filas_info = [
        fila("Tutor",        recibo.get("tutor_nombre")     or "—"),
        fila("Alumno",       recibo.get("alumno_nombre")    or "—"),
        fila("Categoría",    recibo.get("categoria_nombre") or "—"),
        fila("Tipo de Pago", _label_tipo(tipo_pago)),
    ]
    if tipo_pago == "pago_cuota" and mes_pago:
        filas_info.append(fila("Mes de la Cuota", _label_mes(mes_pago)))

    filas_info.append(fila("Fecha de Pago",
                            _fmt_fecha(recibo.get("fecha_pago"))))
    filas_info.append(fila("Forma de Pago",
                            (recibo.get("forma_pago") or "").capitalize()))

    descripcion = (recibo.get("descripcion") or "").strip()
    if descripcion:
        filas_info.append(fila("Descripción", descripcion.capitalize()))

    filas_montos = [
        fila("Monto base",  _fmt_moneda(monto),
             _fmt_moneda(monto)),
        fila("Descuento",   _fmt_moneda(descuento),
             f"- {_fmt_moneda(descuento)}"),
        fila("Mora",        _fmt_moneda(mora),
             f"+ {_fmt_moneda(mora)}"),
    ]

    header_row = [
        P("Concepto", es_lbl),
        P("Detalle",  es_lbl),
        P("Importe",  _e("imp", parent=es_lbl, alignment=TA_RIGHT)),
    ]

    fila_total = [
        P("Total a pagar:", es_total_l),
        P("",               es_total_l),
        P(_fmt_moneda(total_recibo), es_total_v),
    ]

    n_info    = len(filas_info)
    n_montos  = len(filas_montos)
    idx_total = 1 + n_info + n_montos

    todas_filas = [header_row] + filas_info + filas_montos + [fila_total]

    filas_parc = []
    if es_parcial:
        filas_parc = [
            [P("Monto abonado:",   es_abonado_l),
             P("(pagado en este acto)", es_val),
             P(_fmt_moneda(abonado_real), es_abonado_v)],
            [P("Saldo pendiente:", es_saldo_l),
             P("(deuda restante)", es_val),
             P(_fmt_moneda(saldo_deuda), es_saldo_v)],
        ]
        todas_filas += filas_parc

    # Estilos alternados
    alt_info = [
        ("BACKGROUND", (0, 1 + i), (-1, 1 + i),
         COLOR_FILA_PAR if i % 2 == 0 else COLOR_FILA_IMPAR)
        for i in range(n_info)
    ]
    alt_montos = [
        ("BACKGROUND", (0, 1 + n_info + i), (-1, 1 + n_info + i),
         COLOR_FILA_PAR if i % 2 == 0 else COLOR_FILA_IMPAR)
        for i in range(n_montos)
    ]

    estilos_parc = []
    if es_parcial:
        ia = idx_total + 1
        isaldo = idx_total + 2
        estilos_parc = [
            ("BACKGROUND", (0, ia),     (-1, ia),     COLOR_VERDE_BG),
            ("BACKGROUND", (0, isaldo), (-1, isaldo), COLOR_ROJO_BG),
            ("LINEABOVE",  (0, ia),     (-1, ia),     0.6, COLOR_LINEA),
        ]

    tabla = Table(todas_filas, colWidths=col_w, repeatRows=1)
    tabla.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0),           COLOR_GRIS_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0),           colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),           "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),           9),
        ("LINEBELOW",     (0, 0), (-1, 0),           1, COLOR_NEGRO),
        # Alternado
        *alt_info,
        *alt_montos,
        # Separador antes de montos
        ("LINEABOVE",  (0, 1 + n_info), (-1, 1 + n_info), 0.6, COLOR_LINEA),
        # Total
        ("BACKGROUND", (0, idx_total), (-1, idx_total), COLOR_TOTAL_BG),
        ("FONTNAME",   (0, idx_total), (-1, idx_total), "Helvetica-Bold"),
        ("LINEABOVE",  (0, idx_total), (-1, idx_total), 1.2, COLOR_NEGRO),
        # Parcial
        *estilos_parc,
        # Globales
        ("FONTSIZE",       (0, 1), (-1, -1),  9),
        ("VALIGN",         (0, 0), (-1, -1),  "MIDDLE"),
        ("LEFTPADDING",    (0, 0), (-1, -1),  10),
        ("RIGHTPADDING",   (0, 0), (-1, -1),  10),
        ("TOPPADDING",     (0, 0), (-1, -1),  7),
        ("BOTTOMPADDING",  (0, 0), (-1, -1),  7),
        ("GRID",           (0, 0), (-1, idx_total - 1), 0.3, COLOR_LINEA),
        ("BOX",            (0, 0), (-1, -1),  0.8, COLOR_NEGRO),
        ("ALIGN",          (2, 0), (2, -1),   "RIGHT"),
    ]))

    story.append(KeepTogether(tabla))
    story.append(Spacer(1, 18))

    # ── PIE ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.6, color=COLOR_LINEA))
    story.append(Spacer(1, 8))

    if es_parcial:
        pie_txt = (f"Pago PARCIAL registrado. Abonado: {_fmt_moneda(abonado_real)} — "
                   f"Saldo pendiente: {_fmt_moneda(saldo_deuda)}. Gracias por su compromiso.")
    else:
        pie_txt = "Gracias por su pago. ¡Seguimos creciendo juntos!"

    story.append(Paragraph(pie_txt, es_footer))

    doc.build(story, onFirstPage=_construir_pagina, onLaterPages=_construir_pagina)
    return resultado_ruta


# ── Test local ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/home/claude")

    # Mock get_logo_path para test sin proyecto
    import utils.assets as _a
    _orig = _a.get_logo_path

    recibo_completo = {
        "id": "42",
        "tutor_nombre":     "Pablo Kenny",
        "alumno_nombre":    "Ignacio Andres Aquino",
        "categoria_nombre": "U11",
        "tipo_pago":        "pago_cuota",
        "mes_pago":         "mayo",
        "fecha_pago":       "2026-05-21",
        "fecha_emision":    "2026-05-21 10:30",
        "emitido_por":      "Administración",
        "monto":            100.0,
        "descuento":        5.0,
        "mora":             0.0,
        "forma_pago":       "efectivo",
        "descripcion":      "",
        "pago_completo":    1,
        "monto_pagado":     95.0,
    }
    recibo_parcial = {
        "id": "43",
        "tutor_nombre":     "Pablo Kenny",
        "alumno_nombre":    "Ignacio Andres Aquino",
        "categoria_nombre": "U11",
        "tipo_pago":        "pago_cuota",
        "mes_pago":         "mayo",
        "fecha_pago":       "2026-05-21",
        "fecha_emision":    "2026-05-21 10:30",
        "emitido_por":      "Administración",
        "monto":            100.0,
        "descuento":        0.0,
        "mora":             10.0,
        "forma_pago":       "transferencia",
        "descripcion":      "Cuota con mora por atraso",
        "pago_completo":    0,
        "monto_pagado":     50.0,
    }

    r1 = generar_pdf_recibo(recibo_completo, "/mnt/user-data/outputs/recibo_completo.pdf")
    r2 = generar_pdf_recibo(recibo_parcial,  "/mnt/user-data/outputs/recibo_parcial.pdf")
    print(f"OK:\n  {r1}\n  {r2}")