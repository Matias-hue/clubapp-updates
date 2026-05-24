import tkinter as tk
from tkinter import messagebox

from models.tutores import (
    crear_tutor, obtener_tutores, eliminar_tutor, actualizar_tutor,
    NOMBRE_MAX, APELLIDO_MAX, TELEFONO_MAX, DOMICILIO_MAX
)
from ui.tabla_scroll import crear_tabla_scroll, agregar_header, fila_color


# ==============================
# HELPERS
# ==============================
def _aplicar_hover(btn, color_normal, color_hover):
    btn.bind("<Enter>", lambda e: btn.config(bg=color_hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=color_normal))


# ==============================
# HELPERS DE VALIDACIÓN (UI)
# ==============================
def _validar_campos_ui(nombre, apellido, telefono, domicilio):
    """
    Valida todos los campos desde la UI.
    Devuelve None si todo es válido, o un mensaje de error (str).
    """
    error = None

    if not nombre:
        error = "El nombre es obligatorio."
    elif len(nombre) > NOMBRE_MAX:
        error = f"El nombre no puede superar los {NOMBRE_MAX} caracteres."

    if error is None and not apellido:
        error = "El apellido es obligatorio."
    elif error is None and len(apellido) > APELLIDO_MAX:
        error = f"El apellido no puede superar los {APELLIDO_MAX} caracteres."

    if error is None and telefono:
        if len(telefono) > TELEFONO_MAX:
            error = f"El teléfono no puede superar los {TELEFONO_MAX} caracteres."
        elif not telefono.lstrip("+").replace("-", "").replace(" ", "").isdigit():
            error = "El teléfono solo puede contener números, espacios, guiones y '+'."

    if error is None and domicilio and len(domicilio) > DOMICILIO_MAX:
        error = f"El domicilio no puede superar los {DOMICILIO_MAX} caracteres."

    return error


def _solo_telefono(texto_nuevo):
    """Permite dígitos, espacios, guiones y '+' solo al inicio."""
    resultado = True
    if texto_nuevo == "":
        resultado = True
    else:
        permitidos = set("0123456789 +-")
        if not all(c in permitidos for c in texto_nuevo):
            resultado = False
        elif texto_nuevo.count("+") > 1:
            resultado = False
        elif "+" in texto_nuevo and not texto_nuevo.startswith("+"):
            resultado = False
    return resultado


def _registrar_validacion_telefono(entry):
    vcmd = (entry.register(_solo_telefono), "%P")
    entry.config(validate="key", validatecommand=vcmd)


# ==============================
# LIMPIAR FRAME
# ==============================
def limpiar_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()


# ==============================
# CARGAR TABLA (sin columna id)
# ==============================
def cargar_tutores(contenedor_tabla, filtro=""):
    limpiar_frame(contenedor_tabla)

    outer, tabla_frame = crear_tabla_scroll(contenedor_tabla)
    outer.pack(fill="both", expand=True)

    rows = obtener_tutores(filtro)

    headers = ["Nombre", "Apellido", "Teléfono", "Domicilio", "Acciones"]
    agregar_header(tabla_frame, headers)

    if not rows:
        tk.Label(tabla_frame, text="No hay tutores registrados",
                 fg="gray", font=("Arial", 10), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
        return

    for i, r in enumerate(rows, start=1):
        bg = fila_color(i)

        tk.Label(tabla_frame, text=r.get("nombre", ""),
                 bg=bg, padx=8, font=("Arial", 10, "bold")).grid(
            row=i, column=0, sticky="nsew", padx=1, pady=1)
        tk.Label(tabla_frame, text=r.get("apellido", ""),
                 bg=bg, padx=8, font=("Arial", 10, "bold")).grid(
            row=i, column=1, sticky="nsew", padx=1, pady=1)
        tk.Label(tabla_frame, text=r.get("telefono") or "—",
                 bg=bg, padx=8).grid(
            row=i, column=2, sticky="nsew", padx=1, pady=1)
        tk.Label(tabla_frame, text=r.get("domicilio") or "—",
                 bg=bg, padx=8).grid(
            row=i, column=3, sticky="nsew", padx=1, pady=1)

        acciones = tk.Frame(tabla_frame, bg=bg)
        acciones.grid(row=i, column=4, padx=8, pady=4, sticky="nsew")

        btn_editar = tk.Button(acciones, text="✎ Editar", bg="#27ae60", fg="white",
                               font=("Arial", 8, "bold"), relief="groove",
                               padx=6, pady=2, cursor="hand2",
                               command=lambda r=r: abrir_editar(r, contenedor_tabla))
        btn_editar.pack(side="left", padx=(0, 4))
        _aplicar_hover(btn_editar, "#27ae60", "#1e8449")

        btn_eliminar = tk.Button(acciones, text="🗑 Eliminar", bg="#e74c3c", fg="white",
                                 font=("Arial", 8, "bold"), relief="groove",
                                 padx=6, pady=2, cursor="hand2",
                                 command=lambda r=r: eliminar_tutor_ui(
                                     r["id"], r["nombre"], r["apellido"],
                                     contenedor_tabla))
        btn_eliminar.pack(side="left")
        _aplicar_hover(btn_eliminar, "#e74c3c", "#c0392b")


# ==============================
# ELIMINAR TUTOR
# ==============================
def eliminar_tutor_ui(tutor_id, nombre, apellido, contenedor_tabla):
    if messagebox.askyesno("Confirmar eliminación", f"¿Eliminar a {nombre} {apellido}?"):
        try:
            eliminar_tutor(tutor_id)
            cargar_tutores(contenedor_tabla)
        except ValueError as e:
            messagebox.showwarning("No se puede eliminar", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ==============================
# CREAR TUTOR
# ==============================
def crear_tutor_ui(entries, contenedor_tabla):
    nombre = entries["nombre"].get().strip()
    apellido = entries["apellido"].get().strip()
    telefono = entries["telefono"].get().strip()
    domicilio = entries["domicilio"].get().strip()

    error = _validar_campos_ui(nombre, apellido, telefono, domicilio)
    if error is not None:
        messagebox.showwarning("Datos inválidos", error)
        return

    try:
        crear_tutor(nombre, apellido, telefono or None, domicilio or None)
        for entry in entries.values():
            entry.delete(0, tk.END)
        cargar_tutores(contenedor_tabla)
        messagebox.showinfo("Éxito", "Tutor creado correctamente")
    except ValueError as e:
        messagebox.showwarning("Datos inválidos", str(e))
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo crear el tutor:\n{str(e)}")


# ==============================
# EDITAR TUTOR (modal)
# ==============================
def abrir_editar(r, contenedor_tabla):
    ventana = tk.Toplevel()
    ventana.title("Editar Tutor")
    ventana.grab_set()
    ventana.resizable(False, False)

    ancho, alto = 440, 340
    ventana.update_idletasks()
    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    ventana.geometry(f"{ancho}x{alto}+{(sw - ancho) // 2}+{(sh - alto) // 2}")

    tk.Label(ventana, text=f"Editar: {r['nombre']} {r['apellido']}",
             font=("Arial", 12, "bold")).pack(pady=(14, 6), padx=16, anchor="w")

    datos_frame = tk.LabelFrame(ventana, text="Datos del Tutor",
                                padx=16, pady=10)
    datos_frame.pack(fill="x", padx=16, pady=(0, 10))
    datos_frame.columnconfigure(1, weight=1)

    campos_edit = [
        ("Nombre *",   "nombre",    r.get("nombre", ""),          False),
        ("Apellido *", "apellido",  r.get("apellido", ""),        False),
        ("Teléfono",   "telefono",  r.get("telefono", "") or "",  True),
        ("Domicilio",  "domicilio", r.get("domicilio", "") or "", False),
    ]
    entries_edit = {}
    for i, (label, key, valor, es_tel) in enumerate(campos_edit):
        tk.Label(datos_frame, text=label, anchor="e").grid(
            row=i, column=0, sticky="e", pady=6, padx=(0, 10))
        e = tk.Entry(datos_frame, width=28)
        e.insert(0, valor)
        e.grid(row=i, column=1, sticky="ew", pady=6)
        if es_tel:
            _registrar_validacion_telefono(e)
        entries_edit[key] = e

    btn_frame = tk.Frame(ventana)
    btn_frame.pack(pady=10)

    btn_guardar = tk.Button(btn_frame, text="💾 Guardar", bg="#27ae60", fg="white",
                            font=("Arial", 10, "bold"), width=12,
                            relief="groove", cursor="hand2",
                            command=lambda: _guardar_edicion(
                                r["id"], entries_edit, ventana, contenedor_tabla))
    btn_guardar.pack(side="left", padx=10)
    _aplicar_hover(btn_guardar, "#27ae60", "#1e8449")

    btn_cancelar = tk.Button(btn_frame, text="✕ Cancelar", bg="#7f8c8d", fg="white",
                             font=("Arial", 10, "bold"), width=12,
                             relief="groove", cursor="hand2",
                             command=ventana.destroy)
    btn_cancelar.pack(side="left", padx=10)
    _aplicar_hover(btn_cancelar, "#7f8c8d", "#636e72")


def _guardar_edicion(tutor_id, entries_edit, ventana, contenedor_tabla):
    nombre = entries_edit["nombre"].get().strip()
    apellido = entries_edit["apellido"].get().strip()
    telefono = entries_edit["telefono"].get().strip()
    domicilio = entries_edit["domicilio"].get().strip()

    error = _validar_campos_ui(nombre, apellido, telefono, domicilio)
    if error is not None:
        messagebox.showwarning("Datos inválidos", error)
        return

    try:
        actualizar_tutor(
            tutor_id, nombre, apellido,
            telefono or None,
            domicilio or None,
        )
        ventana.destroy()
        cargar_tutores(contenedor_tabla)
        messagebox.showinfo("Éxito", "Tutor actualizado correctamente")
    except ValueError as e:
        messagebox.showwarning("Datos inválidos", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))


# ==============================
# PANTALLA PRINCIPAL
# ==============================
def mostrar_tutores(parent, volver_callback):
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
    tk.Label(header, text="Gestión de Tutores",
             font=("Arial", 14, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=10)

    # ── Formulario crear tutor (1 fila horizontal) ────────────────────────
    form = tk.LabelFrame(parent, text="Crear nuevo tutor",
                         font=("Arial", 9, "bold"), padx=12, pady=10)
    form.pack(fill="x", padx=8, pady=(8, 4))

    campos = [
        ("Nombre *",   "nombre",    False),
        ("Apellido *", "apellido",  False),
        ("Teléfono",   "telefono",  True),
        ("Domicilio",  "domicilio", False),
    ]
    entries = {}
    for col, (label_text, key, es_tel) in enumerate(campos):
        tk.Label(form, text=label_text, font=("Arial", 9, "bold")).grid(
            row=0, column=col, sticky="w", padx=(10, 2), pady=(0, 4))
        e = tk.Entry(form, width=20)
        e.grid(row=1, column=col, sticky="ew", padx=(10, 2), pady=(0, 6))
        if es_tel:
            _registrar_validacion_telefono(e)
        entries[key] = e
        form.columnconfigure(col, weight=1)

    contenedor_tabla = tk.Frame(parent)

    btn_crear = tk.Button(form, text="+ Crear Tutor", bg="#27ae60", fg="white",
                          font=("Arial", 10, "bold"), relief="groove",
                          pady=6, cursor="hand2",
                          command=lambda: crear_tutor_ui(entries, contenedor_tabla))
    btn_crear.grid(row=2, column=0, columnspan=len(campos),
                   sticky="ew", padx=10, pady=(0, 4))
    _aplicar_hover(btn_crear, "#27ae60", "#1e8449")

    # ── Banda: Búsqueda ───────────────────────────────────────────────────
    banda = tk.Frame(parent)
    banda.pack(fill="x", padx=8, pady=(4, 4))

    buscar_frame = tk.LabelFrame(banda, text="Búsqueda",
                                 font=("Arial", 9, "bold"), padx=10, pady=6)
    buscar_frame.pack(side="left", fill="y")

    tk.Label(buscar_frame, text="Buscar tutor:").pack(side="left")
    entry_buscar = tk.Entry(buscar_frame, width=30)
    entry_buscar.pack(side="left", padx=6)

    btn_buscar = tk.Button(buscar_frame, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, pady=3, cursor="hand2",
                           command=lambda: cargar_tutores(
                               contenedor_tabla, entry_buscar.get()))
    btn_buscar.pack(side="left")
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    entry_buscar.bind("<Return>",
                      lambda e: cargar_tutores(contenedor_tabla, entry_buscar.get()))

    # ── Tabla ─────────────────────────────────────────────────────────────
    contenedor_tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    cargar_tutores(contenedor_tabla)