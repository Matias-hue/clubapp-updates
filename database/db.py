import sqlite3
import os
import sys

APP_NAME = "ClubApp"


def get_app_data_path():
    """
    Carpeta persistente del usuario.
    - Windows: AppData/Local/ClubApp/
    - Mac:     ~/Library/Application Support/ClubApp/
    - Linux:   ~/.local/share/ClubApp/
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")

    resultado = os.path.join(base, APP_NAME)
    return resultado


def get_db_path():
    #resultado = os.path.join(get_app_data_path(), "club.db")
    #return resultado
    base      = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    resultado = os.path.join(base, "..", "data", "club.db")
    resultado = os.path.normpath(resultado)
    return resultado

def _aplicar_migraciones(conn):
    """
    Agrega columnas faltantes a tablas ya existentes.
    ALTER TABLE ignora el error si la columna ya existe (manejado con try/except).
    """
    migraciones = [
        "ALTER TABLE tutores    ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE tutores    ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE categorias ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE categorias ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE alumnos    ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE alumnos    ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE recibos    ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE recibos    ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
    ]
    for sql in migraciones:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # La columna ya existe, no hacer nada
    conn.commit()


def init_db_if_needed():
    """
    Crea la carpeta y las tablas si la DB todavía no existe.
    Aplica migraciones para DBs existentes con schema desactualizado.
    """
    carpeta = get_app_data_path()
    if not os.path.exists(carpeta):
        os.makedirs(carpeta, exist_ok=True)

    conn = sqlite3.connect(get_db_path())
    try:
        conn.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS tutores (
                id         INTEGER  PRIMARY KEY AUTOINCREMENT,
                nombre     TEXT     NOT NULL,
                apellido   TEXT     NOT NULL,
                telefono   TEXT,
                domicilio  TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categorias (
                id          INTEGER  PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT     NOT NULL UNIQUE,
                anio_inicio INTEGER,
                anio_fin    INTEGER,
                valor_cuota REAL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alumnos (
                id               INTEGER  PRIMARY KEY AUTOINCREMENT,
                nombre_apellido  TEXT     NOT NULL,
                dni              TEXT,
                telefono         TEXT,
                email            TEXT,
                numero_camisetas TEXT,
                fecha_nacimiento TEXT,
                activo           INTEGER  NOT NULL DEFAULT 1,
                tutor_id         INTEGER  REFERENCES tutores(id)    ON DELETE SET NULL,
                categoria_id     INTEGER  REFERENCES categorias(id) ON DELETE SET NULL,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recibos (
                id            INTEGER  PRIMARY KEY AUTOINCREMENT,
                alumno_id     INTEGER  REFERENCES alumnos(id)    ON DELETE CASCADE,
                tutor_id      INTEGER  REFERENCES tutores(id)    ON DELETE SET NULL,
                categoria_id  INTEGER  REFERENCES categorias(id) ON DELETE SET NULL,
                tipo_pago     TEXT     NOT NULL DEFAULT 'pago_cuota',
                mes_pago      TEXT,
                fecha_pago    TEXT,
                fecha_emision TEXT,
                monto         REAL     NOT NULL DEFAULT 0,
                descuento     REAL              DEFAULT 0,
                mora          REAL              DEFAULT 0,
                monto_pagado  REAL,
                pago_completo INTEGER           DEFAULT 1,
                forma_pago    TEXT              DEFAULT 'efectivo',
                descripcion   TEXT,
                emitido_por   TEXT,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        _aplicar_migraciones(conn)
    finally:
        conn.close()


def get_connection():
    """
    Conexión SQLite principal.
    Inicializa las tablas si es la primera vez.
    """
    init_db_if_needed()

    conn = sqlite3.connect(get_db_path(), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn