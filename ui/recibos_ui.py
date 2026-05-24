import os
import tempfile
import webbrowser
from datetime import date

import tkinter as tk
from tkinter import messagebox, ttk

from reportlab.lib           import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles    import getSampleStyleSheet
from reportlab.lib.units     import cm
from reportlab.platypus      import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph

from models.alumnos  import obtener_alumnos
from models.recibos  import (
    eliminar_recibo, obtener_recibo, obtener_recibos,
    obtener_deudores, obtener_estado_alumnos, obtener_pagos_mensuales,
    obtener_valor_cuota_alumno,
    MESES, FORMAS_PAGO
)
from models.tutores  import obtener_tutores
from service.gmail_service   import (
    ejecutar_envio_gmail_masivo, leer_config_gmail,
    probar_conexion_gmail
)
from service.recibos_service import (
    enriquecer_alumnos, filtrar_alumnos_por_tutor,
    guardar_recibo_individual, guardar_recibos_multiples,
    parsear_recibo_individual, validar_recibo_individual
)
from ui.tabla_scroll import agregar_header, crear_tabla_scroll, fila_color
from utils.fecha     import arg_a_iso, fmt_fecha
from utils.pdf_utils import abrir_pdf
from utils.ui_helpers import (
    abrir_archivo, calcular_total, centrar, fmt_monto,
    label_tipo_pago, limpiar_frame
)
from utils.pdf_tablas import (
    exportar_pdf_deudores,
    exportar_pdf_alumnos_al_dia,
    exportar_pdf_pagos_mensuales,
)
from utils.excel_tablas import (
    exportar_excel_deudores,
    exportar_excel_alumnos_al_dia,
    exportar_excel_pagos_mensuales,
)

# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
def _aplicar_hover(btn, color_normal, color_hover):
    btn.bind("<Enter>", lambda e: btn.config(bg=color_hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=color_normal))

def _actualizar_color_mes(var, cell, cb_ref):
    nuevo_bg = "#27ae60" if var.get() else "#ecf0f1"
    nuevo_fg = "white"   if var.get() else "#2c3e50"
    cell.config(bg=nuevo_bg)
    cb_ref.config(bg=nuevo_bg, fg=nuevo_fg,
                  selectcolor=nuevo_bg, activebackground=nuevo_bg)
    
    
# ══════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════
MES_ACTUAL     = MESES[date.today().month - 1]
ANIO_ACTUAL    = str(date.today().year)
MESES_VISIBLES = MESES[2:11]


# ══════════════════════════════════════════════
# GMAIL — ventanas de configuración y envío
# ══════════════════════════════════════════════
def abrir_config_gmail(callback_ok=None):
    v = tk.Toplevel()
    v.title("Configurar Gmail")
    v.grab_set()
    centrar(v, 520, 420)
    v.resizable(False, False)

    tk.Label(v, text="Configuración de Gmail",
             font=("Arial", 13, "bold"), pady=10).pack()

    instruc = tk.LabelFrame(v, text="¿Cómo obtener la Contraseña de Aplicación?",
                            padx=10, pady=8)
    instruc.pack(fill="x", padx=20, pady=(0, 10))
    tk.Label(instruc,
             text="1. Abrí myaccount.google.com\n"
                  "2. Seguridad → Verificación en 2 pasos (activala si no está)\n"
                  "3. Seguridad → Contraseñas de aplicaciones\n"
                  "4. Seleccioná 'Correo' y 'Computadora Windows'\n"
                  "5. Google te da una clave de 16 letras → copiala acá",
             justify="left", font=("Arial", 9), fg="#333").pack(anchor="w")
    tk.Button(instruc, text="Abrir myaccount.google.com",
              fg="#1a73e8", cursor="hand2", relief="flat",
              command=lambda: webbrowser.open(
                  "https://myaccount.google.com/apppasswords")
              ).pack(anchor="w", pady=(4, 0))

    form = tk.Frame(v, padx=20)
    form.pack(fill="x")
    tk.Label(form, text="Tu Gmail:").grid(
        row=0, column=0, sticky="e", pady=8, padx=6)
    entry_mail = tk.Entry(form, width=34)
    entry_mail.grid(row=0, column=1, sticky="ew", pady=8)
    tk.Label(form, text="Contraseña de App:").grid(
        row=1, column=0, sticky="e", pady=8, padx=6)
    entry_pw = tk.Entry(form, width=34, show="*")
    entry_pw.grid(row=1, column=1, sticky="ew", pady=8)

    mail_prev, pw_prev = leer_config_gmail()
    entry_mail.insert(0, mail_prev)
    entry_pw.insert(0, pw_prev)

    lbl = tk.Label(v, text="", font=("Arial", 9))
    lbl.pack()

    br = tk.Frame(v)
    br.pack(pady=10)
    tk.Button(br, text="Probar y Guardar", bg="#27ae60", fg="white", width=16,
              command=lambda: probar_conexion_gmail(
                  entry_mail.get().strip(),
                  entry_pw.get().strip(),
                  lbl, callback_ok)
              ).pack(side="left", padx=8)
    tk.Button(br, text="Cerrar", bg="#95a5a6", fg="white",
              width=10, command=v.destroy).pack(side="left", padx=8)


def _abrir_envio_gmail_individual(recibo_id):
    mail_origen, pw = leer_config_gmail()
    if not mail_origen or not pw:
        if messagebox.askyesno("Gmail no configurado",
                               "Todavía no configuraste Gmail.\n"
                               "¿Querés configurarlo ahora?"):
            abrir_config_gmail()
        return

    datos = obtener_recibo(recibo_id)
    if not datos:
        return

    v = tk.Toplevel()
    v.title("Enviar por Gmail")
    v.grab_set()
    centrar(v, 420, 200)
    v.resizable(False, False)

    tk.Label(v, text="Enviar Recibo por Gmail",
             font=("Arial", 12, "bold"), pady=10).pack()
    form = tk.Frame(v, padx=20)
    form.pack(fill="x")
    tk.Label(form, text="Email destino:").grid(
        row=0, column=0, sticky="e", pady=8, padx=6)
    entry_dest = tk.Entry(form, width=30)
    entry_dest.grid(row=0, column=1, sticky="ew", pady=8)

    email_alumno = datos.get("email") or ""
    if "@" in email_alumno:
        entry_dest.insert(0, email_alumno)

    lbl = tk.Label(v, text="", font=("Arial", 9))
    lbl.pack()

    br = tk.Frame(v)
    br.pack(pady=10)
    tk.Button(br, text="Enviar ✉", bg="#EA4335", fg="white", width=12,
              command=lambda: ejecutar_envio_gmail_masivo([recibo_id], lbl, v)
              ).pack(side="left", padx=8)
    tk.Button(br, text="Cancelar", bg="#95a5a6", fg="white",
              width=10, command=v.destroy).pack(side="left", padx=8)


def abrir_envio_gmail_masivo(ids_seleccionados):
    mail_origen, pw = leer_config_gmail()
    if not mail_origen or not pw:
        if messagebox.askyesno("Gmail no configurado",
                               "Todavía no configuraste Gmail.\n"
                               "¿Querés configurarlo ahora?"):
            abrir_config_gmail()
        return

    v = tk.Toplevel()
    v.title("Enviar múltiples recibos por Gmail")
    v.grab_set()
    centrar(v, 460, 200)
    v.resizable(False, False)

    tk.Label(v, text="Envío Masivo por Gmail",
             font=("Arial", 12, "bold"), pady=10).pack()
    tk.Label(v,
             text=f"Se enviarán {len(ids_seleccionados)} recibo(s) al email\n"
                  "registrado de cada alumno.",
             font=("Arial", 10), pady=6).pack()

    lbl_estado = tk.Label(v, text="", font=("Arial", 9))
    lbl_estado.pack()

    br = tk.Frame(v)
    br.pack(pady=10)
    tk.Button(br, text="Enviar todos ✉", bg="#EA4335", fg="white", width=16,
              command=lambda: ejecutar_envio_gmail_masivo(
                  ids_seleccionados, lbl_estado, v)
              ).pack(side="left", padx=8)
    tk.Button(br, text="Cancelar", bg="#95a5a6", fg="white",
              width=10, command=v.destroy).pack(side="left", padx=8)


# ══════════════════════════════════════════════
# SELECTOR DE MESES
# ══════════════════════════════════════════════
def crear_selector_meses(parent, mes_actual_idx=None):
    frame    = tk.LabelFrame(parent, text="Meses a pagar",
                             font=("Arial", 10, "bold"), padx=8, pady=6)
    vars_mes = []
    for i, mes in enumerate(MESES_VISIBLES):
        idx_real = MESES.index(mes)
        var      = tk.BooleanVar(value=(idx_real == mes_actual_idx))
        cb       = tk.Checkbutton(frame, text=mes.capitalize(), variable=var)
        cb.grid(row=i // 3, column=i % 3, sticky="w", padx=6, pady=2)
        vars_mes.append(var)
    return frame, vars_mes


def crear_selector_meses_horizontal(parent, mes_actual_idx=None):
    frame    = tk.LabelFrame(parent, text="Meses a pagar",
                             font=("Arial", 10, "bold"), padx=8, pady=8)
    vars_mes = []
    for i, mes in enumerate(MESES_VISIBLES):
        idx_real = MESES.index(mes)
        var      = tk.BooleanVar(value=(idx_real == mes_actual_idx))

        color_bg = "#27ae60" if var.get() else "#ecf0f1"
        color_fg = "white"   if var.get() else "#2c3e50"

        cell = tk.Frame(frame, bg=color_bg, relief="groove", bd=1)
        cell.pack(side="left", padx=3, pady=2)

        cb = tk.Checkbutton(
            cell,
            text=mes.capitalize(),
            variable=var,
            bg=color_bg, fg=color_fg,
            selectcolor=color_bg,
            activebackground=color_bg,
            font=("Arial", 9, "bold"),
            padx=8, pady=5,
            relief="flat",
            cursor="hand2",
        )
        cb.pack()
        cb.config(command=lambda v=var, c=cell, r=cb: _actualizar_color_mes(v, c, r))
        vars_mes.append(var)
    return frame, vars_mes


def _meses_seleccionados(vars_mes):
    resultado = [MESES_VISIBLES[i] for i, v in enumerate(vars_mes) if v.get()]
    return resultado


# ══════════════════════════════════════════════
# TABLA PRINCIPAL DE RECIBOS
# ══════════════════════════════════════════════
def _toggle_todos_check(vars_check, var_master):
    valor = var_master.get()
    for v in vars_check:
        v.set(valor)


def _confirmar_eliminar(recibo_id, nombre, contenedor_tabla, filtro_tipo=None):
    if messagebox.askyesno("Eliminar Recibo",
                           f"¿Eliminar el recibo de {nombre}?\n"
                           "Esta acción no se puede deshacer."):
        eliminar_recibo(recibo_id)
        _construir_tabla_recibos(contenedor_tabla, filtro_tipo=filtro_tipo)


def _acciones_seleccionados(vars_check, rows_ref, contenedor_tabla,
                             filtro_tipo, accion):
    ids_sel = [rows_ref[i]["id"] for i, v in enumerate(vars_check) if v.get()]
    if not ids_sel:
        messagebox.showwarning("Sin selección",
                               "Marcá al menos un recibo con el checkbox.")
        return

    if accion == "pdf":
        for rid in ids_sel:
            abrir_pdf(rid)
    elif accion == "gmail":
        abrir_envio_gmail_masivo(ids_sel)
    elif accion == "eliminar":
        n = len(ids_sel)
        if messagebox.askyesno("Eliminar seleccionados",
                               f"¿Eliminar {n} recibo(s) seleccionado(s)?\n"
                               "Esta acción no se puede deshacer."):
            for rid in ids_sel:
                eliminar_recibo(rid)
            _construir_tabla_recibos(contenedor_tabla, filtro_tipo=filtro_tipo)


def _construir_tabla_recibos(contenedor_tabla, filtro_texto="",
                              filtro_tipo=None, filtro_mes=None,
                              filtro_forma=None, filtro_parcial=None):
    limpiar_frame(contenedor_tabla)

    rows = obtener_recibos(filtro_texto, mes=filtro_mes, forma_pago=filtro_forma)
    if filtro_tipo:
        rows = [r for r in rows if r.get("tipo_pago") == filtro_tipo]
    if filtro_parcial is True:
        rows = [r for r in rows if int(r.get("pago_completo") or 1) == 0]
    elif filtro_parcial is False:
        rows = [r for r in rows if int(r.get("pago_completo") or 1) == 1]

    vars_check = []
    var_master  = tk.BooleanVar(value=False)

    outer, tabla_frame = crear_tabla_scroll(contenedor_tabla)
    outer.pack(fill="both", expand=True)

    headers = ["✓", "Alumno", "Tutor", "Categoría", "Tipo", "Mes",
               "Fecha", "Monto", "Monto abonado", "Desc.", "Mora", "Estado",
               "Forma Pago", "Acciones"]
    agregar_header(tabla_frame, headers)

    cb_master = tk.Checkbutton(tabla_frame, variable=var_master,
                               command=lambda: _toggle_todos_check(
                                   vars_check, var_master))
    cb_master.grid(row=0, column=0, padx=4)

    if not rows:
        tk.Label(tabla_frame, text="No hay recibos registrados",
                 fg="gray", font=("Arial", 10), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
        return

    for i, r in enumerate(rows, start=1):
        bg            = fila_color(i)
        monto         = float(r.get("monto")        or 0)
        descuento     = float(r.get("descuento")    or 0)
        mora          = float(r.get("mora")         or 0)
        abonado       = float(r.get("monto_pagado") or monto)
        pago_completo = int(r.get("pago_completo") if r.get("pago_completo") is not None else 1)
        total_recibo  = monto - descuento + mora
        estado_txt    = ("Completo" if pago_completo
                         else f"Parcial (debe ${total_recibo - abonado:.2f})")

        var_cb = tk.BooleanVar(value=False)
        vars_check.append(var_cb)
        tk.Checkbutton(tabla_frame, variable=var_cb, bg=bg).grid(
            row=i, column=0, padx=4, pady=2)

        vals = [
            r.get("alumno_nombre")    or "—",
            r.get("tutor_nombre")     or "—",
            r.get("categoria_nombre") or "—",
            label_tipo_pago(r.get("tipo_pago", "")),
            (r.get("mes_pago")    or "—").capitalize(),
            fmt_fecha(r.get("fecha_pago")) or "—",
            fmt_monto(monto),
            fmt_monto(abonado),
            fmt_monto(r.get("descuento")),
            fmt_monto(r.get("mora")),
            estado_txt,
            (r.get("forma_pago") or "—").capitalize(),
        ]
        for col, val in enumerate(vals):
            color_txt = "#c0392b" if "Parcial" in val else "#333"
            tk.Label(tabla_frame, text=val, bg=bg, padx=6, pady=4,
                     font=("Arial", 9), fg=color_txt).grid(
                row=i, column=col + 1, sticky="nsew", padx=1, pady=1)

        rid = r["id"]
        acc = tk.Frame(tabla_frame, bg=bg)
        acc.grid(row=i, column=len(vals) + 1,
                 sticky="nsew", padx=4, pady=2)
        tk.Button(acc, text="PDF", bg="#2c3e50", fg="white", width=4,
                  font=("Arial", 8),
                  command=lambda rid=rid: abrir_pdf(rid)
                  ).pack(side="left", padx=1)
        tk.Button(acc, text="Gmail", bg="#EA4335", fg="white", width=5,
                  font=("Arial", 8),
                  command=lambda rid=rid: _abrir_envio_gmail_individual(rid)
                  ).pack(side="left", padx=1)
        tk.Button(acc, text="🗑", bg="#e74c3c", fg="white", width=3,
                  font=("Arial", 8),
                  command=lambda rid=rid, n=r.get("alumno_nombre", ""),
                                  ct=contenedor_tabla, ft=filtro_tipo:
                      _confirmar_eliminar(rid, n, ct, ft)
                  ).pack(side="left", padx=1)


# ══════════════════════════════════════════════
# MODAL CREAR RECIBO INDIVIDUAL
# ══════════════════════════════════════════════
def _toggle_parcial(var_parcial, frame_parcial):
    if var_parcial.get():
        frame_parcial.grid()
    else:
        frame_parcial.grid_remove()


def _on_tutor_seleccionado(combo_tutor, combo_alumno, alumnos, tutores, entry_monto):
    tutor_texto = combo_tutor.get()
    tutor_id    = None
    for t in tutores:
        if f"{t['nombre']} {t['apellido']}" == tutor_texto:
            tutor_id = t["id"]
            break

    alumnos_filtrados = filtrar_alumnos_por_tutor(alumnos, tutor_id)
    combo_alumno["values"] = [
        f"{a['nombre_apellido']} (DNI: {a.get('dni') or 's/d'})"
        for a in alumnos_filtrados
    ]
    combo_alumno._alumnos_filtrados = alumnos_filtrados
    combo_alumno.set("")
    combo_alumno.config(state="readonly")
    entry_monto.delete(0, tk.END)


def _on_alumno_seleccionado(combo_alumno, entry_monto):
    alumnos_ref = getattr(combo_alumno, "_alumnos_filtrados", [])
    idx_alumno  = combo_alumno.current()
    if idx_alumno < 0 or idx_alumno >= len(alumnos_ref):
        return
    alumno = alumnos_ref[idx_alumno]
    cuota  = obtener_valor_cuota_alumno(alumno["id"])
    if cuota:
        entry_monto.delete(0, tk.END)
        entry_monto.insert(0, str(cuota))


def _on_guardar_recibo_individual(modal, contenedor_tabla, filtro_tipo,
                                   combo_alumno, combo_tutor, combo_tipo,
                                   vars_mes, entry_fecha, entry_monto,
                                   entry_desc, entry_mora, combo_forma,
                                   entry_descripcion, entry_emisor,
                                   var_parcial, entry_monto_pagado,
                                   tutores,
                                   modo_desc="$", modo_mora="$"):
    alumnos_ref = getattr(combo_alumno, "_alumnos_filtrados", [])
    meses_sel   = _meses_seleccionados(vars_mes)
    error       = validar_recibo_individual(
        combo_alumno.current(),
        combo_tutor.current(),
        entry_monto.get(),
        meses_sel
    )
    if error:
        messagebox.showwarning("Falta dato", error)
        return

    try:
        datos = parsear_recibo_individual(
            combo_tipo, combo_forma, entry_fecha,
            entry_monto, entry_desc, entry_mora,
            entry_descripcion, entry_emisor,
            var_parcial, entry_monto_pagado,
            FORMAS_PAGO,
            modo_desc=modo_desc,
            modo_mora=modo_mora,
        )
        nuevos_ids = guardar_recibo_individual(
            alumnos_ref[combo_alumno.current()],
            tutores[combo_tutor.current()],
            datos,
            meses_sel
        )
        modal.destroy()
        _construir_tabla_recibos(contenedor_tabla, filtro_tipo=filtro_tipo)
        n = len(nuevos_ids)
        if messagebox.askyesno("Recibo(s) creado(s)",
                               f"Se crearon {n} recibo(s) correctamente.\n"
                               "¿Abrís los PDFs ahora?"):
            for rid in nuevos_ids:
                abrir_pdf(rid)
    except ValueError as e:
        messagebox.showerror("Error", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))


def abrir_crear_recibo(contenedor_tabla, filtro_tipo=None):
    modal = tk.Toplevel()
    modal.title("Nuevo Recibo")
    modal.grab_set()
    centrar(modal, 620, 700)
    modal.resizable(False, False)

    # ── Título ────────────────────────────────────────────────────────────
    tk.Label(modal, text="Crear Nuevo Recibo",
             font=("Arial", 14, "bold"), pady=12).pack()

    alumnos = obtener_alumnos()
    tutores = obtener_tutores()

    # ══ ZONA SUPERIOR: dos columnas ══════════════════════════════════════
    zona_sup = tk.Frame(modal, padx=16)
    zona_sup.pack(fill="x", pady=(0, 8))
    zona_sup.columnconfigure(0, weight=1)
    zona_sup.columnconfigure(1, weight=1)

    # ── Columna izquierda: Información General ────────────────────────────
    col_izq = tk.LabelFrame(zona_sup, text="Información General",
                            font=("Arial", 10, "bold"), padx=12, pady=10)
    col_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    col_izq.columnconfigure(0, weight=1)

    tk.Label(col_izq, text="Tutor *", anchor="w",
             font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
    combo_tutor = ttk.Combobox(col_izq, state="readonly")
    combo_tutor["values"] = [f"{t['nombre']} {t['apellido']}" for t in tutores]
    combo_tutor.grid(row=1, column=0, sticky="ew", pady=(0, 8))

    tk.Label(col_izq, text="Alumno *", anchor="w",
             font=("Arial", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 2))
    combo_alumno = ttk.Combobox(col_izq, state="disabled")
    combo_alumno["values"] = []
    combo_alumno.grid(row=3, column=0, sticky="ew", pady=(0, 8))

    tk.Label(col_izq, text="Tipo de Pago *", anchor="w",
             font=("Arial", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 2))
    combo_tipo = ttk.Combobox(col_izq, values=["Pago de Cuota", "Otros Pagos"])
    if filtro_tipo == "pago_cuota":
        combo_tipo.current(0)
        combo_tipo.config(state="disabled")
    elif filtro_tipo == "otros_pagos":
        combo_tipo.current(1)
        combo_tipo.config(state="disabled")
    else:
        combo_tipo.current(0)
        combo_tipo.config(state="readonly")
    combo_tipo.grid(row=5, column=0, sticky="ew", pady=(0, 4))

    # ── Columna derecha: Detalles de Pago ────────────────────────────────
    col_der = tk.LabelFrame(zona_sup, text="Detalles de Pago",
                            font=("Arial", 10, "bold"), padx=12, pady=10)
    col_der.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    col_der.columnconfigure(0, weight=1)
    col_der.columnconfigure(1, weight=1)

    tk.Label(col_der, text="Fecha de Pago *", anchor="w",
             font=("Arial", 9, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
    entry_fecha = tk.Entry(col_der)
    entry_fecha.insert(0, date.today().strftime("%d/%m/%Y"))
    entry_fecha.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    tk.Label(col_der, text="Monto cuota ($) *", anchor="w",
             font=("Arial", 9, "bold")).grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(0, 2))
    entry_monto = tk.Entry(col_der)
    entry_monto.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    tk.Label(col_der, text="Descuento", anchor="w",
             font=("Arial", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 2))
    tk.Label(col_der, text="Mora", anchor="w",
             font=("Arial", 9, "bold")).grid(row=4, column=1, sticky="w", pady=(0, 2))

    frame_desc = tk.Frame(col_der)
    frame_desc.grid(row=5, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
    entry_desc = tk.Entry(frame_desc, width=8)
    entry_desc.insert(0, "0")
    entry_desc.pack(side="left")
    combo_modo_desc = ttk.Combobox(frame_desc, state="readonly",
                                   values=["$", "%"], width=3)
    combo_modo_desc.current(0)
    combo_modo_desc.pack(side="left", padx=(4, 0))

    frame_mora = tk.Frame(col_der)
    frame_mora.grid(row=5, column=1, sticky="ew", padx=(4, 0), pady=(0, 4))
    entry_mora = tk.Entry(frame_mora, width=8)
    entry_mora.insert(0, "0")
    entry_mora.pack(side="left")
    combo_modo_mora = ttk.Combobox(frame_mora, state="readonly",
                                   values=["$", "%"], width=3)
    combo_modo_mora.current(0)
    combo_modo_mora.pack(side="left", padx=(4, 0))

    # ══ ZONA INFERIOR: dos columnas ══════════════════════════════════════
    zona_inf = tk.Frame(modal, padx=16)
    zona_inf.pack(fill="x", pady=(0, 4))
    zona_inf.columnconfigure(0, weight=1)
    zona_inf.columnconfigure(1, weight=1)

    # ── Columna izquierda: Datos del Pago (sin Descripción) ───────────────
    col_pago = tk.LabelFrame(zona_inf, text="Datos del Pago",
                             font=("Arial", 10, "bold"), padx=12, pady=10)
    col_pago.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    col_pago.columnconfigure(0, weight=1)

    tk.Label(col_pago, text="Forma de Pago", anchor="w",
             font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
    combo_forma = ttk.Combobox(col_pago, state="readonly",
                               values=[f.capitalize() for f in FORMAS_PAGO])
    combo_forma.current(0)
    combo_forma.grid(row=1, column=0, sticky="ew", pady=(0, 8))

    tk.Label(col_pago, text="Emitido Por", anchor="w",
             font=("Arial", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 2))
    entry_emisor = tk.Entry(col_pago)
    entry_emisor.grid(row=3, column=0, sticky="ew", pady=(0, 8))

    var_parcial      = tk.IntVar(value=0)
    var_monto_pagado = tk.StringVar()

    frame_parcial = tk.Frame(col_pago)
    frame_parcial.grid(row=5, column=0, sticky="ew", pady=(0, 4))
    frame_parcial.columnconfigure(0, weight=1)
    frame_parcial.grid_remove()

    tk.Label(frame_parcial, text="Monto abonado ($) *", anchor="w",
             font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
    entry_monto_pagado = tk.Entry(frame_parcial, textvariable=var_monto_pagado)
    entry_monto_pagado.grid(row=1, column=0, sticky="ew")
    tk.Label(frame_parcial,
             text="El saldo pendiente queda registrado en el recibo.",
             font=("Arial", 7), fg="#888").grid(
        row=2, column=0, sticky="w", pady=(2, 0))

    tk.Checkbutton(col_pago, text="Pago parcial", variable=var_parcial,
                   command=lambda: _toggle_parcial(var_parcial, frame_parcial)
                   ).grid(row=4, column=0, sticky="w", pady=(0, 4))

    # ── Columna derecha: Meses a pagar ────────────────────────────────────
    frame_meses, vars_mes = crear_selector_meses(
        zona_inf, mes_actual_idx=date.today().month - 1)
    frame_meses.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    # ══ DESCRIPCIÓN: abajo, ancho completo ═══════════════════════════════
    zona_desc = tk.LabelFrame(modal, text="Descripción",
                              font=("Arial", 10, "bold"), padx=12, pady=10)
    zona_desc.pack(fill="x", padx=16, pady=(0, 8))
    zona_desc.columnconfigure(0, weight=1)

    entry_descripcion = tk.Entry(zona_desc, font=("Arial", 10))
    entry_descripcion.grid(row=0, column=0, sticky="ew", ipady=6)

    # ── Bindings ──────────────────────────────────────────────────────────
    combo_tutor.bind(
        "<<ComboboxSelected>>",
        lambda e: _on_tutor_seleccionado(
            combo_tutor, combo_alumno, alumnos, tutores, entry_monto))
    combo_alumno.bind(
        "<<ComboboxSelected>>",
        lambda e: _on_alumno_seleccionado(combo_alumno, entry_monto))

    # ── Botones ───────────────────────────────────────────────────────────
    br = tk.Frame(modal)
    br.pack(pady=12)

    btn_guardar = tk.Button(br, text="💾 Guardar Recibo(s)", bg="#27ae60", fg="white",
                            font=("Arial", 10, "bold"), relief="groove",
                            padx=16, pady=6, cursor="hand2",
                            command=lambda: _on_guardar_recibo_individual(
                                modal, contenedor_tabla, filtro_tipo,
                                combo_alumno, combo_tutor, combo_tipo,
                                vars_mes, entry_fecha, entry_monto,
                                entry_desc, entry_mora, combo_forma,
                                entry_descripcion, entry_emisor,
                                var_parcial, var_monto_pagado,
                                tutores,
                                combo_modo_desc.get(), combo_modo_mora.get()))
    btn_guardar.pack(side="left", padx=8)
    _aplicar_hover(btn_guardar, "#27ae60", "#1e8449")

    btn_cancelar = tk.Button(br, text="✕ Cancelar", bg="#7f8c8d", fg="white",
                             font=("Arial", 10, "bold"), relief="groove",
                             padx=16, pady=6, cursor="hand2",
                             command=modal.destroy)
    btn_cancelar.pack(side="left", padx=8)
    _aplicar_hover(btn_cancelar, "#7f8c8d", "#626f70")


# ══════════════════════════════════════════════
# MODAL RECIBOS MÚLTIPLES
# ══════════════════════════════════════════════
def _toggle_abonado_multi(var_parc, e_abonado):
    estado = "normal" if var_parc.get() else "disabled"
    e_abonado.config(state=estado)


def _seleccionar_todos_multi(filas_data, valor):
    for f in filas_data:
        f["var_inc"].set(valor)


def _actualizar_contador_multi(filas_data, lbl_sel):
    n = sum(1 for f in filas_data if f["var_inc"].get())
    lbl_sel.config(text=f"Seleccionados: {n} / {len(filas_data)}")


def _poblar_tabla_multi(frame_tabla, alumnos_filtrados, filas_data,
                         es_cuota, lbl_sel):
    limpiar_frame(frame_tabla)
    filas_data.clear()

    headers = ["✓", "Alumno", "Tutor", "Categoría", "Cuota",
               "Monto ($)", "Desc.", "Modo D.", "Mora", "Modo M.",
               "¿Pago parcial?", "Monto abonado ($)"]
    for col, h in enumerate(headers):
        tk.Label(frame_tabla, text=h, bg="#2c3e50", fg="white",
                 font=("Arial", 9, "bold"), padx=6, pady=5).grid(
            row=0, column=col, sticky="nsew", padx=1, pady=1)

    for i, a in enumerate(alumnos_filtrados, start=1):
        bg    = fila_color(i)
        cuota = obtener_valor_cuota_alumno(a["id"])

        var_inc = tk.BooleanVar(value=False)
        tk.Checkbutton(frame_tabla, variable=var_inc, bg=bg,
                       command=lambda: _actualizar_contador_multi(
                           filas_data, lbl_sel)
                       ).grid(row=i, column=0, padx=4, pady=2)

        for col, texto in enumerate([
            a.get("nombre_apellido", "—"),
            a.get("tutor_nombre",    "—"),
            a.get("categoria_nombre","—"),
            fmt_monto(cuota),
        ], start=1):
            tk.Label(frame_tabla, text=texto, bg=bg, padx=6,
                     font=("Arial", 9)).grid(
                row=i, column=col, sticky="nsew", padx=1, pady=1)

        monto_inicial = str(cuota) if (es_cuota and cuota) else "0"
        e_monto = tk.Entry(frame_tabla, width=9, relief="groove")
        e_monto.insert(0, monto_inicial)
        e_monto.grid(row=i, column=5, padx=2, pady=2)

        e_desc = tk.Entry(frame_tabla, width=7, relief="groove")
        e_desc.insert(0, "0")
        e_desc.grid(row=i, column=6, padx=2, pady=2)

        cb_modo_desc = ttk.Combobox(frame_tabla, state="readonly",
                                     values=["$", "%"], width=3)
        cb_modo_desc.current(0)
        cb_modo_desc.grid(row=i, column=7, padx=2, pady=2)

        e_mora = tk.Entry(frame_tabla, width=7, relief="groove")
        e_mora.insert(0, "0")
        e_mora.grid(row=i, column=8, padx=2, pady=2)

        cb_modo_mora = ttk.Combobox(frame_tabla, state="readonly",
                                     values=["$", "%"], width=3)
        cb_modo_mora.current(0)
        cb_modo_mora.grid(row=i, column=9, padx=2, pady=2)

        var_parc    = tk.IntVar(value=0)
        var_abonado = tk.StringVar()
        e_abonado   = tk.Entry(frame_tabla, width=9, relief="groove",
                               textvariable=var_abonado)
        e_abonado.config(state="disabled")
        tk.Checkbutton(frame_tabla, variable=var_parc, bg=bg,
                       command=lambda vp=var_parc, ea=e_abonado:
                           _toggle_abonado_multi(vp, ea)
                       ).grid(row=i, column=10, padx=2, pady=2)
        e_abonado.grid(row=i, column=11, padx=2, pady=2)

        filas_data.append({
            "alumno":      a,
            "var_inc":     var_inc,
            "e_monto":     e_monto,
            "e_desc":      e_desc,
            "modo_desc":   cb_modo_desc,
            "e_mora":      e_mora,
            "modo_mora":   cb_modo_mora,
            "var_parc":    var_parc,
            "e_abonado":   e_abonado,
            "var_abonado": var_abonado,
        })

    _actualizar_contador_multi(filas_data, lbl_sel)


def _filtrar_tabla_multi(texto, todos_alumnos, frame_tabla,
                          filas_data, es_cuota, lbl_sel):
    txt       = texto.strip().lower()
    filtrados = [
        a for a in todos_alumnos
        if txt in (a.get("nombre_apellido")   or "").lower()
        or txt in (a.get("tutor_nombre")      or "").lower()
        or txt in (a.get("categoria_nombre")  or "").lower()
    ]
    _poblar_tabla_multi(frame_tabla, filtrados, filas_data, es_cuota, lbl_sel)


def _on_tipo_cambio_multi(combo_tipo, entry_buscar, todos_alumnos,
                           frame_tabla, filas_data, lbl_sel):
    es_cuota = combo_tipo.current() == 0
    _filtrar_tabla_multi(
        entry_buscar.get(), todos_alumnos,
        frame_tabla, filas_data, es_cuota, lbl_sel)


def _on_guardar_recibos_multiples(modal, contenedor_tabla, filtro_tipo,
                                   filas_data, tipo_raw, meses_sel,
                                   fecha_val, forma_raw, descripcion,
                                   emisor, tutores):
    filas_sel = [f for f in filas_data if f["var_inc"].get()]
    if not filas_sel:
        messagebox.showwarning("Sin selección", "No hay alumnos seleccionados.")
        return
    if not meses_sel:
        messagebox.showwarning("Sin mes", "Seleccioná al menos un mes.")
        return

    nuevos_ids, errores = guardar_recibos_multiples(
        filas_sel, tipo_raw, meses_sel,
        fecha_val, forma_raw, descripcion, emisor, tutores
    )

    if errores:
        messagebox.showerror("Errores al guardar", "\n".join(errores))
    else:
        modal.destroy()
        _construir_tabla_recibos(contenedor_tabla, filtro_tipo=filtro_tipo)
        n_alumnos = len(filas_sel)
        n_meses   = len(meses_sel)
        if messagebox.askyesno("Recibos creados",
                               f"Se crearon {len(nuevos_ids)} recibo(s) "
                               f"({n_alumnos} alumno(s) × {n_meses} mes(es)).\n"
                               "¿Abrís los PDFs ahora?"):
            for rid in nuevos_ids:
                abrir_pdf(rid)


def abrir_crear_recibos_multiples(contenedor_tabla, filtro_tipo=None):
    modal = tk.Toplevel()
    modal.title("Recibos Múltiples")
    modal.grab_set()
    centrar(modal, 1000, 740)
    modal.resizable(True, True)

    tk.Label(modal, text="Crear Recibos para Múltiples Alumnos",
             font=("Arial", 14, "bold"), pady=10).pack()

    # ── Datos comunes ─────────────────────────────────────────────────────
    panel_top = tk.LabelFrame(modal, text="Datos Generales y Pagos",
                              font=("Arial", 10, "bold"), padx=14, pady=10)
    panel_top.pack(fill="x", padx=16, pady=(0, 6))
    panel_top.columnconfigure((1, 3, 5), weight=1)

    tk.Label(panel_top, text="Tipo de Pago *:",
             font=("Arial", 9, "bold")).grid(
        row=0, column=0, sticky="e", padx=6, pady=4)
    combo_tipo = ttk.Combobox(panel_top, state="readonly", width=16,
                               values=["Pago de Cuota", "Otros Pagos"])
    if filtro_tipo == "pago_cuota":
        combo_tipo.current(0)
        combo_tipo.config(state="disabled")
    elif filtro_tipo == "otros_pagos":
        combo_tipo.current(1)
        combo_tipo.config(state="disabled")
    else:
        combo_tipo.current(0)
        combo_tipo.config(state="readonly")
    combo_tipo.grid(row=0, column=1, sticky="ew", padx=6, pady=4)

    tk.Label(panel_top, text="Fecha *:",
             font=("Arial", 9, "bold")).grid(
        row=0, column=2, sticky="e", padx=6, pady=4)
    entry_fecha = tk.Entry(panel_top, width=13)
    entry_fecha.insert(0, date.today().strftime("%d/%m/%Y"))
    entry_fecha.grid(row=0, column=3, sticky="ew", padx=6, pady=4)

    tk.Label(panel_top, text="Forma de Pago:",
             font=("Arial", 9, "bold")).grid(
        row=0, column=4, sticky="e", padx=6, pady=4)
    combo_forma = ttk.Combobox(panel_top, state="readonly", width=14,
                                values=[f.capitalize() for f in FORMAS_PAGO])
    combo_forma.current(0)
    combo_forma.grid(row=0, column=5, sticky="ew", padx=6, pady=4)

    tk.Label(panel_top, text="Descripción:",
             font=("Arial", 9, "bold")).grid(
        row=1, column=0, sticky="e", padx=6, pady=4)
    entry_descripcion = tk.Entry(panel_top, width=22)
    entry_descripcion.grid(row=1, column=1, columnspan=2,
                           sticky="ew", padx=6, pady=4)

    tk.Label(panel_top, text="Emitido Por:",
             font=("Arial", 9, "bold")).grid(
        row=1, column=3, sticky="e", padx=6, pady=4)
    entry_emisor = tk.Entry(panel_top, width=14)
    entry_emisor.grid(row=1, column=4, columnspan=2,
                      sticky="ew", padx=6, pady=4)

    # ── Selector de meses horizontal ──────────────────────────────────────
    frame_meses, vars_mes = crear_selector_meses_horizontal(
        modal, mes_actual_idx=date.today().month - 1)
    frame_meses.pack(fill="x", padx=16, pady=(0, 6))

    # ── Barra búsqueda y selección ────────────────────────────────────────
    barra_frame = tk.LabelFrame(modal, text="Búsqueda y Selección",
                                font=("Arial", 10, "bold"), padx=10, pady=6)
    barra_frame.pack(fill="x", padx=16, pady=(0, 6))

    tk.Label(barra_frame, text="Buscar:").pack(side="left")
    entry_buscar = tk.Entry(barra_frame, width=32)
    entry_buscar.pack(side="left", padx=6)
    tk.Label(barra_frame, text="(nombre, tutor o categoría)",
             font=("Arial", 8), fg="#888").pack(side="left")

    lbl_sel = tk.Label(barra_frame, text="", font=("Arial", 9, "bold"), fg="#2c3e50")
    lbl_sel.pack(side="right", padx=8)

    btn_todos = tk.Button(barra_frame, text="✓ Todos", bg="#27ae60", fg="white",
                          font=("Arial", 9, "bold"), relief="groove",
                          padx=8, cursor="hand2",
                          command=lambda: _seleccionar_todos_multi(filas_data, True))
    btn_todos.pack(side="left", padx=(10, 4))
    _aplicar_hover(btn_todos, "#27ae60", "#1e8449")

    btn_ninguno = tk.Button(barra_frame, text="✗ Ninguno", bg="#e74c3c", fg="white",
                            font=("Arial", 9, "bold"), relief="groove",
                            padx=8, cursor="hand2",
                            command=lambda: _seleccionar_todos_multi(filas_data, False))
    btn_ninguno.pack(side="left", padx=4)
    _aplicar_hover(btn_ninguno, "#e74c3c", "#c0392b")

    # ── Tabla alumnos ─────────────────────────────────────────────────────
    panel_tabla = tk.LabelFrame(modal, text="Alumnos Activos",
                                font=("Arial", 10, "bold"), padx=6, pady=6)
    panel_tabla.pack(fill="both", expand=True, padx=16, pady=(0, 6))
    outer_t, frame_tabla = crear_tabla_scroll(panel_tabla)
    outer_t.pack(fill="both", expand=True)

    todos_alumnos = obtener_alumnos()
    enriquecer_alumnos(todos_alumnos)
    tutores    = obtener_tutores()
    filas_data = []

    _poblar_tabla_multi(frame_tabla, todos_alumnos, filas_data,
                        combo_tipo.current() == 0, lbl_sel)

    # ── Botones ───────────────────────────────────────────────────────────
    br = tk.Frame(modal)
    br.pack(pady=10)

    btn_guardar = tk.Button(br, text="💾 Guardar Recibos", bg="#27ae60", fg="white",
                            font=("Arial", 10, "bold"), relief="groove",
                            padx=16, pady=6, cursor="hand2",
                            command=lambda: _on_guardar_recibos_multiples(
                                modal, contenedor_tabla, filtro_tipo,
                                filas_data,
                                "pago_cuota" if combo_tipo.current() == 0 else "otros_pagos",
                                _meses_seleccionados(vars_mes),
                                arg_a_iso(entry_fecha.get().strip()),
                                FORMAS_PAGO[combo_forma.current()],
                                entry_descripcion.get().strip(),
                                entry_emisor.get().strip(),
                                tutores))
    btn_guardar.pack(side="left", padx=8)
    _aplicar_hover(btn_guardar, "#27ae60", "#1e8449")

    btn_cancelar = tk.Button(br, text="✕ Cancelar", bg="#7f8c8d", fg="white",
                             font=("Arial", 10, "bold"), relief="groove",
                             padx=16, pady=6, cursor="hand2",
                             command=modal.destroy)
    btn_cancelar.pack(side="left", padx=8)
    _aplicar_hover(btn_cancelar, "#7f8c8d", "#626f70")

    # ── Bindings ──────────────────────────────────────────────────────────
    combo_tipo.bind(
        "<<ComboboxSelected>>",
        lambda e: _on_tipo_cambio_multi(
            combo_tipo, entry_buscar, todos_alumnos,
            frame_tabla, filas_data, lbl_sel))
    entry_buscar.bind(
        "<KeyRelease>",
        lambda e: _filtrar_tabla_multi(
            entry_buscar.get(), todos_alumnos,
            frame_tabla, filas_data,
            combo_tipo.current() == 0, lbl_sel))


# ══════════════════════════════════════════════
# VISTA: DEUDORES
# ══════════════════════════════════════════════
def _cargar_deudores(combo_mes, contenedor, btn_pdf_ref, btn_excel_ref, lbl_total_ref):
    mes_sel = MESES_VISIBLES[combo_mes.current()]
    limpiar_frame(contenedor)

    outer, tabla = crear_tabla_scroll(contenedor)
    outer.pack(fill="both", expand=True)

    rows    = obtener_deudores(mes_sel)
    headers = ["Alumno", "Tutor", "Categoría", "Último Pago de Cuota"]
    agregar_header(tabla, headers)

    if not rows:
        tk.Label(tabla,
                 text=f"✅ Sin deudores en {mes_sel.capitalize()}",
                 fg="#27ae60", font=("Arial", 10, "bold"), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
        lbl_total_ref[0].config(text="")
        btn_pdf_ref[0].config(state="disabled")
        btn_excel_ref[0].config(state="disabled")
    else:
        for i, r in enumerate(rows, start=1):
            bg   = fila_color(i)
            vals = [
                r.get("alumno_nombre")    or "—",
                r.get("tutor_nombre")     or "—",
                r.get("categoria_nombre") or "—",
                fmt_fecha(r.get("ultimo_pago")) or "Sin pagos registrados",
            ]
            for col, val in enumerate(vals):
                tk.Label(tabla, text=val, bg=bg, padx=6, pady=5,
                         font=("Arial", 9)).grid(
                    row=i, column=col, sticky="nsew", padx=1, pady=1)

        lbl_total_ref[0].config(
            text=f"Total deudores en {mes_sel.capitalize()}: {len(rows)}")
        btn_pdf_ref[0].config(
            state="normal",
            command=lambda r=rows, m=mes_sel: exportar_pdf_deudores(r, m))
        btn_excel_ref[0].config(
            state="normal",
            command=lambda r=rows, m=mes_sel: exportar_excel_deudores(r, m))


def abrir_vista_deudores():
    v = tk.Toplevel()
    v.title("Deudores por Mes")
    centrar(v, 800, 580)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text="Ver Deudores de Mes", font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Filtros ───────────────────────────────────────────────────────────
    filtros = tk.LabelFrame(v, text="Filtros", font=("Arial", 9, "bold"),
                            padx=10, pady=6)
    filtros.pack(fill="x", padx=12, pady=(8, 4))

    tk.Label(filtros, text="Mes a revisar:").pack(side="left")
    combo_mes = ttk.Combobox(filtros, state="readonly", width=16,
                              values=[m.capitalize() for m in MESES_VISIBLES])
    mes_hoy     = date.today().month - 1
    idx_visible = (MESES_VISIBLES.index(MESES[mes_hoy])
                   if MESES[mes_hoy] in MESES_VISIBLES else 0)
    combo_mes.current(idx_visible)
    combo_mes.pack(side="left", padx=8)

    btn_buscar = tk.Button(filtros, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2",
                           command=lambda: _cargar_deudores(
                               combo_mes, contenedor, btn_pdf_ref,
                               btn_excel_ref, lbl_total_ref))
    btn_buscar.pack(side="left")
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    # ── Tabla ─────────────────────────────────────────────────────────────
    contenedor = tk.Frame(v)
    contenedor.pack(fill="both", expand=True, padx=12, pady=4)

    # ── Pie ───────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=6)

    lbl_total = tk.Label(pie, text="", font=("Arial", 10, "bold"), fg="#c0392b")
    lbl_total.pack(side="left", padx=10)

    btn_pdf = tk.Button(pie, text="📄 Exportar PDF", bg="#8e44ad", fg="white",
                        font=("Arial", 9, "bold"), relief="groove",
                        cursor="hand2", state="disabled")
    btn_pdf.pack(side="left", padx=6)
    _aplicar_hover(btn_pdf, "#8e44ad", "#7d3c98")

    btn_excel = tk.Button(pie, text="📊 Exportar Excel", bg="#1a6e3c", fg="white",
                          font=("Arial", 9, "bold"), relief="groove",
                          cursor="hand2", state="disabled")
    btn_excel.pack(side="left", padx=6)
    _aplicar_hover(btn_excel, "#1a6e3c", "#145a32")

    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2", command=v.destroy)
    btn_cerrar.pack(side="left", padx=6)
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")

    btn_pdf_ref   = [btn_pdf]
    btn_excel_ref = [btn_excel]
    lbl_total_ref = [lbl_total]

    combo_mes.bind("<<ComboboxSelected>>",
                   lambda e: _cargar_deudores(
                       combo_mes, contenedor, btn_pdf_ref,
                       btn_excel_ref, lbl_total_ref))

    _cargar_deudores(combo_mes, contenedor, btn_pdf_ref, btn_excel_ref, lbl_total_ref)


# ══════════════════════════════════════════════
# VISTA: ALUMNOS AL DÍA
# ══════════════════════════════════════════════
def _cargar_alumnos_al_dia(combo_mes, entry_buscar, var_estado,
                            contenedor, lbl_resumen, btn_pdf_ref, btn_excel_ref):
    mes_sel    = MESES_VISIBLES[combo_mes.current()]
    estado_sel = var_estado.get()
    rows       = obtener_estado_alumnos(
        mes=mes_sel, filtro=entry_buscar.get().strip())

    if estado_sel == "Al día":
        rows = [r for r in rows if r["estado"] == "Al día"]
    elif estado_sel == "En deuda":
        rows = [r for r in rows if r["estado"] == "En deuda"]

    limpiar_frame(contenedor)
    outer, tabla = crear_tabla_scroll(contenedor)
    outer.pack(fill="both", expand=True)

    headers = ["Alumno", "Tutor", "Categoría", "Estado", "Último Pago", "Alerta"]
    agregar_header(tabla, headers)

    al_dia   = sum(1 for r in rows if r["estado"] == "Al día")
    en_deuda = sum(1 for r in rows if r["estado"] == "En deuda")
    lbl_resumen.config(
        text=f"Al día: {al_dia}   |   En deuda: {en_deuda}   |   Total: {len(rows)}")
    btn_pdf_ref[0].config(
        command=lambda r=rows, m=mes_sel, e=estado_sel:
            exportar_pdf_alumnos_al_dia(r, m, e))
    btn_excel_ref[0].config(
        command=lambda r=rows, m=mes_sel, e=estado_sel:
            exportar_excel_alumnos_al_dia(r, m, e))

    if not rows:
        tk.Label(tabla, text="No hay alumnos que coincidan",
                 fg="gray", font=("Arial", 10), pady=20).grid(
            row=1, column=0, columnspan=len(headers))
        return

    for i, r in enumerate(rows, start=1):
        es_al_dia = r["estado"] == "Al día"

        # BUG FIX: color de fila ligado al estado, no a la alerta
        bg = "#d5f5e3" if es_al_dia else "#fde8e8"

        # BUG FIX: alerta solo tiene sentido si está en deuda
        if es_al_dia:
            alerta_txt   = "—"
            alerta_color = "#888"
        elif r["alerta"]:
            alerta_txt   = "⚠ Sin pago reciente"
            alerta_color = "#c0392b"
        else:
            alerta_txt   = "Deuda reciente"
            alerta_color = "#e67e22"

        vals = [
            r.get("alumno_nombre")    or "—",
            r.get("tutor_nombre")     or "—",
            r.get("categoria_nombre") or "—",
            r["estado"],
            fmt_fecha(r.get("ultimo_pago")) or "Sin pagos",
            alerta_txt,
        ]
        colores_txt = [
            "#333",
            "#333",
            "#333",
            "#27ae60" if es_al_dia else "#c0392b",
            "#333",
            alerta_color,
        ]
        for col, (val, color_txt) in enumerate(zip(vals, colores_txt)):
            tk.Label(tabla, text=val, bg=bg, padx=6, pady=5,
                     font=("Arial", 9), fg=color_txt).grid(
                row=i, column=col, sticky="nsew", padx=1, pady=1)


def abrir_vista_alumnos_al_dia():
    v = tk.Toplevel()
    v.title("Estado de Alumnos")
    centrar(v, 900, 620)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text="Alumnos al Día / En Deuda",
             font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Filtros ───────────────────────────────────────────────────────────
    filtros = tk.LabelFrame(v, text="Filtros", font=("Arial", 9, "bold"),
                            padx=10, pady=6)
    filtros.pack(fill="x", padx=12, pady=(8, 4))

    fila1 = tk.Frame(filtros)
    fila1.pack(fill="x", pady=(0, 4))

    tk.Label(fila1, text="Mes:").pack(side="left")
    combo_mes = ttk.Combobox(fila1, state="readonly", width=14,
                              values=[m.capitalize() for m in MESES_VISIBLES])
    mes_hoy     = date.today().month - 1
    idx_visible = (MESES_VISIBLES.index(MESES[mes_hoy])
                   if MESES[mes_hoy] in MESES_VISIBLES else 0)
    combo_mes.current(idx_visible)
    combo_mes.pack(side="left", padx=6)

    tk.Label(fila1, text="Buscar:").pack(side="left", padx=(12, 0))
    entry_buscar = tk.Entry(fila1, width=26)
    entry_buscar.pack(side="left", padx=6)

    btn_buscar = tk.Button(fila1, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2",
                           command=lambda: recargar_alumnos_dia())
    btn_buscar.pack(side="left", padx=(0, 12))
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    fila2 = tk.Frame(filtros)
    fila2.pack(fill="x")

    tk.Label(fila2, text="Estado:").pack(side="left")
    var_estado = tk.StringVar(value="Todos")
    for txt in ("Todos", "Al día", "En deuda"):
        tk.Radiobutton(fila2, text=txt, variable=var_estado,
                       value=txt).pack(side="left", padx=4)

    # ── Tabla ─────────────────────────────────────────────────────────────
    contenedor = tk.Frame(v)
    contenedor.pack(fill="both", expand=True, padx=12, pady=4)

    # ── Pie ───────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=6)

    lbl_resumen = tk.Label(pie, text="", font=("Arial", 10))
    lbl_resumen.pack(side="left", padx=10)

    btn_pdf = tk.Button(pie, text="📄 Exportar PDF", bg="#8e44ad", fg="white",
                        font=("Arial", 9, "bold"), relief="groove", cursor="hand2")
    btn_pdf.pack(side="left", padx=6)
    _aplicar_hover(btn_pdf, "#8e44ad", "#7d3c98")

    btn_excel = tk.Button(pie, text="📊 Exportar Excel", bg="#1a6e3c", fg="white",
                          font=("Arial", 9, "bold"), relief="groove", cursor="hand2")
    btn_excel.pack(side="left", padx=6)
    _aplicar_hover(btn_excel, "#1a6e3c", "#145a32")

    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2", command=v.destroy)
    btn_cerrar.pack(side="left", padx=6)
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")

    btn_pdf_ref   = [btn_pdf]
    btn_excel_ref = [btn_excel]

    def recargar_alumnos_dia():
        _cargar_alumnos_al_dia(
            combo_mes, entry_buscar, var_estado,
            contenedor, lbl_resumen, btn_pdf_ref, btn_excel_ref)

    combo_mes.bind("<<ComboboxSelected>>", lambda e: recargar_alumnos_dia())
    entry_buscar.bind("<KeyRelease>",      lambda e: recargar_alumnos_dia())
    entry_buscar.bind("<Return>",          lambda e: recargar_alumnos_dia())
    var_estado.trace_add("write",          lambda *_: recargar_alumnos_dia())

    recargar_alumnos_dia()


# ══════════════════════════════════════════════
# VISTA: PAGOS MENSUALES
# ══════════════════════════════════════════════
def _cargar_pagos_mensuales(combo_mes, combo_anio, entry_buscar,
                             contenedor, lbl_total, combo_criterio):
    por_fecha_emision = (combo_criterio.current() == 0)
    mes_val           = combo_mes.get()
    anio_val          = combo_anio.get()

    rows = obtener_pagos_mensuales(
        mes               = None if mes_val  == "Todos" else mes_val,
        anio              = None if anio_val == "Todos" else anio_val,
        filtro            = entry_buscar.get().strip(),
        por_fecha_emision = por_fecha_emision
    )

    limpiar_frame(contenedor)
    outer, tabla = crear_tabla_scroll(contenedor)
    outer.pack(fill="both", expand=True)

    headers = ["Tutor", "Alumno", "Categoría", "Mes Cuota", "Fecha Emisión",
               "Monto", "Forma de Pago", "Descripción"]
    agregar_header(tabla, headers)

    grand_total = 0.0
    for i, r in enumerate(rows, start=1):
        bg    = fila_color(i)
        monto = float(r.get("monto") or 0)
        grand_total += monto
        vals = [
            r.get("tutor_nombre")     or "—",
            r.get("alumno_nombre")    or "—",
            r.get("categoria_nombre") or "—",
            (r.get("mes_pago")    or "—").capitalize(),
            fmt_fecha(r.get("fecha_emision")) or "—",
            fmt_monto(monto),
            (r.get("forma_pago") or "—").capitalize(),
            r.get("descripcion") or "—",
        ]
        for col, val in enumerate(vals):
            tk.Label(tabla, text=val, bg=bg, padx=6, pady=5,
                     font=("Arial", 9)).grid(
                row=i, column=col, sticky="nsew", padx=1, pady=1)

    if not rows:
        tk.Label(tabla,
                 text="No hay pagos registrados con los filtros actuales",
                 fg="gray", font=("Arial", 10), pady=40).grid(
            row=1, column=0, columnspan=len(headers))

    lbl_total.config(
        text=f"Registros: {len(rows)}   |   Total recaudado: {fmt_monto(grand_total)}")
    return rows


def _obtener_rows_pagos(combo_mes, combo_anio, entry_buscar, combo_criterio):
    resultado = obtener_pagos_mensuales(
        mes               = None if combo_mes.get()  == "Todos" else combo_mes.get(),
        anio              = None if combo_anio.get() == "Todos" else combo_anio.get(),
        filtro            = entry_buscar.get().strip(),
        por_fecha_emision = (combo_criterio.current() == 0)
    )
    return resultado


def abrir_vista_pagos_mensuales():
    v = tk.Toplevel()
    v.title("Pagos Mensuales")
    centrar(v, 1050, 660)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(v, bg="#d0d3d8")
    header.pack(fill="x")
    tk.Label(header, text="Pagos Mensuales", font=("Arial", 14, "bold"),
             bg="#d0d3d8", fg="#2c3e50").pack(side="left", padx=16, pady=8)

    # ── Filtros ───────────────────────────────────────────────────────────
    filtros = tk.LabelFrame(v, text="Filtros", font=("Arial", 9, "bold"),
                            padx=10, pady=6)
    filtros.pack(fill="x", padx=12, pady=(8, 4))

    tk.Label(filtros, text="Mes:").pack(side="left")
    combo_mes = ttk.Combobox(filtros, state="readonly", width=14,
                             values=["Todos"] + [m.capitalize()
                                                 for m in MESES_VISIBLES])
    combo_mes.current(1)
    combo_mes.pack(side="left", padx=6)

    tk.Label(filtros, text="Año:").pack(side="left")
    combo_anio = ttk.Combobox(
        filtros, state="readonly", width=8,
        values=["Todos"] + [str(y) for y in range(date.today().year, 2022, -1)])
    combo_anio.current(1)
    combo_anio.pack(side="left", padx=6)

    tk.Label(filtros, text="Agrupar por:").pack(side="left", padx=(12, 4))
    combo_criterio = ttk.Combobox(filtros, state="readonly", width=28,
                                  values=["Fecha de Emisión (Caja Real)",
                                          "Mes de la Cuota (Devengado)"])
    combo_criterio.current(0)
    combo_criterio.pack(side="left", padx=6)

    tk.Label(filtros, text="Buscar:").pack(side="left", padx=(12, 4))
    entry_buscar = tk.Entry(filtros, width=25)
    entry_buscar.pack(side="left", padx=6)

    btn_buscar = tk.Button(filtros, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2",
                           command=lambda: recargar_pagos())
    btn_buscar.pack(side="left", padx=6)
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    # ── Tabla ─────────────────────────────────────────────────────────────
    contenedor = tk.Frame(v)
    contenedor.pack(fill="both", expand=True, padx=12, pady=4)

    # ── Pie ───────────────────────────────────────────────────────────────
    pie = tk.Frame(v)
    pie.pack(pady=6)

    lbl_total = tk.Label(pie, text="", font=("Arial", 10, "bold"))
    lbl_total.pack(side="left", padx=10)

    btn_pdf = tk.Button(pie, text="📄 Exportar PDF", bg="#8e44ad", fg="white",
                        font=("Arial", 9, "bold"), relief="groove", cursor="hand2",
                        command=lambda: exportar_pdf_pagos_mensuales(
                            _obtener_rows_pagos(combo_mes, combo_anio,
                                                entry_buscar, combo_criterio),
                            combo_mes.get(), combo_anio.get(), combo_criterio.get()))
    btn_pdf.pack(side="left", padx=6)
    _aplicar_hover(btn_pdf, "#8e44ad", "#7d3c98")

    btn_excel = tk.Button(pie, text="📊 Exportar Excel", bg="#1a6e3c", fg="white",
                          font=("Arial", 9, "bold"), relief="groove", cursor="hand2",
                          command=lambda: exportar_excel_pagos_mensuales(
                              _obtener_rows_pagos(combo_mes, combo_anio,
                                                  entry_buscar, combo_criterio),
                              combo_mes.get(), combo_anio.get(), combo_criterio.get()))
    btn_excel.pack(side="left", padx=6)
    _aplicar_hover(btn_excel, "#1a6e3c", "#145a32")

    btn_cerrar = tk.Button(pie, text="✕ Cerrar", bg="#7f8c8d", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2", command=v.destroy)
    btn_cerrar.pack(side="left", padx=6)
    _aplicar_hover(btn_cerrar, "#7f8c8d", "#626f70")

    def recargar_pagos():
        _cargar_pagos_mensuales(combo_mes, combo_anio, entry_buscar,
                                contenedor, lbl_total, combo_criterio)

    combo_mes.bind("<<ComboboxSelected>>",      lambda e: recargar_pagos())
    combo_anio.bind("<<ComboboxSelected>>",     lambda e: recargar_pagos())
    combo_criterio.bind("<<ComboboxSelected>>", lambda e: recargar_pagos())
    entry_buscar.bind("<Return>",               lambda e: recargar_pagos())

    recargar_pagos()


# ══════════════════════════════════════════════
# PANTALLA PRINCIPAL
# ══════════════════════════════════════════════
def _limpiar_filtros_pantalla(combo_mes_filtro, combo_forma_filtro,
                               entry_buscar, var_parcial):
    combo_mes_filtro.current(0)
    combo_forma_filtro.current(0)
    var_parcial.set("Todos")
    entry_buscar.delete(0, tk.END)


def _refrescar_pantalla(contenedor_tabla, combo_mes_filtro, combo_forma_filtro,
                         entry_buscar, filtro_tipo, var_parcial):
    mes_val    = combo_mes_filtro.get()
    forma_val  = combo_forma_filtro.get()
    parc_val   = var_parcial.get()
    filtro_parc = True  if parc_val == "Parciales" \
             else False if parc_val == "Completos"  \
             else None

    _construir_tabla_recibos(
        contenedor_tabla,
        filtro_texto   = entry_buscar.get(),
        filtro_tipo    = filtro_tipo,
        filtro_mes     = None if mes_val   == "Todos" else mes_val.lower(),
        filtro_forma   = None if forma_val == "Todas" else forma_val.lower(),
        filtro_parcial = filtro_parc,
    )


def _mostrar_pantalla_recibos(parent, volver_callback, titulo, filtro_tipo=None):
    limpiar_frame(parent)

    # ── Header ────────────────────────────────────────────────────────────
    header = tk.Frame(parent, bg="#2c3e50")
    header.pack(fill="x")
    btn_volver = tk.Button(header, text="< Volver", command=volver_callback,
                           bg="#2c3e50", fg="white", relief="flat",
                           font=("Arial", 10), padx=10, cursor="hand2")
    btn_volver.pack(side="left", pady=8, padx=10)
    _aplicar_hover(btn_volver, "#2c3e50", "#1a252f")
    tk.Label(header, text=titulo, font=("Arial", 14, "bold"),
             bg="#2c3e50", fg="white").pack(side="left", padx=10)
    btn_gmail_cfg = tk.Button(header, text="⚙ Configurar Gmail",
                              bg="#EA4335", fg="white",
                              font=("Arial", 9), relief="groove",
                              padx=10, cursor="hand2",
                              command=abrir_config_gmail)
    btn_gmail_cfg.pack(side="right", pady=8, padx=10)
    _aplicar_hover(btn_gmail_cfg, "#EA4335", "#c0392b")

    # ══ ZONA SUPERIOR: dos columnas ══════════════════════════════════════
    panel_superior = tk.Frame(parent)
    panel_superior.pack(fill="x", padx=8, pady=(8, 4))

    # ── COLUMNA IZQUIERDA: sidebar de gestión ─────────────────────────────
    sidebar = tk.Frame(panel_superior, bg="#ecf0f1")
    sidebar.pack(side="left", fill="y", padx=(0, 8))

    BTN_FONT = ("Arial", 9, "bold")

    frame_recibos = tk.LabelFrame(sidebar, text="Gestión de Recibos",
                                  bg="#ecf0f1", font=("Arial", 9, "bold"),
                                  padx=6, pady=6)
    frame_recibos.pack(fill="x", padx=4, pady=(4, 6))

    btn_nuevo = tk.Button(frame_recibos, text="+ Nuevo Recibo",
                          bg="#27ae60", fg="white", font=BTN_FONT,
                          relief="groove", pady=5, cursor="hand2",
                          command=lambda: abrir_crear_recibo(
                              contenedor_tabla, filtro_tipo))
    btn_nuevo.pack(fill="x", pady=(0, 4))
    _aplicar_hover(btn_nuevo, "#27ae60", "#1e8449")

    btn_multiples = tk.Button(frame_recibos, text="+ Recibos Múltiples",
                              bg="#1e8449", fg="white", font=BTN_FONT,
                              relief="groove", pady=5, cursor="hand2",
                              command=lambda: abrir_crear_recibos_multiples(
                                  contenedor_tabla, filtro_tipo))
    btn_multiples.pack(fill="x")
    _aplicar_hover(btn_multiples, "#1e8449", "#176339")

    frame_alumnos = tk.LabelFrame(sidebar, text="Gestión de Alumnos",
                                  bg="#ecf0f1", font=("Arial", 9, "bold"),
                                  padx=6, pady=6)
    frame_alumnos.pack(fill="x", padx=4, pady=(0, 4))

    btn_deudores = tk.Button(frame_alumnos,
                             text=f"👥 Ver deudores de {MES_ACTUAL.capitalize()}",
                             bg="#e67e22", fg="white", font=BTN_FONT,
                             relief="groove", pady=5, cursor="hand2",
                             wraplength=180,
                             command=abrir_vista_deudores)
    btn_deudores.pack(fill="x", pady=(0, 4))
    _aplicar_hover(btn_deudores, "#e67e22", "#ca6f1e")

    btn_al_dia = tk.Button(frame_alumnos, text="✅ Alumnos al día",
                           bg="#27ae60", fg="white", font=BTN_FONT,
                           relief="groove", pady=5, cursor="hand2",
                           command=abrir_vista_alumnos_al_dia)
    btn_al_dia.pack(fill="x", pady=(0, 4))
    _aplicar_hover(btn_al_dia, "#27ae60", "#1e8449")

    btn_pagos_mens = tk.Button(frame_alumnos, text="📊 Pagos Mensuales",
                               bg="#8e44ad", fg="white", font=BTN_FONT,
                               relief="groove", pady=5, cursor="hand2",
                               command=abrir_vista_pagos_mensuales)
    btn_pagos_mens.pack(fill="x")
    _aplicar_hover(btn_pagos_mens, "#8e44ad", "#7d3c98")

    # ── COLUMNA DERECHA: filtros + acciones ───────────────────────────────
    panel_der = tk.Frame(panel_superior)
    panel_der.pack(side="left", fill="both", expand=True)

    # — Búsqueda y Filtros —
    filtros_frame = tk.LabelFrame(panel_der, text="Búsqueda y Filtros",
                                  font=("Arial", 9, "bold"), padx=10, pady=8)
    filtros_frame.pack(fill="x", pady=(0, 4))

    fila1 = tk.Frame(filtros_frame)
    fila1.pack(fill="x", pady=(0, 6))
    tk.Label(fila1, text="Buscar:").pack(side="left")
    entry_buscar = tk.Entry(fila1, width=50)
    entry_buscar.pack(side="left", padx=6)

    btn_buscar = tk.Button(fila1, text="Buscar", bg="#2c3e50", fg="white",
                           font=("Arial", 9, "bold"), relief="groove",
                           padx=10, cursor="hand2",
                           command=lambda: recargar())
    btn_buscar.pack(side="left", padx=(0, 4))
    _aplicar_hover(btn_buscar, "#2c3e50", "#1a252f")

    btn_limpiar = tk.Button(fila1, text="Limpiar", bg="#7f8c8d", fg="white",
                            font=("Arial", 9, "bold"), relief="groove",
                            padx=10, cursor="hand2",
                            command=lambda: limpiar())
    btn_limpiar.pack(side="left")
    _aplicar_hover(btn_limpiar, "#7f8c8d", "#626f70")

    fila2 = tk.Frame(filtros_frame)
    fila2.pack(fill="x")
    tk.Label(fila2, text="Mes:").pack(side="left")
    combo_mes_filtro = ttk.Combobox(
        fila2, state="readonly", width=13,
        values=["Todos"] + [m.capitalize() for m in MESES_VISIBLES])
    combo_mes_filtro.current(0)
    combo_mes_filtro.pack(side="left", padx=(4, 14))

    tk.Label(fila2, text="Forma de pago:").pack(side="left")
    combo_forma_filtro = ttk.Combobox(
        fila2, state="readonly", width=14,
        values=["Todos", "Efectivo", "Transferencia"])
    combo_forma_filtro.current(0)
    combo_forma_filtro.pack(side="left", padx=(4, 14))

    tk.Label(fila2, text="Estado pago:").pack(side="left")
    combo_parcial = ttk.Combobox(
        fila2, state="readonly", width=12,
        values=["Todos", "Completos", "Parciales"])
    combo_parcial.current(0)
    combo_parcial.pack(side="left", padx=(4, 0))

    # — Acciones de Tabla —
    acciones_frame = tk.LabelFrame(panel_der, text="Acciones de Tabla",
                                   font=("Arial", 9, "bold"), padx=10, pady=6)
    acciones_frame.pack(fill="x", pady=(0, 4))

    fila_acc = tk.Frame(acciones_frame)
    fila_acc.pack(fill="x")
    tk.Label(fila_acc, text="Con seleccionados:",
             font=("Arial", 9)).pack(side="left", padx=(0, 8))

    btn_pdf_sel = tk.Button(fila_acc, text="📄 PDF", bg="#2c3e50", fg="white",
                            font=("Arial", 9, "bold"), relief="groove",
                            padx=8, cursor="hand2",
                            command=lambda: _acciones_seleccionados(
                                _vars_check[0], _rows[0],
                                contenedor_tabla, filtro_tipo, "pdf"))
    btn_pdf_sel.pack(side="left", padx=3)
    _aplicar_hover(btn_pdf_sel, "#2c3e50", "#1a252f")

    btn_gmail_sel = tk.Button(fila_acc, text="✉ Gmail", bg="#EA4335", fg="white",
                              font=("Arial", 9, "bold"), relief="groove",
                              padx=8, cursor="hand2",
                              command=lambda: _acciones_seleccionados(
                                  _vars_check[0], _rows[0],
                                  contenedor_tabla, filtro_tipo, "gmail"))
    btn_gmail_sel.pack(side="left", padx=3)
    _aplicar_hover(btn_gmail_sel, "#EA4335", "#c0392b")

    btn_elim_sel = tk.Button(fila_acc, text="🗑 Eliminar", bg="#e74c3c", fg="white",
                             font=("Arial", 9, "bold"), relief="groove",
                             padx=8, cursor="hand2",
                             command=lambda: _acciones_seleccionados(
                                 _vars_check[0], _rows[0],
                                 contenedor_tabla, filtro_tipo, "eliminar"))
    btn_elim_sel.pack(side="left", padx=3)
    _aplicar_hover(btn_elim_sel, "#e74c3c", "#c0392b")

    leyenda = tk.Frame(fila_acc)
    leyenda.pack(side="right", padx=4)
    for txt, col in [("PDF = ver recibo", "#2c3e50"),
                     ("Gmail = enviar email", "#EA4335"),
                     ("🗑 = eliminar", "#e74c3c")]:
        tk.Label(leyenda, text=f"  {txt}  ", bg=col, fg="white",
                 font=("Arial", 7), padx=3).pack(side="left", padx=2)

    # ══ ZONA INFERIOR: tabla sola, ancho completo ═════════════════════════
    contenedor_tabla = tk.Frame(parent)
    contenedor_tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── referencias mutables para botones de acción masiva ────────────────
    _vars_check = [[]]
    _rows       = [[]]

    def recargar():
        parc_val    = combo_parcial.get()
        filtro_parc = True  if parc_val == "Parciales" \
                 else False if parc_val == "Completos"  \
                 else None
        mes_val   = combo_mes_filtro.get()
        forma_val = combo_forma_filtro.get()

        rows_tmp = obtener_recibos(
            entry_buscar.get(),
            mes=None if mes_val == "Todos" else mes_val.lower(),
            forma_pago=None if forma_val == "Todos" else forma_val.lower()
        )
        if filtro_tipo:
            rows_tmp = [r for r in rows_tmp if r.get("tipo_pago") == filtro_tipo]
        if filtro_parc is True:
            rows_tmp = [r for r in rows_tmp if int(r.get("pago_completo") or 1) == 0]
        elif filtro_parc is False:
            rows_tmp = [r for r in rows_tmp if int(r.get("pago_completo") or 1) == 1]

        _rows[0] = rows_tmp

        _construir_tabla_recibos(
            contenedor_tabla,
            filtro_texto   = entry_buscar.get(),
            filtro_tipo    = filtro_tipo,
            filtro_mes     = None if mes_val == "Todos" else mes_val.lower(),
            filtro_forma   = None if forma_val == "Todos" else forma_val.lower(),
            filtro_parcial = filtro_parc,
        )

    def limpiar():
        combo_mes_filtro.current(0)
        combo_forma_filtro.current(0)
        combo_parcial.current(0)
        entry_buscar.delete(0, tk.END)
        recargar()

    entry_buscar.bind("<Return>",                   lambda e: recargar())
    combo_mes_filtro.bind("<<ComboboxSelected>>",   lambda e: recargar())
    combo_forma_filtro.bind("<<ComboboxSelected>>", lambda e: recargar())
    combo_parcial.bind("<<ComboboxSelected>>",      lambda e: recargar())

    recargar()


# ══════════════════════════════════════════════
# PUNTOS DE ENTRADA PÚBLICOS
# ══════════════════════════════════════════════
def mostrar_recibos(parent, volver_callback):
    _mostrar_pantalla_recibos(parent, volver_callback,
                              "Recibos de Pago", filtro_tipo=None)


def mostrar_pago_cuotas(parent, volver_callback):
    _mostrar_pantalla_recibos(parent, volver_callback,
                              "Pago de Cuotas", filtro_tipo="pago_cuota")


def mostrar_pagos_varios(parent, volver_callback):
    _mostrar_pantalla_recibos(parent, volver_callback,
                              "Pagos Varios", filtro_tipo="otros_pagos")