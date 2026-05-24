# ui/listados_ui.py
import tkinter as tk
from tkinter import ttk

from models.listados import obtener_tutores_con_alumnos, obtener_categorias_con_alumnos
from database.db import get_connection


def limpiar_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    x  = (sw - ancho) // 2
    y  = (sh - alto)  // 2
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


# ============================================================
# TOGGLE EN DB
# ============================================================
def _toggle_activo_db(alumno_id, nuevo_valor):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE alumnos SET activo = ? WHERE id = ?",
            (nuevo_valor, alumno_id)
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# RECALCULAR CONTADORES DESDE LA LISTA LOCAL
# ============================================================
def _recalcular_contadores(registro):
    """
    Recalcula total_alumnos y alumnos_activos en base
    a la lista 'alumnos' que ya está en memoria.
    """
    alumnos        = registro.get("alumnos", [])
    total          = len(alumnos)
    activos        = sum(1 for a in alumnos if str(a.get("activo", "")) == "1")
    registro["total_alumnos"]   = total
    registro["alumnos_activos"] = activos


# ============================================================
# MODAL: TABLA DE ALUMNOS (reutilizable)
# ============================================================
def abrir_modal_alumnos(titulo, alumnos, columnas_extra, on_toggle_callback):
    modal = tk.Toplevel()
    modal.title(titulo)
    modal.grab_set()
    modal.resizable(True, True)
    modal.minsize(700, 400)

    ancho, alto = 980, 560
    modal.update_idletasks()
    sw = modal.winfo_screenwidth()
    sh = modal.winfo_screenheight()
    modal.geometry(f"{ancho}x{alto}+{(sw - ancho) // 2}+{(sh - alto) // 2}")

    # — Header —
    header = tk.Frame(modal, bg="#2c3e50")
    header.pack(fill="x")
    tk.Label(header, text=titulo, font=("Arial", 13, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=16, pady=10)

    # — Leyenda —
    leyenda = tk.Frame(modal, bg="#f4f6f7")
    leyenda.pack(fill="x", padx=16, pady=(8, 0))
    tk.Label(leyenda, text="●", fg="#27ae60",
             font=("Arial", 12), bg="#f4f6f7").pack(side="left", padx=(0, 2))
    tk.Label(leyenda, text="Activo  ",
             font=("Arial", 9), bg="#f4f6f7").pack(side="left")
    tk.Label(leyenda, text="●", fg="#e74c3c",
             font=("Arial", 12), bg="#f4f6f7").pack(side="left", padx=(0, 2))
    tk.Label(leyenda, text="Inactivo",
             font=("Arial", 9), bg="#f4f6f7").pack(side="left")

    # — Tabla —
    outer = tk.Frame(modal)
    outer.pack(fill="both", expand=True, padx=12, pady=8)

    canvas      = tk.Canvas(outer, highlightthickness=0)
    sc_y        = ttk.Scrollbar(outer, orient="vertical",   command=canvas.yview)
    sc_x        = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
    tabla_frame = tk.Frame(canvas)

    tabla_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=tabla_frame, anchor="nw")
    canvas.configure(yscrollcommand=sc_y.set, xscrollcommand=sc_x.set)

    sc_y.pack(side="right",  fill="y")
    sc_x.pack(side="bottom", fill="x")
    canvas.pack(side="left", fill="both", expand=True)

    def _scroll(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",  _scroll))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    headers_base  = ["Nombre", "DNI", "F. Nac.", "Teléfono", "Email", "Camiseta"]
    headers_extra = [h for h, _ in (columnas_extra or [])]
    keys_extra    = [k for _, k in (columnas_extra or [])]
    headers_full  = headers_base + headers_extra + ["Estado", "Acción"]

    def _dibujar_headers():
        for col, h in enumerate(headers_full):
            tk.Label(
                tabla_frame, text=h,
                font=("Arial", 9, "bold"),
                bg="#2c3e50", fg="white",
                padx=8, pady=6
            ).grid(row=0, column=col, sticky="nsew", padx=1, pady=(0, 2))

    def _dibujar_tabla():
        for w in tabla_frame.winfo_children():
            w.destroy()
        _dibujar_headers()

        if not alumnos:
            tk.Label(
                tabla_frame,
                text="Sin alumnos registrados",
                fg="gray", font=("Arial", 10), pady=20
            ).grid(row=1, column=0, columnspan=len(headers_full))
            return

        for i, alumno in enumerate(alumnos, start=1):
            es_activo = str(alumno.get("activo", "")) == "1"
            bg        = ("#f0fff4" if i % 2 == 0 else "#e8f8f0") if es_activo \
                   else ("#fff5f5" if i % 2 == 0 else "#ffeaea")
            color_dot = "#27ae60" if es_activo else "#e74c3c"

            valores = [
                alumno.get("nombre_apellido",  ""),
                alumno.get("dni")              or "—",
                alumno.get("fecha_nacimiento") or "—",
                alumno.get("telefono")         or "—",
                alumno.get("email")            or "—",
                alumno.get("numero_camisetas") or "—",
            ] + [alumno.get(k) or "—" for k in keys_extra]

            for col, val in enumerate(valores):
                tk.Label(
                    tabla_frame, text=val, bg=bg,
                    font=("Arial", 9), padx=6, pady=4
                ).grid(row=i, column=col, sticky="nsew", padx=1, pady=1)

            col_estado = len(valores)
            tk.Label(
                tabla_frame,
                text="● Activo" if es_activo else "● Inactivo",
                fg=color_dot, bg=bg,
                font=("Arial", 9, "bold"), padx=6
            ).grid(row=i, column=col_estado, sticky="w", padx=4)

            nuevo_val  = 0 if es_activo else 1
            label_btn  = "Desactivar" if es_activo else "Activar"
            color_btn  = "#e67e22"    if es_activo else "#27ae60"
            color_hover = "#ca6f1e"   if es_activo else "#1e8449"

            def _hacer_toggle(aid=alumno["id"], nv=nuevo_val):
                _toggle_activo_db(aid, nv)
                for a in alumnos:
                    if a["id"] == aid:
                        a["activo"] = nv
                        break
                on_toggle_callback()
                _dibujar_tabla()

            btn = tk.Button(
                tabla_frame,
                text=label_btn, bg=color_btn, fg="white",
                font=("Arial", 8, "bold"), width=9,
                relief="groove", cursor="hand2",
                command=_hacer_toggle
            )
            btn.grid(row=i, column=col_estado + 1, padx=6, pady=2)
            btn.bind("<Enter>", lambda e, b=btn, c=color_hover: b.config(bg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=color_btn:   b.config(bg=c))

    _dibujar_tabla()

    # — Pie —
    pie = tk.Frame(modal, bg="#f4f6f7")
    pie.pack(fill="x", pady=6)
    tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
              font=("Arial", 10, "bold"), width=12,
              relief="groove", cursor="hand2",
              command=modal.destroy).pack(pady=6)

    return modal


# ============================================================
# UTILIDAD: lista scrolleable de tarjetas verticales
# ============================================================
def _crear_scroll_vertical(parent, bg="#f4f6f8"):
    outer = tk.Frame(parent)
    outer.pack(fill="both", expand=True, padx=20, pady=8)

    canvas      = tk.Canvas(outer, bg=bg, highlightthickness=0)
    scrollbar   = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    lista_frame = tk.Frame(canvas, bg=bg)

    lista_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=lista_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def _scroll(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",  _scroll))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return canvas, lista_frame


# ============================================================
# PANTALLA: TUTORES CON ALUMNOS
# ============================================================
def mostrar_tutores_con_alumnos(parent, volver_callback):
    limpiar_frame(parent)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(parent, bg="#2c3e50")
    header.pack(fill="x")
    btn_volver = tk.Button(header, text="< Volver", command=volver_callback,
                           bg="#2c3e50", fg="white", relief="flat",
                           font=("Arial", 10), padx=10, cursor="hand2")
    btn_volver.pack(side="left", pady=8, padx=10)
    btn_volver.bind("<Enter>", lambda e: btn_volver.config(bg="#1a252f"))
    btn_volver.bind("<Leave>", lambda e: btn_volver.config(bg="#2c3e50"))
    tk.Label(header, text="Tutores con Alumnos",
             font=("Arial", 14, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=10)

    datos = obtener_tutores_con_alumnos()

    # ── Búsqueda ──────────────────────────────────────────────────────────
    search_frame = tk.Frame(parent, bg="#f4f6f7")
    search_frame.pack(fill="x", padx=20, pady=(10, 4))
    tk.Label(search_frame, text="Buscar tutor:",
             bg="#f4f6f7", font=("Arial", 9)).pack(side="left")
    entry_buscar = tk.Entry(search_frame, width=35, font=("Arial", 9))
    entry_buscar.pack(side="left", padx=8)
    btn_buscar = tk.Button(search_frame, text="Buscar",
                           bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, pady=3, cursor="hand2",
                           command=lambda: renderizar(entry_buscar.get()))
    btn_buscar.pack(side="left")
    btn_buscar.bind("<Enter>", lambda e: btn_buscar.config(bg="#1a252f"))
    btn_buscar.bind("<Leave>", lambda e: btn_buscar.config(bg="#2c3e50"))
    entry_buscar.bind("<Return>", lambda e: renderizar(entry_buscar.get()))

    canvas, lista_frame = _crear_scroll_vertical(parent)

    def renderizar(filtro=""):
        limpiar_frame(lista_frame)
        filtro_lower = filtro.lower()

        visible = [
            t for t in datos
            if filtro_lower in t["nombre"].lower()
            or filtro_lower in t["apellido"].lower()
        ]

        if not visible:
            tk.Label(lista_frame, text="Sin resultados",
                     bg="#f4f6f8", font=("Arial", 11), fg="gray"
                     ).pack(pady=30)
            return

        for tutor in visible:
            activos   = tutor.get("alumnos_activos") or 0
            total     = tutor.get("total_alumnos")   or 0
            inactivos = total - activos

            card = tk.Frame(lista_frame, bg="white", bd=1, relief="solid")
            card.pack(fill="x", pady=5, padx=4)

            tk.Frame(card, bg="#2c3e50", width=6).pack(side="left", fill="y")

            info = tk.Frame(card, bg="white")
            info.pack(side="left", fill="both", expand=True, padx=14, pady=10)

            tk.Label(info,
                     text=f"👤  {tutor['nombre']} {tutor['apellido']}",
                     font=("Arial", 12, "bold"), bg="white",
                     fg="#2c3e50").pack(anchor="w")

            detalles = []
            if tutor.get("telefono"):
                detalles.append(f"📞 {tutor['telefono']}")
            if tutor.get("domicilio"):
                detalles.append(f"🏠 {tutor['domicilio']}")
            if detalles:
                tk.Label(info, text="   ".join(detalles),
                         font=("Arial", 9), fg="#555", bg="white"
                         ).pack(anchor="w")

            badge_row = tk.Frame(info, bg="white")
            badge_row.pack(anchor="w", pady=(6, 0))

            for texto, bg_b in [
                (f"{total} alumno{'s' if total != 1 else ''}",         "#2c3e50"),
                (f"✅ {activos} activo{'s' if activos != 1 else ''}",  "#27ae60"),
            ]:
                tk.Label(badge_row, text=f"  {texto}  ",
                         bg=bg_b, fg="white", font=("Arial", 9, "bold"),
                         padx=3, pady=2, relief="groove"
                         ).pack(side="left", padx=2)

            if inactivos > 0:
                tk.Label(badge_row,
                         text=f"  ⛔ {inactivos} inactivo{'s' if inactivos != 1 else ''}  ",
                         bg="#e74c3c", fg="white", font=("Arial", 9, "bold"),
                         padx=3, pady=2, relief="groove"
                         ).pack(side="left", padx=2)

            btn_frame = tk.Frame(card, bg="white")
            btn_frame.pack(side="right", padx=16, pady=10)

            snap = tutor["alumnos"]

            def _on_toggle(t=tutor, f=filtro):
                _recalcular_contadores(t)
                renderizar(f)

            btn_ver = tk.Button(
                btn_frame,
                text="Ver alumnos ▸",
                bg="#2980b9", fg="white",
                font=("Arial", 10, "bold"),
                width=14, height=2,
                relief="groove", cursor="hand2",
                command=lambda titulo_modal=f"{tutor['nombre']} {tutor['apellido']}",
                               al=snap, cb=_on_toggle:
                    abrir_modal_alumnos(
                        f"Alumnos de {titulo_modal}",
                        al,
                        columnas_extra=[("Categoría", "categoria_nombre")],
                        on_toggle_callback=cb
                    )
            )
            btn_ver.pack()
            btn_ver.bind("<Enter>", lambda e, b=btn_ver: b.config(bg="#1f618d"))
            btn_ver.bind("<Leave>", lambda e, b=btn_ver: b.config(bg="#2980b9"))

    renderizar()


# ============================================================
# PANTALLA: CATEGORÍAS CON ALUMNOS
# ============================================================
def mostrar_categorias_con_alumnos(parent, volver_callback):
    limpiar_frame(parent)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(parent, bg="#2c3e50")
    header.pack(fill="x")
    btn_volver = tk.Button(header, text="< Volver", command=volver_callback,
                           bg="#2c3e50", fg="white", relief="flat",
                           font=("Arial", 10), padx=10, cursor="hand2")
    btn_volver.pack(side="left", pady=8, padx=10)
    btn_volver.bind("<Enter>", lambda e: btn_volver.config(bg="#1a252f"))
    btn_volver.bind("<Leave>", lambda e: btn_volver.config(bg="#2c3e50"))
    tk.Label(header, text="Categorías con Alumnos",
             font=("Arial", 14, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=10)

    datos = obtener_categorias_con_alumnos()

    canvas, lista_frame = _crear_scroll_vertical(parent)

    COLORES = ["#2980b9", "#8e44ad", "#16a085", "#d35400", "#c0392b", "#27ae60"]
    HOVERS  = ["#1f618d", "#6c3483", "#117a65", "#a04000", "#922b21", "#1e8449"]

    def renderizar():
        limpiar_frame(lista_frame)

        for idx, cat in enumerate(datos):
            activos   = cat.get("alumnos_activos") or 0
            total     = cat.get("total_alumnos")   or 0
            inactivos = total - activos
            color     = COLORES[idx % len(COLORES)]
            hover     = HOVERS[idx % len(HOVERS)]

            card = tk.Frame(lista_frame, bg="white", bd=1, relief="solid")
            card.pack(fill="x", pady=5, padx=4)

            tk.Frame(card, bg=color, width=8).pack(side="left", fill="y")

            body = tk.Frame(card, bg="white")
            body.pack(side="left", fill="both", expand=True, padx=16, pady=10)

            top_row = tk.Frame(body, bg="white")
            top_row.pack(fill="x")

            tk.Label(top_row,
                     text=f"⚽  Categoría {cat['nombre']}",
                     font=("Arial", 13, "bold"), bg="white", fg=color
                     ).pack(side="left")

            rango = f"Nacidos {cat.get('anio_inicio', '?')} – {cat.get('anio_fin', '?')}"
            cuota = f"Cuota: ${cat.get('valor_cuota', 0):.0f}"
            tk.Label(top_row,
                     text=f"   {rango}   |   {cuota}",
                     font=("Arial", 9), fg="#666", bg="white"
                     ).pack(side="left", padx=10)

            badge_row = tk.Frame(body, bg="white")
            badge_row.pack(anchor="w", pady=(6, 0))

            for texto, bg_b in [
                (f"{total} total",                                            "#7f8c8d"),
                (f"✅ {activos} activo{'s' if activos != 1 else ''}",        "#27ae60"),
                (f"⛔ {inactivos} inactivo{'s' if inactivos != 1 else ''}",  "#e74c3c"),
            ]:
                tk.Label(badge_row, text=f"  {texto}  ",
                         bg=bg_b, fg="white", font=("Arial", 9, "bold"),
                         padx=3, pady=2, relief="groove"
                         ).pack(side="left", padx=2)

            btn_frame = tk.Frame(card, bg="white")
            btn_frame.pack(side="right", padx=16, pady=10)

            snap = cat["alumnos"]

            def _on_toggle(c=cat):
                _recalcular_contadores(c)
                renderizar()

            btn_ver = tk.Button(
                btn_frame,
                text="Ver alumnos ▸",
                bg=color, fg="white",
                font=("Arial", 10, "bold"),
                width=14, height=2,
                relief="groove", cursor="hand2",
                command=lambda titulo_modal=cat["nombre"],
                               al=snap, cb=_on_toggle:
                    abrir_modal_alumnos(
                        f"Alumnos — Categoría {titulo_modal}",
                        al,
                        columnas_extra=[
                            ("Tutor",      "tutor_nombre"),
                            ("Tel. Tutor", "tutor_telefono"),
                        ],
                        on_toggle_callback=cb
                    )
            )
            btn_ver.pack()
            btn_ver.bind("<Enter>", lambda e, b=btn_ver, h=hover: b.config(bg=h))
            btn_ver.bind("<Leave>", lambda e, b=btn_ver, c=color: b.config(bg=c))

    renderizar()