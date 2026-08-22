### codigo que tem q apertar pra gerar grafico

import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# Função para calcular a resistividade aparente
def calcular_resistividade_aparente():
    av1 = float(av1_entry.get())
    i1 = float(i1_entry.get())
    constante = float(constante_entry.get())
    espacamento_ab_2 = float(espacamento_entry.get())

    # Calcular resistividade aparente
    res_aparente = (av1 / i1) * constante

    # Adicionar o resultado à lista
    resultados.append(res_aparente)
    espacamentos.append(espacamento_ab_2)  # Adicionar o valor de "Espaçamento Ab/2" à lista

    # Atualizar rótulo com os resultados anteriores
    resultado_label.config(text="Resistividade Aparente: {:.2f}".format(res_aparente))

# Função para resetar dados
def resetar_dados():
    global resultados, espacamentos
    resultados = []
    espacamentos = []

# Função para resetar o último cálculo do gráfico
def resetar_ultimo_calculo():
    global resultados, espacamentos

    if resultados and espacamentos:
        resultados.pop()
        espacamentos.pop()

# Função para visualizar o gráfico
def visualizar_grafico():
    if resultados and espacamentos:
        # Criar uma nova janela
        janela_grafico = Toplevel(root)
        janela_grafico.title('Gráfico da Resistividade Aparente')

        # Configurar o gráfico na nova janela
        fig, ax = plt.subplots()
        ax.plot(espacamentos, resultados, marker='o')
        ax.set_title('Resultados da Resistividade Aparente')
        ax.set_xlabel('Espaçamento Ab/2')
        ax.set_ylabel('Resistividade')
        ax.grid(True)

        # Adicionar o gráfico à nova janela
        canvas = FigureCanvasTkAgg(fig, master=janela_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack()

        # Função para salvar a imagem
        def salvar_imagem():
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
            if file_path:
                fig.savefig(file_path)
                messagebox.showinfo("Salvo", f"A imagem foi salva em:\n{file_path}")

        # Botão para salvar a imagem
        salvar_button = tk.Button(janela_grafico, text="Salvar Imagem", command=salvar_imagem, font=fonte)
        salvar_button.pack()

# Inicializar a lista de resultados e espacamentos
resultados = []
espacamentos = []

# Criar a janela principal
root = tk.Tk()
root.title("Calculadora de Resistividade Aparente")

# Criar frame
frame = tk.Frame(root)
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

constante_label = tk.Label(frame, text="Fator Geometrico:", font=fonte)
constante_label.pack()

constante_entry = tk.Entry(frame, font=fonte)
constante_entry.pack()

espacamento_label = tk.Label(frame, text="Espaçamento Ab/2:", font=fonte)
espacamento_label.pack()

espacamento_entry = tk.Entry(frame, font=fonte)
espacamento_entry.pack()

calcular_button = tk.Button(frame, text="Calcular", command=calcular_resistividade_aparente, font=fonte)
calcular_button.pack()

resetar_button = tk.Button(frame, text="Resetar Dados", command=resetar_dados, font=fonte)
resetar_button.pack()

resetar_ultimo_button = tk.Button(frame, text="Resetar Último Cálculo", command=resetar_ultimo_calculo, font=fonte)
resetar_ultimo_button.pack()

visualizar_button = tk.Button(frame, text="Visualizar Gráfico", command=visualizar_grafico, font=fonte)
visualizar_button.pack()

resultado_label = tk.Label(frame, text="", font=fonte)
resultado_label.pack()

# Executar aplicativo
root.mainloop()
