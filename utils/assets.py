import os
import sys


def get_assets_path():
    resultado = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return resultado


def get_logo_path():
    resultado = os.path.join(get_assets_path(), "utils", "logo.png")
    return resultado