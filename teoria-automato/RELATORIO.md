# Relatório do Projeto: Simulador de Autômatos

## Identificação
- Disciplina: SIN 141 - Introdução à Teoria da Computação
- Docentes: Prof. Dr. Alan Diêgo; Prof. Dr. Pedro Henrique
- Equipe:
	- 8772 Ana Flávia T. Alves
	- 9343 Carlos Eduardo
	- 9390 Laissa Rosa d. Santos
- Período: 2026-1

## Resumo
Este relatório descreve o desenvolvimento de um sistema para manipulação de autômatos finitos e gramáticas regulares, com foco em conversões, simulações e minimização.

## Objetivo
Desenvolver um sistema capaz de receber um AFN, convertê-lo para AFD, simular a aceitação de palavras, minimizar AFDs e realizar conversões entre autômatos finitos e gramática regular.

## Estrutura do Projeto
- Backend: Flask (rotas HTTP e processamento de entrada)
- Modelos: classes de autômatos (AFN/AFD)
- Conversões: GR <-> AF
- Visualização: Graphviz

## Telas e Fluxo
1) Entrada de AFN e GR: formulário inicial com campos para estados, alfabeto, transições e produções.
2) Visualização: exibição das imagens do AFN/AFD, simulação de palavra, minimização e equivalência.
3) Saída de GR: gramática regular gerada a partir do autômato.

## Diagrama UML
O diagrama de classes encontra-se em [diagrama.puml](diagrama.puml).

## Tecnologias
- Python 3.x
- Flask
- Graphviz

## Requisitos Atendidos
- Entrada de AFN
- Conversão AFN -> AFD
- Simulação de palavras no AFD
- Minimização de AFD
- GR -> AF (via GR -> AFN)
- AF -> GR

## Potencialidades e Limitações
- Potencialidades: interface simples, geração automática de diagramas e validação básica de entrada.
- Limitações: não trata gramáticas fora do formato regular; a entrada de transições exige JSON em formato definido.

## Requisitos Funcionais Adicionais
- Verificação de equivalência AFN x AFD por testes de palavras.

## Considerações Finais
O sistema atende aos requisitos solicitados, com interface simples e validação básica de entradas. Recomenda-se a execução de testes com entradas representativas durante a apresentação.

## Observações de Uso
- Transições devem ser informadas em JSON com chave "estado,simbolo".
- Gramática regular aceita setas diferentes (->, =>, ::=, →) e epsilon (ε, &, eps).
