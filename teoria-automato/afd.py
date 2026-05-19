from automato_finito import AutomatoFinito


class AFD(AutomatoFinito):

    """Simula o AFD de forma determinística.
        Retorna False imediatamente se:
        - O símbolo não pertence ao alfabeto.
        - Não há transição definida (estado morto implícito).
    """
    def aceita_palavra(self, palavra):
        estado_atual = self.estado_inicial
        for simbolo in palavra:
            if simbolo not in self.alfabeto:
                return False
            estado_atual = self.transicoes.get((estado_atual, simbolo))
            if estado_atual is None:
                return False
        return estado_atual in self.estados_aceitacao


    def minimizar(self):
        """
        Correções em relação à versão anterior:
        1. Remove estados inacessíveis antes de particionar — estados que nunca
           são alcançados a partir do inicial distorcem a minimização.
        2. Usa identificadores de grupo (índices inteiros) na assinatura de cada
           estado, não o destino bruto. Isso garante que estados equivalentes
           sejam fundidos corretamente mesmo quando seus destinos têm nomes
           diferentes (comum após AFN-ε → AFD).
        3. Ignora destinos ausentes (estado morto implícito) de forma uniforme,
           representando-os como None na assinatura.
        4. Renomeia os estados resultantes para q0, q1, … mantendo q0 como
           inicial, facilitando a leitura.
        """
        
        #1° Remove estados inacessíveis
        acessiveis = self._estados_acessiveis()
        estados = acessiveis
        transicoes = {
            (e, s): d
            for (e, s), d in self.transicoes.items()
            if e in acessiveis and d in acessiveis
        }
        aceitacao = self.estados_aceitacao & acessiveis

        #2° Partição inicial: aceitação × não-aceitação
        nao_aceitacao = estados - aceitacao
        particao = []
        if aceitacao:
            particao.append(frozenset(aceitacao))
        if nao_aceitacao:
            particao.append(frozenset(nao_aceitacao))

        if not particao:
            # AFD vazio
            return AFD(set(), self.alfabeto, {}, self.estado_inicial, set())

        alfabeto = sorted(self.alfabeto)

        #3° Refinamento iterativo
        while True:
            #Mapeia cada estado ao índice do seu grupo atual
            estado_para_grupo = {}
            for idx, grupo in enumerate(particao):
                for estado in grupo:
                    estado_para_grupo[estado] = idx

            nova_particao = []
            mudou = False

            for grupo in particao:
                #Divide o grupo pela assinatura de transições
                subdivisoes = {}
                for estado in grupo:
                    assinatura = tuple(
                        estado_para_grupo.get(transicoes.get((estado, s)))
                        #None representa destino inexistente (estado morto)
                        for s in alfabeto
                    )
                    subdivisoes.setdefault(assinatura, set()).add(estado)

                for subgrupo in subdivisoes.values():
                    nova_particao.append(frozenset(subgrupo))
                    if len(subdivisoes) > 1:
                        mudou = True

            particao = nova_particao
            if not mudou:
                break

        #4° Constrói o AFD minimizado
        #Renomeia grupos: o grupo do estado inicial recebe nome "q0"
        grupo_inicial = next(
            g for g in particao if self.estado_inicial in g
        )
        outros = [g for g in particao if g is not grupo_inicial]

        #Garante q0 = inicial, q1, q2, … para os demais
        grupos_ordenados = [grupo_inicial] + sorted(outros, key=lambda g: sorted(g)[0])
        grupo_para_nome = {g: f"q{i}" for i, g in enumerate(grupos_ordenados)}

        #Estado representante de cada grupo (qualquer membro serve)
        repr_grupo = {g: next(iter(g)) for g in grupos_ordenados}

        novos_estados = set(grupo_para_nome.values())
        novo_estado_inicial = grupo_para_nome[grupo_inicial]
        novos_estados_aceitacao = {
            grupo_para_nome[g]
            for g in grupos_ordenados
            if repr_grupo[g] in aceitacao
        }

        novas_transicoes = {}
        for g in grupos_ordenados:
            rep = repr_grupo[g]
            nome_atual = grupo_para_nome[g]
            for s in alfabeto:
                destino = transicoes.get((rep, s))
                if destino is not None:
                    grupo_destino = next(
                        (grp for grp in grupos_ordenados if destino in grp), None
                    )
                    if grupo_destino is not None:
                        novas_transicoes[(nome_atual, s)] = grupo_para_nome[grupo_destino]

        return AFD(
            novos_estados,
            self.alfabeto,
            novas_transicoes,
            novo_estado_inicial,
            novos_estados_aceitacao,
        )
    
    """Retorna o conjunto de estados alcançáveis a partir do inicial."""
    def _estados_acessiveis(self):
        visitados = {self.estado_inicial}
        fila = [self.estado_inicial]
        while fila:
            atual = fila.pop(0)
            for simbolo in self.alfabeto:
                prox = self.transicoes.get((atual, simbolo))
                if prox and prox not in visitados:
                    visitados.add(prox)
                    fila.append(prox)
        return visitados
