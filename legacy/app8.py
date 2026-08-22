### codigo de criação de aplicativo

from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.screen import MDScreen
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


class RootWidget(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Widgets
        self.av1_label = MDLabel(text="AV 1:")
        self.av1_entry = MDTextField()

        self.i1_label = MDLabel(text="I 1:")
        self.i1_entry = MDTextField()

        self.constante_label = MDLabel(text="Fator Geometrico:")
        self.constante_entry = MDTextField()

        self.espacamento_label = MDLabel(text="Espaçamento Ab/2:")
        self.espacamento_entry = MDTextField()

        self.calcular_button = MDRaisedButton(text="Calcular", on_press=self.calcular_resistividade_aparente)
        self.resetar_button = MDRaisedButton(text="Resetar Dados", on_press=self.resetar_dados)
        self.visualizar_button = MDRaisedButton(text="Visualizar Gráfico", on_press=self.visualizar_grafico)

        self.resultado_label = MDLabel(text="Resistividade Aparente: ")

        # Adicionando widgets ao layout
        self.add_widget(self.av1_label)
        self.add_widget(self.av1_entry)
        self.add_widget(self.i1_label)
        self.add_widget(self.i1_entry)
        self.add_widget(self.constante_label)
        self.add_widget(self.constante_entry)
        self.add_widget(self.espacamento_label)
        self.add_widget(self.espacamento_entry)
        self.add_widget(self.calcular_button)
        self.add_widget(self.resetar_button)
        self.add_widget(self.visualizar_button)
        self.add_widget(self.resultado_label)

    def calcular_resistividade_aparente(self, instance):
        av1 = float(self.av1_entry.text)
        i1 = float(self.i1_entry.text)
        constante = float(self.constante_entry.text)
        espacamento_ab_2 = float(self.espacamento_entry.text)

        # Adicione aqui a lógica para calcular a resistividade aparente
        res_aparente = (av1 / i1) * constante

        # Atualizar rótulo com os resultados anteriores
        self.resultado_label.text = f"Resistividade Aparente: {res_aparente:.2f}"

    def resetar_dados(self, instance):
        # Adicione aqui a lógica para resetar os dados
        pass

    def visualizar_grafico(self, instance):
        # Adicione aqui a lógica para visualizar o gráfico
        pass


class MyApp(MDApp):
    def build(self):
        return RootWidget()


if __name__ == '__main__':
    MyApp().run()
