import re
from afn import AFN


_EPSILON = {"&", "ε", "eps", "epsilon", "lambda", "λ"}
_ARROWS = ("->", "=>", "::=", "→")

#Estado morto — não deve gerar produções na gramática
_ESTADO_MORTO = "D"


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


def _parse_alternativa(alternativa):
    alt = alternativa.strip().rstrip(";")
    if not alt:
        return None

    if alt in _EPSILON:
        return ("EPS",)

    tokens = alt.split()
    if len(tokens) == 1:
        token = _strip_quotes(tokens[0])
        if token in _EPSILON:
            return ("EPS",)
        if len(token) == 1:
            return (token, None)
        terminal = token[0]
        nao_terminal = _normalize_nao_terminal(token[1:])
        return (terminal, nao_terminal)

    if len(tokens) == 2:
        terminal = _strip_quotes(tokens[0])
        nao_terminal = _normalize_nao_terminal(tokens[1])
        return (terminal, nao_terminal)

    raise ValueError("Producao invalida: use terminal ou terminal + nao terminal.")

"""Remove comentários e normaliza linhas da gramática."""
def parse_gramatica_regular(texto):
    linhas = []
    for raw in texto.splitlines():
        linha = re.split(r"#|//", raw, maxsplit=1)[0].strip()
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

"""Converte GR regular para AFN equivalente."""
def gr_para_afn(gramatica):
    producoes = gramatica["producoes"]
    simbolo_inicial = gramatica["simbolo_inicial"]

    estados = set(producoes.keys())
    estado_final = "F"
    while estado_final in estados:
        estado_final = f"{estado_final}F"
    estados.add(estado_final)

    alfabeto = set()
    transicoes = {}
    estados_aceitacao = {estado_final}

    for nao_terminal, alternativas in producoes.items():
        for alternativa in alternativas:
            parsed = _parse_alternativa(alternativa)
            if parsed is None:
                continue

            if parsed[0] == "EPS":
                estados_aceitacao.add(nao_terminal)
                continue

            simbolo, proximo = parsed
            if not simbolo or len(simbolo) != 1 or not simbolo.isalnum():
                raise ValueError("Simbolo invalido na producao.")
            alfabeto.add(simbolo)

            if proximo:
                proximo = _normalize_nao_terminal(proximo)
                estados.add(proximo)
                transicoes.setdefault((nao_terminal, simbolo), []).append(proximo)
            else:
                transicoes.setdefault((nao_terminal, simbolo), []).append(estado_final)

    return AFN(estados, alfabeto, transicoes, simbolo_inicial, estados_aceitacao)

"""Converte autômato finito (AFN ou AFD) para estrutura de GR linear à direita.

O estado morto D é excluído das produções — ele nunca leva a aceitação,
portanto suas transições não contribuem para a linguagem gerada.
"""
def af_para_gramatica(automato):
    producoes = {}

    for (estado, simbolo), destino in automato.transicoes.items():
        #Ignora transições do/para estado morto
        if estado == _ESTADO_MORTO:
            continue

        #Destino pode ser lista (AFN) ou string (AFD)
        destinos = destino if isinstance(destino, list) else [destino]

        for dest in destinos:
            if dest == _ESTADO_MORTO:
                #Transição para D não gera produção (linguagem não avança)
                continue
            producoes.setdefault(estado, []).append(f"{simbolo}{dest}")

    #Estados de aceitação geram a produção vazia (palavra aceita aqui)
    for estado in automato.estados_aceitacao:
        if estado == _ESTADO_MORTO:
            continue
        producoes.setdefault(estado, []).append("ε")

    #Garante que o símbolo inicial apareça primeiro
    simbolo_inicial = automato.estado_inicial

    return {
        "simbolo_inicial": simbolo_inicial,
        "estados": sorted(
            e for e in automato.estados if e != _ESTADO_MORTO
        ),
        "alfabeto": sorted(
            s for s in automato.alfabeto
        ),
        "producoes": producoes,
    }

"""Formata a GR no padrão formal:

        G = ({estados}, {símbolos}, P, S)

        P = {
            S → aA | b
            A → aS | ε
        }
    """
def gramatica_para_texto(gramatica):
    simbolo_inicial = gramatica["simbolo_inicial"]
    producoes       = gramatica["producoes"]
    estados         = gramatica.get("estados", sorted(producoes.keys()))
    alfabeto        = gramatica.get("alfabeto", [])

    #Cabeçalho formal (conjuntos e símbolo inicial)
    estados_str  = ", ".join(estados)
    alfabeto_str = ", ".join(alfabeto)
    cabecalho = (
        f"G = ({{{estados_str}}}, {{{alfabeto_str}}}, P, {simbolo_inicial})"
    )

    #Regras de produção, ordenadas por símbolo inicial e depois alfabética
    linhas_p = []

    #Símbolo inicial primeiro
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
