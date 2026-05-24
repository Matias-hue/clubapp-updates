from database.db import get_connection


# ==============================
# CONSTANTES DE VALIDACIÓN
# ==============================
NOMBRE_MAX       = 150
DNI_MAX          = 15
TELEFONO_MAX     = 20
EMAIL_MAX        = 150
CAMISETA_MAX     = 10
FECHA_MIN_ANIO   = 1950


# ==============================
# VALIDACIONES PRIVADAS
# ==============================
def _validar_nombre_apellido(nombre_apellido):
    error = None
    if not nombre_apellido or not nombre_apellido.strip():
        error = "El nombre completo es obligatorio."
    elif len(nombre_apellido.strip()) > NOMBRE_MAX:
        error = f"El nombre no puede superar los {NOMBRE_MAX} caracteres."
    return error


def _validar_dni(dni):
    error = None
    if dni:
        dni_limpio = dni.strip()
        if len(dni_limpio) > DNI_MAX:
            error = f"El DNI no puede superar los {DNI_MAX} caracteres."
        elif not dni_limpio.isdigit():
            error = "El DNI solo puede contener números."
    return error


def _validar_fecha_nacimiento(fecha_nacimiento):
    error = None
    if fecha_nacimiento:
        partes = fecha_nacimiento.split("-")
        if len(partes) != 3:
            error = "La fecha de nacimiento debe tener el formato YYYY-MM-DD."
        else:
            try:
                anio = int(partes[0])
                mes  = int(partes[1])
                dia  = int(partes[2])
                if anio < FECHA_MIN_ANIO or anio > 2099:
                    error = f"El año de nacimiento debe estar entre {FECHA_MIN_ANIO} y 2099."
                elif mes < 1 or mes > 12:
                    error = "El mes de nacimiento debe estar entre 1 y 12."
                elif dia < 1 or dia > 31:
                    error = "El día de nacimiento debe estar entre 1 y 31."
            except ValueError:
                error = "La fecha de nacimiento contiene valores no numéricos."
    return error


def _validar_telefono(telefono):
    error = None
    if telefono:
        tel = telefono.strip()
        if len(tel) > TELEFONO_MAX:
            error = f"El teléfono no puede superar los {TELEFONO_MAX} caracteres."
        elif not tel.lstrip("+").replace("-", "").replace(" ", "").isdigit():
            error = "El teléfono solo puede contener números, espacios, guiones y '+'."
    return error


def _validar_email(email):
    error = None
    if email:
        em = email.strip()
        if len(em) > EMAIL_MAX:
            error = f"El email no puede superar los {EMAIL_MAX} caracteres."
        else:
            partes = em.split("@")
            local_valido  = len(partes) == 2 and len(partes[0]) > 0
            dominio_partes = partes[1].split(".") if local_valido else []
            dominio_valido = (
                len(dominio_partes) >= 2
                and all(len(p) > 0 for p in dominio_partes)
                and len(dominio_partes[-1]) >= 2
            )
            if not local_valido or not dominio_valido:
                error = "El email no tiene un formato válido (ej: nombre@gmail.com)."
    return error


def _validar_numero_camiseta(numero_camisetas):
    error = None
    if numero_camisetas:
        nc = str(numero_camisetas).strip()
        if len(nc) > CAMISETA_MAX:
            error = f"El número de camiseta no puede superar los {CAMISETA_MAX} caracteres."
        elif not nc.isdigit():
            error = "El número de camiseta solo puede contener dígitos."
        elif int(nc) <= 0:
            error = "El número de camiseta debe ser mayor a 0."
    return error


def _validar_tutor(tutor_id):
    error = None
    if not tutor_id:
        error = "Debe seleccionar un tutor válido."
    return error


def _obtener_categoria_superior(categoria_id):
    """
    Devuelve el id de la categoría inmediatamente superior (mayor edad),
    es decir, la que tiene el anio_inicio inmediatamente menor al de la
    categoría dada. Devuelve None si no existe categoría superior.
    """
    conn = get_connection()
    cat_superior_id = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT anio_inicio FROM categorias WHERE id = ?", (categoria_id,))
        fila = cur.fetchone()
        if fila:
            anio_inicio_actual = fila[0]
            cur.execute("""
                SELECT id FROM categorias
                WHERE anio_inicio < ?
                ORDER BY anio_inicio DESC
                LIMIT 1
            """, (anio_inicio_actual,))
            fila_sup = cur.fetchone()
            if fila_sup:
                cat_superior_id = fila_sup[0]
    finally:
        conn.close()
    return cat_superior_id


def _validar_camiseta_unica(numero_camisetas, categoria_id, alumno_id_excluir=None):
    """
    Valida que el número de camiseta no esté en uso dentro de la categoría
    ni en la categoría inmediatamente superior (ya que un alumno puede
    jugar en su categoría o en la superior).
    Devuelve None si es válido, o un mensaje de error (str).
    """
    error = None
    if not numero_camisetas or not categoria_id:
        error = None
    else:
        nc = str(numero_camisetas).strip()
        cat_superior_id = _obtener_categoria_superior(categoria_id)

        categorias_a_verificar = [categoria_id]
        if cat_superior_id is not None:
            categorias_a_verificar.append(cat_superior_id)

        conn = get_connection()
        try:
            cur = conn.cursor()
            for cat_id in categorias_a_verificar:
                if alumno_id_excluir:
                    cur.execute("""
                        SELECT a.nombre_apellido, c.nombre
                        FROM alumnos a
                        JOIN categorias c ON a.categoria_id = c.id
                        WHERE a.numero_camisetas = ?
                          AND a.categoria_id = ?
                          AND a.activo = 1
                          AND a.id != ?
                    """, (nc, cat_id, alumno_id_excluir))
                else:
                    cur.execute("""
                        SELECT a.nombre_apellido, c.nombre
                        FROM alumnos a
                        JOIN categorias c ON a.categoria_id = c.id
                        WHERE a.numero_camisetas = ?
                          AND a.categoria_id = ?
                          AND a.activo = 1
                    """, (nc, cat_id))
                fila = cur.fetchone()
                if fila and error is None:
                    error = (
                        f"La camiseta N°{nc} ya está en uso por "
                        f"{fila[0]} (categoría {fila[1]}). "
                        f"No puede repetirse en la misma categoría ni en la superior."
                    )
        finally:
            conn.close()
    return error


def _validar_alumno(nombre_apellido, dni, fecha_nacimiento, telefono,
                    email, numero_camisetas, categoria_id, tutor_id,
                    alumno_id_excluir=None):
    """
    Ejecuta todas las validaciones en orden.
    Devuelve None si todo es válido, o el primer mensaje de error (str).
    """
    error = _validar_nombre_apellido(nombre_apellido)
    if error is None:
        error = _validar_dni(dni)
    if error is None:
        error = _validar_fecha_nacimiento(fecha_nacimiento)
    if error is None:
        error = _validar_telefono(telefono)
    if error is None:
        error = _validar_email(email)
    if error is None:
        error = _validar_numero_camiseta(numero_camisetas)
    if error is None:
        error = _validar_tutor(tutor_id)
    if error is None:
        error = _validar_camiseta_unica(numero_camisetas, categoria_id, alumno_id_excluir)
    return error


# ==============================
# CREAR ALUMNO
# ==============================
def crear_alumno(nombre_apellido, dni, fecha_nacimiento, telefono, email,
                 numero_camisetas, categoria_id, tutor_id):
    error = _validar_alumno(
        nombre_apellido, dni, fecha_nacimiento, telefono,
        email, numero_camisetas, categoria_id, tutor_id
    )
    if error is not None:
        raise ValueError(error)

    conn = get_connection()
    resultado = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alumnos
            (nombre_apellido, dni, fecha_nacimiento, telefono, email,
             numero_camisetas, categoria_id, tutor_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            nombre_apellido.strip(),
            dni.strip() if dni else None,
            fecha_nacimiento or None,
            telefono.strip() if telefono else None,
            email.strip() if email else None,
            numero_camisetas.strip() if numero_camisetas else None,
            categoria_id,
            tutor_id,
        ))
        conn.commit()
        resultado = cursor.lastrowid
    finally:
        conn.close()
    return resultado


# ==============================
# OBTENER ALUMNOS (con filtros)
# ==============================
def obtener_alumnos(filtro="", solo_activos=False, solo_al_dia=False,
                    solo_deudores=False, tutor_id=None):
    conn = get_connection()
    rows = []
    try:
        cursor = conn.cursor()

        query = """
            SELECT a.id, a.nombre_apellido, a.dni, a.fecha_nacimiento,
                   a.telefono, a.email, a.numero_camisetas,
                   a.categoria_id, a.tutor_id, a.activo, a.created_at, a.updated_at,
                   t.nombre  AS tutor_nombre,
                   t.apellido AS tutor_apellido,
                   c.nombre  AS categoria_nombre
            FROM alumnos a
            LEFT JOIN tutores    t ON a.tutor_id    = t.id
            LEFT JOIN categorias c ON a.categoria_id = c.id
            WHERE 1 = 1
        """
        params = []

        if filtro:
            query += " AND (a.nombre_apellido LIKE ? OR a.dni LIKE ?) "
            params.append(f"%{filtro}%")
            params.append(f"%{filtro}%")

        if solo_activos:
            query += " AND a.activo = 1 "

        if tutor_id:
            query += " AND a.tutor_id = ? "
            params.append(tutor_id)

        query += " ORDER BY a.nombre_apellido "

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return rows


# ==============================
# ACTUALIZAR ALUMNO
# ==============================
def actualizar_alumno(alumno_id, nombre_apellido, dni, fecha_nacimiento, telefono,
                      email, numero_camisetas, categoria_id, tutor_id):
    error = _validar_alumno(
        nombre_apellido, dni, fecha_nacimiento, telefono,
        email, numero_camisetas, categoria_id, tutor_id,
        alumno_id_excluir=alumno_id
    )
    if error is not None:
        raise ValueError(error)

    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alumnos
            SET nombre_apellido  = ?,
                dni              = ?,
                fecha_nacimiento = ?,
                telefono         = ?,
                email            = ?,
                numero_camisetas = ?,
                categoria_id     = ?,
                tutor_id         = ?,
                updated_at       = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            nombre_apellido.strip(),
            dni.strip() if dni else None,
            fecha_nacimiento or None,
            telefono.strip() if telefono else None,
            email.strip() if email else None,
            numero_camisetas.strip() if numero_camisetas else None,
            categoria_id,
            tutor_id,
            alumno_id,
        ))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado


# ==============================
# ELIMINAR ALUMNO
# ==============================
def eliminar_alumno(alumno_id):
    conn = get_connection()
    resultado = False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alumnos WHERE id = ?", (alumno_id,))
        conn.commit()
        resultado = cursor.rowcount > 0
    finally:
        conn.close()
    return resultado