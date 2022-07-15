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

* ppd/check-in: Exchange em que os clientes mandam mensagens para mostrar que estão conectados
  * Campos do body:
    * `pid`: o ID específico do cliente que está mandando a mensagem
* ppd/voting: Exchange em que os clientes mandam os seus votos para decidir o líder
  * Campos do body:
    * `sender`: o ID do cliente que está votando
    * `vote`: o ID do cliente que está sendo votado por `sender`
* ppd/challenges: Exchange em que o líder envia os challenges para todos os clientes
  * Campos do body:
    * `sender`: o ID do rementente da mensagem, idealmente o líder
    * `challenge`: Dificuldade do desafio a ser resolvido pelos clientes

## Fluxo de funcionamento

### "Servidor"

* Somente inicializa as filas que serão usadas

### Clientes

* Faz o próprio check-in, mandando na fila `check-in` o seu PID (Personal ID)
* Fica ouvindo a fila `check-in` até reconhecer que todos os outros membros entraram
  * Sempre que ele percebe um cliente novo, ele re-envia seu check-in, para garantir que esse cliente novo receba
* Após todos os membros estarem dentro, faz-se a votação do líder
  * Cada cliente vota aleatoriamente e manda seu voto na fila `voting`
  * O vencedor da votação é o cliente com mais votos, usando o PID como desempate
    * O menor PID vence o desempate
* Feita a votação para líder, o líder irá gerar um desafio aleatório e mandar na fila `challenge`
* Os clientes então consumiram o challenge da fila `challenge` e começarão a tentar resolvê-lo
* O processo de resolução do desafio depende da dificuldade dele
  * Desafios de dificuldade até 20 são bastante rápidos, então não se usa paralelismo para resolvê-los
  * Desafios de dificuldade maior do que 20 serão paralelizados
