from database.db import get_connection


# ==============================
# CONSTANTES DE VALIDACIÓN
# ==============================
NOMBRE_MAX = 100
APELLIDO_MAX = 100
TELEFONO_MAX = 20
DOMICILIO_MAX = 200


# ==============================
# VALIDACIONES PRIVADAS
# ==============================
def _validar_nombre(nombre):
    error = None
    if not nombre or not nombre.strip():
        error = "El nombre es obligatorio."
    elif len(nombre.strip()) > NOMBRE_MAX:
        error = f"El nombre no puede superar los {NOMBRE_MAX} caracteres."
    return error


def _validar_apellido(apellido):
    error = None
    if not apellido or not apellido.strip():
        error = "El apellido es obligatorio."
    elif len(apellido.strip()) > APELLIDO_MAX:
        error = f"El apellido no puede superar los {APELLIDO_MAX} caracteres."
    return error


def _validar_telefono(telefono):
    error = None
    if telefono:
        if len(telefono.strip()) > TELEFONO_MAX:
            error = f"El teléfono no puede superar los {TELEFONO_MAX} caracteres."
        elif not telefono.strip().lstrip("+").replace("-", "").replace(" ", "").isdigit():
            error = "El teléfono solo puede contener números, espacios, guiones y '+'."
    return error


def _validar_domicilio(domicilio):
    error = None
    if domicilio and len(domicilio.strip()) > DOMICILIO_MAX:
        error = f"El domicilio no puede superar los {DOMICILIO_MAX} caracteres."
    return error


def _validar_tutor(nombre, apellido, telefono, domicilio):
    error = _validar_nombre(nombre)
    if error is None:
        error = _validar_apellido(apellido)
    if error is None:
        error = _validar_telefono(telefono)
    if error is None:
        error = _validar_domicilio(domicilio)
    return error


# ==============================
# CREAR TUTOR
# ==============================
def crear_tutor(nombre, apellido, telefono=None, domicilio=None):
    error = _validar_tutor(nombre, apellido, telefono, domicilio)
    if error is not None:
        raise ValueError(error)

    conn = get_connection()
    resultado = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tutores (nombre, apellido, telefono, domicilio, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            nombre.strip(),
            apellido.strip(),
            telefono.strip() if telefono else None,
            domicilio.strip() if domicilio else None,
        ))
        conn.commit()
        resultado = cursor.lastrowid
    finally:
        conn.close()
    return resultado


# ==============================
# OBTENER TUTORES
# ==============================
def obtener_tutores(filtro=""):
    conn = get_connection()
    filas = []
    try:
        cursor = conn.cursor()
        if filtro:
            cursor.execute("""
                SELECT id, nombre, apellido, telefono, domicilio
                FROM tutores
                WHERE nombre LIKE ? OR apellido LIKE ?
                ORDER BY apellido, nombre
            """, (f"%{filtro}%", f"%{filtro}%"))
        else:
            cursor.execute("""
                SELECT id, nombre, apellido, telefono, domicilio
                FROM tutores ORDER BY apellido, nombre
            """)
        filas = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return filas


# ==============================
# ACTUALIZAR TUTOR
# ==============================
def actualizar_tutor(tutor_id, nombre, apellido, telefono=None, domicilio=None):
    error = _validar_tutor(nombre, apellido, telefono, domicilio)
    if error is not None:
        raise ValueError(error)

    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tutores
            SET nombre = ?, apellido = ?, telefono = ?, domicilio = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            nombre.strip(),
            apellido.strip(),
            telefono.strip() if telefono else None,
            domicilio.strip() if domicilio else None,
            tutor_id,
        ))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado


# ==============================
# ELIMINAR TUTOR
# ==============================
def eliminar_tutor(tutor_id):
    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM alumnos WHERE tutor_id = ?", (tutor_id,)
        )
        cantidad = cursor.fetchone()[0]
        if cantidad > 0:
            raise ValueError(
                f"No se puede eliminar: este tutor tiene {cantidad} "
                f"alumno{'s' if cantidad > 1 else ''} asignado{'s' if cantidad > 1 else ''}. "
                "Reasigná los alumnos antes de eliminar."
            )
        cursor.execute("DELETE FROM tutores WHERE id = ?", (tutor_id,))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado