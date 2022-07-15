# Lab 05

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
