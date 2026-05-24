import os
import smtplib
import webbrowser
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import tkinter as tk
from tkinter import messagebox

from models.recibos import obtener_recibo
from utils.fecha import fmt_fecha
from utils.pdf_utils import generar_pdf
from utils.ui_helpers import abrir_archivo, calcular_total, centrar, fmt_monto, label_tipo_pago


_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "config_gmail.txt"
)


# ══════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════
def leer_config_gmail():
    resultado = ("", "")
    try:
        with open(_CONFIG_FILE) as f:
            lineas = f.read().splitlines()
            mail   = lineas[0].strip() if lineas else ""
            pw     = lineas[1].strip() if len(lineas) > 1 else ""
            resultado = (mail, pw)
    except FileNotFoundError:
        pass
    return resultado


def guardar_config_gmail(email, pw):
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    with open(_CONFIG_FILE, "w") as f:
        f.write(f"{email}\n{pw}\n")


# ══════════════════════════════════════════════
# PROBAR CONEXIÓN
# ══════════════════════════════════════════════
def probar_conexion_gmail(mail, pw, lbl, callback_ok):
    resultado = False
    if not mail or not pw:
        lbl.config(text="Completá ambos campos", fg="red")
    else:
        lbl.config(text="Probando conexión…", fg="#555")
        lbl.update()
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as s:
                s.login(mail, pw)
            guardar_config_gmail(mail, pw)
            lbl.config(text="✅ Conexión exitosa. Configuración guardada.", fg="green")
            resultado = True
            if callback_ok:
                callback_ok()
        except smtplib.SMTPAuthenticationError:
            lbl.config(
                text="❌ Credenciales incorrectas. ¿Usaste la Contraseña de Aplicación?",
                fg="red"
            )
        except Exception as e:
            lbl.config(text=f"❌ Error: {e}", fg="red")
    return resultado


# ══════════════════════════════════════════════
# ENVÍO MASIVO
# ══════════════════════════════════════════════
def ejecutar_envio_gmail_masivo(ids_seleccionados, lbl_estado, ventana):
    mail_origen, pw = leer_config_gmail()
    if not mail_origen or not pw:
        lbl_estado.config(text="❌ Gmail no configurado", fg="red")
        return

    NOMBRE_INSTITUCION = "Club Siglo XXI"
    from_header        = f"{NOMBRE_INSTITUCION} <{mail_origen}>"

    enviados = 0
    errores  = []

    for recibo_id in ids_seleccionados:
        datos = obtener_recibo(recibo_id)
        if not datos:
            errores.append(f"#{recibo_id}: no encontrado")
            continue

        email_dest = datos.get("email") or ""
        partes_dest     = email_dest.split("@")
        dominio_partes  = partes_dest[1].split(".") if len(partes_dest) == 2 else []
        email_dest_valido = (
            len(partes_dest) == 2
            and len(partes_dest[0]) > 0
            and len(dominio_partes) >= 2
            and all(len(p) > 0 for p in dominio_partes)
            and len(dominio_partes[-1]) >= 2
        )
        if not email_dest_valido:
            errores.append(
                f"#{recibo_id} ({datos.get('alumno_nombre', '')}): email inválido o sin email"
            )
            continue

        ruta = generar_pdf(recibo_id)
        if not ruta:
            errores.append(f"#{recibo_id}: error al generar PDF")
            continue

        total   = calcular_total(datos)
        mes_txt = ""
        if datos.get("mes_pago"):
            mes_txt = f" — Mes: {datos.get('mes_pago', '').capitalize()}"

        asunto = (
            f"Recibo de pago - {datos.get('alumno_nombre', '')} "
            f"- {label_tipo_pago(datos.get('tipo_pago', ''))}"
        )
        cuerpo = (
            f"Estimado/a,\n\n"
            f"Adjuntamos el recibo de pago de {datos.get('alumno_nombre', '')}.\n"
            f"Tipo: {label_tipo_pago(datos.get('tipo_pago', ''))}{mes_txt}\n"
            f"Fecha: {fmt_fecha(datos.get('fecha_pago', '')) or '—'}"
            f"  |  Total: {fmt_monto(total)}\n\n"
            f"Muchas gracias.\n{NOMBRE_INSTITUCION}"
        )

        lbl_estado.config(
            text=f"Enviando {enviados + 1}/{len(ids_seleccionados)}…",
            fg="#555"
        )
        lbl_estado.update()

        try:
            msg            = MIMEMultipart()
            msg["From"]    = from_header
            msg["To"]      = email_dest
            msg["Subject"] = asunto
            msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

            with open(ruta, "rb") as f:
                parte = MIMEBase("application", "octet-stream")
                parte.set_payload(f.read())
            encoders.encode_base64(parte)
            parte.add_header(
                "Content-Disposition",
                f'attachment; filename="recibo_{recibo_id}.pdf"'
            )
            msg.attach(parte)

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
                smtp.login(mail_origen, pw)
                smtp.sendmail(mail_origen, email_dest, msg.as_string())
            enviados += 1

        except Exception as e:
            errores.append(f"#{recibo_id}: {e}")

    if errores:
        resumen = f"Enviados: {enviados}. Errores:\n" + "\n".join(errores)
        messagebox.showwarning("Envío con errores", resumen)
    else:
        lbl_estado.config(text=f"✅ {enviados} recibo(s) enviados", fg="green")
        ventana.after(1800, ventana.destroy)