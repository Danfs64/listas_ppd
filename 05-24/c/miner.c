#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int challenge;
    char* seed;
    int winner;
} Transaction;

Transaction TRANSACTIONS[1000];
int LAST_TRANS = -1;

int CHALL = 1;
int generate_challenge() {
    CHALL++;
    return CHALL >> 1;
}

/*
    Retorna o valor atual da transação com
    desafio ainda pendente de solução.
*/
int getTransactionID() {
    return LAST_TRANS;
}

/* 
    Se `tid` for válido, retorna o valor
    do desafio associado a ele.
    Retorna -1 se o `tid` for inválido.
*/
int getChallenge(int tid) {
    if(tid > LAST_TRANS)
        return -1;

    return TRANSACTIONS[tid].challenge;
}

/*
    Se `tid` for válido:
    - retorna 0 se o desafio dessa transação já foi resolvido;
    - retorna 1 caso a transação ainda possua desafio pendente;
    
    Retorna -1 se a `tid` for inválida.
*/
int getTransactionStatus(int tid) {
    if(tid > LAST_TRANS)
        return -1;

    int winner = TRANSACTIONS[tid].winner;

    return winner == -1;
}

/* 
    Retorna o ClientID do vencedor da transação `tid`;
    Retorna 0 se `tid` ainda não tem vencedor;
    Retorna -1 se `tid` for inválida.
*/
int getWinner(int tid) {
    if(tid > LAST_TRANS)
        return -1;

    int winner = TRANSACTIONS[tid].winner;
    if(winner == -1)
        return 0;
    else
        return winner;
}

/*
    Retorna uma tupla com:
    - o status;
    - a seed;
    - e o desafio.
    associados ao `tid`.

    Se `tid` for inválido, retorna uma tupla (-1, None, -1)
*/
// TODO C não tem tupla D:
// int getSeed(int tid) {
//     if(tid > LAST_TRANS)
//         return (-1, None, -1);

//     Transaction transaction = TRANSACTIONS[tid];
//     int challenge = transaction.challenge;
//     char* seed = transaction.seed;
//     int winner = transaction.winner;

//     return (getTransactionStatus(tid), seed, challenge);
// }

/*
    Submete uma semente (seed) para o hashing SHA-1 que
    resolva o desafio proposto para a referida `tid`.

    - Retorna -1 se a `tid` for inválida.
    - Retorna 2 se o desafio já foi solucionado;
    - Retorna 0 se a seed não resolve o challenge;
    - Retorna 1 se a seed resolve o challenge;
*/
int submitChallenge(int tid, int cid, char* seed) {
    int result = check_seed(seed, tid);

    if(result == 1) {
        TRANSACTIONS[tid].winner = cid;
        TRANSACTIONS[tid].seed = seed;

        LAST_TRANS++;
        TRANSACTIONS[LAST_TRANS].challenge = generate_challenge();
        TRANSACTIONS[LAST_TRANS].seed = NULL;
        TRANSACTIONS[LAST_TRANS].winner = -1;
    }

    return result;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        /* code */
    }

}