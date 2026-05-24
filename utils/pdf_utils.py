import os
import tempfile

from tkinter import messagebox

from models.recibos import obtener_recibo
from utils.pdf_recibo import generar_pdf_recibo
from utils.ui_helpers import dialogo_guardar_o_abrir


def generar_pdf(recibo_id):
    datos     = obtener_recibo(recibo_id)
    resultado = None
    if not datos:
        messagebox.showerror("Error", f"No se encontró el recibo #{recibo_id}")
    else:
        ruta = os.path.join(tempfile.gettempdir(), f"recibo_{recibo_id}.pdf")
        generar_pdf_recibo(datos, ruta)
        resultado = ruta
    return resultado


def abrir_pdf(recibo_id):
    ruta = generar_pdf(recibo_id)
    if ruta:
        dialogo_guardar_o_abrir(ruta, f"recibo_{recibo_id}.pdf")