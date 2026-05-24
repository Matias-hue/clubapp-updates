# models/stats.py
from datetime import datetime

from database.db import get_connection


def contar_tutores():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tutores")
        return cur.fetchone()[0]
    finally:
        conn.close()


def contar_alumnos_activos():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alumnos WHERE activo = 1")
        return cur.fetchone()[0]
    finally:
        conn.close()


def contar_categorias():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM categorias")
        return cur.fetchone()[0]
    finally:
        conn.close()


def contar_recibos_mes_actual():
    conn = get_connection()
    try:
        cur = conn.cursor()
        anio_mes = datetime.now().strftime("%Y-%m")
        cur.execute("""
            SELECT COUNT(*) FROM recibos
            WHERE strftime('%Y-%m', fecha_pago) = ?
        """, (anio_mes,))
        return cur.fetchone()[0]
    finally:
        conn.close()


def obtener_stats():
    """Agrupa los 4 conteos para el dashboard."""
    return {
        "tutores":     contar_tutores(),
        "alumnos":     contar_alumnos_activos(),
        "categorias":  contar_categorias(),
        "recibos_mes": contar_recibos_mes_actual(),
    }