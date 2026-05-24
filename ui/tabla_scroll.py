import tkinter as tk
from tkinter import ttk


def _on_mousewheel(event, canvas):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def crear_tabla_scroll(parent, bg_header="#2c3e50", fg_header="white"):
    outer = tk.Frame(parent)

    canvas = tk.Canvas(outer, highlightthickness=0)
    scroll_y = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    scroll_x = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)

    tabla_frame = tk.Frame(canvas)

    tabla_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=tabla_frame, anchor="nw")
    canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    scroll_y.pack(side="right", fill="y")
    scroll_x.pack(side="bottom", fill="x")
    canvas.pack(side="left", fill="both", expand=True)

    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: _on_mousewheel(ev, canvas)))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return outer, tabla_frame


def agregar_header(tabla_frame, headers, bg="#2c3e50", fg="white"):
    for col, texto in enumerate(headers):
        tk.Label(
            tabla_frame, text=texto,
            font=("Arial", 10, "bold"),
            bg=bg, fg=fg,
            padx=10, pady=6
        ).grid(row=0, column=col, sticky="nsew", padx=1, pady=(0, 2))


def fila_color(i):
    return "#f9f9f9" if i % 2 == 0 else "white"