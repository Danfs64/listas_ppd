from dataclasses import dataclass
from xmlrpc.server import SimpleXMLRPCServer
from hashlib import sha1

@dataclass
class Transaction:
    challenge: int
    seed: int
    winner: int


TRANSACTIONS: dict[int, Transaction] = {}

LAST_TRANS = -1


def set_last_trans(last_trans: int):
    global LAST_TRANS
    LAST_TRANS = last_trans

def _get_last_trans():
    return LAST_TRANS

CHALL = 1
def generate_challenge():
    global CHALL
    CHALL += 1
    return CHALL // 2


def getTransactionID() -> int:
    ''' Retorna o valor atual da transação com
        desafio ainda pendente de solução.
    '''
    return _get_last_trans()

def getChallenge(tid: int) -> int:
    ''' * Se `tid` for válido, retorna o valor
        do desafio associado a ele.
        * Retorne -1 se o `tid` for inválido.
    '''
    if tid > _get_last_trans():
        return -1

    return TRANSACTIONS[tid].challenge

def getTransactionStatus(tid: int) -> int:
    ''' Se `tid` for válido:
        * retorna 0 se o desafio dessa transação já foi resolvido;
        * retorna 1 caso a transação ainda possua desafio pendente;

        Retorna -1 se a `tid` for inválida.
    '''
    if tid > _get_last_trans():
        return -1

    winner = TRANSACTIONS[tid].winner
    return int(winner == -1)

def getWinner(tid: int) -> int:
    ''' * Retorna o ClientID do vencedor da transação `tid`;
        * Retorna 0 se `tid` ainda não tem vencedor;
        * Retorna -1 se `tid` for inválida.
    '''
    if tid > _get_last_trans():
        return -1

    winner = TRANSACTIONS[tid].winner

    if winner == -1:
        return 0
    else:
        return winner

def getSeed(tid: int):
    ''' Retorna uma tupla com:
        * o status;
        * a seed;
        * e o desafio.
        associados ao `tid`.

        Se `tid` for inválido, retorna uma tupla (-1, None, -1)
    '''
    if tid > _get_last_trans():
        return (-1, None, -1)

    transaction = TRANSACTIONS[tid]
    challenge = transaction.challenge
    seed = transaction.seed
    winner = transaction.winner
    
    return (getTransactionStatus(tid), seed, challenge)

def submitChallenge(tid: int, cid: int, seed: int) -> int:
    ''' Submete uma semente (seed) para o hashing SHA-1 que
        resolva o desafio proposto para a referida `tid`.

        * Retorna -1 se a `tid` for inválida.
        * Retorns 2 se o desafio já foi solucionado;
        * Retorna 0 se a seed não resolve o challenge;
        * Retorna 1 se a seed resolve o challenge;
    '''
    global TRANSACTIONS
    result = check_seed(seed, tid)

    if result == 1:
        TRANSACTIONS[tid].winner = cid
        TRANSACTIONS[tid].seed = seed

        set_last_trans(_get_last_trans() + 1)
        TRANSACTIONS[_get_last_trans()] = Transaction(generate_challenge(), None, -1)

    return result


def check_seed(seed: int, tid: int) -> int:
    if tid > _get_last_trans():
        return -1
    if tid < _get_last_trans():
        return 2

    byte_seed = seed.to_bytes(8, "little")
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = TRANSACTIONS[_get_last_trans()].challenge
    solution_bits = int(sha1_bytes, 16) >> (160-target_bits)

    return int(solution_bits == 0)


if __name__ == "__main__":
    # Cria a primeira transação
    set_last_trans(0)
    TRANSACTIONS[0] = Transaction(generate_challenge(), None, -1)

    # Seta o servidor
    server = SimpleXMLRPCServer(("localhost", 1515))
    print("Listening on port 1515...")
    # server.register_multicall_functions()
    server.register_function(getTransactionID, 'getTransactionID')
    server.register_function(getChallenge, 'getChallenge')
    server.register_function(getTransactionStatus, 'getTransactionStatus')
    server.register_function(submitChallenge, 'submitChallenge')
    server.register_function(getWinner, 'getWinner')
    server.register_function(getSeed, 'getSeed')        

    # roda o servidor
    server.serve_forever()
