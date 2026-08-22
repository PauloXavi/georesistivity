### codigo de com reset de dados

import tkinter as tk
import matplotlib.pyplot as plt

# Função para calcular a resistividade aparente
def calcular_resistividade_aparente():
    av1 = float(av1_entry.get())
    i1 = float(i1_entry.get())
    constante = float(constante_entry.get())

    # Calcular resistividade aparente
    res_aparente = (av1 / i1) * constante

    # Adicionar o resultado à lista
    resultados.append(res_aparente)

    # Atualizar rótulo com os resultados anteriores
    resultado_label.config(text="Resistividade Aparente: {:.2f}".format(res_aparente))

    # Atualizar o gráfico
    atualizar_grafico()

# Função para resetar dados
def resetar_dados():
    global resultados
    resultados = []
    plt.clf()  # Limpar o gráfico
    plt.title('Resultados da Resistividade Aparente')
    plt.xlabel('Espaçamento Ab/2')
    plt.ylabel('Resistividade')
    plt.grid(True)
    plt.draw()

# Função para atualizar o gráfico
def atualizar_grafico():
    plt.plot(resultados, marker='o')
    plt.draw()
    plt.pause(0.1)  # Adicionar um pequeno atraso para permitir a atualização da GUI

# Inicializar a lista de resultados
resultados = []

# Criar a janela principal
app = tk.Tk()
app.title("Calculadora de Resistividade Aparente")

# Ajustar o tamanho do aplicativo
largura_tela = app.winfo_screenwidth()
altura_tela = app.winfo_screenheight()
app.geometry(f"{largura_tela}x{altura_tela}")

# Criar frame
frame = tk.Frame(app)
frame.pack(expand=True, fill='both')

# Ajustar o tamanho da fonte para telas menores
fonte = ('Helvetica', 12)

# Criar widgets
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

resetar_button = tk.Button(frame, text="Resetar Dados", command=resetar_dados, font=fonte)
resetar_button.pack()

resultado_label = tk.Label(frame, text="", font=fonte)
resultado_label.pack()

# Configurar gráfico inicial
plt.ion()  # Modo interativo para gráficos contínuos
atualizar_grafico()

# Executar aplicativo
app.mainloop()
