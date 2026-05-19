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
        
        dot.render(f'static/{nome_arquivo}', format='png', cleanup=True)
        return f'{nome_arquivo}.png'
