import itertools
from graphviz import Digraph
from automato_finito import AutomatoFinito
from afd import AFD

# Símbolos reconhecidos como epsilon (transição vazia)
_EPSILON = {"&", "ε", "eps", "epsilon", "lambda", "λ"}


def _eh_epsilon(simbolo):
    return simbolo in _EPSILON


class AFN(AutomatoFinito):

    # ─────────────────────────────────────────────
    #  EPSILON-FECHAMENTO
    # ─────────────────────────────────────────────

    def epsilon_fechamento(self, estados):
        """Retorna o epsilon-fechamento de um conjunto de estados.

        O epsilon-fechamento de um estado q é o conjunto de todos os estados
        alcançáveis a partir de q usando apenas transições epsilon (incluindo
        o próprio q).
        """
        fechamento = set(estados)
        pilha = list(estados)

        while pilha:
            estado = pilha.pop()
            for simbolo, destinos in self._transicoes_epsilon_de(estado):
                for dest in destinos:
                    if dest not in fechamento:
                        fechamento.add(dest)
                        pilha.append(dest)

        return frozenset(fechamento)

    def _transicoes_epsilon_de(self, estado):
        """Gera pares (simbolo, destinos) onde o símbolo é epsilon."""
        for (e, s), destinos in self.transicoes.items():
            if e == estado and _eh_epsilon(s):
                yield s, destinos

    # CONVERSÃO AFN-& p/ AFD
    def converter_para_afd(self):
        """Construção de subconjuntos com epsilon-fechamento.

        Algoritmo:
        1. Estado inicial do AFD = &-fechamento({estado_inicial do AFN})
        2. Para cada estado (conjunto) e cada símbolo do alfabeto real:
           a. Mover: alcança todos os destinos via símbolo
           b. Fechar: aplica &-fechamento sobre o resultado
        3. Um estado do AFD é de aceitação se contém algum estado
           de aceitação do AFN.
        """
        # Alfabeto real: exclui símbolos epsilon
        alfabeto_real = {s for s in self.alfabeto if not _eh_epsilon(s)}

        estado_inicial_afd = self.epsilon_fechamento({self.estado_inicial})

        fila = [estado_inicial_afd]
        visitados = {estado_inicial_afd}
        novas_transicoes = {}
        estados_aceitacao_afd = set()

        #Mapeia frozenset → nome legível
        def nome(conj):
            if not conj:
                return "∅"
            return "".join(sorted(conj))

        estado_map = {estado_inicial_afd: nome(estado_inicial_afd)}

        while fila:
            conjunto_atual = fila.pop(0)
            nome_atual = estado_map[conjunto_atual]

            #Verifica aceitação
            if conjunto_atual & self.estados_aceitacao:
                estados_aceitacao_afd.add(nome_atual)

            for simbolo in sorted(alfabeto_real):
                #Mover: todos os destinos via 'simbolo' a partir do conjunto
                alcancados = set()
                for estado in conjunto_atual:
                    alcancados.update(self.transicoes.get((estado, simbolo), []))

                #Fechar: &-fechamento do resultado
                novo_conjunto = self.epsilon_fechamento(alcancados)

                if not novo_conjunto:
                    #Transição morta → aponta para estado-morto D
                    novas_transicoes[(nome_atual, simbolo)] = "D"
                    continue

                if novo_conjunto not in estado_map:
                    estado_map[novo_conjunto] = nome(novo_conjunto)
                    visitados.add(novo_conjunto)
                    fila.append(novo_conjunto)

                novas_transicoes[(nome_atual, simbolo)] = estado_map[novo_conjunto]

        estados_afd = set(estado_map.values())
        estado_inicial_nome = estado_map[estado_inicial_afd]

        #### Estado morto D ####
        # Verifica se alguma transição aponta para D, ou se algum estado
        # existente ainda está sem transição para algum símbolo.
        # Em ambos os casos, D é adicionado com auto-loops em todo o alfabeto.
        precisa_D = any(d == "D" for d in novas_transicoes.values())
        if not precisa_D:
            for e in estados_afd:
                for s in sorted(alfabeto_real):
                    if (e, s) not in novas_transicoes:
                        precisa_D = True
                        break
                if precisa_D:
                    break

        if precisa_D:
            estados_afd.add("D")
            #Preenche transições faltantes de todos os estados para D
            for e in list(estados_afd):
                for s in sorted(alfabeto_real):
                    if (e, s) not in novas_transicoes:
                        novas_transicoes[(e, s)] = "D"
            #D faz auto-loop em todo símbolo
            for s in sorted(alfabeto_real):
                novas_transicoes[("D", s)] = "D"

        return AFD(
            estados_afd,
            alfabeto_real,
            novas_transicoes,
            estado_inicial_nome,
            estados_aceitacao_afd,
        )

    """Aceita a palavra se existir algum caminho que leve a estado de aceitação.

        Usa ε-fechamento a cada passo para considerar transições vazias.
        """
    def aceitar_palavra(self, palavra):
        # Estado inicial expandido pelo ε-fechamento
        estados_atuais = self.epsilon_fechamento({self.estado_inicial})
        return self._aceita_conjunto(estados_atuais, palavra)

    def _aceita_conjunto(self, estados_atuais, palavra):
        """Simula o AFN-ε sobre um conjunto de estados correntes."""
        if not palavra:
            # Aceita se algum estado atual for de aceitação
            return bool(estados_atuais & self.estados_aceitacao)

        simbolo = palavra[0]
        proximos = set()
        for estado in estados_atuais:
            proximos.update(self.transicoes.get((estado, simbolo), []))

        # Aplica ε-fechamento após cada movimento
        proximos_fechados = self.epsilon_fechamento(proximos)
        return self._aceita_conjunto(proximos_fechados, palavra[1:])

    # Mantém compatibilidade com chamadas diretas recursivas legadas
    def _aceita_palavra_recursivo(self, estado_atual, palavra):
        estados = self.epsilon_fechamento({estado_atual})
        return self._aceita_conjunto(estados, palavra)

    """Gera todas as palavras do alfabeto até tamanho_max, incluindo vazia."""
    def gerar_palavras_iter(self, alfabeto, tamanho_max):
        palavras = [""]  # Palavra vazia
        for tamanho in range(1, tamanho_max + 1):
            palavras.extend(
                "".join(p) for p in itertools.product(alfabeto, repeat=tamanho)
            )
        return palavras
    
    """Compara aceitações do AFN e do AFD em palavras de até comprimento 5.
        Usa apenas o alfabeto real (sem epsilon) para gerar as palavras de teste.
    """
    def verificar_equivalencia(self, afd):
        alfabeto_real = [s for s in self.alfabeto if not _eh_epsilon(s)]
        palavras_teste = self.gerar_palavras_iter(alfabeto_real, 5)

        for palavra in palavras_teste:
            aceita_afn = self.aceitar_palavra(palavra)
            aceita_afd = afd.aceita_palavra(palavra)
            if aceita_afn != aceita_afd:
                return False
        return True
    
    """Desenha o AFN com transições, incluindo as epsilon (tracejadas)."""
    def desenhar(self, nome_arquivo):
        dot = Digraph()
        dot.attr(rankdir="LR")

        for estado in self.estados:
            if estado in self.estados_aceitacao:
                dot.node(str(estado), shape="doublecircle")
            else:
                dot.node(str(estado))

        for (estado, simbolo), proximos_estados in self.transicoes.items():
            #Transições epsilon são desenhadas tracejadas para clareza visual
            estilo = "dashed" if _eh_epsilon(simbolo) else "solid"
            rotulo = "ε" if _eh_epsilon(simbolo) else simbolo
            for proximo in proximos_estados:
                dot.edge(str(estado), str(proximo), label=rotulo, style=estilo)

        dot.attr("node", shape="point")
        dot.edge("", str(self.estado_inicial))

        dot.render(f"static/{nome_arquivo}", format="png", cleanup=True)
        return f"{nome_arquivo}.png"
