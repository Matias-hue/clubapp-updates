from database.db import get_connection


# ==============================
# CONSTANTES DE VALIDACIÓN
# ==============================
ANIO_MIN = 1900
ANIO_MAX = 2100
CUOTA_MAX = 9_999_999.99
NOMBRE_MAX = 100


# ==============================
# VALIDACIONES
# ==============================
def _validar_nombre(nombre):
    resultado = None
    if not nombre or not nombre.strip():
        resultado = "El nombre de la categoría es obligatorio."
    elif len(nombre.strip()) > NOMBRE_MAX:
        resultado = f"El nombre no puede superar los {NOMBRE_MAX} caracteres."
    return resultado


def _validar_anios(anio_inicio, anio_fin):
    resultado = None
    if anio_inicio is not None:
        if not isinstance(anio_inicio, int):
            resultado = "El año de inicio debe ser un número entero."
        elif anio_inicio < ANIO_MIN or anio_inicio > ANIO_MAX:
            resultado = f"El año de inicio debe estar entre {ANIO_MIN} y {ANIO_MAX}."
    if resultado is None and anio_fin is not None:
        if not isinstance(anio_fin, int):
            resultado = "El año de fin debe ser un número entero."
        elif anio_fin < ANIO_MIN or anio_fin > ANIO_MAX:
            resultado = f"El año de fin debe estar entre {ANIO_MIN} y {ANIO_MAX}."
    if resultado is None and anio_inicio is not None and anio_fin is not None:
        if anio_inicio > anio_fin:
            resultado = "El año de inicio no puede ser mayor al año de fin."
    return resultado


def _validar_cuota(valor_cuota):
    resultado = None
    if valor_cuota is not None:
        if not isinstance(valor_cuota, (int, float)):
            resultado = "El valor de cuota debe ser un número válido."
        elif valor_cuota < 0:
            resultado = "El valor de cuota no puede ser negativo."
        elif valor_cuota > CUOTA_MAX:
            resultado = f"El valor de cuota no puede superar ${CUOTA_MAX:,.2f}."
    return resultado


# ==============================
# CREAR CATEGORÍA
# ==============================
def crear_categoria(nombre, anio_inicio=None, anio_fin=None, valor_cuota=None):
    error = _validar_nombre(nombre)
    if error is None:
        error = _validar_anios(anio_inicio, anio_fin)
    if error is None:
        error = _validar_cuota(valor_cuota)
    if error is not None:
        raise ValueError(error)

    conn = get_connection()
    resultado = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO categorias (nombre, anio_inicio, anio_fin, valor_cuota, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (nombre.strip(), anio_inicio, anio_fin, valor_cuota))
        conn.commit()
        resultado = cursor.lastrowid
    finally:
        conn.close()
    return resultado


# ==============================
# OBTENER CATEGORÍAS
# ==============================
def obtener_categorias(filtro=""):
    conn = get_connection()
    filas = []
    try:
        cursor = conn.cursor()
        if filtro:
            cursor.execute("""
                SELECT id, nombre, anio_inicio, anio_fin, valor_cuota
                FROM categorias
                WHERE nombre LIKE ?
                ORDER BY CAST(SUBSTR(nombre, 2) AS INTEGER)
            """, (f"%{filtro}%",))
        else:
            cursor.execute("""
                SELECT id, nombre, anio_inicio, anio_fin, valor_cuota
                FROM categorias ORDER BY CAST(SUBSTR(nombre, 2) AS INTEGER)
            """)
        filas = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return filas


# ==============================
# ACTUALIZAR CATEGORÍA
# ==============================
def actualizar_categoria(categoria_id, nombre, anio_inicio=None, anio_fin=None, valor_cuota=None):
    error = _validar_nombre(nombre)
    if error is None:
        error = _validar_anios(anio_inicio, anio_fin)
    if error is None:
        error = _validar_cuota(valor_cuota)
    if error is not None:
        raise ValueError(error)

    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE categorias
            SET nombre = ?,
                anio_inicio = ?,
                anio_fin = ?,
                valor_cuota = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (nombre.strip(), anio_inicio, anio_fin, valor_cuota, categoria_id))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado


# ==============================
# ELIMINAR CATEGORÍA
# ==============================
def eliminar_categoria(categoria_id):
    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM alumnos WHERE categoria_id = ?", (categoria_id,)
        )
        cantidad = cursor.fetchone()[0]
        if cantidad > 0:
            raise ValueError(
                f"No se puede eliminar: hay {cantidad} "
                f"alumno{'s' if cantidad > 1 else ''} en esta categoría. "
                "Reasigná los alumnos antes de eliminar."
            )
        cursor.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado


def ajustar_anios_categorias(delta):
    """
    Suma o resta `delta` (1 o -1) a anio_inicio y anio_fin
    de todas las categorías.
    """
    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE categorias
            SET anio_inicio = anio_inicio + ?,
                anio_fin    = anio_fin    + ?,
                updated_at  = CURRENT_TIMESTAMP
        """, (delta, delta))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado