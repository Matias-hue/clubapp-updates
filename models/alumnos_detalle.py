# models/alumnos_detalle.py
"""
Queries adicionales para la vista detallada de alumnos:
  - estado de deuda
  - último pago
  - historial de pagos
  - resumen anual
  - calculadora de deuda
"""
from datetime import date, datetime

from database.db import get_connection


MESES_ES = {
    3:  "marzo",
    4:  "abril",
    5:  "mayo",
    6:  "junio",
    7:  "julio",
    8:  "agosto",
    9:  "septiembre",
    10: "octubre",
    11: "noviembre",
}


def _meses_desde(fecha_inicio: date, fecha_fin: date) -> list:
    """
    Devuelve lista de meses del club (marzo-noviembre)
    entre fecha_inicio y fecha_fin.
    """
    meses = []
    anio  = fecha_inicio.year
    mes   = fecha_inicio.month

    while (anio, mes) <= (fecha_fin.year, fecha_fin.month):
        if mes in MESES_ES:
            meses.append(MESES_ES[mes])
        mes += 1
        if mes > 12:
            mes  = 1
            anio += 1

    return meses


def _fecha_ingreso(alumno_id) -> date:
    """Devuelve la fecha de ingreso del alumno (created_at)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT created_at FROM alumnos WHERE id = ?", (str(alumno_id),))
        row = cur.fetchone()
        if not row or not row[0]:
            return date.today().replace(day=1)
        txt = str(row[0])[:10]
        return datetime.strptime(txt, "%Y-%m-%d").date().replace(day=1)
    finally:
        conn.close()


def _meses_pagados(alumno_id) -> set:
    """Devuelve meses con pago COMPLETO."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT LOWER(mes_pago) FROM recibos
            WHERE CAST(alumno_id AS TEXT) = CAST(? AS TEXT)
              AND tipo_pago     = 'pago_cuota'
              AND pago_completo = 1
              AND mes_pago IS NOT NULL AND mes_pago != ''
        """, (str(alumno_id),))
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


def _meses_parciales(alumno_id) -> set:
    """Devuelve meses con pago PARCIAL (sin pago completo en el mismo mes)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT LOWER(mes_pago) FROM recibos
            WHERE CAST(alumno_id AS TEXT) = CAST(? AS TEXT)
              AND tipo_pago     = 'pago_cuota'
              AND pago_completo = 0
              AND mes_pago IS NOT NULL AND mes_pago != ''
        """, (str(alumno_id),))
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


# ══════════════════════════════════════════════
# ESTADO DEUDA + ÚLTIMO PAGO
# (usado en la tabla principal)
# ══════════════════════════════════════════════
def obtener_resumen_deuda(alumno_id, created_at=None) -> dict:
    if created_at:
        txt    = str(created_at)[:10]
        inicio = datetime.strptime(txt, "%Y-%m-%d").date().replace(day=1)
    else:
        inicio = _fecha_ingreso(alumno_id)

    hoy      = date.today()
    pagados  = _meses_pagados(alumno_id)
    parciales = _meses_parciales(alumno_id)

    todos_hasta_hoy = _meses_desde(inicio, hoy)

    # Adeudado: no tiene pago completo (parcial cuenta como deuda)
    adeudados = [m for m in todos_hasta_hoy if m not in pagados]

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(fecha_pago) FROM recibos
            WHERE CAST(alumno_id AS TEXT) = CAST(? AS TEXT)
              AND tipo_pago = 'pago_cuota'
        """, (str(alumno_id),))
        row = cur.fetchone()
        ultimo_pago = row[0] if row else None
    finally:
        conn.close()

    return {
        "meses_activo":    len(todos_hasta_hoy),
        "meses_pagados":   len(pagados),
        "meses_parciales": len(parciales - pagados),  # parciales sin completar
        "meses_adeudados": adeudados,
        "ultimo_pago":     ultimo_pago,
    }


# ══════════════════════════════════════════════
# HISTORIAL DE PAGOS
# ══════════════════════════════════════════════
def obtener_historial(alumno_id) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.id, r.fecha_pago, r.tipo_pago, r.mes_pago,
                   r.monto, r.descuento, r.mora, r.forma_pago,
                   r.descripcion, r.pago_completo
            FROM recibos r
            WHERE CAST(r.alumno_id AS TEXT) = CAST(? AS TEXT)
            ORDER BY r.fecha_pago ASC, CAST(r.id AS INTEGER) ASC
        """, (str(alumno_id),))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ══════════════════════════════════════════════
# RESUMEN ANUAL
# ══════════════════════════════════════════════
def obtener_resumen_anual(alumno_id, created_at=None) -> list:
    if created_at:
        txt    = str(created_at)[:10]
        inicio = datetime.strptime(txt, "%Y-%m-%d").date().replace(day=1)
    else:
        inicio = _fecha_ingreso(alumno_id)

    pagados   = _meses_pagados(alumno_id)
    parciales = _meses_parciales(alumno_id)
    hoy       = date.today()
    result    = []

    for numero_mes, nombre_mes in MESES_ES.items():
        mes_date = date(hoy.year, numero_mes, 1)

        if nombre_mes in pagados:
            estado = "pagado"
        elif nombre_mes in parciales:
            estado = "parcial"
        elif mes_date < inicio:
            estado = "no_aplica"
        elif mes_date > hoy:
            estado = "futuro"
        else:
            estado = "adeudado"

        result.append({
            "mes":    nombre_mes.capitalize(),
            "estado": estado,
        })

    return result