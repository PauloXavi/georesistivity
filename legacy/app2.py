### CODIGO COM APENAS A1 E I1###

import tkinter as tk

def calcular_resistividade_aparente():
    av1 = float(av1_entry.get())
    i1 = float(i1_entry.get())
    constante = float(constante_entry.get())

    res_aparente = (av1 / i1) * constante

    resultado_label.config(text="Resistividade Aparente: {:.2f}".format(res_aparente))

app = tk.Tk()
app.title("Calculadora de Resistividade Aparente")

# Ajustar o tamanho do aplicativo
largura_tela = app.winfo_screenwidth()
altura_tela = app.winfo_screenheight()
app.geometry(f"{largura_tela}x{altura_tela}")

frame = tk.Frame(app)
frame.pack(expand=True, fill='both')

# Ajustar o tamanho da fonte para telas menores
fonte = ('Helvetica', 12)

av1_label = tk.Label(frame, text="AV 1:", font=fonte)
av1_label.pack()

av1_entry = tk.Entry(frame, font=fonte)
av1_entry.pack()

i1_label = tk.Label(frame, text="I 1:", font=fonte)
i1_label.pack()

i1_entry = tk.Entry(frame, font=fonte)
i1_entry.pack()

constante_label = tk.Label(frame, text="Constante:", font=fonte)
constante_label.pack()

constante_entry = tk.Entry(frame, font=fonte)
constante_entry.pack()

calcular_button = tk.Button(frame, text="Calcular", command=calcular_resistividade_aparente, font=fonte)
calcular_button.pack()

resultado_label = tk.Label(frame, text="", font=fonte)
resultado_label.pack()

app.mainloop()
