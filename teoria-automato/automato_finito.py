import os
from graphviz import Digraph

class AutomatoFinito:
    def __init__(self, estados, alfabeto, transicoes, estado_inicial, estados_aceitacao):
        self.estados = estados
        self.alfabeto = alfabeto
        self.transicoes = transicoes
        self.estado_inicial = estado_inicial
        self.estados_aceitacao = estados_aceitacao

    def desenhar(self, nome_arquivo):
        #Gera uma imagem do automato via Graphviz.
        dot = Digraph()
        dot.attr(rankdir='LR')

        for estado in self.estados:
            if estado in self.estados_aceitacao:
                dot.node(str(estado), shape='doublecircle')
            else:
                dot.node(str(estado))

        for (estado, simbolo), proximo_estado in self.transicoes.items():
            dot.edge(str(estado), str(proximo_estado), label=simbolo)

        dot.attr('node', shape='point')
        dot.edge('', str(self.estado_inicial))
        
        # Salva sempre no static local do projeto.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(base_dir, 'static')
        os.makedirs(static_dir, exist_ok=True)
        out_path = os.path.join(static_dir, nome_arquivo)
        dot.render(out_path, format='png', cleanup=True)
        return f'{nome_arquivo}.png'
