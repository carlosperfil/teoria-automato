# Simulador de Autômatos

## Identificação

- **Disciplina:** SIN 141 — Introdução à Teoria da Computação
- **Docentes:** Prof. Dr. Alan Diêgo; Prof. Dr. Pedro Henrique
- **Equipe:**
  - 8772 Ana Flávia T. Alves
  - 9343 Carlos Eduardo
  - 9390 Laissa Rosa d. Santos
- **Período:** 2026-1

---

## Resumo

Este relatório descreve o desenvolvimento de um sistema web para manipulação de autômatos finitos e gramáticas regulares. O sistema permite entrada visual (desenho interativo), entrada textual de AFN via formulário, e entrada de Gramáticas Regulares, realizando conversões, simulações e minimizações automaticamente com visualização gráfica dos autômatos gerados.

---

## Objetivo

Desenvolver um sistema capaz de:

- Receber um **AFN** (incluindo transições epsilon) e convertê-lo para **AFD**
- Simular a aceitação de palavras no AFD
- Minimizar AFDs 
- Realizar conversões bidirecionais entre **Autômatos Finitos** e **Gramáticas Regulares**
- Exibir a gramática gerada no formato formal `G = ({Q}, {Σ}, P, S)`

---

## Estrutura do Projeto

```
teoria-automato/
│
├── main.py                  # Servidor Flask — rotas e orquestração
├── automato_finito.py       # Classe base AutomatoFinito
├── afn.py                   # AFN com epsilon-fechamento e conversão para AFD
├── afd.py                   # AFD com simulação e minimização
├── gramatica_regular.py     # Parser de GR, GR→AFN, AF→GR, formatação
│
└── templates/
    ├── index.html           # Tela inicial: canvas, formulário, gramática
    ├── visualizar.html      # Resultado: imagens AFN/AFD + ações + gramáticas
    ├── simulacao.html       # Resultado da simulação de palavra
    ├── equivalencia.html    # Resultado da verificação de equivalência
    └── erro.html            # Exibição amigável de erros
```

---

## Telas e Fluxo

### 1. Tela Inicial (`index.html`)

Menu lateral com três modos de entrada:

**Desenhar Autômato** — canvas interativo com ferramentas:
- Criar estado (clique no canvas)
- Criar transição (clique no estado origem → destino, modal de símbolo)
- Alternar estado de aceitação / Definir estado inicial
- Deletar elemento selecionado / Limpar canvas
- Símbolos epsilon: `ε`, `&`, `eps`, `epsilon`, `lambda`, `λ`

**Entrar com Autômato** — formulário com:
- Campos de texto para estados, alfabeto, estado inicial e estados de aceitação
- Transições em dois formatos alternáveis:
  - **Tabela** — linhas com estado, símbolo, destinos
  - **Texto** — uma transição por linha: `q0,a → q1 q2`

**Entrar com Gramática** — text area para produções no formato:
```
S -> aA | b
A -> aS | b | ε
```
Aceita setas: `->`, `=>`, `::=`, `→`

---

### 2. Tela de Resultado (`visualizar.html`)

Exibe:
- Imagem do **AFN** gerado
- Imagem do **AFD** equivalente (com estado morto `D` quando necessário)
- Imagem do **AFD Minimizado** (após ação de minimização)
- **Gramáticas** em abas — Do AFN / Do AFD — no formato:
  ```
  G = ({q0, q1, q2}, {a, b}, P, q0)

  P = {
      q0 → aq1 | bq0
      q1 → ε
  }
  ```

Ações disponíveis:
- **Simular** — testa uma palavra no AFD
- **Minimizar AFD** — aplica o algoritmo de Hopcroft
- **Verificar Equivalência** — compara AFN e AFD por palavras de teste
- **Gerar Gramáticas** — exibe GR do AFN e do AFD em abas

---

### 3. Tela de Simulação (`simulacao.html`)

Exibe a palavra testada e o resultado (aceita ✅ / rejeita ❌) com indicação visual.

### 4. Tela de Equivalência (`equivalencia.html`)

Exibe se AFN e AFD são equivalentes, com badge colorido.

---

## Diagrama de Classes (UML)

```
┌──────────────────────────────┐
│       AutomatoFinito         │
│──────────────────────────────│
│ + estados: set               │
│ + alfabeto: set              │
│ + transicoes: dict           │
│ + estado_inicial: str        │
│ + estados_aceitacao: set     │
│──────────────────────────────│
│ + desenhar(nome): str        │
└──────────────┬───────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────────────────────────────┐
│     AFD     │  │                AFN                   │
│─────────────│  │─────────────────────────────────────-│
│             │  │                                      │
│─────────────│  │─────────────────────────────────────-│
│+ aceita_    │  │+ epsilon_fechamento(estados): froz.  │
│  palavra()  │  │+ converter_para_afd(): AFD           │
│+ minimizar()│  │+ aceitar_palavra(palavra): bool      │
│+ _estados_  │  │+ verificar_equivalencia(afd): bool   │
│  acessiveis │  │+ desenhar(nome): str                 │
└─────────────┘  └──────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                  gramatica_regular                    │
│──────────────────────────────────────────────────────│
│ parse_gramatica_regular(texto) → dict                │
│ gr_para_afn(gramatica) → AFN                         │
│ af_para_gramatica(automato) → dict                   │
│ gramatica_para_texto(gramatica) → str                │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                      main.py                         │
│──────────────────────────────────────────────────────│
│ POST /             → processa AFN, salva sessão      │
│ POST /minimizar    → minimiza AFD da sessão          │
│ POST /simular      → testa palavra no AFD            │
│ POST /equivalencia → compara AFN e AFD               │
│ POST /gramatica    → GR → AFN → AFD                  │
│ POST /af_para_gramatica → AF → GR (AFN e AFD)        │
└──────────────────────────────────────────────────────┘
```

---

## Algoritmos Implementados

### Epsilon-Fechamento (AFN)
Dado um conjunto de estados, calcula por BFS todos os estados alcançáveis por transições epsilon, incluindo o próprio estado. Executado no estado inicial e após cada símbolo lido durante a conversão e a simulação.

### Conversão AFN-ε → AFD (Construção de Subconjuntos)
1. Estado inicial do AFD = ε-fechamento({q₀})
2. Para cada estado-conjunto e cada símbolo real: Move + ε-fechamento
3. Estados sem transição apontam para o **estado morto D**
4. D tem auto-loops em todo símbolo e não é estado de aceitação

### Minimização de AFD (Refinamento de Partições)
1. Remove estados inacessíveis a partir do estado inicial
2. Partição inicial: {aceitação} ∪ {não-aceitação}
3. Refina iterativamente por assinaturas de transição (índices de grupo)
4. Renomeia grupos como q0, q1, … com q0 = estado inicial
5. O estado D é incluído na minimização como grupo próprio

### Simulação de Palavras
- **AFN:** ε-fechamento a cada passo, explorando todos os caminhos simultaneamente
- **AFD:** percurso determinístico, rejeita se símbolo não pertence ao alfabeto ou transição ausente

### Verificação de Equivalência
Gera todas as palavras do alfabeto real até comprimento 5 e compara as aceitações do AFN e do AFD. Retorna falso na primeira divergência.

### AF → GR Linear à Direita
- Cada transição `(q, a) → p` gera a produção `q → ap`
- Estados de aceitação geram `q → ε`
- Transições do/para estado morto D são omitidas
- Exibida no formato formal `G = ({Q}, {Σ}, P, S)`

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.x | Linguagem principal |
| Flask | Servidor web, roteamento HTTP, sessões |
| Graphviz (`graphviz`) | Geração de imagens dos autômatos |
| HTML5 Canvas | Canvas interativo para desenho de AFN |
| JavaScript (vanilla) | Lógica do canvas, abas, syntax highlighting |
| Jinja2 | Templating dos HTMLs |

---

## Requisitos Atendidos

- ✅ Entrada de AFN (formulário, canvas interativo e gramática)
- ✅ Suporte a transições epsilon (ε, &, eps, lambda, λ)
- ✅ Conversão AFN-ε → AFD (construção de subconjuntos com epsilon-fechamento)
- ✅ Estado morto D com completude das transições
- ✅ Simulação de palavras no AFD
- ✅ Minimização de AFD (algoritmo de Hopcroft com remoção de estados inacessíveis)
- ✅ GR → AFN → AFD (via parser de gramática regular)
- ✅ AF → GR (do AFN e do AFD, em formato formal)
- ✅ Verificação de equivalência AFN × AFD
- ✅ Visualização gráfica dos autômatos (Graphviz)
- ✅ Persistência de estado entre requisições (flask.session)
- ✅ Tratamento de erros com página amigável

---

## Potencialidades e Limitações

**Potencialidades:**
- Interface moderna com três modos de entrada distintos
- Canvas interativo elimina a necessidade de conhecer JSON
- Gramáticas exibidas no formato formal com syntax highlighting
- Estado morto garante completude total do AFD
- Minimização correta após conversão de AFN-ε (estados inacessíveis removidos)

**Limitações:**
- Equivalência verificada por amostragem (palavras até comprimento 5)
- Sem persistência permanente (estado perdido ao fechar o navegador)
- Graphviz precisa estar instalado no servidor

---

## Observações de Uso

- Transições epsilon: use `ε`, `&`, `eps`, `epsilon`, `lambda` ou `λ` como símbolo
- No formato texto de transições: `q0,a → q1 q2` (múltiplos destinos separados por espaço)
- Gramática regular aceita `->`, `=>`, `::=` e `→` como setas de produção
- Comentários na gramática com `#` ou `//`
- O estado `D` é adicionado automaticamente ao AFD quando necessário

---

## Instalação

### 1. Clone o repositório

### 2. Crie e ative um ambiente virtual (opcional, mas recomendado)

#### Windows


python -m venv venv
venv\Scripts\activate


#### macOS e Linux


python3 -m venv venv
source venv/bin/activate


### 3. Instale as dependências


pip install -r requirements.txt


### 4. Instale o Graphviz

O Graphviz é usado para gerar visualizações dos autômatos. Dependendo do seu sistema operacional, siga as instruções abaixo para instalar:

#### Windows

Baixe e instale o Graphviz a partir do [site oficial](https://graphviz.gitlab.io/_pages/Download/Download_windows.html). Certifique-se de adicionar o Graphviz ao PATH durante a instalação.

#### macOS


brew install graphviz


#### Linux


sudo apt-get install graphviz


### 5. Execute o projeto

No terminal, execute:

python main.py


O servidor Flask será iniciado em \`http://127.0.0.1:5001\`.
