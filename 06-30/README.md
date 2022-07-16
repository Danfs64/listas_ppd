# Lab 05

## Pré-requisitos

* Python 3.9.0+
  * Testado em Python 3.9.5
* Pika 1.3.0+
  * Testado com Pika 1.3.0
* RabbitMQ

## Como executar

1. Inicialize o RabbitMQ
    * `sudo service rabbitmq-server start` no Linux
2. Execute o "Servidor" `server.py` primeiro, que irá apenas para criar as filas/exchanges
3. Execute os clientes `client.py`, `<NUM_CLIENTS>` vezes
    * `NUM_CLIENTS` está definido na linha 5 do `client.py`

## Filas

Todas as filas usadas são:

* Geradas por exchanges fanout, ou seja, cada mensagem publicada para a exchange será distribuída para todas as filas registradas nela, já que não usamos routing_keys
* Recebem um JSON como body. Os campos desse JSON serão especificados para cada fila/exchange

As exchanges usadas são:

* `ppd/check-in`: Exchange em que os clientes mandam mensagens para mostrar que estão conectados
  * Campos do body:
    * `pid`: o ID específico do cliente que está mandando a mensagem
* `ppd/leader`: Exchange em que os clientes mandam os seus votos para decidir o líder
  * Campos do body:
    * `sender`: o ID do cliente que está votando
    * `vote`: o ID do cliente que está sendo votado por `sender`
* `ppd/challenges`: Exchange em que o líder envia os challenges para todos os clientes
  * Campos do body:
    * `cid`: o ID do challenge, iniciado em 0 e incrementado a cada challenge gerado
    * `sender`: o ID do rementente da mensagem, idealmente o líder
    * `challenge`: Dificuldade do desafio a ser resolvido pelos clientes
* `ppd/solutions`: Exchange em que os clientes enviam suas propostas de resolução do desafio
  * Campos do body:
    * `cid`: o ID do challenge a ser resolvido
    * `sender`: o ID de quem enviou a proposta de solução
    * `solution`: A seed que supostamente resolve o challenge
* `ppd/voting`: Exchange em que são mandadas as mensagens de votação das soluções
  * Campos do body:
    * `solved`: Booleano que identifica se o emissor do voto concorda que o desafio foi solucionado

P.S.: Na exchange de votação, como estamos supondo que:

* Não há agentes maliciosos: não precisamos identificar quem está enviando cada voto, pois cada um só manda um voto
* Não há falhas de comunicação: sempre haverá no máximo uma votação em andamento (os clientes esperam todos os votos serem enviados antes de voltarem a olhar a fila de solutions), não sendo necessário identificar o desafio tentando ser resolvido, pois cada `NUM_CLIENTS` votos seguidos definem uma votação.

## Fluxo de funcionamento

### "Servidor"

* Somente inicializa as filas que serão usadas

### Cliente

* Faz o próprio check-in, mandando na fila `check-in` o seu PID (Personal ID)
* Fica ouvindo a fila `check-in` até reconhecer que todos os outros membros entraram
  * Sempre que percebe um cliente novo, re-envia seu check-in, para garantir que esse cliente novo receba
* Após todos os membros estarem dentro, faz-se a votação do líder
  * Cada cliente vota aleatoriamente e manda seu voto na fila `leader`
  * O vencedor da votação é o cliente com mais votos, usando o PID como desempate
    * O menor PID vence o desempate
* Feita a votação para líder, o líder irá gerar um desafio aleatório e mandar na fila `challenge`
* Consome o challenge da fila `challenge` e começa a tentar resolvê-lo em uma thread/processo separado
  * A thread/processo separado manda para a fila `solution` sempre que encontra uma solução
* O processo de resolução do desafio depende da dificuldade:
  * Desafios de dificuldade até 20 são bastante rápidos, então não se usa paralelismo para resolvê-los
  * Desafios de dificuldade maior do que 20 serão paralelizados
* Consome da fila de `solution` para checar quando um desafio foi resolvido
* Para cada resolução lida de `solution`, o cliente checa a solução e manda seu voto para a fila de `voting`
* Se a votação passa, o processo/thread de resolução é parado, a tabela interna de transações é atualizada, e volta para a consumir challenges para serem resolvidos
