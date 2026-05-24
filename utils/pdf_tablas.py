"""
Genera PDFs de las vistas de tabla:
  - Deudores por mes
  - Alumnos al día / en deuda
  - Pagos mensuales

Usa reportlab en landscape A4, mismo estilo visual que pdf_recibo.py.
"""
import os
import tempfile
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)

from utils.fecha import fmt_fecha
from utils.ui_helpers import dialogo_guardar_o_abrir, fmt_monto


# ── Paleta compartida ────────────────────────────────────────────────────
COLOR_HEADER   = colors.HexColor("#2c3e50")
COLOR_TH_BG    = colors.HexColor("#dde3ea")
COLOR_FILA_PAR = colors.HexColor("#f7f9fb")
COLOR_LINEA    = colors.HexColor("#cccccc")
COLOR_VERDE    = colors.HexColor("#27ae60")
COLOR_ROJO     = colors.HexColor("#e74c3c")
COLOR_TOTAL_BG = colors.HexColor("#d5f5e3")


# ── Helpers internos ─────────────────────────────────────────────────────
def _estilos():
    styles    = getSampleStyleSheet()
    titulo    = ParagraphStyle(
        "titulo_tabla", parent=styles["Normal"],
        fontSize=16, fontName="Helvetica-Bold",
        textColor=COLOR_HEADER, alignment=TA_CENTER, spaceAfter=4
    )
    subtitulo = ParagraphStyle(
        "subtitulo_tabla", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER, spaceAfter=2
    )
    celda     = ParagraphStyle(
        "celda_tabla", parent=styles["Normal"],
        fontSize=8, leading=11
    )
    celda_bold = ParagraphStyle(
        "celda_bold_tabla", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold", leading=11
    )
    celda_der  = ParagraphStyle(
        "celda_der_tabla", parent=styles["Normal"],
        fontSize=8, leading=11, alignment=TA_RIGHT
    )
    total_label = ParagraphStyle(
        "total_label_tabla", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", leading=12
    )
    total_valor = ParagraphStyle(
        "total_valor_tabla", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
        leading=12, alignment=TA_RIGHT
    )
    return {
        "titulo": titulo, "subtitulo": subtitulo,
        "celda": celda, "celda_bold": celda_bold,
        "celda_der": celda_der,
        "total_label": total_label, "total_valor": total_valor,
    }


def _P(texto, estilo):
    return Paragraph(str(texto) if texto else "—", estilo)


def _construir_borde(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(COLOR_HEADER)
    canvas_obj.setLineWidth(1.2)
    margen      = 1.0 * cm
    ancho, alto = landscape(A4)
    canvas_obj.rect(margen, margen, ancho - 2 * margen, alto - 2 * margen)
    canvas_obj.restoreState()


def _estilo_tabla_base(n_filas_datos, idx_total=None):
    """Devuelve el TableStyle base con colores alternados."""
    estilos = [
        ("BACKGROUND",    (0, 0),  (-1, 0),  COLOR_TH_BG),
        ("FONTNAME",      (0, 0),  (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0),  (-1, 0),  8),
        ("LINEBELOW",     (0, 0),  (-1, 0),  1,   COLOR_HEADER),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 7),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("GRID",          (0, 0),  (-1, -1 if idx_total is None else idx_total - 1),
                          0.4, COLOR_LINEA),
        ("BOX",           (0, 0),  (-1, -1), 0.8, COLOR_HEADER),
    ]
    for i in range(n_filas_datos):
        fila_idx = i + 1
        bg       = COLOR_FILA_PAR if i % 2 == 0 else colors.white
        estilos.append(("BACKGROUND", (0, fila_idx), (-1, fila_idx), bg))

    if idx_total is not None:
        estilos += [
            ("BACKGROUND", (0, idx_total), (-1, idx_total), COLOR_TOTAL_BG),
            ("FONTNAME",   (0, idx_total), (-1, idx_total), "Helvetica-Bold"),
            ("LINEABOVE",  (0, idx_total), (-1, idx_total), 1.2, COLOR_HEADER),
        ]
    return TableStyle(estilos)


def _doc_landscape(ruta, titulo_str, subtitulo_str):
    """Crea el SimpleDocTemplate y el encabezado de story."""
    doc   = SimpleDocTemplate(
        ruta,
        pagesize=landscape(A4),
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm,  bottomMargin=1.8 * cm,
    )
    est   = _estilos()
    story = [
        Paragraph(titulo_str,    est["titulo"]),
        Paragraph(subtitulo_str, est["subtitulo"]),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=0.6, color=COLOR_LINEA),
        Spacer(1, 8),
    ]
    return doc, story, est


def _ruta_tmp(nombre):
    return os.path.join(tempfile.gettempdir(), nombre)


# ════════════════════════════════════════════════════════════════════════
# 1. DEUDORES POR MES
# ════════════════════════════════════════════════════════════════════════
def exportar_pdf_deudores(rows, mes_sel):
    """
    rows: lista de dicts con alumno_nombre, tutor_nombre,
          categoria_nombre, ultimo_pago
    mes_sel: string del mes (ej: "mayo")
    """
    ruta  = _ruta_tmp(f"deudores_{mes_sel}.pdf")
    fecha = datetime.today().strftime("%d/%m/%Y %H:%M")

    doc, story, est = _doc_landscape(
        ruta,
        f"Deudores — {mes_sel.capitalize()}",
        f"Generado el {fecha}  |  Total deudores: {len(rows)}"
    )

    headers = ["Alumno", "Tutor", "Categoría", "Último Pago de Cuota"]
    ancho   = landscape(A4)[0] - 3.6 * cm
    col_w   = [ancho * 0.32, ancho * 0.25, ancho * 0.20, ancho * 0.23]

    filas = [[_P(h, est["celda_bold"]) for h in headers]]
    for r in rows:
        filas.append([
            _P(r.get("alumno_nombre")    or "—", est["celda"]),
            _P(r.get("tutor_nombre")     or "—", est["celda"]),
            _P(r.get("categoria_nombre") or "—", est["celda"]),
            _P(fmt_fecha(r.get("ultimo_pago")) or "Sin pagos registrados", est["celda"]),
        ])

    tabla = Table(filas, colWidths=col_w, repeatRows=1)
    tabla.setStyle(_estilo_tabla_base(len(rows)))
    story.append(tabla)

    doc.build(story, onFirstPage=_construir_borde, onLaterPages=_construir_borde)
    dialogo_guardar_o_abrir(ruta, f"deudores_{mes_sel}.pdf")


# ════════════════════════════════════════════════════════════════════════
# 2. ALUMNOS AL DÍA / EN DEUDA
# ════════════════════════════════════════════════════════════════════════
def exportar_pdf_alumnos_al_dia(rows, mes_sel, estado_sel):
    """
    rows: lista de dicts enriquecidos con estado, alerta, ultimo_pago
    mes_sel: string del mes
    estado_sel: "Todos" | "Al día" | "En deuda"
    """
    ruta  = _ruta_tmp(f"alumnos_estado_{mes_sel}.pdf")
    fecha = datetime.today().strftime("%d/%m/%Y %H:%M")

    al_dia   = sum(1 for r in rows if r.get("estado") == "Al día")
    en_deuda = sum(1 for r in rows if r.get("estado") == "En deuda")

    doc, story, est = _doc_landscape(
        ruta,
        f"Estado de Alumnos — {mes_sel.capitalize()}",
        f"Generado el {fecha}  |  Al día: {al_dia}   En deuda: {en_deuda}   Total: {len(rows)}"
    )

    headers = ["Alumno", "Tutor", "Categoría", "Estado", "Último Pago", "Alerta"]
    ancho   = landscape(A4)[0] - 3.6 * cm
    col_w   = [
        ancho * 0.28, ancho * 0.20, ancho * 0.17,
        ancho * 0.12, ancho * 0.13, ancho * 0.10
    ]

    filas = [[_P(h, est["celda_bold"]) for h in headers]]
    for r in rows:
        alerta_txt = "Sin pago reciente" if r.get("alerta") else "OK"
        filas.append([
            _P(r.get("alumno_nombre")    or "—", est["celda"]),
            _P(r.get("tutor_nombre")     or "—", est["celda"]),
            _P(r.get("categoria_nombre") or "—", est["celda"]),
            _P(r.get("estado")           or "—", est["celda_bold"]),
            _P(fmt_fecha(r.get("ultimo_pago")) or "Sin pagos", est["celda"]),
            _P(alerta_txt,                       est["celda"]),
        ])

    n_datos     = len(rows)
    tabla       = Table(filas, colWidths=col_w, repeatRows=1)
    estilo_base = _estilo_tabla_base(n_datos)

    for i, r in enumerate(rows):
        fila_idx = i + 1
        color    = COLOR_VERDE if r.get("estado") == "Al día" else COLOR_ROJO
        estilo_base.add("TEXTCOLOR", (3, fila_idx), (3, fila_idx), color)

    tabla.setStyle(estilo_base)
    story.append(tabla)

    doc.build(story, onFirstPage=_construir_borde, onLaterPages=_construir_borde)
    dialogo_guardar_o_abrir(ruta, f"alumnos_estado_{mes_sel}.pdf")


# ════════════════════════════════════════════════════════════════════════
# 3. PAGOS MENSUALES
# ════════════════════════════════════════════════════════════════════════
def exportar_pdf_pagos_mensuales(rows, mes_val, anio_val, criterio_txt):
    """
    rows: lista de dicts de obtener_pagos_mensuales
    mes_val, anio_val: strings de los filtros aplicados
    criterio_txt: "Fecha de Emisión (Caja Real)" | "Mes de la Cuota (Devengado)"
    """
    ruta        = _ruta_tmp("pagos_mensuales.pdf")
    fecha       = datetime.today().strftime("%d/%m/%Y %H:%M")
    grand_total = sum(float(r.get("monto") or 0) for r in rows)
    filtro_txt  = f"Mes: {mes_val}   Año: {anio_val}   Criterio: {criterio_txt}"

    doc, story, est = _doc_landscape(
        ruta,
        "Pagos Mensuales",
        f"Generado el {fecha}  |  {filtro_txt}  |  Registros: {len(rows)}"
    )

    headers = ["Tutor", "Alumno", "Categoría", "Mes Cuota",
               "Fecha Emisión", "Monto", "Forma de Pago", "Descripción"]
    ancho   = landscape(A4)[0] - 3.6 * cm
    col_w   = [
        ancho * 0.16, ancho * 0.18, ancho * 0.12, ancho * 0.09,
        ancho * 0.11, ancho * 0.09, ancho * 0.11, ancho * 0.14
    ]

    filas = [[_P(h, est["celda_bold"]) for h in headers]]
    for r in rows:
        monto = float(r.get("monto") or 0)
        filas.append([
            _P(r.get("tutor_nombre")     or "—",          est["celda"]),
            _P(r.get("alumno_nombre")    or "—",          est["celda"]),
            _P(r.get("categoria_nombre") or "—",          est["celda"]),
            _P((r.get("mes_pago") or "—").capitalize(),   est["celda"]),
            _P(fmt_fecha(r.get("fecha_emision")) or "—",  est["celda"]),
            _P(fmt_monto(monto),                          est["celda_der"]),
            _P((r.get("forma_pago") or "—").capitalize(), est["celda"]),
            _P(r.get("descripcion") or "—",               est["celda"]),
        ])

    idx_total = len(rows) + 1
    filas.append([
        _P("", est["total_label"]),
        _P("", est["total_label"]),
        _P("", est["total_label"]),
        _P("", est["total_label"]),
        _P("TOTAL", est["total_label"]),
        _P(fmt_monto(grand_total), est["total_valor"]),
        _P("", est["total_label"]),
        _P("", est["total_label"]),
    ])

    tabla = Table(filas, colWidths=col_w, repeatRows=1)
    tabla.setStyle(_estilo_tabla_base(len(rows), idx_total=idx_total))
    tabla.setStyle(TableStyle([
        ("ALIGN", (5, 0), (5, -1), "RIGHT"),
    ]))
    story.append(tabla)

    doc.build(story, onFirstPage=_construir_borde, onLaterPages=_construir_borde)
    dialogo_guardar_o_abrir(ruta, "pagos_mensuales.pdf")