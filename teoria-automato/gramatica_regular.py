from afn import AFN

_EPSILON = {"&", "ε", "eps", "epsilon", "lambda", "λ"}
_ARROWS = ("->", "=>", "::=", "→")

# Estado morto — não deve gerar produções na gramática
_ESTADO_MORTO = "D"

class GramaticaRegular:
    def __init__(self, simbolo_inicial, producoes, estados=None, alfabeto=None):
        self.simbolo_inicial = simbolo_inicial
        self.producoes = producoes
        self.estados = estados if estados is not None else sorted(producoes.keys())
        self.alfabeto = alfabeto if alfabeto is not None else []

    @classmethod
    def from_texto(cls, texto):
        dados = _parse_gramatica_regular(texto)
        return cls(
            simbolo_inicial=dados["simbolo_inicial"],
            producoes=dados["producoes"],
            estados=dados.get("estados"),
            alfabeto=dados.get("alfabeto")
        )

    @classmethod
    def from_automato(cls, automato):
        dados = _af_para_gramatica(automato)
        return cls(
            simbolo_inicial=dados["simbolo_inicial"],
            producoes=dados["producoes"],
            estados=dados.get("estados"),
            alfabeto=dados.get("alfabeto")
        )

    def converter_para_afn(self):
        dados = {
            "simbolo_inicial": self.simbolo_inicial,
            "producoes": self.producoes,
        }
        return _gr_para_afn(dados)

    def __str__(self):
        dados = {
            "simbolo_inicial": self.simbolo_inicial,
            "producoes": self.producoes,
            "estados": self.estados,
            "alfabeto": self.alfabeto
        }
        return _gramatica_para_texto(dados)


def _strip_quotes(token):
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
        return token[1:-1]
    return token


def _normalize_nao_terminal(token):
    token = token.strip()
    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1].strip()
    if token.startswith("[") and token.endswith("]"):
        token = token[1:-1].strip()
    return token


def _split_linha_producao(linha):
    for seta in _ARROWS:
        if seta in linha:
            esquerda, direita = linha.split(seta, 1)
            return esquerda, direita
    raise ValueError("Linha sem seta de producao.")


def _is_quoted(token):
    token = token.strip()
    return len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}


def _token_e_nao_terminal(token, nao_terminais):
    """Não-terminal se existir no lado esquerdo e não estiver entre aspas."""
    raw = token.strip()
    if _is_quoted(raw):
        return False
    normalizado = _normalize_nao_terminal(raw)
    return normalizado in nao_terminais


def _token_e_terminal(token, nao_terminais):
    """Terminal de 1 caractere, exceto epsilon e não-terminal conhecido."""
    raw = token.strip()
    if raw in _EPSILON:
        return False
    unquoted = _strip_quotes(raw) if _is_quoted(raw) else raw
    if _token_e_nao_terminal(unquoted, nao_terminais):
        return False
    return len(unquoted) == 1 and not unquoted.isspace()


def _simbolo_valido(simbolo):
    return simbolo and len(simbolo) == 1 and not simbolo.isspace() and simbolo not in _EPSILON


# ─────────────────────────────────────────────────────────────────────────────
#  PARSER DE ALTERNATIVA — suporta múltiplos terminais e NTs com nomes longos
# ─────────────────────────────────────────────────────────────────────────────

def _parse_alternativa_linear(alternativa, nao_terminais):
    """Reconhece uma alternativa de produção linear regular (direita ou esquerda).

    Gramáticas regulares permitem múltiplos terminais, desde que o único
    não-terminal fique EXCLUSIVAMENTE no fim (linear direita) ou no início
    (linear esquerda). Exemplos válidos:

        Linear direita : a, aA, baS, bbaA  →  ("RIGHT", "ba", "S")
        Linear esquerda: A, Aa, Sba, Abba  →  ("LEFT",  "S",  "ba")
        Só terminais   : a, ba, abc         →  ("TERM",  "ba")
        Vazia          : ε, &               →  ("EPS",)

    Retorno:
        ("EPS",)
        ("TERM",  terminais)          — string com 1+ terminais, sem NT
        ("RIGHT", terminais, nt)      — terminais seguidos de NT
        ("LEFT",  nt,        terminais)
    """
    alt = alternativa.strip().rstrip(";")
    if not alt:
        return None

    if alt in _EPSILON:
        return ("EPS",)

    # ── Normaliza a alternativa numa lista de "peças":
    #    cada peça é um token separado por espaço OU um char individual
    #    quando o token for colado (ex: "baS" → chars avulsos).
    #    Vamos trabalhar diretamente com a string "achatada" (sem espaços
    #    internos) e identificar onde está o NT, se houver.

    # Remove espaços internos para unificar "b a S" e "baS"
    sem_espacos = alt.replace(" ", "")

    # Verifica se é epsilon colado (improvável, mas cobre "& " etc.)
    if sem_espacos in _EPSILON:
        return ("EPS",)

    # ── Tenta encontrar um NT conhecido como sufixo (linear DIREITA) ──────────
    # Varre todos os prefixos de terminais possíveis: do mais longo para o mais curto,
    # para preferir o NT mais longo em caso de ambiguidade.
    melhor_direita = None
    for i in range(len(sem_espacos), 0, -1):
        sufixo = sem_espacos[i:]
        prefixo = sem_espacos[:i]
        if not sufixo:
            continue
        nt = _normalize_nao_terminal(sufixo)
        if nt in nao_terminais:
            # prefixo deve ser todo de terminais válidos (1 char cada)
            if prefixo and _todos_terminais(prefixo, nao_terminais):
                melhor_direita = ("RIGHT", prefixo, nt)
                break  # primeiro (mais longo NT) encontrado

    # ── Tenta encontrar um NT conhecido como prefixo (linear ESQUERDA) ────────
    melhor_esquerda = None
    for i in range(1, len(sem_espacos) + 1):
        prefixo = sem_espacos[:i]
        sufixo  = sem_espacos[i:]
        nt = _normalize_nao_terminal(prefixo)
        if nt in nao_terminais:
            # sufixo deve ser todo de terminais válidos
            if sufixo and _todos_terminais(sufixo, nao_terminais):
                melhor_esquerda = ("LEFT", nt, sufixo)
                break  # primeiro (mais curto NT) encontrado

    # ── Decide o resultado ────────────────────────────────────────────────────
    if melhor_direita and melhor_esquerda:
        # Ambiguidade real: NT é tanto prefixo quanto sufixo válido
        raise ValueError(
            f"Producao ambigua: '{alt}'. "
            "Use espaços para separar terminais de não-terminais."
        )

    if melhor_direita:
        return melhor_direita

    if melhor_esquerda:
        return melhor_esquerda

    # ── Sem NT: deve ser só terminais ─────────────────────────────────────────
    if _todos_terminais(sem_espacos, nao_terminais):
        return ("TERM", sem_espacos)

    raise ValueError(
        f"Producao invalida: '{alt}'. "
        "Verifique se todos os não-terminais foram declarados no lado esquerdo "
        "e se cada símbolo terminal tem exatamente 1 caractere. "
        f"Não-terminais reconhecidos: {sorted(nao_terminais)}."
    )


def _todos_terminais(s, nao_terminais):
    """Retorna True se cada caractere de 's' for um terminal válido
    (1 char, não epsilon, não reconhecido como NT isolado).
    """
    for ch in s:
        if not _simbolo_valido(ch):
            return False
        # Um único char que seja NT declarado não é terminal aqui
        # (ex: se "A" for NT, "A" sozinho não é terminal)
        # Mas dentro de uma sequência colada, chars que coincidem com
        # NTs de 1 char são ambíguos — aceitamos como terminal neste contexto,
        # pois a busca por sufixo/prefixo acima já tratou o caso NT.
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  PARSE DE GRAMÁTICA
# ─────────────────────────────────────────────────────────────────────────────

def _parse_gramatica_regular(texto):
    """Remove comentários e normaliza linhas da gramática."""
    linhas = []
    for raw in texto.splitlines():
        linha = raw
        for marcador in ("#", "//"):
            pos = linha.find(marcador)
            if pos != -1:
                linha = linha[:pos]
        linha = linha.strip()
        if linha:
            linhas.append(linha)
    if not linhas:
        raise ValueError("Gramatica vazia.")

    producoes = {}
    simbolo_inicial = None
    for linha in linhas:
        esquerda, direita = _split_linha_producao(linha)
        esquerda = esquerda.strip()
        if not esquerda:
            raise ValueError("Nao terminal vazio.")
        esquerda = _normalize_nao_terminal(esquerda)
        if simbolo_inicial is None:
            simbolo_inicial = esquerda

        alternativas = [a.strip() for a in direita.split("|") if a.strip()]
        producoes.setdefault(esquerda, [])
        producoes[esquerda].extend(alternativas)

    return {
        "simbolo_inicial": simbolo_inicial,
        "producoes": producoes,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  DETECÇÃO DE DIREÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _detectar_direcao_gramatica(gramatica):
    """Infere se a gramática é linear à direita ou à esquerda."""
    producoes = gramatica["producoes"]
    nao_terminais = set(producoes.keys())
    direcao = None

    for alternativas in producoes.values():
        for alternativa in alternativas:
            parsed = _parse_alternativa_linear(alternativa, nao_terminais)
            if parsed is None:
                continue
            if parsed[0] == "RIGHT":
                if direcao is None:
                    direcao = "right"
                elif direcao != "right":
                    raise ValueError(
                        "Gramatica mista: nao misture linear a direita e a esquerda."
                    )
            elif parsed[0] == "LEFT":
                if direcao is None:
                    direcao = "left"
                elif direcao != "left":
                    raise ValueError(
                        "Gramatica mista: nao misture linear a direita e a esquerda."
                    )

    return direcao or "right"


# ─────────────────────────────────────────────────────────────────────────────
#  CONVERSÃO GR → AFN
# ─────────────────────────────────────────────────────────────────────────────

def _gr_para_afn(gramatica):
    """Converte GR regular para AFN equivalente."""
    direcao = _detectar_direcao_gramatica(gramatica)
    if direcao == "left":
        return _gr_esquerda_para_afn(gramatica)
    return _gr_direita_para_afn(gramatica)


def _gr_direita_para_afn(gramatica):
    """Conversão direta de GR linear à direita para AFN.

    Suporta múltiplos terminais: S -> baA gera estados intermediários
    S -b-> _q0 -a-> A, encadeando um estado por terminal extra.
    """
    producoes = gramatica["producoes"]
    simbolo_inicial = gramatica["simbolo_inicial"]
    nao_terminais = set(producoes.keys())

    estados = set(producoes.keys())
    estado_final = "F"
    while estado_final in estados:
        estado_final = f"{estado_final}F"
    estados.add(estado_final)

    alfabeto = set()
    transicoes = {}
    estados_aceitacao = {estado_final}

    # Contador para gerar nomes únicos de estados intermediários
    contador = [0]

    def novo_intermediario():
        nome = f"_q{contador[0]}"
        contador[0] += 1
        while nome in estados:
            nome = f"_q{contador[0]}"
            contador[0] += 1
        estados.add(nome)
        return nome

    def encadear(origem, terminais, destino_final):
        """Cria cadeia de transições: origem -t0-> _q -t1-> ... -tn-> destino_final."""
        atual = origem
        for i, ch in enumerate(terminais):
            if not _simbolo_valido(ch):
                raise ValueError(f"Simbolo invalido na producao: '{ch}'")
            alfabeto.add(ch)
            proximo = destino_final if i == len(terminais) - 1 else novo_intermediario()
            transicoes.setdefault((atual, ch), []).append(proximo)
            atual = proximo

    for nao_terminal, alternativas in producoes.items():
        for alternativa in alternativas:
            parsed = _parse_alternativa_linear(alternativa, nao_terminais)
            if parsed is None:
                continue

            if parsed[0] == "EPS":
                estados_aceitacao.add(nao_terminal)
                continue

            if parsed[0] == "LEFT":
                raise ValueError(
                    "Gramatica linear a esquerda detectada. Use apenas producoes a direita."
                )

            if parsed[0] == "TERM":
                # Só terminais, sem NT: encadeia até estado final de aceitação
                encadear(nao_terminal, parsed[1], estado_final)

            else:  # RIGHT: (RIGHT, terminais_str, nt)
                terminais, nt = parsed[1], parsed[2]
                destino = _normalize_nao_terminal(nt)
                estados.add(destino)
                encadear(nao_terminal, terminais, destino)

    return AFN(estados, alfabeto, transicoes, simbolo_inicial, estados_aceitacao)


def _gr_esquerda_para_afn(gramatica):
    """Reescreve GR linear à esquerda como GR à direita equivalente e reverte o AFN.

    Inversão: A -> Bba  (LEFT, "B", "ba")  vira  A -> abB  na gramática reversa,
    que depois tem o AFN invertido para preservar a linguagem original.
    """
    producoes = gramatica["producoes"]
    simbolo_inicial = gramatica["simbolo_inicial"]
    nao_terminais = set(producoes.keys())

    producoes_direita = {}
    for nao_terminal, alternativas in producoes.items():
        for alternativa in alternativas:
            parsed = _parse_alternativa_linear(alternativa, nao_terminais)
            if parsed is None:
                continue
            if parsed[0] == "EPS":
                producoes_direita.setdefault(nao_terminal, []).append("ε")
                continue
            if parsed[0] == "TERM":
                # Só terminais: reverter a string de terminais
                producoes_direita.setdefault(nao_terminal, []).append(parsed[1][::-1])
                continue
            if parsed[0] == "RIGHT":
                raise ValueError(
                    "Gramatica linear a direita detectada. Use apenas producoes a esquerda."
                )
            # LEFT: (LEFT, nt_origem, terminais_str)
            # Ex: A -> Bba  →  parsed = ("LEFT", "B", "ba")
            # Na gramática reversa: A -> abB  (terminais invertidos + NT no fim)
            nt_origem, terminais = parsed[1], parsed[2]
            terminais_rev = terminais[::-1]
            producoes_direita.setdefault(nao_terminal, []).append(f"{terminais_rev}{nt_origem}")

    gr_reversa = {
        "simbolo_inicial": simbolo_inicial,
        "producoes": producoes_direita,
    }

    afn_reverso = _gr_direita_para_afn(gr_reversa)
    return _reverter_afn(afn_reverso)


def _reverter_afn(afn):
    """Inverte todas as transições e ajusta estado inicial/aceitação."""
    novo_inicio = "I"
    while novo_inicio in afn.estados:
        novo_inicio = f"{novo_inicio}I"

    novos_estados = set(afn.estados)
    novos_estados.add(novo_inicio)
    novas_transicoes = {}

    for (estado, simbolo), destinos in afn.transicoes.items():
        for destino in destinos:
            novas_transicoes.setdefault((destino, simbolo), []).append(estado)

    for estado_final in afn.estados_aceitacao:
        novas_transicoes.setdefault((novo_inicio, "ε"), []).append(estado_final)

    novo_alfabeto = set(afn.alfabeto)
    novo_alfabeto.add("ε")

    return AFN(
        novos_estados,
        novo_alfabeto,
        novas_transicoes,
        novo_inicio,
        {afn.estado_inicial},
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CONVERSÃO AF → GRAMÁTICA
# ─────────────────────────────────────────────────────────────────────────────

def _af_para_gramatica(automato):
    """Converte autômato finito (AFN ou AFD) para estrutura de GR linear à direita.

    O estado morto D é excluído das produções — ele nunca leva a aceitação,
    portanto suas transições não contribuem para a linguagem gerada.
    """
    producoes = {}

    for (estado, simbolo), destino in automato.transicoes.items():
        if estado == _ESTADO_MORTO:
            continue

        destinos = destino if isinstance(destino, list) else [destino]

        for dest in destinos:
            if dest == _ESTADO_MORTO:
                continue
            producoes.setdefault(estado, []).append(f"{simbolo}{dest}")

    for estado in automato.estados_aceitacao:
        if estado == _ESTADO_MORTO:
            continue
        producoes.setdefault(estado, []).append("ε")

    simbolo_inicial = automato.estado_inicial

    return {
        "simbolo_inicial": simbolo_inicial,
        "estados": sorted(e for e in automato.estados if e != _ESTADO_MORTO),
        "alfabeto": sorted(s for s in automato.alfabeto),
        "producoes": producoes,
    }


def _gramatica_para_texto(gramatica):
    """Formata a GR no padrão formal:

        G = ({estados}, {símbolos}, P, S)

        P = {
            S → aA | b
            A → aS | ε
        }
    """
    simbolo_inicial = gramatica["simbolo_inicial"]
    producoes       = gramatica["producoes"]
    estados         = gramatica.get("estados", sorted(producoes.keys()))
    alfabeto        = gramatica.get("alfabeto", [])

    estados_str  = ", ".join(estados)
    alfabeto_str = ", ".join(alfabeto)
    cabecalho = (
        f"G = ({{{estados_str}}}, {{{alfabeto_str}}}, P, {simbolo_inicial})"
    )

    linhas_p = []

    if simbolo_inicial in producoes and producoes[simbolo_inicial]:
        alts = " | ".join(producoes[simbolo_inicial])
        linhas_p.append(f"    {simbolo_inicial} → {alts}")

    for nt in sorted(producoes.keys()):
        if nt == simbolo_inicial:
            continue
        if not producoes[nt]:
            continue
        alts = " | ".join(producoes[nt])
        linhas_p.append(f"    {nt} → {alts}")

    bloco_p = "P = {\n" + "\n".join(linhas_p) + "\n}"

    return f"{cabecalho}\n\n{bloco_p}"
