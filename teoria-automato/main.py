from flask import Flask, render_template, request, session, redirect
from afn import AFN
from afd import AFD
from gramatica_regular import GramaticaRegular
import json

"""Converte JSON de transições {'estado,simbolo': [destinos]} para dict de tuplas."""
def _parse_transicoes_json(raw):
    raw_dict = json.loads(raw)
    transicoes = {}
    for chave, destinos in raw_dict.items():
        if "," not in chave:
            raise ValueError(f"Chave de transicao invalida: {chave!r}")
        estado, simbolo = [p.strip() for p in chave.split(",", 1)]
        transicoes[(estado, simbolo)] = destinos if isinstance(destinos, list) else [destinos]
    return transicoes

"""Divide por vírgula ou espaço, retorna lista sem vazios."""
def _normalizar_lista(valor):
    if not valor:
        return []
    return [v.strip() for v in (valor.split(",") if "," in valor else valor.split()) if v.strip()]


"""Serializa um AutomatoFinito para dict JSON-compatível."""
def _automato_para_dict(automato):
    if automato is None:
        return None
    trans_serial = {
        f"{e}|{s}": d
        for (e, s), d in automato.transicoes.items()
    }
    return {
        "tipo": type(automato).__name__,
        "estados": list(automato.estados),
        "alfabeto": list(automato.alfabeto),
        "transicoes": trans_serial,
        "estado_inicial": automato.estado_inicial,
        "estados_aceitacao": list(automato.estados_aceitacao),
    }

"""Desserializa um dict de volta para AFN ou AFD."""
def _dict_para_automato(d):
    if d is None:
        return None
    trans = {
        tuple(chave.split("|", 1)): valor
        for chave, valor in d["transicoes"].items()
    }
    estados        = set(d["estados"])
    alfabeto       = set(d["alfabeto"])
    estado_inicial = d["estado_inicial"]
    estados_aceit  = set(d["estados_aceitacao"])

    if d["tipo"] == "AFN":
        trans_afn = {k: (v if isinstance(v, list) else [v]) for k, v in trans.items()}
        return AFN(estados, alfabeto, trans_afn, estado_inicial, estados_aceit)
    else:
        trans_afd = {k: (v[0] if isinstance(v, list) else v) for k, v in trans.items()}
        return AFD(estados, alfabeto, trans_afd, estado_inicial, estados_aceit)


def _salvar_session(afn, afd):
    # Persiste automatos na sessao para uso nas rotas seguintes.
    session["afn"] = _automato_para_dict(afn)
    session["afd"] = _automato_para_dict(afd)


def _carregar_session():
    # Recupera automatos da sessao, se existirem.
    afn = _dict_para_automato(session.get("afn"))
    afd = _dict_para_automato(session.get("afd"))
    return afn, afd


#APP
app = Flask(__name__)
app.secret_key = "automatasim-secret-2026"

def _render_visualizar(**kwargs):
    # Centraliza a tela de resultado com defaults consistentes.
    defaults = dict(
        afn_imagem=None,
        afd_imagem=None,
        afd_min_imagem=None,
        gramatica_afn=None,
        gramatica_afd=None,
    )
    defaults.update(kwargs)
    return render_template("visualizar.html", **defaults)


def _salvar_visualizacao(**kwargs):
    # Guarda o contexto de visualizacao para o redirect PRG.
    session["visualizar_ctx"] = kwargs


def _carregar_visualizacao():
    return session.get("visualizar_ctx", {})


def _gerar_gramaticas(afn, afd):
    # Gera GRs para AFN/AFD quando disponiveis.
    gr_afn = str(GramaticaRegular.from_automato(afn)) if afn is not None else None
    gr_afd = str(GramaticaRegular.from_automato(afd)) if afd is not None else None
    return gr_afn, gr_afd


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            estados           = _normalizar_lista(request.form.get("estados", ""))
            alfabeto          = _normalizar_lista(request.form.get("alfabeto", ""))
            estado_inicial    = request.form.get("estado_inicial", "").strip()
            estados_aceitacao = _normalizar_lista(request.form.get("estados_aceitacao", ""))
            raw_trans         = request.form.get("transicoes", "").strip()

            if not estados:
                raise ValueError("Lista de estados vazia.")
            if not estado_inicial:
                raise ValueError("Estado inicial nao definido.")
            if not raw_trans:
                raise ValueError("Transicoes nao fornecidas.")

            transicoes = _parse_transicoes_json(raw_trans)
            afn = AFN(set(estados), set(alfabeto), transicoes, estado_inicial, set(estados_aceitacao))
            afd = afn.converter_para_afd()
            _salvar_session(afn, afd)

            _salvar_visualizacao(
                afn_imagem=afn.desenhar("afn"),
                afd_imagem=afd.desenhar("afd"),
            )
            return redirect("/resultado")
        except Exception as e:
            print(f"[ERRO /] {e}")
            return render_template("erro.html", mensagem=str(e)), 400

    return render_template("index.html")


@app.route("/minimizar", methods=["POST"])
def minimizar():
    try:
        afn, afd = _carregar_session()
        if afd is None:
            raise ValueError("Nenhum AFD disponivel para minimizar.")
        afd_min = afd.minimizar()
        #Substitui o AFD da sessão pelo minimizado para ações seguintes
        _salvar_session(afn, afd_min)
        _salvar_visualizacao(afd_min_imagem=afd_min.desenhar("afd_min"))
        return redirect("/resultado")
    except Exception as e:
        print(f"[ERRO /minimizar] {e}")
        return render_template("erro.html", mensagem=str(e)), 400


@app.route("/simular", methods=["POST"])
def simular():
    try:
        _, afd = _carregar_session()
        if afd is None:
            raise ValueError("Nenhum AFD disponivel para simulacao.")
        palavra  = request.form.get("palavra", "")
        if palavra.strip() in {"&", "ε", "eps", "epsilon", "lambda", "λ"}:
            palavra = ""
        aceita   = afd.aceita_palavra(palavra)
        resultado = (
            "A palavra foi aceita pelo AFD."
            if aceita else
            "A palavra foi rejeitada pelo AFD."
        )
        return render_template("simulacao.html", palavra=palavra, resultado=resultado)
    except Exception as e:
        print(f"[ERRO /simular] {e}")
        return render_template("erro.html", mensagem=str(e)), 400


@app.route("/equivalencia", methods=["POST"])
def equivalencia():
    try:
        afn, afd = _carregar_session()
        if afn is None or afd is None:
            raise ValueError("Gere os automatos antes de verificar equivalencia.")
        equiv = afn.verificar_equivalencia(afd)
        resultado = (
            "Os autômatos são equivalentes."
            if equiv else
            "Os autômatos não são equivalentes."
        )
        return render_template("equivalencia.html", equivalente=resultado)
    except Exception as e:
        print(f"[ERRO /equivalencia] {e}")
        return render_template("erro.html", mensagem=str(e)), 400


@app.route("/gramatica", methods=["POST"])
def gramatica():
    try:
        texto = request.form.get("gramatica", "").strip()
        if not texto:
            raise ValueError("Gramatica vazia.")
        gramatica_obj = GramaticaRegular.from_texto(texto)
        afn = gramatica_obj.converter_para_afn()
        afd = afn.converter_para_afd()
        _salvar_session(afn, afd)
        _salvar_visualizacao(
            afn_imagem=afn.desenhar("afn_gr"),
            afd_imagem=afd.desenhar("afd_gr"),
        )
        return redirect("/resultado")
    except Exception as e:
        print(f"[ERRO /gramatica] {e}")
        return render_template("erro.html", mensagem=str(e)), 400


@app.route("/af_para_gramatica", methods=["POST"])
def af_para_gramatica_view():
    try:
        afn, afd = _carregar_session()
        if afn is None and afd is None:
            raise ValueError("Defina um automato antes de gerar a gramatica.")
        gr_afn, gr_afd = _gerar_gramaticas(afn, afd)
        _salvar_visualizacao(gramatica_afn=gr_afn, gramatica_afd=gr_afd)
        return redirect("/resultado")
    except Exception as e:
        print(f"[ERRO /af_para_gramatica] {e}")
        return render_template("erro.html", mensagem=str(e)), 400


@app.route("/resultado", methods=["GET"])
def resultado():
    return _render_visualizar(**_carregar_visualizacao())


if __name__ == "__main__":
    app.run(debug=True, port=5001)
