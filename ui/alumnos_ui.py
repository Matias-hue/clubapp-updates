import tkinter as tk
from tkinter import messagebox, ttk
from datetime import date

try:
    from tkcalendar import DateEntry
    _TIENE_CALENDAR = True
except ImportError:
    _TIENE_CALENDAR = False

from database.db            import get_connection
from models.alumnos         import crear_alumno, actualizar_alumno, eliminar_alumno, obtener_alumnos
from models.alumnos_detalle import obtener_historial, obtener_resumen_anual, obtener_resumen_deuda
from models.categorias      import obtener_categorias
from models.tutores         import obtener_tutores
from ui.tabla_scroll        import agregar_header, crear_tabla_scroll, fila_color
from utils.fecha            import arg_a_iso, fmt_fecha


# ─────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────
MESES_CLUB = ["marzo", "abril", "mayo", "junio", "julio",
              "agosto", "septiembre", "octubre", "noviembre"]


# ─────────────────────────────────────────────────────────────────────────
# HELPERS GENERALES
# ─────────────────────────────────────────────────────────────────────────
def limpiar_frame(frame):
    for w in frame.winfo_children():
        w.destroy()


def centrar(v, ancho, alto):
    v.update_idletasks()
    sw, sh = v.winfo_screenwidth(), v.winfo_screenheight()
    v.geometry(f"{ancho}x{alto}+{(sw - ancho) // 2}+{(sh - alto) // 2}")


def _es_activo(valor):
    return str(valor) == "1"


def _fmt(v):
    try:
        resultado = f"${float(v):.2f}"
    except Exception:
        resultado = "$0.00"
    return resultado


def _label_tipo(t):
    return "Cuota" if t == "pago_cuota" else "Otro"

def _aplicar_hover(btn, color_normal, color_hover):
    btn.bind("<Enter>", lambda e: btn.config(bg=color_hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=color_normal))



# ─────────────────────────────────────────────────────────────────────────
# WIDGET FECHA  (DD/MM/YYYY hacia el usuario, ISO hacia la BD)
# ─────────────────────────────────────────────────────────────────────────
def _crear_entry_fecha(parent, valor_iso="", width=28):
    valor_arg = fmt_fecha(valor_iso) if valor_iso else ""
    if _TIENE_CALENDAR:
        e = DateEntry(parent, width=width - 2,
                      date_pattern="dd/mm/yyyy", locale="es_AR")
        if valor_arg:
            try:
                partes = valor_arg.split("/")
                e.set_date(date(int(partes[2]), int(partes[1]), int(partes[0])))
            except Exception:
                pass
    else:
        e = tk.Entry(parent, width=width)
        e.insert(0, valor_arg if valor_arg else "DD/MM/YYYY")
    return e


# ─────────────────────────────────────────────────────────────────────────
# MODAL: VER ALUMNO
# ─────────────────────────────────────────────────────────────────────────
def abrir_ver_alumno(r):
    v = tk.Toplevel()
    v.title(f"Ficha — {r.get('nombre_apellido', '')}")
    v.grab_set()
    centrar(v, 440, 460)
    v.resizable(False, False)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text="Ficha del Alumno", font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Contenido ─────────────────────────────────────────────────────────
    ficha_frame = tk.LabelFrame(v, text="Datos del Alumno",
                                font=("Arial", 9, "bold"), padx=12, pady=8)
    ficha_frame.pack(fill="both", expand=True, padx=12, pady=(10, 6))
    ficha_frame.columnconfigure(1, weight=1)

    activo = _es_activo(r.get("activo"))
    tutor  = (f"{r.get('tutor_nombre', '') or ''} "
              f"{r.get('tutor_apellido', '') or ''}").strip() or "—"

    campos = [
        ("Nombre y Apellido",   r.get("nombre_apellido") or "—"),
        ("DNI",                 r.get("dni")             or "—"),
        ("Fecha de Nacimiento", fmt_fecha(r.get("fecha_nacimiento")) or "—"),
        ("Teléfono",            r.get("telefono")        or "—"),
        ("Email",               r.get("email")           or "—"),
        ("N° de Camiseta",      r.get("numero_camisetas") or "—"),
        ("Categoría",           r.get("categoria_nombre") or "—"),
        ("Tutor",               tutor),
        ("Estado",              "✅ Activo" if activo else "⛔ Inactivo"),
    ]
    for i, (label, valor) in enumerate(campos):
        bg_fila = "#f9f9f9" if i % 2 == 0 else "white"
        tk.Label(ficha_frame, text=label, font=("Arial", 9, "bold"),
                 bg=bg_fila, anchor="e", padx=10, pady=6, width=18).grid(
            row=i, column=0, sticky="nsew", padx=(0, 1))
        tk.Label(ficha_frame, text=valor, bg=bg_fila,
                 anchor="w", padx=10, pady=6, font=("Arial", 9)).grid(
            row=i, column=1, sticky="nsew")

    # ── Botón ─────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=10)
    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=14, pady=5, cursor="hand2", command=v.destroy)
    btn_cerrar.pack()
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")


# ─────────────────────────────────────────────────────────────────────────
# MODAL: HISTORIAL DE PAGOS
# ─────────────────────────────────────────────────────────────────────────
def abrir_historial(r):
    v = tk.Toplevel()
    v.title(f"Historial — {r.get('nombre_apellido', '')}")
    v.grab_set()
    centrar(v, 920, 500)
    v.resizable(True, True)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header,
             text=f"Historial de Pagos — {r.get('nombre_apellido', '')}",
             font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Tabla ─────────────────────────────────────────────────────────────
    panel = tk.LabelFrame(v, text="Pagos Registrados",
                          font=("Arial", 9, "bold"), padx=8, pady=8)
    panel.pack(fill="both", expand=True, padx=12, pady=(10, 6))

    outer, tabla = crear_tabla_scroll(panel)
    outer.pack(fill="both", expand=True)

    headers = ["Fecha", "Tipo", "Mes", "Monto", "Descuento",
               "Mora", "Total", "Forma de Pago", "Descripción", "Estado"]
    agregar_header(tabla, headers)

    pagos = obtener_historial(r["id"])
    if not pagos:
        tk.Label(tabla, text="Sin pagos registrados", fg="gray",
                 font=("Arial", 10), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
    else:
        for i, p in enumerate(pagos, start=1):
            bg       = fila_color(i)
            monto    = float(p.get("monto")     or 0)
            desc     = float(p.get("descuento") or 0)
            mora     = float(p.get("mora")      or 0)
            total    = monto - desc + mora
            completo = str(p.get("pago_completo", "")) == "1"
            vals = [
                fmt_fecha(p.get("fecha_pago")) or "—",
                _label_tipo(p.get("tipo_pago", "")),
                (p.get("mes_pago") or "—").capitalize(),
                _fmt(monto), _fmt(desc), _fmt(mora), _fmt(total),
                (p.get("forma_pago") or "—").capitalize(),
                p.get("descripcion") or "—",
                "✅ Pagado" if completo else "⚠ Parcial",
            ]
            for col, val in enumerate(vals):
                tk.Label(tabla, text=val, bg=bg, padx=6, pady=4,
                         font=("Arial", 9)).grid(
                    row=i, column=col, sticky="nsew", padx=1, pady=1)

    # ── Botón ─────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=8)
    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=14, pady=5, cursor="hand2", command=v.destroy)
    btn_cerrar.pack()
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")


# ─────────────────────────────────────────────────────────────────────────
# MODAL: RESUMEN ANUAL
# ─────────────────────────────────────────────────────────────────────────
_CONFIG_RESUMEN = {
    "pagado":    ("#d4edda", "#27ae60", "✅ Pagado"),
    "parcial":   ("#fff3cd", "#e67e22", "⚠ Parcial"),
    "adeudado":  ("#fde8e8", "#e74c3c", "❌ Adeudado"),
    "futuro":    ("#f0f4ff", "#7f8c8d", "— Futuro"),
    "no_aplica": ("#f5f5f5", "#bbb",    "— N/A"),
}


def abrir_resumen_anual(r):
    v = tk.Toplevel()
    v.title(f"Resumen Anual — {r.get('nombre_apellido', '')}")
    v.grab_set()
    centrar(v, 380, 460)
    v.resizable(False, True)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text=f"Resumen Anual {date.today().year}",
             font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Alumno ────────────────────────────────────────────────────────────
    tk.Label(v, text=r.get("nombre_apellido", ""),
             font=("Arial", 11, "bold"), fg="#2c3e50").pack(pady=(10, 4))

    # ── Tabla ─────────────────────────────────────────────────────────────
    panel = tk.LabelFrame(v, text="Estado por Mes",
                          font=("Arial", 9, "bold"), padx=12, pady=8)
    panel.pack(fill="both", expand=True, padx=12, pady=(0, 6))
    panel.columnconfigure(0, weight=1)
    panel.columnconfigure(1, weight=1)

    for col, txt in enumerate(["Mes", "Estado"]):
        tk.Label(panel, text=txt, font=("Arial", 10, "bold"),
                 bg="#2c3e50", fg="white", padx=10, pady=6).grid(
            row=0, column=col, sticky="nsew", padx=1, pady=(0, 2))

    resumen_completo = obtener_resumen_anual(r["id"], r.get("created_at"))
    resumen = [item for item in resumen_completo
               if item["mes"].lower() in MESES_CLUB]

    for i, item in enumerate(resumen, start=1):
        bg, color, etiqueta = _CONFIG_RESUMEN.get(
            item["estado"], ("#fff", "#333", item["estado"]))
        tk.Label(panel, text=item["mes"].capitalize(), bg=bg,
                 font=("Arial", 10, "bold"), padx=10, pady=8).grid(
            row=i, column=0, sticky="nsew", padx=1, pady=1)
        tk.Label(panel, text=etiqueta, bg=bg, fg=color,
                 font=("Arial", 10, "bold"), padx=10, pady=8).grid(
            row=i, column=1, sticky="nsew", padx=1, pady=1)

    # ── Botón ─────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=8)
    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=14, pady=5, cursor="hand2", command=v.destroy)
    btn_cerrar.pack()
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")


# ─────────────────────────────────────────────────────────────────────────
# MODAL: CALCULADORA DE DEUDA
# ─────────────────────────────────────────────────────────────────────────
def _fila_deuda(frame, label, valor, fila, color_val="#2c3e50", grande=False):
    bg = "#f9f9f9" if fila % 2 == 0 else "white"
    tk.Label(frame, text=label, bg=bg, anchor="w",
             font=("Arial", 10), padx=12, pady=10).grid(
        row=fila, column=0, sticky="nsew", padx=1, pady=1)
    tk.Label(frame, text=str(valor), bg=bg, fg=color_val,
             font=("Arial", 12 if grande else 10, "bold"),
             anchor="e", padx=12).grid(
        row=fila, column=1, sticky="nsew", padx=1, pady=1)


def abrir_deuda(r):
    v = tk.Toplevel()
    v.title(f"Deuda — {r.get('nombre_apellido', '')}")
    v.grab_set()
    centrar(v, 420, 420)
    v.resizable(False, False)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text="Calculadora de Deuda", font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    tk.Label(v, text=r.get("nombre_apellido", ""),
             font=("Arial", 11, "bold"), fg="#2c3e50").pack(pady=(10, 4))

    # ── Resumen ───────────────────────────────────────────────────────────
    deuda = obtener_resumen_deuda(r["id"], r.get("created_at"))

    panel = tk.LabelFrame(v, text="Resumen de Deuda",
                          font=("Arial", 9, "bold"), padx=12, pady=8)
    panel.pack(fill="both", expand=True, padx=12, pady=(0, 6))
    panel.columnconfigure(0, weight=1)
    panel.columnconfigure(1, weight=1)

    n_adeud    = len(deuda["meses_adeudados"])
    color_deud = "#e74c3c" if n_adeud > 0 else "#27ae60"

    _fila_deuda(panel, "Alumno",            r.get("nombre_apellido", ""), 0)
    _fila_deuda(panel, "Meses activo",      deuda["meses_activo"],        1)
    _fila_deuda(panel, "Pagos registrados", deuda["meses_pagados"],       2, "#27ae60")
    _fila_deuda(panel, "Meses adeudados",   n_adeud, 3, color_deud, grande=True)

    if deuda["meses_adeudados"]:
        tk.Label(panel, text="Meses sin pagar:",
                 font=("Arial", 9, "bold"), fg="#e74c3c",
                 anchor="w", padx=12, pady=6).grid(
            row=4, column=0, columnspan=2, sticky="w")
        lista_txt = ",  ".join(m.capitalize() for m in deuda["meses_adeudados"])
        tk.Label(panel, text=lista_txt, wraplength=340,
                 font=("Arial", 9), fg="#c0392b",
                 justify="left", anchor="w", padx=12, pady=4).grid(
            row=5, column=0, columnspan=2, sticky="w")
    else:
        tk.Label(panel, text="✅ Sin deudas pendientes",
                 font=("Arial", 10, "bold"), fg="#27ae60",
                 pady=10).grid(row=4, column=0, columnspan=2)

    # ── Botón ─────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=8)
    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=14, pady=5, cursor="hand2", command=v.destroy)
    btn_cerrar.pack()
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")


# ─────────────────────────────────────────────────────────────────────────
# ACCIONES MASIVAS
# ─────────────────────────────────────────────────────────────────────────
def desactivar_seleccionados(vars_seleccion, contenedor_tabla):
    ids = [aid for aid, var in vars_seleccion.items() if var.get()]
    if not ids:
        messagebox.showwarning("Sin selección", "Seleccioná al menos un alumno.")
    else:
        if messagebox.askyesno("Confirmar", f"¿Desactivar {len(ids)} alumno(s)?"):
            conn = get_connection()
            try:
                conn.cursor().executemany(
                    "UPDATE alumnos SET activo = 0 WHERE id = ?",
                    [(i,) for i in ids])
                conn.commit()
            finally:
                conn.close()
            cargar_alumnos(contenedor_tabla)


def activar_seleccionados(vars_seleccion, contenedor_tabla):
    ids = [aid for aid, var in vars_seleccion.items() if var.get()]
    if not ids:
        messagebox.showwarning("Sin selección", "Seleccioná al menos un alumno.")
    else:
        if messagebox.askyesno("Confirmar", f"¿Activar {len(ids)} alumno(s)?"):
            conn = get_connection()
            try:
                conn.cursor().executemany(
                    "UPDATE alumnos SET activo = 1 WHERE id = ?",
                    [(i,) for i in ids])
                conn.commit()
            finally:
                conn.close()
            cargar_alumnos(contenedor_tabla)


def eliminar_seleccionados(vars_seleccion, contenedor_tabla):
    ids = [aid for aid, var in vars_seleccion.items() if var.get()]
    if not ids:
        messagebox.showwarning("Sin selección", "Seleccioná al menos un alumno.")
    else:
        if messagebox.askyesno("Eliminar",
                               f"¿Eliminar definitivamente {len(ids)} alumno(s)?\n"
                               "Esta acción no se puede deshacer."):
            conn = get_connection()
            try:
                conn.cursor().executemany(
                    "DELETE FROM alumnos WHERE id = ?",
                    [(i,) for i in ids])
                conn.commit()
            finally:
                conn.close()
            cargar_alumnos(contenedor_tabla)


# ─────────────────────────────────────────────────────────────────────────
# TABLA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────
def cargar_alumnos(contenedor_tabla, filtro="", solo_activos=False,
                   solo_al_dia=False, solo_deudores=False, tutor_id=None,
                   vars_seleccion=None):
    limpiar_frame(contenedor_tabla)
    outer, tabla = crear_tabla_scroll(contenedor_tabla)
    outer.pack(fill="both", expand=True)

    if vars_seleccion is None:
        vars_seleccion = {}

    rows = obtener_alumnos(filtro=filtro, solo_activos=solo_activos,
                           tutor_id=tutor_id)

    rows_filtradas = []
    for r in rows:
        deuda_info  = obtener_resumen_deuda(r["id"], r.get("created_at"))
        tiene_deuda = len(deuda_info["meses_adeudados"]) > 0
        incluir     = True
        if solo_al_dia   and tiene_deuda:
            incluir = False
        if solo_deudores and not tiene_deuda:
            incluir = False
        if incluir:
            r["_deuda_info"] = deuda_info
            rows_filtradas.append(r)
    rows = rows_filtradas

    headers = [
        "Nombre y Apellido", "N° Camiseta", "Categoría", "Tutor",
        "Estado", "Estado Deuda", "Último Pago", "Ver", "Acciones", "✓"
    ]
    agregar_header(tabla, headers)

    vars_seleccion.clear()

    if not rows:
        tk.Label(tabla, text="No hay alumnos que coincidan con los filtros.",
                 fg="gray", font=("Arial", 10), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
    else:
        for i, r in enumerate(rows, start=1):
            activo = _es_activo(r.get("activo"))
            bg     = ("#f0fff4" if i % 2 == 0 else "#e8f8f0") if activo \
                     else ("#fff5f5" if i % 2 == 0 else "#ffeaea")

            tutor = (f"{r.get('tutor_nombre', '') or ''} "
                     f"{r.get('tutor_apellido', '') or ''}").strip() or "—"

            deuda_info = r["_deuda_info"]
            adeudados  = deuda_info["meses_adeudados"]
            n_adeud    = len(adeudados)
            ultimo     = fmt_fecha(deuda_info["ultimo_pago"]) or "—"

            if n_adeud == 0:
                deuda_txt, deuda_color = "✅ Al día", "#27ae60"
            else:
                nombres    = ", ".join(m.capitalize() for m in adeudados[:3])
                sufijo     = f" +{n_adeud - 3}" if n_adeud > 3 else ""
                deuda_txt  = f"❌ {n_adeud} mes{'es' if n_adeud > 1 else ''}: {nombres}{sufijo}"
                deuda_color = "#e74c3c"

            datos = [
                (r.get("nombre_apellido", ""), True),
                (r.get("numero_camisetas") or "—", False),
                (r.get("categoria_nombre") or "—", False),
                (tutor, False),
            ]
            for col, (val, bold) in enumerate(datos):
                tk.Label(tabla, text=val, bg=bg, padx=6,
                         font=("Arial", 9, "bold") if bold else ("Arial", 9)).grid(
                    row=i, column=col, sticky="nsew", padx=1, pady=1)

            tk.Label(tabla,
                     text="● Activo" if activo else "● Inactivo",
                     fg="#27ae60" if activo else "#e74c3c",
                     bg=bg, font=("Arial", 9, "bold"), padx=6).grid(
                row=i, column=4, sticky="nsew", padx=1, pady=1)

            tk.Label(tabla, text=deuda_txt, fg=deuda_color,
                     bg=bg, font=("Arial", 9), padx=6,
                     wraplength=180, justify="left").grid(
                row=i, column=5, sticky="nsew", padx=1, pady=1)

            tk.Label(tabla, text=ultimo, bg=bg, font=("Arial", 9), padx=6).grid(
                row=i, column=6, sticky="nsew", padx=1, pady=1)

            tk.Button(tabla, text="👁", bg="#2980b9", fg="white",
                      font=("Arial", 10), width=3,
                      command=lambda r=r: abrir_ver_alumno(r)).grid(
                row=i, column=7, sticky="nsew", padx=2, pady=2)

            btn_acciones = tk.Menubutton(tabla, text="Acciones ▼",
                                         bg="#34495e", fg="white",
                                         font=("Arial", 8), relief="raised")
            menu_acciones = tk.Menu(btn_acciones, tearoff=0)
            menu_acciones.add_command(label="Historial",
                                      command=lambda r=r: abrir_historial(r))
            menu_acciones.add_command(label="Resumen Anual",
                                      command=lambda r=r: abrir_resumen_anual(r))
            menu_acciones.add_command(label="Deuda",
                                      command=lambda r=r: abrir_deuda(r))
            menu_acciones.add_separator()
            menu_acciones.add_command(
                label="Editar",
                command=lambda r=r: abrir_editar_alumno(r, contenedor_tabla, vars_seleccion))
            menu_acciones.add_command(
                label="Desactivar" if activo else "Activar",
                command=lambda r=r, a=activo: toggle_activo(
                    r, a, contenedor_tabla, vars_seleccion))
            menu_acciones.add_separator()
            menu_acciones.add_command(
                label="Eliminar",
                command=lambda r=r: eliminar_alumno_ui(
                    r["id"], r["nombre_apellido"], contenedor_tabla, vars_seleccion))
            btn_acciones.config(menu=menu_acciones)
            btn_acciones.grid(row=i, column=8, sticky="nsew", padx=2, pady=2)

            var_sel = tk.BooleanVar(value=False)
            vars_seleccion[r["id"]] = var_sel
            tk.Checkbutton(tabla, variable=var_sel, bg=bg).grid(
                row=i, column=9, padx=4, pady=2)


# ─────────────────────────────────────────────────────────────────────────
# TOGGLE / ELIMINAR INDIVIDUAL
# ─────────────────────────────────────────────────────────────────────────
def toggle_activo(r, activo_actual, contenedor_tabla, vars_seleccion):
    nuevo  = 0 if activo_actual else 1
    accion = "desactivar" if activo_actual else "activar"
    if messagebox.askyesno("Confirmar", f"¿{accion.capitalize()} a {r['nombre_apellido']}?"):
        conn = get_connection()
        try:
            conn.execute("UPDATE alumnos SET activo = ? WHERE id = ?",
                         (nuevo, r["id"]))
            conn.commit()
        finally:
            conn.close()
        cargar_alumnos(contenedor_tabla, vars_seleccion=vars_seleccion)


def eliminar_alumno_ui(alumno_id, nombre, contenedor_tabla, vars_seleccion):
    if messagebox.askyesno("Eliminar Alumno",
                           f"¿Eliminar definitivamente a {nombre}?\n\n"
                           "Tip: usá 'Desactivar' para una baja temporal."):
        try:
            eliminar_alumno(alumno_id)
            cargar_alumnos(contenedor_tabla, vars_seleccion=vars_seleccion)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ─────────────────────────────────────────────────────────────────────────
# CREAR ALUMNO
# ─────────────────────────────────────────────────────────────────────────
def crear_alumno_ui(entries, entry_fecha, combo_tutor, combo_categoria,
                    contenedor_tabla, vars_seleccion):
    nombre_apellido  = entries["nombre_apellido"].get().strip()
    dni              = entries["dni"].get().strip()
    fecha_nac        = arg_a_iso(entry_fecha.get().strip())
    telefono         = entries["telefono"].get().strip()
    email            = entries["email"].get().strip()
    numero_camisetas = entries["numero_camisetas"].get().strip()
    tutor_text       = combo_tutor.get().strip()
    categoria_text   = combo_categoria.get().strip()

    error = None
    tutor_id     = None
    categoria_id = None

    if not tutor_text:
        error = "Debe seleccionar un tutor."
    else:
        tutores  = obtener_tutores()
        tutor_id = next(
            (t["id"] for t in tutores
             if f"{t['nombre']} {t['apellido']}" == tutor_text), None)
        if not tutor_id:
            error = f"Tutor no encontrado: {tutor_text}"

    if error is None and categoria_text:
        cats         = obtener_categorias()
        categoria_id = next(
            (c["id"] for c in cats if c["nombre"] == categoria_text), None)

    if error is not None:
        messagebox.showwarning("Datos inválidos", error)
    else:
        try:
            crear_alumno(nombre_apellido, dni, fecha_nac, telefono,
                         email, numero_camisetas, categoria_id, tutor_id)
            for e in entries.values():
                e.delete(0, tk.END)
            combo_tutor.set("")
            combo_categoria.set("")
            cargar_alumnos(contenedor_tabla, vars_seleccion=vars_seleccion)
            messagebox.showinfo("Éxito", "Alumno creado correctamente")
        except ValueError as e:
            messagebox.showwarning("Datos inválidos", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el alumno:\n{e}")


# ─────────────────────────────────────────────────────────────────────────
# GUARDAR EDICIÓN
# ─────────────────────────────────────────────────────────────────────────
def _guardar_edicion(alumno_id, entries_edit, entry_fecha,
                     combo_tutor, combo_cat, tutores, cats,
                     ventana, contenedor_tabla, vars_seleccion):
    nombre     = entries_edit["nombre_apellido"].get().strip()
    camis      = entries_edit["numero_camisetas"].get().strip()
    tutor_text = combo_tutor.get().strip()
    cat_text   = combo_cat.get().strip()

    error        = None
    tutor_id     = None
    categoria_id = None

    if not tutor_text:
        error = "Seleccioná un tutor."
    else:
        tutor_id = next(
            (t["id"] for t in tutores
             if f"{t['nombre']} {t['apellido']}" == tutor_text), None)
        if not tutor_id:
            error = "Tutor no válido."

    if error is None and cat_text:
        categoria_id = next(
            (c["id"] for c in cats if c["nombre"] == cat_text), None)

    if error is not None:
        messagebox.showwarning("Datos inválidos", error)
    else:
        try:
            actualizar_alumno(
                alumno_id, nombre,
                entries_edit["dni"].get().strip(),
                arg_a_iso(entry_fecha.get().strip()),
                entries_edit["telefono"].get().strip(),
                entries_edit["email"].get().strip(),
                camis, categoria_id, tutor_id)
            ventana.destroy()
            cargar_alumnos(contenedor_tabla, vars_seleccion=vars_seleccion)
            messagebox.showinfo("Éxito", "Alumno actualizado correctamente")
        except ValueError as e:
            messagebox.showwarning("Datos inválidos", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ─────────────────────────────────────────────────────────────────────────
# MODAL: EDITAR ALUMNO
# ─────────────────────────────────────────────────────────────────────────
def abrir_editar_alumno(r, contenedor_tabla, vars_seleccion):
    v = tk.Toplevel()
    v.title("Editar Alumno")
    v.grab_set()
    centrar(v, 480, 560)
    v.resizable(False, False)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text=f"Editar: {r['nombre_apellido']}",
             font=("Arial", 13, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Formulario ────────────────────────────────────────────────────────
    form_frame = tk.LabelFrame(v, text="Datos del Alumno",
                               font=("Arial", 9, "bold"), padx=16, pady=10)
    form_frame.pack(fill="x", padx=12, pady=(10, 6))

    campos_texto = [
        ("Nombre Completo *", "nombre_apellido", r.get("nombre_apellido", "") or ""),
        ("DNI",               "dni",             r.get("dni", "")             or ""),
        ("Teléfono",          "telefono",        r.get("telefono", "")        or ""),
        ("Email",             "email",           r.get("email", "")           or ""),
        ("N° de Camiseta",    "numero_camisetas",r.get("numero_camisetas", "") or ""),
    ]
    entries_edit = {}
    for i, (label, key, valor) in enumerate(campos_texto):
        tk.Label(form_frame, text=label, font=("Arial", 9, "bold"),
                 anchor="e").grid(row=i, column=0, sticky="e", pady=5, padx=(0, 8))
        e = tk.Entry(form_frame, width=30)
        e.insert(0, valor)
        e.grid(row=i, column=1, pady=5, sticky="ew")
        entries_edit[key] = e
    form_frame.columnconfigure(1, weight=1)

    fila = len(campos_texto)
    tk.Label(form_frame, text="Fecha de Nacimiento", font=("Arial", 9, "bold"),
             anchor="e").grid(row=fila, column=0, sticky="e", pady=5, padx=(0, 8))
    entry_fecha = _crear_entry_fecha(form_frame, r.get("fecha_nacimiento", "") or "")
    entry_fecha.grid(row=fila, column=1, pady=5, sticky="ew")

    tk.Label(form_frame, text="Tutor *", font=("Arial", 9, "bold"),
             anchor="e").grid(row=fila + 1, column=0, sticky="e", pady=5, padx=(0, 8))
    combo_tutor = ttk.Combobox(form_frame, width=27, state="readonly")
    tutores = obtener_tutores()
    combo_tutor["values"] = [f"{t['nombre']} {t['apellido']}" for t in tutores]
    combo_tutor.set(
        f"{r.get('tutor_nombre', '') or ''} {r.get('tutor_apellido', '') or ''}".strip())
    combo_tutor.grid(row=fila + 1, column=1, pady=5, sticky="ew")

    tk.Label(form_frame, text="Categoría", font=("Arial", 9, "bold"),
             anchor="e").grid(row=fila + 2, column=0, sticky="e", pady=5, padx=(0, 8))
    combo_cat = ttk.Combobox(form_frame, width=27, state="readonly")
    cats = obtener_categorias()
    combo_cat["values"] = [c["nombre"] for c in cats]
    combo_cat.set(r.get("categoria_nombre") or "")
    combo_cat.grid(row=fila + 2, column=1, pady=5, sticky="ew")

    # ── Botones ───────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=14)

    btn_guardar = tk.Button(pie, text="💾 Guardar", bg="#27ae60", fg="white",
                            font=("Arial", 10, "bold"), relief="groove",
                            padx=14, pady=6, cursor="hand2",
                            command=lambda: _guardar_edicion(
                                r["id"], entries_edit, entry_fecha,
                                combo_tutor, combo_cat, tutores, cats,
                                v, contenedor_tabla, vars_seleccion))
    btn_guardar.pack(side="left", padx=8)
    _aplicar_hover(btn_guardar, "#27ae60", "#1e8449")

    btn_cancelar = tk.Button(pie, text="✕ Cancelar", bg="#7f8c8d", fg="white",
                             font=("Arial", 10, "bold"), relief="groove",
                             padx=14, pady=6, cursor="hand2", command=v.destroy)
    btn_cancelar.pack(side="left", padx=8)
    _aplicar_hover(btn_cancelar, "#7f8c8d", "#626f70")


# ─────────────────────────────────────────────────────────────────────────
# RECARGAR CON FILTROS
# ─────────────────────────────────────────────────────────────────────────
def _recargar_alumnos(contenedor_tabla, entry_buscar, var_solo_activos,
                       var_al_dia, var_deudores, combo_filtro_tutor,
                       vars_seleccion):
    tutor_id   = None
    tutor_text = combo_filtro_tutor.get().strip()
    if tutor_text and tutor_text != "Todos":
        tutores  = obtener_tutores()
        tutor_id = next(
            (t["id"] for t in tutores
             if f"{t['nombre']} {t['apellido']}" == tutor_text), None)

    cargar_alumnos(
        contenedor_tabla,
        filtro        = entry_buscar.get(),
        solo_activos  = var_solo_activos.get(),
        solo_al_dia   = var_al_dia.get(),
        solo_deudores = var_deudores.get(),
        tutor_id      = tutor_id,
        vars_seleccion= vars_seleccion,
    )


# ─────────────────────────────────────────────────────────────────────────
# PANTALLA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────
def mostrar_alumnos(parent, volver_callback):
    limpiar_frame(parent)

    # ── Header ─────────────────────────────────
    header = tk.Frame(parent, bg="#2c3e50")
    header.pack(fill="x")
    btn_volver = tk.Button(header, text="< Volver", command=volver_callback,
                           bg="#2c3e50", fg="white", relief="flat",
                           font=("Arial", 10), padx=10, cursor="hand2")
    btn_volver.pack(side="left", pady=8, padx=10)
    btn_volver.bind("<Enter>", lambda e: btn_volver.config(bg="#1a252f"))
    btn_volver.bind("<Leave>", lambda e: btn_volver.config(bg="#2c3e50"))
    tk.Label(header, text="Gestión de Alumnos",
             font=("Arial", 14, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=10)

    # ── Formulario crear alumno (3 columnas) ──────────────────────────────
    form = tk.LabelFrame(parent, text="Crear nuevo alumno",
                         font=("Arial", 9, "bold"), padx=12, pady=10)
    form.pack(fill="x", padx=8, pady=(8, 4))

    campos_texto = [
        ("Nombre Completo *", "nombre_apellido"),
        ("DNI",               "dni"),
        ("Teléfono",          "telefono"),
        ("Email",             "email"),
        ("N° de Camiseta",    "numero_camisetas"),
    ]
    entries = {}
    for idx, (lbl, key) in enumerate(campos_texto):
        col_base = (idx % 3) * 2
        fila     = idx // 3
        tk.Label(form, text=lbl, anchor="e").grid(
            row=fila, column=col_base, sticky="e", padx=(10, 4), pady=4)
        entries[key] = tk.Entry(form, width=22)
        entries[key].grid(row=fila, column=col_base + 1, sticky="ew",
                          padx=(0, 10), pady=4)

    fila2 = 2
    tk.Label(form, text="Fecha de Nacimiento", anchor="e").grid(
        row=fila2, column=0, sticky="e", padx=(10, 4), pady=4)
    entry_fecha = _crear_entry_fecha(form, width=22)
    entry_fecha.grid(row=fila2, column=1, sticky="ew", padx=(0, 10), pady=4)

    tk.Label(form, text="Tutor *", anchor="e").grid(
        row=fila2, column=2, sticky="e", padx=(10, 4), pady=4)
    combo_tutor = ttk.Combobox(form, width=20, state="readonly")
    combo_tutor["values"] = [
        f"{t['nombre']} {t['apellido']}" for t in obtener_tutores()]
    combo_tutor.grid(row=fila2, column=3, sticky="ew", padx=(0, 10), pady=4)

    tk.Label(form, text="Categoría", anchor="e").grid(
        row=fila2, column=4, sticky="e", padx=(10, 4), pady=4)
    combo_cat = ttk.Combobox(form, width=20, state="readonly")
    combo_cat["values"] = [c["nombre"] for c in obtener_categorias()]
    combo_cat.grid(row=fila2, column=5, sticky="ew", padx=(0, 10), pady=4)

    for col in range(1, 6, 2):
        form.columnconfigure(col, weight=1)

    contenedor_tabla = tk.Frame(parent)
    vars_seleccion   = {}

    btn_crear = tk.Button(form, text="+ Crear Alumno", bg="#27ae60", fg="white",
                          font=("Arial", 10, "bold"), relief="groove",
                          pady=6, cursor="hand2",
                          command=lambda: crear_alumno_ui(
                              entries, entry_fecha, combo_tutor, combo_cat,
                              contenedor_tabla, vars_seleccion))
    btn_crear.grid(row=3, column=0, columnspan=6, pady=(8, 4), padx=10, sticky="ew")
    _aplicar_hover(btn_crear, "#27ae60", "#1e8449")

    # ── Banda: Filtros | Seleccionados ────────────────────────────────────
    banda = tk.Frame(parent)
    banda.pack(fill="x", padx=8, pady=(4, 4))
    banda.columnconfigure(0, weight=1)
    banda.columnconfigure(1, weight=1)

    # — Filtros —
    filtros_frame = tk.LabelFrame(banda, text="Búsqueda y Filtros",
                                  font=("Arial", 9, "bold"), padx=10, pady=6)
    filtros_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

    fila_f1 = tk.Frame(filtros_frame)
    fila_f1.pack(fill="x", pady=(0, 4))
    tk.Label(fila_f1, text="Buscar:").pack(side="left")
    entry_buscar = tk.Entry(fila_f1, width=28)
    entry_buscar.pack(side="left", padx=6)

    btn_buscar = tk.Button(fila_f1, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, pady=3, cursor="hand2",
                           command=lambda: _recargar_alumnos(
                               contenedor_tabla, entry_buscar, var_solo_activos,
                               var_al_dia, var_deudores, combo_filtro_tutor,
                               vars_seleccion))
    btn_buscar.pack(side="left", padx=(0, 4))
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    fila_f2 = tk.Frame(filtros_frame)
    fila_f2.pack(fill="x")
    tk.Label(fila_f2, text="Tutor:").pack(side="left")
    combo_filtro_tutor = ttk.Combobox(fila_f2, width=22, state="readonly")
    combo_filtro_tutor["values"] = (
        ["Todos"] + [f"{t['nombre']} {t['apellido']}"
                     for t in obtener_tutores()])
    combo_filtro_tutor.set("Todos")
    combo_filtro_tutor.pack(side="left", padx=6)

    var_solo_activos = tk.BooleanVar(value=False)
    var_al_dia       = tk.BooleanVar(value=False)
    var_deudores     = tk.BooleanVar(value=False)

    for texto, var in [("Solo activos", var_solo_activos),
                       ("Al día",       var_al_dia),
                       ("Deudores",     var_deudores)]:
        tk.Checkbutton(fila_f2, text=texto, variable=var,
                       command=lambda: _recargar_alumnos(
                           contenedor_tabla, entry_buscar, var_solo_activos,
                           var_al_dia, var_deudores, combo_filtro_tutor,
                           vars_seleccion)
                       ).pack(side="left", padx=4)

    # — Seleccionados —
    sel_frame = tk.LabelFrame(banda, text="Acciones sobre Seleccionados",
                               font=("Arial", 9, "bold"), padx=10, pady=6)
    sel_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

    BTN_SEL = ("Arial", 9, "bold")

    fila_s1 = tk.Frame(sel_frame)
    fila_s1.pack(fill="x", pady=(0, 4))

    btn_activar = tk.Button(fila_s1, text="✓ Activar", bg="#27ae60", fg="white",
                            font=BTN_SEL, relief="groove", padx=10, pady=4,
                            cursor="hand2",
                            command=lambda: activar_seleccionados(
                                vars_seleccion, contenedor_tabla))
    btn_activar.pack(side="left", padx=(0, 6))
    _aplicar_hover(btn_activar, "#27ae60", "#1e8449")

    btn_desact = tk.Button(fila_s1, text="✗ Desactivar", bg="#e67e22", fg="white",
                           font=BTN_SEL, relief="groove", padx=10, pady=4,
                           cursor="hand2",
                           command=lambda: desactivar_seleccionados(
                               vars_seleccion, contenedor_tabla))
    btn_desact.pack(side="left", padx=(0, 6))
    _aplicar_hover(btn_desact, "#e67e22", "#ca6f1e")

    btn_elim = tk.Button(fila_s1, text="🗑 Eliminar", bg="#e74c3c", fg="white",
                         font=BTN_SEL, relief="groove", padx=10, pady=4,
                         cursor="hand2",
                         command=lambda: eliminar_seleccionados(
                             vars_seleccion, contenedor_tabla))
    btn_elim.pack(side="left")
    _aplicar_hover(btn_elim, "#e74c3c", "#c0392b")

    fila_s2 = tk.Frame(sel_frame)
    fila_s2.pack(fill="x")

    btn_sel_todos = tk.Button(fila_s2, text="☑ Seleccionar todos",
                              bg="#5d6d7e", fg="white",
                              font=BTN_SEL, relief="groove", padx=10, pady=4,
                              cursor="hand2",
                              command=lambda: [v.set(True)
                                               for v in vars_seleccion.values()])
    btn_sel_todos.pack(side="left", padx=(0, 6))
    _aplicar_hover(btn_sel_todos, "#5d6d7e", "#4a5568")

    btn_desel_todos = tk.Button(fila_s2, text="☐ Deseleccionar todos",
                                bg="#95a5a6", fg="white",
                                font=BTN_SEL, relief="groove", padx=10, pady=4,
                                cursor="hand2",
                                command=lambda: [v.set(False)
                                                 for v in vars_seleccion.values()])
    btn_desel_todos.pack(side="left")
    _aplicar_hover(btn_desel_todos, "#95a5a6", "#7f8c8d")

    # ── Tabla (ancho completo, expande) ───────────────────────────────────
    contenedor_tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── Bindings ──────────────────────────────────────────────────────────
    entry_buscar.bind(
        "<Return>",
        lambda e: _recargar_alumnos(
            contenedor_tabla, entry_buscar, var_solo_activos,
            var_al_dia, var_deudores, combo_filtro_tutor, vars_seleccion))
    combo_filtro_tutor.bind(
        "<<ComboboxSelected>>",
        lambda e: _recargar_alumnos(
            contenedor_tabla, entry_buscar, var_solo_activos,
            var_al_dia, var_deudores, combo_filtro_tutor, vars_seleccion))

    cargar_alumnos(contenedor_tabla, vars_seleccion=vars_seleccion)