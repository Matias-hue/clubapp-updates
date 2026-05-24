from database.db import get_connection
from models.recibos import (
    crear_recibos_meses, obtener_valor_cuota_alumno,
    MESES, MONTO_MAX, DESCRIPCION_MAX
)
from utils.fecha import arg_a_iso

# ══════════════════════════════════════════════
# CONVERSIÓN PORCENTAJE → MONTO
# ══════════════════════════════════════════════
def resolver_monto_o_porcentaje(valor_str, modo, monto_base):
    """
    modo: "$" → valor directo | "%" → calcula porcentaje sobre monto_base
    Devuelve float o None si hay error.
    """
    resultado = None
    try:
        valor = float(valor_str.strip() or "0")
        if modo == "%":
            if not (0 <= valor <= 100):
                resultado = None  # fuera de rango, se valida aparte
            else:
                resultado = round(monto_base * valor / 100, 2)
        else:
            resultado = valor
    except (ValueError, AttributeError):
        resultado = None
    return resultado


# ══════════════════════════════════════════════
# ENRIQUECER ALUMNOS CON TUTOR Y CATEGORÍA
# ══════════════════════════════════════════════
def enriquecer_alumnos(alumnos):
    conn = get_connection()
    try:
        for alumno in alumnos:
            row_t = conn.execute(
                "SELECT nombre || ' ' || apellido FROM tutores WHERE id = ?",
                (alumno.get("tutor_id"),)
            ).fetchone()
            row_c = conn.execute(
                "SELECT nombre FROM categorias WHERE id = ?",
                (alumno.get("categoria_id"),)
            ).fetchone()
            alumno["tutor_nombre"]     = row_t[0] if row_t else "—"
            alumno["categoria_nombre"] = row_c[0] if row_c else "—"
    finally:
        conn.close()
    return alumnos


# ══════════════════════════════════════════════
# VALIDACIONES PRIVADAS DE SERVICIO
# ══════════════════════════════════════════════
def _validar_monto_str(valor_str, nombre_campo="Monto"):
    error = None
    if not valor_str or not valor_str.strip():
        error = f"{nombre_campo} es obligatorio."
    else:
        try:
            valor = float(valor_str.strip())
            if valor < 0:
                error = f"{nombre_campo} no puede ser negativo."
            elif valor > MONTO_MAX:
                error = f"{nombre_campo} no puede superar ${MONTO_MAX:,.2f}."
        except ValueError:
            error = f"{nombre_campo} debe ser un número válido."
    return error


def _validar_fecha_str(fecha_str):
    error = None
    if not fecha_str or not fecha_str.strip():
        error = "La fecha de pago es obligatoria."
    else:
        iso = arg_a_iso(fecha_str.strip())
        if not iso:
            error = "La fecha de pago no tiene un formato válido (DD/MM/YYYY)."
    return error


def _validar_monto_pagado_str(mp_str, monto_str):
    error = _validar_monto_str(mp_str, "Monto abonado")
    if error is None:
        try:
            mp    = float(mp_str.strip())
            monto = float(monto_str.strip())
            if mp <= 0:
                error = "El monto abonado debe ser mayor a 0."
            elif mp > monto:
                error = "El monto abonado no puede ser mayor al monto total."
        except ValueError:
            error = "El monto abonado debe ser un número válido."
    return error


# ══════════════════════════════════════════════
# VALIDAR FORMULARIO RECIBO INDIVIDUAL
# ══════════════════════════════════════════════
def validar_recibo_individual(idx_alumno, idx_tutor, monto_str, meses_sel):
    error = None
    if idx_alumno < 0:
        error = "Seleccioná un alumno."
    if error is None and idx_tutor < 0:
        error = "Seleccioná un tutor."
    if error is None:
        error = _validar_monto_str(monto_str, "Monto")
    if error is None and not meses_sel:
        error = "Seleccioná al menos un mes."
    return error


# ══════════════════════════════════════════════
# PARSEAR DATOS DE RECIBO INDIVIDUAL
# ══════════════════════════════════════════════
def parsear_recibo_individual(combo_tipo, combo_forma, entry_fecha,
                               entry_monto, entry_desc, entry_mora,
                               entry_descripcion, entry_emisor,
                               var_parcial, var_monto_pagado,
                               formas_pago,
                               modo_desc="$", modo_mora="$"):   # <-- nuevos
    fecha_str = entry_fecha.get().strip()
    monto_str = entry_monto.get().strip()
    desc_raw  = entry_desc.get().strip() or "0"
    mora_raw  = entry_mora.get().strip() or "0"

    error = _validar_fecha_str(fecha_str)
    if error is None:
        error = _validar_monto_str(monto_str, "Monto")

    # Resolver descuento y mora según modo
    desc_val = None
    mora_val = None
    if error is None:
        monto_base = float(monto_str)
        if modo_desc == "%":
            try:
                pct = float(desc_raw)
                if not (0 <= pct <= 100):
                    error = "El porcentaje de descuento debe estar entre 0 y 100."
                else:
                    desc_val = round(monto_base * pct / 100, 2)
            except ValueError:
                error = "Descuento debe ser un número válido."
        else:
            error = _validar_monto_str(desc_raw, "Descuento")
            if error is None:
                desc_val = float(desc_raw)

    if error is None:
        if modo_mora == "%":
            try:
                pct = float(mora_raw)
                if not (0 <= pct <= 100):
                    error = "El porcentaje de mora debe estar entre 0 y 100."
                else:
                    mora_val = round(monto_base * pct / 100, 2)
            except ValueError:
                error = "Mora debe ser un número válido."
        else:
            error = _validar_monto_str(mora_raw, "Mora")
            if error is None:
                mora_val = float(mora_raw)

    descripcion = entry_descripcion.get().strip()
    if error is None and len(descripcion) > DESCRIPCION_MAX:
        error = f"La descripción no puede superar los {DESCRIPCION_MAX} caracteres."

    if error is not None:
        raise ValueError(error)

    tipo_raw  = "pago_cuota" if combo_tipo.current() == 0 else "otros_pagos"
    forma_raw = formas_pago[combo_forma.current()]

    monto_pagado  = None
    pago_completo = 1
    if var_parcial.get():
        mp_str = var_monto_pagado.get().strip()
        error  = _validar_monto_pagado_str(mp_str, monto_str)
        if error is not None:
            raise ValueError(error)
        monto_pagado  = float(mp_str)
        pago_completo = 0

    resultado = {
        "tipo_pago":     tipo_raw,
        "forma_pago":    forma_raw,
        "fecha_pago":    arg_a_iso(fecha_str),
        "monto":         float(monto_str),
        "descuento":     desc_val,
        "mora":          mora_val,
        "descripcion":   descripcion,
        "emitido_por":   entry_emisor.get().strip(),
        "monto_pagado":  monto_pagado,
        "pago_completo": pago_completo,
    }
    return resultado


# ══════════════════════════════════════════════
# GUARDAR RECIBOS INDIVIDUALES
# ══════════════════════════════════════════════
def guardar_recibo_individual(alumno, tutor, datos, meses_sel):
    nuevos_ids = crear_recibos_meses(
        tutor_id      = tutor["id"],
        alumno_id     = alumno["id"],
        fecha_pago    = datos["fecha_pago"],
        monto         = datos["monto"],
        descripcion   = datos["descripcion"],
        forma_pago    = datos["forma_pago"],
        descuento     = datos["descuento"],
        mora          = datos["mora"],
        tipo_pago     = datos["tipo_pago"],
        meses         = meses_sel,
        pago_completo = datos["pago_completo"],
        emitido_por   = datos["emitido_por"],
        monto_pagado  = datos["monto_pagado"],
    )
    return nuevos_ids


# ══════════════════════════════════════════════
# GUARDAR RECIBOS MÚLTIPLES
# ══════════════════════════════════════════════
def guardar_recibos_multiples(filas_sel, tipo_raw, meses_sel,
                               fecha_val, forma_raw, descripcion,
                               emisor, tutores):
    nuevos_ids = []
    errores    = []

    error_fecha = _validar_fecha_str(fecha_val) if fecha_val else "La fecha es obligatoria."
    if error_fecha is not None:
        errores.append(f"Fecha inválida: {error_fecha}")
        return nuevos_ids, errores

    for fila in filas_sel:
        alumno    = fila["alumno"]
        nombre_al = alumno.get("nombre_apellido", "?")
        error     = None

        monto_str  = fila["e_monto"].get().strip()
        desc_raw   = fila["e_desc"].get().strip() or "0"
        mora_raw   = fila["e_mora"].get().strip() or "0"
        modo_desc  = fila.get("modo_desc", "$")
        modo_mora  = fila.get("modo_mora", "$")

        error = _validar_monto_str(monto_str, "Monto")

        desc_val   = None
        mora_val   = None
        monto_base = 0.0

        if error is None:
            monto_base = float(monto_str)

        if error is None:
            if modo_desc == "%":
                try:
                    pct = float(desc_raw)
                    if not (0 <= pct <= 100):
                        error = "El porcentaje de descuento debe estar entre 0 y 100."
                    else:
                        desc_val = round(monto_base * pct / 100, 2)
                except ValueError:
                    error = "Descuento debe ser un número válido."
            else:
                error = _validar_monto_str(desc_raw, "Descuento")
                if error is None:
                    desc_val = float(desc_raw)

        if error is None:
            if modo_mora == "%":
                try:
                    pct = float(mora_raw)
                    if not (0 <= pct <= 100):
                        error = "El porcentaje de mora debe estar entre 0 y 100."
                    else:
                        mora_val = round(monto_base * pct / 100, 2)
                except ValueError:
                    error = "Mora debe ser un número válido."
            else:
                error = _validar_monto_str(mora_raw, "Mora")
                if error is None:
                    mora_val = float(mora_raw)

        monto_pagado  = None
        pago_completo = 1
        if error is None and fila["var_parc"].get():
            ab_str = fila["var_abonado"].get().strip()
            error  = _validar_monto_pagado_str(ab_str, monto_str)
            if error is None:
                monto_pagado  = float(ab_str)
                pago_completo = 0

        if error is not None:
            errores.append(f"{nombre_al}: {error}")
        else:
            try:
                tutor_id   = alumno.get("tutor_id") or (tutores[0]["id"] if tutores else 1)
                ids_alumno = crear_recibos_meses(
                    tutor_id      = tutor_id,
                    alumno_id     = alumno["id"],
                    fecha_pago    = fecha_val,
                    monto         = monto_base,
                    descripcion   = descripcion,
                    forma_pago    = forma_raw,
                    descuento     = desc_val,
                    mora          = mora_val,
                    tipo_pago     = tipo_raw,
                    meses         = meses_sel,
                    pago_completo = pago_completo,
                    emitido_por   = emisor,
                    monto_pagado  = monto_pagado,
                )
                nuevos_ids.extend(ids_alumno)
            except ValueError as e:
                errores.append(f"{nombre_al}: {e}")

    return nuevos_ids, errores


# ══════════════════════════════════════════════
# AUTOCOMPLETAR ALUMNO
# ══════════════════════════════════════════════
def autocompletar_alumno(idx_alumno, alumnos, tutores):
    tutor_idx = -1
    cuota     = 0.0
    if idx_alumno >= 0:
        alumno = alumnos[idx_alumno]
        cuota  = obtener_valor_cuota_alumno(alumno["id"])
        for j, t in enumerate(tutores):
            if str(t["id"]) == str(alumno.get("tutor_id")):
                tutor_idx = j
                break
    resultado = (tutor_idx, cuota)
    return resultado


# ══════════════════════════════════════════════
# FILTRAR ALUMNOS POR TUTOR
# ══════════════════════════════════════════════
def filtrar_alumnos_por_tutor(alumnos, tutor_id):
    alumnos_activos = [a for a in alumnos if a.get("activo") == 1]
    if tutor_id is None:
        resultado = alumnos_activos
    else:
        resultado = [
            a for a in alumnos_activos
            if str(a.get("tutor_id")) == str(tutor_id)
        ]
    return resultado