# database/migraciones.py
"""
Migraciones de base de datos.
Ejecutar una vez cuando se actualiza el sistema.
Se puede correr directamente: python database/migraciones.py
"""
from db import get_connection


def migrar_monto_pagado():
    """
    Agrega la columna monto_pagado a la tabla recibos si no existe.
    La inicializa con el valor de monto para todos los recibos existentes.
    """
    conn      = get_connection()
    resultado = ""
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(recibos)")
        cols = [c[1] for c in cur.fetchall()]

        if "monto_pagado" not in cols:
            cur.execute("ALTER TABLE recibos ADD COLUMN monto_pagado REAL")
            cur.execute("UPDATE recibos SET monto_pagado = monto WHERE monto_pagado IS NULL")
            conn.commit()
            resultado = "✅ Columna monto_pagado agregada y datos existentes migrados."
        else:
            resultado = "ℹ️  La columna monto_pagado ya existe, no se hizo nada."
    finally:
        conn.close()
    return resultado


def ejecutar_todas():
    print("=== Migraciones ===")
    print(migrar_monto_pagado())
    print("===================")


if __name__ == "__main__":
    ejecutar_todas()