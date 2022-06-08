#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/sha.h>


typedef struct {
    int challenge;
    char* seed;
    int winner;
} Transaction;

Transaction TRANSACTIONS[1000];
int LAST_TRANS = -1;


typedef struct {
    int status;
    char* seed;
    int challenge;
} TransactionInfo;

/*
    Gera o próximo challenge
    O challenge aumenta a cada 2 chamadas
*/
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
    Retorna uma struct que contêm:
    - o status;
    - a seed;
    - e o desafio.
    associados ao `tid`.

    Se `tid` for inválido, retorna a struct preenchida com (-1, NULL, -1)
*/
TransactionInfo getSeed(int tid) {
    if(tid > LAST_TRANS) {
        TransactionInfo ret;
        ret.challenge = -1;
        ret.status = -1;
        ret.seed = NULL;

        return ret;
    }

    Transaction transaction = TRANSACTIONS[tid];
    TransactionInfo ret;

    ret.challenge = transaction.challenge;
    ret.status = (transaction.winner == -1);
    ret.seed = transaction.seed;

    return ret;
}

int check_seed(char* seed, int tid) {
    if(tid > LAST_TRANS) return -1;
    if(tid < LAST_TRANS) return  2;

    int target_bits = TRANSACTIONS[LAST_TRANS].challenge;
    int target_bytes = target_bits/8;
    int remainder_bits = target_bits%8;

    unsigned char sha_result[40];
    SHA1(seed, strlen(seed), sha_result);

    // Checks bits 8 by 8
    for(int i = 0; i < target_bytes; i++) {
        if((sha_result[i] & 0xFF) != 0) {
            return 0;
        }
    }

    // Creates a mask that has <target_bits> 1's and then enough 0's to complete a byte
    int mask = ((1 << target_bits)-1) << (8 - target_bits);
    // Checks the bits that can't be grouped in a byte
    if((sha_result[target_bytes] & mask) != 0)
        return 0;
    else
        return 1;
}

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
        // Finaliza a transação atual
        TRANSACTIONS[tid].winner = cid;
        TRANSACTIONS[tid].seed = malloc(sizeof(char)*strlen(seed));
        strcpy(TRANSACTIONS[tid].seed, seed);

        // Gera a próxima transação
        LAST_TRANS++;
        TRANSACTIONS[LAST_TRANS].challenge = generate_challenge();
        TRANSACTIONS[LAST_TRANS].seed = NULL;
        TRANSACTIONS[LAST_TRANS].winner = -1;
    }

    return result;
}

int main(int argc, char *argv[]) {

    LAST_TRANS = 0;
    TRANSACTIONS[0].challenge = generate_challenge();
    TRANSACTIONS[0].winner = -1;
    TRANSACTIONS[0].seed = NULL;

    // int result = submitChallenge(0, 666, "qbcabcap");
    // printf("%d\n", result);

    // int tid = getTransactionID();
    // printf("%d\n", tid);

    // printf("%d %d\n", getChallenge(tid), getChallenge(tid-1));
    // printf("%d %d\n", getTransactionStatus(tid), getTransactionStatus(tid-1));
    // printf("%d %d\n", getWinner(tid), getWinner(tid-1));

    // TransactionInfo seed1, seed2;
    // seed1 = getSeed(tid);
    // seed2 = getSeed(tid-1);
    // printf("%d %s %d\n", seed1.challenge, seed1.seed, seed1.status);
    // printf("%d %s %d\n", seed2.challenge, seed2.seed, seed2.status);

    return 0;
}