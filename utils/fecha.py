# utils/fecha.py


def fmt_fecha(valor):
    """
    ISO (YYYY-MM-DD) → argentino (DD/MM/YYYY).
    Devuelve "" si el valor es None o vacío, "?" si el formato es inválido.
    Esto permite usar: fmt_fecha(x) or "texto alternativo"
    """
    resultado = ""
    if valor:
        partes = str(valor).strip().split("-")
        resultado = f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else "?"
    return resultado


def arg_a_iso(valor):
    """
    Argentino (DD/MM/YYYY) → ISO (YYYY-MM-DD).
    Devuelve el valor sin cambios si no tiene el formato esperado.
    """
    resultado = valor
    if valor:
        partes = str(valor).strip().split("/")
        if len(partes) == 3:
            resultado = f"{partes[2]}-{partes[1]}-{partes[0]}"
    return resultado