import os
import shutil
import subprocess
import tempfile
import tkinter as tk
from datetime import datetime
import locale

from tkinter import messagebox

from ui.tutores_ui      import mostrar_tutores
from ui.alumnos_ui      import mostrar_alumnos
from ui.categorias_ui   import mostrar_categorias
from ui.listados_ui     import mostrar_tutores_con_alumnos, mostrar_categorias_con_alumnos
from ui.recibos_ui      import mostrar_recibos, mostrar_pago_cuotas, mostrar_pagos_varios
from models.stats       import obtener_stats
from utils.rutas        import resource_path
from utils.updater      import hay_actualizacion, descargar_actualizacion
from utils.backup       import (
    hacer_backup, restaurar_backup,
    listar_backups, abrir_carpeta_backups, formatear_nombre_backup
)


# ══════════════════════════════════════════════
# CONFIGURACIÓN INICIAL
# ══════════════════════════════════════════════
try:
    locale.setlocale(locale.LC_TIME, 'es_AR.UTF-8')
except Exception:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Argentina.1252')
    except Exception:
        pass


# ══════════════════════════════════════════════
# HELPERS DE UI
# ══════════════════════════════════════════════
def centrar_ventana(ventana, ancho=None, alto=None):
    """
    Centra cualquier ventana (Tk o Toplevel).
    Si ancho/alto son None usa el tamaño actual de la ventana.
    """
    ventana.update_idletasks()
    ancho_v = ancho or ventana.winfo_width()
    alto_v  = alto  or ventana.winfo_height()
    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    x  = (sw - ancho_v) // 2
    y  = (sh - alto_v)  // 2
    ventana.geometry(f"{ancho_v}x{alto_v}+{x}+{y}")


def limpiar_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def actualizar_hora(label_hora):
    ahora = datetime.now()
    label_hora.config(text=ahora.strftime("%H:%M"))
    label_hora.after(15000, actualizar_hora, label_hora)


def construir_stat_card(parent, emoji, texto, numero, color, columna, comando):
    """Tarjeta de estadística clickeable que navega a su pantalla."""
    card = tk.Frame(parent, bg="white", relief="solid", bd=1, height=150,
                    cursor="hand2")
    card.grid(row=0, column=columna, padx=12, pady=8, sticky="nsew")
    card.pack_propagate(False)

    icon_frame = tk.Frame(card, bg=color, width=68, height=68)
    icon_frame.pack(pady=(18, 10))
    icon_frame.pack_propagate(False)
    lbl_icon = tk.Label(icon_frame, text=emoji, font=("Arial", 30),
                        bg=color, fg="white", cursor="hand2")
    lbl_icon.pack(expand=True)

    line = tk.Frame(card, bg="white")
    line.pack(pady=8)
    lbl_txt = tk.Label(line, text=texto, font=("Arial", 13, "bold"),
                       bg="white", fg="#2c3e50", cursor="hand2")
    lbl_txt.pack(side="left")
    lbl_num = tk.Label(line, text=str(numero), font=("Arial", 13, "bold"),
                       bg="white", fg=color, cursor="hand2")
    lbl_num.pack(side="left", padx=(3, 0))

    # Vincular click a todos los widgets de la tarjeta
    for widget in [card, icon_frame, lbl_icon, line, lbl_txt, lbl_num]:
        widget.bind("<Button-1>", lambda e, cmd=comando: cmd())

    # Hover sutil
    def _on_enter(e):
        card.config(bg="#f0f2f5")
        line.config(bg="#f0f2f5")
        lbl_txt.config(bg="#f0f2f5")
        lbl_num.config(bg="#f0f2f5")

    def _on_leave(e):
        card.config(bg="white")
        line.config(bg="white")
        lbl_txt.config(bg="white")
        lbl_num.config(bg="white")

    for widget in [card, icon_frame, lbl_icon, line, lbl_txt, lbl_num]:
        widget.bind("<Enter>", _on_enter)
        widget.bind("<Leave>", _on_leave)


def construir_boton_sidebar(parent, icon, text, content,
                             botones_acciones, botones_listados):
    btn = tk.Button(
        parent,
        text=f"  {icon}   {text}",
        bg="#263a5f", fg="white", relief="flat",
        font=("Arial", 10), anchor="w", padx=16, pady=5,
        cursor="hand2",
        command=lambda t=text: mostrar_pantalla(
            t, content,
            lambda: mostrar_dashboard(content, botones_acciones, botones_listados)
        )
    )
    btn.pack(fill="x", padx=10, pady=1)
    btn.bind("<Enter>", lambda e: btn.config(bg="#3b5280"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#263a5f"))


def construir_boton_dashboard(parent, texto, content,
                               botones_acciones, botones_listados):
    btn = tk.Button(
        parent,
        text=texto,
        font=("Arial", 11, "bold"),
        bg="#f0f2f5", fg="#2c3e50", activebackground="#e2e6ea",
        relief="solid", bd=1, height=2, anchor="w", padx=20,
        cursor="hand2",
        command=lambda t=texto: mostrar_pantalla(
            t, content,
            lambda: mostrar_dashboard(content, botones_acciones, botones_listados)
        )
    )
    btn.pack(fill="x", pady=6, padx=18)
    btn.bind("<Enter>", lambda e: btn.config(bg="#dde3ea", fg="#1e2a44"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#f0f2f5", fg="#2c3e50"))


# ══════════════════════════════════════════════
# BACKUPS
# ══════════════════════════════════════════════
def abrir_ventana_backups(root):
    v = tk.Toplevel()
    v.title("Backups")
    v.grab_set()
    v.resizable(False, False)
    v.update_idletasks()
    ancho, alto = 520, 420
    sw = v.winfo_screenwidth()
    sh = v.winfo_screenheight()
    v.geometry(f"{ancho}x{alto}+{(sw - ancho) // 2}+{(sh - alto) // 2}")

    header = tk.Frame(v, bg="#2c3e50")
    header.pack(fill="x")
    tk.Label(header, text="Gestión de Backups", font=("Arial", 13, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=16, pady=10)

    # — Crear backup manual —
    frame_crear = tk.LabelFrame(v, text="Crear backup ahora",
                                font=("Arial", 9, "bold"), padx=10, pady=8)
    frame_crear.pack(fill="x", padx=16, pady=(12, 6))

    tk.Label(frame_crear,
             text="Guardá una copia de seguridad de todos los datos actuales.",
             font=("Arial", 9), fg="#555").pack(anchor="w", pady=(0, 6))

    btn_crear = tk.Button(frame_crear, text="💾 Crear backup manual",
                          bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                          relief="groove", padx=12, pady=5, cursor="hand2",
                          command=lambda: _on_crear_backup(lista_box, lbl_estado))
    btn_crear.pack(side="left")
    btn_crear.bind("<Enter>", lambda e: btn_crear.config(bg="#1e8449"))
    btn_crear.bind("<Leave>", lambda e: btn_crear.config(bg="#27ae60"))

    btn_carpeta = tk.Button(frame_crear, text="📂 Abrir carpeta",
                            bg="#2980b9", fg="white", font=("Arial", 10, "bold"),
                            relief="groove", padx=12, pady=5, cursor="hand2",
                            command=abrir_carpeta_backups)
    btn_carpeta.pack(side="left", padx=(8, 0))
    btn_carpeta.bind("<Enter>", lambda e: btn_carpeta.config(bg="#1f618d"))
    btn_carpeta.bind("<Leave>", lambda e: btn_carpeta.config(bg="#2980b9"))

    # — Lista de backups disponibles —
    frame_lista = tk.LabelFrame(v, text="Backups disponibles (más reciente primero)",
                                font=("Arial", 9, "bold"), padx=10, pady=8)
    frame_lista.pack(fill="both", expand=True, padx=16, pady=(0, 6))

    scroll = tk.Scrollbar(frame_lista)
    scroll.pack(side="right", fill="y")

    lista_box = tk.Listbox(frame_lista, yscrollcommand=scroll.set,
                           font=("Arial", 10), selectmode="single",
                           activestyle="dotbox", height=8)
    lista_box.pack(fill="both", expand=True)
    scroll.config(command=lista_box.yview)

    lbl_estado = tk.Label(v, text="", font=("Arial", 9), fg="#27ae60")
    lbl_estado.pack(pady=(0, 4))

    _poblar_lista_backups(lista_box)

    # — Restaurar —
    pie = tk.Frame(v)
    pie.pack(pady=(0, 12))

    btn_restaurar = tk.Button(pie, text="🔄 Restaurar seleccionado",
                              bg="#e67e22", fg="white", font=("Arial", 10, "bold"),
                              relief="groove", padx=12, pady=5, cursor="hand2",
                              command=lambda: _on_restaurar_backup(lista_box, lbl_estado, v))
    btn_restaurar.pack(side="left", padx=8)
    btn_restaurar.bind("<Enter>", lambda e: btn_restaurar.config(bg="#ca6f1e"))
    btn_restaurar.bind("<Leave>", lambda e: btn_restaurar.config(bg="#e67e22"))

    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 10, "bold"), relief="groove",
                           padx=12, pady=5, cursor="hand2", command=v.destroy)
    btn_cerrar.pack(side="left", padx=8)
    btn_cerrar.bind("<Enter>", lambda e: btn_cerrar.config(bg="#626f70"))
    btn_cerrar.bind("<Leave>", lambda e: btn_cerrar.config(bg="#7f8c8d"))


def _poblar_lista_backups(lista_box):
    lista_box.delete(0, tk.END)
    archivos = listar_backups()
    if not archivos:
        lista_box.insert(tk.END, "  No hay backups disponibles")
    else:
        for nombre in archivos:
            lista_box.insert(tk.END, f"  {formatear_nombre_backup(nombre)}")


def _on_crear_backup(lista_box, lbl_estado):
    ok = hacer_backup(manual=True)
    if ok:
        lbl_estado.config(text="✅ Backup creado correctamente.", fg="#27ae60")
        _poblar_lista_backups(lista_box)
    else:
        lbl_estado.config(text="❌ No se pudo crear el backup.", fg="#e74c3c")


def _on_restaurar_backup(lista_box, lbl_estado, ventana):
    idx = lista_box.curselection()
    if not idx:
        messagebox.showwarning("Sin selección",
                               "Seleccioná un backup de la lista primero.")
        return
    archivos     = listar_backups()
    nombre       = archivos[idx[0]]
    nombre_fmt   = formatear_nombre_backup(nombre)
    confirmacion = messagebox.askyesno(
        "Restaurar backup",
        f"¿Restaurar el backup:\n{nombre_fmt}?\n\n"
        "⚠ Esto reemplazará todos los datos actuales.\n"
        "Se recomienda hacer un backup antes de continuar."
    )
    if confirmacion:
        ok = restaurar_backup(nombre)
        if ok:
            messagebox.showinfo(
                "Restauración exitosa",
                "✅ Backup restaurado correctamente.\n"
                "Reiniciá la aplicación para ver los cambios."
            )
            ventana.destroy()
        else:
            lbl_estado.config(text="❌ No se pudo restaurar el backup.", fg="#e74c3c")


# ══════════════════════════════════════════════
# NAVEGACIÓN
# ══════════════════════════════════════════════
def mostrar_pantalla(nombre, content, volver_callback):
    if nombre == "Tutores":
        mostrar_tutores(content, volver_callback)
    elif nombre == "Alumnos":
        mostrar_alumnos(content, volver_callback)
    elif nombre == "Categorias":
        mostrar_categorias(content, volver_callback)
    elif nombre == "Recibos":
        mostrar_recibos(content, volver_callback)
    elif nombre == "Tutores con alumnos":
        mostrar_tutores_con_alumnos(content, volver_callback)
    elif nombre == "Categorías con alumnos":
        mostrar_categorias_con_alumnos(content, volver_callback)
    elif nombre == "Pago de cuotas":
        mostrar_pago_cuotas(content, volver_callback)
    elif nombre == "Pagos varios":
        mostrar_pagos_varios(content, volver_callback)
    else:
        limpiar_frame(content)
        tk.Label(content, text=f"Pantalla de {nombre} en desarrollo",
                 font=("Arial", 16)).pack(expand=True)


# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
def mostrar_dashboard(content, botones_acciones, botones_listados):
    limpiar_frame(content)

    volver = lambda: mostrar_dashboard(content, botones_acciones, botones_listados)

    # ── Header ───────────────────────────────────────────────────────────
    header = tk.Frame(content, bg="#f4f6f9", height=80)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(header, text="¡Bienvenido, Administrador!",
             font=("Arial", 18, "bold"), bg="#f4f6f9", fg="#1e2a44"
             ).pack(side="left", padx=35, pady=20)

    fecha_frame = tk.Frame(header, bg="#f4f6f9")
    fecha_frame.pack(side="right", padx=35)

    hoy   = datetime.now()
    dias  = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    meses = ["enero","febrero","marzo","abril","mayo","junio",
              "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    fecha_str = (f"{dias[hoy.weekday()]}, {hoy.day} "
                 f"de {meses[hoy.month-1]} de {hoy.year}")

    tk.Label(fecha_frame, text=fecha_str, font=("Arial", 10),
             bg="#f4f6f9", fg="#6c757d").pack(anchor="e")

    label_hora = tk.Label(fecha_frame, text=hoy.strftime("%H:%M"),
                          font=("Arial", 14, "bold"), bg="#f4f6f9", fg="#1e2a44")
    label_hora.pack(anchor="e")
    actualizar_hora(label_hora)

    # ── Stat cards clickeables ────────────────────────────────────────────
    stats = obtener_stats()

    stats_frame = tk.Frame(content, bg="#f4f6f9")
    stats_frame.pack(fill="x", padx=30, pady=25)

    stats_data = [
        ("👥", "Tutores: ",         stats["tutores"],     "#3b8dd4", "Tutores"),
        ("🎓", "Alumnos activos: ", stats["alumnos"],     "#28a745", "Alumnos"),
        ("🏆", "Categorías: ",      stats["categorias"],  "#f39c12", "Categorias"),
        ("📄", "Recibos del mes: ", stats["recibos_mes"], "#8e44ad", "Recibos"),
    ]

    for i, (emoji, texto, numero, color, pantalla) in enumerate(stats_data):
        cmd = lambda p=pantalla: mostrar_pantalla(p, content, volver)
        construir_stat_card(stats_frame, emoji, texto, numero, color,
                            columna=i, comando=cmd)

    for col in range(4):
        stats_frame.columnconfigure(col, weight=1)

    # ── Body ─────────────────────────────────────────────────────────────
    body = tk.Frame(content, bg="#f4f6f9")
    body.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    left_container = tk.Frame(body, bg="white", relief="solid", bd=1)
    left_container.pack(side="left", fill="both", expand=True,
                        padx=(0, 15), pady=5)

    tk.Label(left_container, text="Acciones principales",
             font=("Arial", 14, "bold"), bg="white", fg="#2c3e50"
             ).pack(anchor="w", padx=20, pady=(15, 10))

    for texto in botones_acciones:
        construir_boton_dashboard(left_container, texto, content,
                                   botones_acciones, botones_listados)

    right_container = tk.Frame(body, bg="white", relief="solid", bd=1)
    right_container.pack(side="right", fill="both", expand=True,
                         padx=(15, 0), pady=5)

    tk.Label(right_container, text="Listados y reportes",
             font=("Arial", 14, "bold"), bg="white", fg="#2c3e50"
             ).pack(anchor="w", padx=20, pady=(15, 10))

    for texto in botones_listados:
        construir_boton_dashboard(right_container, texto, content,
                                   botones_acciones, botones_listados)

    # ── Consejo ───────────────────────────────────────────────────────────
    consejo = tk.Frame(content, bg="#e3f2fd", height=62)
    consejo.pack(fill="x", padx=30, pady=10)
    consejo.pack_propagate(False)

    tk.Label(consejo, text="💡", font=("Arial", 18),
             bg="#e3f2fd").pack(side="left", padx=20)
    tk.Label(consejo,
             text="Mantené los datos actualizados para obtener reportes "
                  "precisos y una mejor gestión del club.",
             bg="#e3f2fd", fg="#1e2a44", font=("Arial", 10),
             wraplength=780).pack(side="left", padx=5)


# ══════════════════════════════════════════════
# SIDEBAR COLAPSABLE
# ══════════════════════════════════════════════
def construir_sidebar(main_frame, content, botones_acciones, botones_listados, root):
    ANCHO_EXPANDIDO = 240
    ANCHO_COLAPSADO = 48
    estado          = {"expandido": True}

    sidebar = tk.Frame(main_frame, width=ANCHO_EXPANDIDO, bg="#1e2a44")
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    top_bar = tk.Frame(sidebar, bg="#1e2a44")
    top_bar.pack(fill="x", pady=(10, 0))

    btn_hamburguesa = tk.Button(
        top_bar, text="☰",
        bg="#1e2a44", fg="white", relief="flat",
        font=("Arial", 16, "bold"), padx=10, pady=4,
        activebackground="#263a5f", cursor="hand2",
    )
    btn_hamburguesa.pack(side="left", padx=4)
    btn_hamburguesa.bind("<Enter>", lambda e: btn_hamburguesa.config(bg="#263a5f"))
    btn_hamburguesa.bind("<Leave>", lambda e: btn_hamburguesa.config(bg="#1e2a44"))

    lbl_titulo = tk.Label(
        top_bar, text="CLUB SIGLO XXI",
        bg="#1e2a44", fg="white",
        font=("Arial", 12, "bold")
    )
    lbl_titulo.pack(side="left", padx=6, pady=6)

    tk.Frame(sidebar, bg="#263a5f", height=1).pack(fill="x", pady=(6, 0))

    contenido = tk.Frame(sidebar, bg="#1e2a44")
    contenido.pack(fill="both", expand=True)

    lbl_acciones = tk.Label(contenido, text="ACCIONES", bg="#1e2a44", fg="#a8b2c3",
                            font=("Arial", 9, "bold"))
    lbl_acciones.pack(anchor="w", padx=20, pady=(14, 4))

    acciones_items = [
        ("👤", "Tutores"),
        ("👥", "Alumnos"),
        ("🏆", "Categorias"),
        ("📄", "Recibos"),
    ]
    for icon, text in acciones_items:
        construir_boton_sidebar(contenido, icon, text, content,
                                botones_acciones, botones_listados)

    lbl_listados = tk.Label(contenido, text="LISTADOS", bg="#1e2a44", fg="#a8b2c3",
                            font=("Arial", 9, "bold"))
    lbl_listados.pack(anchor="w", padx=20, pady=(16, 4))

    listados_items = [
        ("📅", "Pago de cuotas"),
        ("💰", "Pagos varios"),
        ("👤", "Tutores con alumnos"),
        ("🏅", "Categorías con alumnos"),
    ]
    for icon, text in listados_items:
        construir_boton_sidebar(contenido, icon, text, content,
                                botones_acciones, botones_listados)

    btn_salir = tk.Button(
        sidebar, text="✕  Salir",
        bg="#e74c3c", fg="white", relief="flat",
        font=("Arial", 10, "bold"), anchor="w", padx=16, pady=6,
        command=root.quit
    )
    btn_salir.pack(side="bottom", fill="x", padx=10, pady=12)
    btn_salir.bind("<Enter>", lambda e: btn_salir.config(bg="#c0392b"))
    btn_salir.bind("<Leave>", lambda e: btn_salir.config(bg="#e74c3c"))

    btn_backup = tk.Button(
        sidebar, text="💾  Backups",
        bg="#2980b9", fg="white", relief="flat",
        font=("Arial", 10, "bold"), anchor="w", padx=16, pady=6,
        cursor="hand2",
        command=lambda: abrir_ventana_backups(root)
    )
    btn_backup.pack(side="bottom", fill="x", padx=10, pady=(0, 4))
    btn_backup.bind("<Enter>", lambda e: btn_backup.config(bg="#1f618d"))
    btn_backup.bind("<Leave>", lambda e: btn_backup.config(bg="#2980b9"))

    def toggle_sidebar():
        if estado["expandido"]:
            sidebar.config(width=ANCHO_COLAPSADO)
            contenido.pack_forget()
            lbl_titulo.pack_forget()
            btn_salir.config(text="✕", padx=4)
            estado["expandido"] = False
        else:
            sidebar.config(width=ANCHO_EXPANDIDO)
            lbl_titulo.pack(side="left", padx=6, pady=6)
            contenido.pack(fill="both", expand=True)
            btn_salir.config(text="✕  Salir", padx=16)
            estado["expandido"] = True

    btn_hamburguesa.config(command=toggle_sidebar)
    return sidebar


# ══════════════════════════════════════════════
# APP PRINCIPAL
# ══════════════════════════════════════════════
def main():
    root = tk.Tk()
    root.title("Club Siglo XXI - Sistema de Gestión")
    root.minsize(900, 600)
    root.configure(bg="#f4f6f9")
    root.iconbitmap(resource_path("utils/logo.ico"))

    centrar_ventana(root, 1180, 700)

    main_frame = tk.Frame(root, bg="#f4f6f9")
    main_frame.pack(fill="both", expand=True)

    botones_acciones = ["Tutores", "Alumnos", "Categorias", "Recibos"]
    botones_listados = ["Pago de cuotas", "Pagos varios",
                        "Tutores con alumnos", "Categorías con alumnos"]

    content = tk.Frame(main_frame, bg="#f4f6f9")

    construir_sidebar(main_frame, content, botones_acciones, botones_listados, root)

    content.pack(side="right", fill="both", expand=True)
    mostrar_dashboard(content, botones_acciones, botones_listados)

    if hay_actualizacion():
        respuesta = messagebox.askyesno(
            "Actualización disponible",
            "Hay una nueva versión disponible.\n¿Deseas actualizar ahora?"
        )
        if respuesta:
            descargar_actualizacion(root=root)

    hacer_backup(manual=False)
    root.mainloop()

if __name__ == "__main__":
    main()