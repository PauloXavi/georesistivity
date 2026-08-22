### CODIGO ORIGINAL

import tkinter as tk

def calcular_resistividade_aparente():
    a1 = float(av1_entry.get())
    I1 = float(i1_entry.get())
    a2 = float(av2_entry.get())
    I2 = float(i2_entry.get())
    a3 = float(av3_entry.get())
    I3 = float(i3_entry.get())

    mediaa = ((a1 + a2 + a3) / 3)
    mediai = ((I1 + I2 + I3) / 3)

    c = float(constante_entry.get())
    div = mediaa / mediai

    res = div * c

    resultado_label.config(text="Resistividade Aparente: {:.2f}".format(res))

app = tk.Tk()
app.title("Calculadora de Resistividade Aparente")

# Ajustar o tamanho do aplicativo
largura_tela = app.winfo_screenwidth()
altura_tela = app.winfo_screenheight()
app.geometry(f"{16}x{9}")

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

av2_label = tk.Label(frame, text="AV 2:", font=fonte)
av2_label.pack()

av2_entry = tk.Entry(frame, font=fonte)
av2_entry.pack()

i2_label = tk.Label(frame, text="I 2:", font=fonte)
i2_label.pack()

i2_entry = tk.Entry(frame, font=fonte)
i2_entry.pack()

av3_label = tk.Label(frame, text="AV 3:", font=fonte)
av3_label.pack()

av3_entry = tk.Entry(frame, font=fonte)
av3_entry.pack()

i3_label = tk.Label(frame, text="I 3:", font=fonte)
i3_label.pack()

i3_entry = tk.Entry(frame, font=fonte)
i3_entry.pack()

constante_label = tk.Label(frame, text="Fator Geometrico:", font=fonte)
constante_label.pack()

constante_entry = tk.Entry(frame, font=fonte)
constante_entry.pack()  

calcular_button = tk.Button(frame, text="Calcular", command=calcular_resistividade_aparente, font=fonte)
calcular_button.pack()

resultado_label = tk.Label(frame, text="", font=fonte)
resultado_label.pack()

app.mainloop()
