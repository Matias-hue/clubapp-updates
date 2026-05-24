import tkinter as tk
from tkinter import messagebox

from models.categorias import (
    crear_categoria, obtener_categorias, actualizar_categoria, eliminar_categoria,
    ajustar_anios_categorias, ANIO_MIN, ANIO_MAX, CUOTA_MAX, NOMBRE_MAX
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
def _solo_digitos(texto_nuevo):
    """Valida que el campo solo admita dígitos (para años)."""
    resultado = texto_nuevo == "" or texto_nuevo.isdigit()
    return resultado


def _solo_numericos(texto_nuevo):
    """Valida que el campo solo admita números con hasta 2 decimales (para cuota)."""
    resultado = True
    if texto_nuevo == "":
        resultado = True
    else:
        partes = texto_nuevo.split(".")
        if len(partes) > 2:
            resultado = False
        elif not all(p.isdigit() for p in partes if p != ""):
            resultado = False
    return resultado


def _validar_campos_ui(nombre, anio_inicio_str, anio_fin_str, valor_cuota_str):
    """
    Valida todos los campos desde la UI.
    Devuelve None si todo es válido, o un mensaje de error (str).
    """
    error = None

    if not nombre:
        error = "El nombre es obligatorio."
    elif len(nombre) > NOMBRE_MAX:
        error = f"El nombre no puede superar los {NOMBRE_MAX} caracteres."

    if error is None and anio_inicio_str:
        if not anio_inicio_str.isdigit():
            error = "El año de inicio debe ser un número entero positivo."
        else:
            anio = int(anio_inicio_str)
            if anio < ANIO_MIN or anio > ANIO_MAX:
                error = f"El año de inicio debe estar entre {ANIO_MIN} y {ANIO_MAX}."

    if error is None and anio_fin_str:
        if not anio_fin_str.isdigit():
            error = "El año de fin debe ser un número entero positivo."
        else:
            anio = int(anio_fin_str)
            if anio < ANIO_MIN or anio > ANIO_MAX:
                error = f"El año de fin debe estar entre {ANIO_MIN} y {ANIO_MAX}."

    if error is None and anio_inicio_str and anio_fin_str:
        if int(anio_inicio_str) > int(anio_fin_str):
            error = "El año de inicio no puede ser mayor al año de fin."

    if error is None and valor_cuota_str:
        try:
            cuota = float(valor_cuota_str)
            if cuota < 0:
                error = "El valor de cuota no puede ser negativo."
            elif cuota > CUOTA_MAX:
                error = f"El valor de cuota no puede superar ${CUOTA_MAX:,.2f}."
        except ValueError:
            error = "El valor de cuota debe ser un número válido."

    return error


def _parsear_campos(anio_inicio_str, anio_fin_str, valor_cuota_str):
    """Convierte los strings validados a sus tipos correctos."""
    anio_inicio = int(anio_inicio_str) if anio_inicio_str else None
    anio_fin = int(anio_fin_str) if anio_fin_str else None
    valor_cuota = float(valor_cuota_str) if valor_cuota_str else None
    return anio_inicio, anio_fin, valor_cuota


def _registrar_validacion(entry, tipo):
    """
    Registra la validación de entrada en tiempo real sobre un Entry.
    tipo: 'digitos' para años, 'numerico' para cuota.
    """
    if tipo == "digitos":
        vcmd = (entry.register(_solo_digitos), "%P")
    else:
        vcmd = (entry.register(_solo_numericos), "%P")
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
def cargar_categorias(contenedor_tabla, filtro=""):
    limpiar_frame(contenedor_tabla)

    outer, tabla_frame = crear_tabla_scroll(contenedor_tabla)
    outer.pack(fill="both", expand=True)

    rows = obtener_categorias(filtro)

    headers = ["Nombre", "Año Inicio", "Año Fin", "Valor Cuota", "Acciones"]
    agregar_header(tabla_frame, headers)

    if not rows:
        tk.Label(tabla_frame, text="No hay categorías registradas",
                 fg="gray", font=("Arial", 10), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
        return

    for i, r in enumerate(rows, start=1):
        bg    = fila_color(i)
        valor = f"${r['valor_cuota']:.2f}" if r.get("valor_cuota") is not None else "—"

        tk.Label(tabla_frame, text=r.get("nombre", ""), bg=bg, padx=8,
                 font=("Arial", 10, "bold")).grid(
            row=i, column=0, sticky="nsew", padx=1, pady=1)
        tk.Label(tabla_frame, text=r.get("anio_inicio") or "—",
                 bg=bg, padx=8).grid(
            row=i, column=1, sticky="nsew", padx=1, pady=1)
        tk.Label(tabla_frame, text=r.get("anio_fin") or "—",
                 bg=bg, padx=8).grid(
            row=i, column=2, sticky="nsew", padx=1, pady=1)
        tk.Label(tabla_frame, text=valor, bg=bg, padx=8).grid(
            row=i, column=3, sticky="nsew", padx=1, pady=1)

        acciones = tk.Frame(tabla_frame, bg=bg)
        acciones.grid(row=i, column=4, padx=8, pady=4, sticky="nsew")

        btn_editar = tk.Button(acciones, text="✎ Editar", bg="#27ae60", fg="white",
                               font=("Arial", 8, "bold"), relief="groove",
                               padx=6, pady=2, cursor="hand2",
                               command=lambda r=r: abrir_editar_categoria(
                                   r, contenedor_tabla))
        btn_editar.pack(side="left", padx=(0, 4))
        _aplicar_hover(btn_editar, "#27ae60", "#1e8449")

        btn_eliminar = tk.Button(acciones, text="🗑 Eliminar", bg="#e74c3c", fg="white",
                                 font=("Arial", 8, "bold"), relief="groove",
                                 padx=6, pady=2, cursor="hand2",
                                 command=lambda r=r: eliminar_categoria_ui(
                                     r["id"], r["nombre"], contenedor_tabla))
        btn_eliminar.pack(side="left")
        _aplicar_hover(btn_eliminar, "#e74c3c", "#c0392b")


# ==============================
# ELIMINAR
# ==============================
def eliminar_categoria_ui(categoria_id, nombre, contenedor_tabla):
    if messagebox.askyesno("Eliminar Categoría", f"¿Eliminar la categoría '{nombre}'?"):
        try:
            eliminar_categoria(categoria_id)
            cargar_categorias(contenedor_tabla)
            messagebox.showinfo("Éxito", "Categoría eliminada correctamente")
        except ValueError as e:
            messagebox.showwarning("No se puede eliminar", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ==============================
# CREAR CATEGORÍA
# ==============================
def crear_categoria_ui(entries, contenedor_tabla):
    nombre = entries["nombre"].get().strip()
    anio_inicio_str = entries["anio_inicio"].get().strip()
    anio_fin_str = entries["anio_fin"].get().strip()
    valor_cuota_str = entries["valor_cuota"].get().strip()

    error = _validar_campos_ui(nombre, anio_inicio_str, anio_fin_str, valor_cuota_str)
    if error is not None:
        messagebox.showwarning("Datos inválidos", error)
        return

    anio_inicio, anio_fin, valor_cuota = _parsear_campos(
        anio_inicio_str, anio_fin_str, valor_cuota_str
    )

    try:
        crear_categoria(nombre, anio_inicio, anio_fin, valor_cuota)
        for entry in entries.values():
            entry.delete(0, tk.END)
        cargar_categorias(contenedor_tabla)
        messagebox.showinfo("Éxito", "Categoría creada correctamente")
    except ValueError as e:
        messagebox.showwarning("Datos inválidos", str(e))
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo crear la categoría:\n{str(e)}")


# ==============================
# EDITAR CATEGORÍA (modal)
# ==============================
def abrir_editar_categoria(r, contenedor_tabla):
    ventana = tk.Toplevel()
    ventana.title("Editar Categoría")
    ventana.grab_set()
    ventana.resizable(False, False)

    ancho, alto = 440, 360
    ventana.update_idletasks()
    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    ventana.geometry(f"{ancho}x{alto}+{(sw - ancho) // 2}+{(sh - alto) // 2}")

    tk.Label(ventana, text=f"Editar: {r['nombre']}",
             font=("Arial", 12, "bold")).pack(pady=(14, 6), padx=16, anchor="w")

    datos_frame = tk.LabelFrame(ventana, text="Datos de la Categoría",
                                padx=16, pady=10)
    datos_frame.pack(fill="x", padx=16, pady=(0, 10))
    datos_frame.columnconfigure(1, weight=1)

    campos_edit = [
        ("Nombre *",        "nombre",      r.get("nombre", ""),             None),
        ("Año Inicio",      "anio_inicio", str(r.get("anio_inicio") or ""), "digitos"),
        ("Año Fin",         "anio_fin",    str(r.get("anio_fin") or ""),    "digitos"),
        ("Valor Cuota ($)", "valor_cuota", str(r.get("valor_cuota") or ""), "numerico"),
    ]
    entries_edit = {}
    for i, (label, key, valor, tipo_val) in enumerate(campos_edit):
        tk.Label(datos_frame, text=label, anchor="e").grid(
            row=i, column=0, sticky="e", pady=6, padx=(0, 10))
        e = tk.Entry(datos_frame, width=28)
        e.insert(0, valor)
        e.grid(row=i, column=1, sticky="ew", pady=6)
        if tipo_val is not None:
            _registrar_validacion(e, tipo_val)
        entries_edit[key] = e

    btn_frame = tk.Frame(ventana)
    btn_frame.pack(pady=10)

    btn_guardar = tk.Button(btn_frame, text="💾 Guardar", bg="#27ae60", fg="white",
                            font=("Arial", 10, "bold"), width=12,
                            relief="groove", cursor="hand2",
                            command=lambda: _guardar_edicion_categoria(
                                r["id"], entries_edit, ventana, contenedor_tabla))
    btn_guardar.pack(side="left", padx=10)
    _aplicar_hover(btn_guardar, "#27ae60", "#1e8449")

    btn_cancelar = tk.Button(btn_frame, text="✕ Cancelar", bg="#7f8c8d", fg="white",
                             font=("Arial", 10, "bold"), width=12,
                             relief="groove", cursor="hand2",
                             command=ventana.destroy)
    btn_cancelar.pack(side="left", padx=10)
    _aplicar_hover(btn_cancelar, "#7f8c8d", "#636e72")


def _guardar_edicion_categoria(categoria_id, entries_edit, ventana, contenedor_tabla):
    nombre = entries_edit["nombre"].get().strip()
    anio_inicio_str = entries_edit["anio_inicio"].get().strip()
    anio_fin_str = entries_edit["anio_fin"].get().strip()
    valor_cuota_str = entries_edit["valor_cuota"].get().strip()

    error = _validar_campos_ui(nombre, anio_inicio_str, anio_fin_str, valor_cuota_str)
    if error is not None:
        messagebox.showwarning("Datos inválidos", error)
        return

    anio_inicio, anio_fin, valor_cuota = _parsear_campos(
        anio_inicio_str, anio_fin_str, valor_cuota_str
    )

    try:
        actualizar_categoria(categoria_id, nombre, anio_inicio, anio_fin, valor_cuota)
        ventana.destroy()
        cargar_categorias(contenedor_tabla)
        messagebox.showinfo("Éxito", "Categoría actualizada correctamente")
    except ValueError as e:
        messagebox.showwarning("Datos inválidos", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))


# ==============================
# AJUSTAR AÑOS
# ==============================
def _ajustar_anios_ui(delta, contenedor_tabla):
    accion = "sumar 1 año" if delta > 0 else "restar 1 año"
    if messagebox.askyesno("Confirmar", f"¿{accion.capitalize()} a todas las categorías?"):
        try:
            ajustar_anios_categorias(delta)
            cargar_categorias(contenedor_tabla)
            messagebox.showinfo("Éxito", f"Se aplicó '{accion}' a todas las categorías.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ==============================
# PANTALLA PRINCIPAL
# ==============================
def mostrar_categorias(parent, volver_callback):
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
    tk.Label(header, text="Gestión de Categorías",
             font=("Arial", 14, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=10)

    # ── Formulario crear categoría (1 fila horizontal) ────────────────────
    form = tk.LabelFrame(parent, text="Crear nueva categoría",
                         font=("Arial", 9, "bold"), padx=12, pady=10)
    form.pack(fill="x", padx=8, pady=(8, 4))

    campos = [
        ("Nombre *",        "nombre",      None),
        ("Año Inicio",      "anio_inicio", "digitos"),
        ("Año Fin",         "anio_fin",    "digitos"),
        ("Valor Cuota ($)", "valor_cuota", "numerico"),
    ]
    entries = {}
    for col, (label_text, key, tipo_val) in enumerate(campos):
        tk.Label(form, text=label_text, font=("Arial", 9, "bold")).grid(
            row=0, column=col, sticky="w", padx=(10, 2), pady=(0, 4))
        e = tk.Entry(form, width=18)
        e.grid(row=1, column=col, sticky="ew", padx=(10, 2), pady=(0, 6))
        if tipo_val is not None:
            _registrar_validacion(e, tipo_val)
        entries[key] = e
        form.columnconfigure(col, weight=1)

    contenedor_tabla = tk.Frame(parent)

    btn_crear = tk.Button(form, text="+ Crear Categoría", bg="#27ae60", fg="white",
                          font=("Arial", 10, "bold"), relief="groove",
                          pady=6, cursor="hand2",
                          command=lambda: crear_categoria_ui(entries, contenedor_tabla))
    btn_crear.grid(row=2, column=0, columnspan=len(campos),
                   sticky="ew", padx=10, pady=(0, 4))
    _aplicar_hover(btn_crear, "#27ae60", "#1e8449")

    # ── Banda: Buscar (izq) | Ajuste global (der) ─────────────────────────
    banda = tk.Frame(parent)
    banda.pack(fill="x", padx=8, pady=(4, 4))

    # — Búsqueda —
    buscar_frame = tk.LabelFrame(banda, text="Búsqueda",
                                 font=("Arial", 9, "bold"), padx=10, pady=6)
    buscar_frame.pack(side="left", fill="y")

    tk.Label(buscar_frame, text="Buscar:").pack(side="left")
    entry_buscar = tk.Entry(buscar_frame, width=30)
    entry_buscar.pack(side="left", padx=6)

    btn_buscar = tk.Button(buscar_frame, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, pady=3, cursor="hand2",
                           command=lambda: cargar_categorias(
                               contenedor_tabla, entry_buscar.get()))
    btn_buscar.pack(side="left")
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    entry_buscar.bind("<Return>",
                      lambda e: cargar_categorias(contenedor_tabla, entry_buscar.get()))

    # — Ajuste global de años —
    anios_frame = tk.LabelFrame(banda, text="Ajuste global de años",
                                font=("Arial", 9, "bold"), padx=10, pady=6)
    anios_frame.pack(side="right", fill="y")

    tk.Label(anios_frame, text="Modificar años de todas las categorías:",
             font=("Arial", 9)).pack(side="left", padx=(0, 8))

    btn_mas = tk.Button(anios_frame, text="＋ 1 año a todas",
                        bg="#2980b9", fg="white",
                        font=("Arial", 9, "bold"), relief="groove",
                        padx=10, pady=4, cursor="hand2",
                        command=lambda: _ajustar_anios_ui(1, contenedor_tabla))
    btn_mas.pack(side="left", padx=(0, 6))
    _aplicar_hover(btn_mas, "#2980b9", "#1f618d")

    btn_menos = tk.Button(anios_frame, text="－ 1 año a todas",
                          bg="#e67e22", fg="white",
                          font=("Arial", 9, "bold"), relief="groove",
                          padx=10, pady=4, cursor="hand2",
                          command=lambda: _ajustar_anios_ui(-1, contenedor_tabla))
    btn_menos.pack(side="left")
    _aplicar_hover(btn_menos, "#e67e22", "#ca6f1e")

    # ── Tabla ─────────────────────────────────────────────────────────────
    contenedor_tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    cargar_categorias(contenedor_tabla)