from dataclasses import dataclass
from hashlib import sha1
import sys
import json

import pika

CONNECTION = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=600)
)
CHANNEL = CONNECTION.channel()



@dataclass
class Transaction:
    challenge: int
    seed: int
    winner: int

    def __str__(self) -> str:
        return (
            f"Challenge: {self.challenge} | "
            f"Seed vencedora: {self.seed if self.seed else 'Nenhuma'} | "
            f"Cliente vencedor: {self.winner if (self.winner != -1) else 'Nenhum'}"
        )

TRANSACTIONS: dict[int, Transaction] = {}
def print_transactions() -> None:
    for k, v in TRANSACTIONS.items():
        print(f"Transação nº {k}")
        print(f"  {v}")

LAST_TRANS = -1
def set_last_trans(last_trans: int) -> None:
    global LAST_TRANS
    LAST_TRANS = last_trans

def _get_last_trans() -> int:
    return LAST_TRANS

CHALL = 1
def generate_challenge() -> int:
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
        * Retorna -1 se o `tid` for inválido.
    '''
    if tid > _get_last_trans():
        return -1

    return TRANSACTIONS[tid].challenge

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


def callback(ch, method, properties, body):
    message_dict = json.loads(body)
    try:
        tid  = int(message_dict['tid'])
        cid  = int(message_dict['cid'])
        seed = int(message_dict['seed'])
    except KeyError:
        print("Algum retardado mandou mensagem no formato errado")
        exit(1)
    result = submitChallenge(tid, cid, seed)
    if result == 1:
        new_trans = _get_last_trans()
        chal_body = json.dumps({
            "tid": new_trans,
            "challenge": getChallenge(new_trans)
        })
        result_body = json.dumps ({
            "tid": tid,
            "cid": cid,
            "seed": seed
        })
        print_transactions()
        CHANNEL.basic_publish(exchange='ppd/challenge', routing_key='', body=chal_body)
        CHANNEL.basic_publish(exchange='ppd/result', routing_key='', body=result_body)

def set_exchanges():
    CHANNEL.exchange_declare(exchange='ppd/challenge',
                                exchange_type='fanout')
    CHANNEL.exchange_declare(exchange='ppd/result',
                                exchange_type='fanout')
    CHANNEL.queue_declare(queue='ppd/seed', durable=True)

    trans = _get_last_trans()
    body = json.dumps({
        "tid": trans,
        "challenge": getChallenge(trans)
    })
    CHANNEL.basic_publish(exchange='ppd/challenge', routing_key='', body=body)
    print("sent first")




if __name__ == "__main__":
    # Cria a primeira transação
    set_last_trans(0)
    TRANSACTIONS[0] = Transaction(generate_challenge(), None, -1)
    
    # Inicializa os exchanges/filas, mandando o primeiro challenge
    set_exchanges()

    # Coloca o servidor para consumir
    CHANNEL.basic_consume(queue='ppd/seed', on_message_callback=callback, auto_ack=True)
    CHANNEL.start_consuming()
