#utils/ui_helpers.py

import os
import sys
import shutil
import subprocess

import tkinter as tk
from tkinter import filedialog


def limpiar_frame(frame):
    for w in frame.winfo_children():
        w.destroy()


def centrar(ventana, ancho, alto, margen=40):
    ventana.update_idletasks()
    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    ancho_final = min(ancho, sw - margen * 2)
    alto_final  = min(alto,  sh - margen * 2)
    x = (sw - ancho_final) // 2
    y = (sh - alto_final)  // 2
    ventana.geometry(f"{ancho_final}x{alto_final}+{x}+{y}")


def fmt_monto(valor):
    try:
        resultado = f"${float(valor):.2f}"
    except Exception:
        resultado = "$0.00"
    return resultado


def label_tipo_pago(tipo):
    resultado = "Pago de Cuota" if tipo == "pago_cuota" else "Otros Pagos"
    return resultado


# FIX BUG 3: Para pagos parciales el total a mostrar en la tabla es monto_pagado
# (lo que realmente se cobró), no monto + mora - descuento (el total completo).
# Para pagos completos, monto_pagado ya viene calculado con mora y descuento
# desde crear_recibo, así que se usa directamente.
def calcular_total(recibo):
    monto_pagado  = recibo.get("monto_pagado")
    pago_completo = int(recibo.get("pago_completo") or 1)

    if monto_pagado is not None:
        resultado = float(monto_pagado)
    elif pago_completo == 1:
        resultado = (
            float(recibo.get("monto")     or 0)
            - float(recibo.get("descuento") or 0)
            + float(recibo.get("mora")      or 0)
        )
    else:
        resultado = float(recibo.get("monto") or 0)

    return resultado


def abrir_archivo(ruta):
    if sys.platform.startswith("win"):
        os.startfile(ruta)
    elif sys.platform == "darwin":
        subprocess.call(["open", ruta])
    else:
        subprocess.call(["xdg-open", ruta])


def dialogo_guardar_o_abrir(ruta_tmp, nombre_sugerido):
    extension = os.path.splitext(nombre_sugerido)[1].lower()
    accion    = [None]

    ventana = tk.Toplevel()
    ventana.title("Archivo listo")
    ventana.resizable(False, False)
    centrar(ventana, 380, 170)
    ventana.grab_set()

    tk.Label(
        ventana,
        text="El archivo está listo.\n¿Qué querés hacer con él?",
        font=("Arial", 11),
        pady=14,
    ).pack()

    botones = tk.Frame(ventana)
    botones.pack(pady=8)

    def _abrir():
        accion[0] = "abrir"
        ventana.destroy()

    def _guardar():
        accion[0] = "guardar"
        ventana.destroy()

    def _cancelar():
        ventana.destroy()

    tk.Button(
        botones, text="👁 Abrir", bg="#2c3e50", fg="white",
        width=10, command=_abrir,
    ).pack(side="left", padx=8)
    tk.Button(
        botones, text="💾 Guardar", bg="#1a6e3c", fg="white",
        width=10, command=_guardar,
    ).pack(side="left", padx=8)
    tk.Button(
        botones, text="Cancelar", bg="#95a5a6", fg="white",
        width=10, command=_cancelar,
    ).pack(side="left", padx=8)

    ventana.wait_window()

    if accion[0] == "abrir":
        abrir_archivo(ruta_tmp)
    elif accion[0] == "guardar":
        if extension == ".pdf":
            tipos = [("PDF", "*.pdf")]
        elif extension in (".xlsx", ".xls"):
            tipos = [("Excel", "*.xlsx")]
        else:
            tipos = [("Todos", "*.*")]

        destino = filedialog.asksaveasfilename(
            defaultextension = extension,
            filetypes        = tipos,
            initialfile      = nombre_sugerido,
        )
        if destino:
            shutil.copy2(ruta_tmp, destino)