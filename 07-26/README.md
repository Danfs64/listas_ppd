# Lab 6

Feito por:

- Daniel Fernandes
- Jairo Marcos
- Juliane Ferreira

## Executando

Rode

```terminal
python client.py
```

e insira o número de clientes que participarão do programa (Ele funcionará sozinho caso seja colocado 1).

Configurações como tamanho de challenges, encoding, host e credenciais de acesso ao broker podem ser alteradas em `settings/config.py`

## Considerações gerais da arquitetura

A ideia principal consiste em ter um processo "gerenciador" que fica consumindo da fila de soluções enquanto outro processo, chamado de "solver" spawna `n` processos filhos que tentarão solucionar o challenge.

Quando qualquer filho do solver julga que encontrou uma solução, ele envia essa solução para a fila e continua procurando por novas soluções.

Já o gerenciador, quando reconhece que houve uma votação que aceitou a solução do desafio:

- envia um SIGTERM para o processo solver, que por sua vez matará todos os seus filhos, não deixando processos zumbis;
- atualiza a tabela de transações e printa ela no terminal;
- refaz a votação para líder, que acarretará em um novo challenge e na criação de um novo processo solver para este challenge.

O solver tenta resolver o challenge gerando exaustivamente seeds aleatórias de um tamanho fixo.
