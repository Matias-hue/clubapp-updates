from datetime import date, datetime

from database.db import get_connection
from models.alumnos_detalle import MESES_ES, _meses_desde


MESES       = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
               "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
TIPOS_PAGO  = ["pago_cuota", "otros_pagos"]
FORMAS_PAGO = ["efectivo", "transferencia", "mercado pago"]

MONTO_MAX       = 999_999.99
DESCRIPCION_MAX = 300
EMISOR_MAX      = 100


_BASE = """
    SELECT r.*,
           t.nombre  || ' ' || t.apellido AS tutor_nombre,
           t.telefono                     AS tutor_telefono,
           a.nombre_apellido              AS alumno_nombre,
           a.email                        AS email,
           c.nombre                       AS categoria_nombre
    FROM recibos r
    LEFT JOIN tutores    t ON r.tutor_id  = t.id
    LEFT JOIN alumnos    a ON r.alumno_id = a.id
    LEFT JOIN categorias c ON a.categoria_id = c.id
"""


def _siguiente_id(cur):
    cur.execute("SELECT MAX(CAST(id AS INTEGER)) FROM recibos")
    row    = cur.fetchone()
    maximo = row[0] if row and row[0] is not None else 0
    return str(maximo + 1)


# ══════════════════════════════════════════════
# VALIDACIONES PRIVADAS
# ══════════════════════════════════════════════
def _validar_monto(monto, nombre_campo="Monto"):
    error = None
    try:
        valor = float(monto)
        if valor < 0:
            error = f"{nombre_campo} no puede ser negativo."
        elif valor > MONTO_MAX:
            error = f"{nombre_campo} no puede superar ${MONTO_MAX:,.2f}."
    except (TypeError, ValueError):
        error = f"{nombre_campo} debe ser un número válido."
    return error


def _validar_fecha(fecha_str):
    error = None
    if not fecha_str:
        error = "La fecha de pago es obligatoria."
    else:
        try:
            datetime.strptime(str(fecha_str)[:10], "%Y-%m-%d")
        except ValueError:
            error = "La fecha de pago no tiene un formato válido."
    return error


def _validar_tipo_pago(tipo_pago):
    error = None
    if tipo_pago not in TIPOS_PAGO:
        error = f"Tipo de pago inválido. Debe ser uno de: {', '.join(TIPOS_PAGO)}."
    return error


def _validar_forma_pago(forma_pago):
    error = None
    if forma_pago not in FORMAS_PAGO:
        error = f"Forma de pago inválida. Debe ser una de: {', '.join(FORMAS_PAGO)}."
    return error


def _validar_mes_pago(mes_pago, tipo_pago):
    error = None
    if tipo_pago == "pago_cuota":
        if not mes_pago or not mes_pago.strip():
            error = "El mes de pago es obligatorio para pagos de cuota."
        elif mes_pago.strip().lower() not in MESES:
            error = f"Mes de pago inválido: '{mes_pago}'."
    return error


def _validar_monto_pagado(monto_pagado, monto, pago_completo):
    error = None
    if pago_completo == 0:
        if monto_pagado is None:
            error = "Debés ingresar el monto abonado para un pago parcial."
        else:
            err_mp = _validar_monto(monto_pagado, "Monto abonado")
            if err_mp is not None:
                error = err_mp
            elif float(monto_pagado) > float(monto):
                error = "El monto abonado no puede ser mayor al monto total."
            elif float(monto_pagado) <= 0:
                error = "El monto abonado debe ser mayor a 0."
    return error


def _validar_descripcion(descripcion):
    error = None
    if descripcion and len(str(descripcion)) > DESCRIPCION_MAX:
        error = f"La descripción no puede superar los {DESCRIPCION_MAX} caracteres."
    return error


def _validar_emisor(emitido_por):
    error = None
    if emitido_por and len(str(emitido_por)) > EMISOR_MAX:
        error = f"El campo 'Emitido por' no puede superar los {EMISOR_MAX} caracteres."
    return error


def _validar_recibo(tutor_id, alumno_id, fecha_pago, monto, descripcion,
                    forma_pago, descuento, mora, tipo_pago, mes_pago,
                    pago_completo, emitido_por, monto_pagado):
    error = None
    if error is None and not tutor_id:
        error = "El tutor es obligatorio."
    if error is None and not alumno_id:
        error = "El alumno es obligatorio."
    if error is None:
        error = _validar_fecha(fecha_pago)
    if error is None:
        error = _validar_monto(monto, "Monto")
    if error is None:
        error = _validar_monto(descuento or 0, "Descuento")
    if error is None:
        error = _validar_monto(mora or 0, "Mora")
    if error is None:
        error = _validar_tipo_pago(tipo_pago)
    if error is None:
        error = _validar_forma_pago(forma_pago)
    if error is None:
        error = _validar_mes_pago(mes_pago, tipo_pago)
    if error is None:
        error = _validar_monto_pagado(monto_pagado, monto, pago_completo)
    if error is None:
        error = _validar_descripcion(descripcion)
    if error is None:
        error = _validar_emisor(emitido_por)
    return error


# ══════════════════════════════════════════════
# VALOR DE CUOTA DE UN ALUMNO
# ══════════════════════════════════════════════
def obtener_valor_cuota_alumno(alumno_id):
    conn      = get_connection()
    resultado = 0.0
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.valor_cuota
            FROM alumnos a
            LEFT JOIN categorias c ON a.categoria_id = c.id
            WHERE a.id = ?
        """, (str(alumno_id),))
        row = cur.fetchone()
        if row and row[0] is not None:
            resultado = float(row[0])
    finally:
        conn.close()
    return resultado


# ══════════════════════════════════════════════
# CREAR UN RECIBO
# ══════════════════════════════════════════════
def crear_recibo(tutor_id, alumno_id, fecha_pago, monto, descripcion,
                 forma_pago, descuento, mora, tipo_pago, mes_pago,
                 pago_completo, emitido_por, monto_pagado=None):
    # FIX BUG 4: monto_pagado para pagos COMPLETOS debe incluir mora y descuento,
    # ya que representa lo que realmente se cobró. Para parciales se usa el valor
    # explícito ingresado por el usuario (que es lo que abonó, sin ajustar).
    if pago_completo == 1:
        monto_abonado = float(monto) - float(descuento or 0) + float(mora or 0)
    else:
        monto_abonado = float(monto_pagado) if monto_pagado is not None else float(monto)

    error = _validar_recibo(
        tutor_id, alumno_id, fecha_pago, monto, descripcion,
        forma_pago, descuento, mora, tipo_pago, mes_pago,
        pago_completo, emitido_por, monto_pagado
    )
    if error is not None:
        raise ValueError(error)

    conn     = get_connection()
    nuevo_id = None
    try:
        cur      = conn.cursor()
        nuevo_id = _siguiente_id(cur)
        cur.execute("""
            INSERT INTO recibos
                (id, tutor_id, alumno_id, fecha_pago, monto, descripcion,
                 forma_pago, descuento, mora, tipo_pago, mes_pago, pago_completo,
                 fecha_emision, emitido_por, monto_pagado,
                 created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?, DATE('now'),?,?,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (nuevo_id, str(tutor_id), str(alumno_id), fecha_pago,
              monto, descripcion or "", forma_pago,
              descuento or 0, mora or 0, tipo_pago,
              mes_pago or "", pago_completo,
              emitido_por or "", monto_abonado))
        conn.commit()
        cur.execute("SELECT pago_completo, monto_pagado FROM recibos WHERE id = ?", (nuevo_id,))
        fila_guardada = cur.fetchone()
    finally:
        conn.close()
    return nuevo_id


# ══════════════════════════════════════════════
# CREAR RECIBOS PARA MÚLTIPLES MESES
# ══════════════════════════════════════════════
def crear_recibos_meses(tutor_id, alumno_id, fecha_pago, monto, descripcion,
                         forma_pago, descuento, mora, tipo_pago, meses,
                         pago_completo, emitido_por, monto_pagado=None):
    if not meses:
        raise ValueError("Debés seleccionar al menos un mes.")

    nuevos_ids = []
    for mes in meses:
        nuevo_id = crear_recibo(
            tutor_id      = tutor_id,
            alumno_id     = alumno_id,
            fecha_pago    = fecha_pago,
            monto         = monto,
            descripcion   = descripcion,
            forma_pago    = forma_pago,
            descuento     = descuento,
            mora          = mora,
            tipo_pago     = tipo_pago,
            mes_pago      = mes,
            pago_completo = pago_completo,
            emitido_por   = emitido_por,
            monto_pagado  = monto_pagado,
        )
        nuevos_ids.append(nuevo_id)
    return nuevos_ids


# ══════════════════════════════════════════════
# OBTENER TODOS
# ══════════════════════════════════════════════
def obtener_recibos(filtro="", mes=None, forma_pago=None):
    conn        = get_connection()
    where_parts = []
    params      = []
    resultado   = []

    if filtro:
        where_parts.append("""
            (a.nombre_apellido LIKE ?
             OR t.nombre  LIKE ? OR t.apellido LIKE ?
             OR r.tipo_pago LIKE ?)
        """)
        params += [f"%{filtro}%"] * 4

    if mes:
        where_parts.append("LOWER(r.mes_pago) = LOWER(?)")
        params.append(mes)

    if forma_pago:
        where_parts.append("LOWER(r.forma_pago) = LOWER(?)")
        params.append(forma_pago)

    sql = _BASE
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += " ORDER BY CAST(r.id AS INTEGER) DESC"

    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        resultado = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return resultado


# ══════════════════════════════════════════════
# OBTENER UNO
# ══════════════════════════════════════════════
def obtener_recibo(recibo_id):
    conn      = get_connection()
    resultado = None
    try:
        cur = conn.cursor()
        cur.execute(_BASE + " WHERE r.id = ?", (str(recibo_id),))
        row = cur.fetchone()
        if row:
            resultado = dict(row)
    finally:
        conn.close()
    return resultado


# ══════════════════════════════════════════════
# ELIMINAR
# ══════════════════════════════════════════════
def eliminar_recibo(recibo_id):
    conn      = get_connection()
    resultado = False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM recibos WHERE id = ?", (str(recibo_id),))
        conn.commit()
        resultado = cur.rowcount > 0
    finally:
        conn.close()
    return resultado


# ══════════════════════════════════════════════
# DEUDORES DE UN MES
# FIX BUGS 1 y 2: el EXISTS ahora exige pago_completo = 1.
# Un alumno con pago parcial sigue figurando como deudor.
# ══════════════════════════════════════════════
def obtener_deudores(mes):
    conn      = get_connection()
    resultado = []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id                          AS alumno_id,
                a.nombre_apellido             AS alumno_nombre,
                a.created_at                  AS created_at,
                t.nombre || ' ' || t.apellido AS tutor_nombre,
                c.nombre                      AS categoria_nombre,
                (SELECT MAX(r2.fecha_pago)
                 FROM recibos r2
                 WHERE r2.alumno_id = CAST(a.id AS TEXT)
                   AND r2.tipo_pago = 'pago_cuota') AS ultimo_pago
            FROM alumnos a
            LEFT JOIN tutores    t ON a.tutor_id    = t.id
            LEFT JOIN categorias c ON a.categoria_id = c.id
            WHERE a.activo = 1
              AND NOT EXISTS (
                  SELECT 1 FROM recibos r
                  WHERE r.alumno_id    = CAST(a.id AS TEXT)
                    AND r.tipo_pago    = 'pago_cuota'
                    AND LOWER(r.mes_pago) = LOWER(?)
                    AND r.pago_completo   = 1
              )
            ORDER BY a.nombre_apellido
        """, (mes,))
        filas = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    meses_lista = list(MESES_ES.values())

    for fila in filas:
        txt           = str(fila.get("created_at") or "")[:10]
        fecha_ingreso = datetime.strptime(txt, "%Y-%m-%d").date() if txt else date.today()
        mes_ingreso   = MESES_ES.get(fecha_ingreso.month)
        idx_ingreso    = meses_lista.index(mes_ingreso) if mes_ingreso in meses_lista else 0
        idx_consultado = meses_lista.index(mes)         if mes in meses_lista         else 0
        if idx_consultado >= idx_ingreso:
            resultado.append(fila)

    return resultado


# ══════════════════════════════════════════════
# ESTADO DE ALUMNOS
# FIX BUGS 1 y 2: el EXISTS ahora exige pago_completo = 1.
# Un pago parcial no cuenta como "Al día".
# ══════════════════════════════════════════════
def obtener_estado_alumnos(mes=None, filtro=""):
    if mes is None:
        mes = MESES[date.today().month - 1]

    conn      = get_connection()
    resultado = []

    sql = """
        SELECT
            a.id                          AS alumno_id,
            a.nombre_apellido             AS alumno_nombre,
            t.nombre || ' ' || t.apellido AS tutor_nombre,
            c.nombre                      AS categoria_nombre,
            (SELECT MAX(r2.fecha_pago)
             FROM recibos r2
             WHERE r2.alumno_id = CAST(a.id AS TEXT)
               AND r2.tipo_pago = 'pago_cuota') AS ultimo_pago,
            EXISTS (
                SELECT 1 FROM recibos r
                WHERE r.alumno_id      = CAST(a.id AS TEXT)
                  AND r.tipo_pago      = 'pago_cuota'
                  AND LOWER(r.mes_pago) = LOWER(?)
                  AND r.pago_completo   = 1
            ) AS pagado_mes
        FROM alumnos a
        LEFT JOIN tutores    t ON a.tutor_id    = t.id
        LEFT JOIN categorias c ON a.categoria_id = c.id
        WHERE a.activo = 1
    """
    params = [mes]
    if filtro:
        sql   += " AND (a.nombre_apellido LIKE ? OR t.nombre LIKE ? OR t.apellido LIKE ?)"
        params += [f"%{filtro}%"] * 3
    sql += " ORDER BY a.nombre_apellido"

    try:
        cur  = conn.cursor()
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        hoy  = date.today()
        for r in rows:
            r["estado"] = "Al día" if r["pagado_mes"] else "En deuda"
            ult         = r.get("ultimo_pago")
            if ult:
                try:
                    r["alerta"] = (hoy - date.fromisoformat(ult)).days > 35
                except Exception:
                    r["alerta"] = False
            else:
                r["alerta"] = True
        resultado = rows
    finally:
        conn.close()
    return resultado


# ══════════════════════════════════════════════
# PAGOS MENSUALES
# ══════════════════════════════════════════════
def obtener_pagos_mensuales(mes=None, anio=None, filtro="", por_fecha_emision=True):
    resultado = []
    conn = get_connection()
    try:
        query = """
            SELECT
                r.id,
                r.fecha_emision,
                r.fecha_pago,
                r.mes_pago,
                r.monto,
                r.descuento,
                r.mora,
                r.monto_pagado,
                r.pago_completo,
                r.forma_pago,
                r.descripcion,
                r.emitido_por,
                a.nombre_apellido as alumno_nombre,
                t.nombre || ' ' || t.apellido as tutor_nombre,
                COALESCE(c.nombre, 'Sin categoría') as categoria_nombre
            FROM recibos r
            JOIN alumnos a ON r.alumno_id = a.id
            JOIN tutores t ON r.tutor_id = t.id
            LEFT JOIN categorias c ON a.categoria_id = c.id
            WHERE 1=1
        """
        params = []

        mes_limpio = None
        if mes and str(mes).lower() != "todos":
            mes_str    = str(mes).strip().lower()
            meses_map  = {
                "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
                "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
                "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
            }
            mes_limpio = meses_map.get(mes_str, mes_str)

        if por_fecha_emision:
            if mes_limpio:
                query += " AND strftime('%m', r.fecha_emision) = ?"
                params.append(mes_limpio)
            if anio and str(anio) != "Todos":
                query += " AND strftime('%Y', r.fecha_emision) = ?"
                params.append(str(anio))
        else:
            if mes and str(mes).lower() != "todos":
                query += " AND LOWER(r.mes_pago) = LOWER(?)"
                params.append(str(mes))
            if anio and str(anio) != "Todos":
                query += " AND strftime('%Y', r.fecha_emision) = ?"
                params.append(str(anio))

        if filtro and str(filtro).strip():
            f = f"%{str(filtro).strip()}%"
            query += """ AND (
                a.nombre_apellido LIKE ?
                OR (t.nombre || ' ' || t.apellido) LIKE ?
                OR c.nombre LIKE ?
                OR r.descripcion LIKE ?
            )"""
            params.extend([f, f, f, f])

        query += " ORDER BY r.fecha_emision DESC, r.id DESC"

        rows      = conn.execute(query, params).fetchall()
        resultado = [dict(row) for row in rows]

    except Exception as e:
        print(f"Error en obtener_pagos_mensuales: {e}")
        resultado = []
    finally:
        conn.close()
    return resultado