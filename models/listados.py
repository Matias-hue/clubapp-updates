# models/listados.py
from database.db import get_connection


# ══════════════════════════════════════════════
# TUTORES CON SUS ALUMNOS
# ══════════════════════════════════════════════
def obtener_tutores_con_alumnos():
    """
    Retorna lista de tutores, cada uno con su lista de alumnos
    (activos e inactivos). Las fechas se devuelven en formato ISO
    (YYYY-MM-DD); el formateo a DD/MM/YYYY se hace en la capa de UI/PDF
    usando utils.fecha.fmt_fecha.
    """
    conn      = get_connection()
    resultado = []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.nombre, t.apellido, t.telefono, t.domicilio,
                   COUNT(a.id)                                        AS total_alumnos,
                   SUM(CASE WHEN a.activo = 1 THEN 1 ELSE 0 END)     AS alumnos_activos
            FROM tutores t
            LEFT JOIN alumnos a ON a.tutor_id = t.id
            GROUP BY t.id
            ORDER BY t.apellido, t.nombre
        """)
        tutores = [dict(r) for r in cur.fetchall()]

        for tutor in tutores:
            cur.execute("""
                SELECT a.id, a.nombre_apellido, a.dni, a.telefono, a.email,
                       a.numero_camisetas, a.fecha_nacimiento, a.activo,
                       c.nombre AS categoria_nombre
                FROM alumnos a
                LEFT JOIN categorias c ON a.categoria_id = c.id
                WHERE a.tutor_id = ?
                ORDER BY a.activo DESC, a.nombre_apellido
            """, (tutor["id"],))
            tutor["alumnos"] = [dict(r) for r in cur.fetchall()]

        resultado = tutores
    finally:
        conn.close()
    return resultado


# ══════════════════════════════════════════════
# CATEGORIAS CON SUS ALUMNOS
# ══════════════════════════════════════════════
def obtener_categorias_con_alumnos():
    """
    Retorna lista de categorías, cada una con su lista de alumnos.
    Las fechas se devuelven en formato ISO (YYYY-MM-DD).
    """
    conn      = get_connection()
    resultado = []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.nombre, c.anio_inicio, c.anio_fin, c.valor_cuota,
                   COUNT(a.id)                                        AS total_alumnos,
                   SUM(CASE WHEN a.activo = 1 THEN 1 ELSE 0 END)     AS alumnos_activos
            FROM categorias c
            LEFT JOIN alumnos a ON a.categoria_id = c.id
            GROUP BY c.id
            ORDER BY c.nombre
        """)
        categorias = [dict(r) for r in cur.fetchall()]

        for cat in categorias:
            cur.execute("""
                SELECT a.id, a.nombre_apellido, a.dni, a.telefono, a.email,
                       a.numero_camisetas, a.fecha_nacimiento, a.activo,
                       t.nombre   AS tutor_nombre,
                       t.apellido AS tutor_apellido,
                       t.telefono AS tutor_telefono
                FROM alumnos a
                LEFT JOIN tutores t ON a.tutor_id = t.id
                WHERE a.categoria_id = ?
                ORDER BY a.activo DESC, a.nombre_apellido
            """, (cat["id"],))
            cat["alumnos"] = [dict(r) for r in cur.fetchall()]

        resultado = categorias
    finally:
        conn.close()
    return resultado