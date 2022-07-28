import json
import pika
from dataclasses import dataclass
from random import randint
from settings import HOSTNAME
from enum import Enum

from Crypto.PublicKey import RSA


class Queue(Enum):
    INIT = 'ppd/init'
    CHAL = 'ppd/chal'
    KEY  = 'ppd/pubkey'

@dataclass
class Transaction:
    challenge: int
    seed: str
    winner: int

    def __str__(self) -> str:
        return (
            f"Challenge: {self.challenge} | "
            f"Seed vencedora: {self.seed if self.seed else 'Nenhuma'} | "
            f"Cliente vencedor: {self.winner if (self.winner != -1) else 'Nenhum'}"
        )

TRANSACTIONS: dict[int, Transaction] = {}
TRANSACTIONS[0] = None

NODEID = randint(0, (1<<32)-1)

MANAGING_CONN  = pika.BlockingConnection(
    host=HOSTNAME
)
FOUR_CHAN = MANAGING_CONN.channel()
MANAGING_CHANN = FOUR_CHAN

PUB_KEY = RSA.importKey(open("public_key.txt").read())

def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue='', exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    return queue_name

def publish_ID() -> None:
    init_msg = {"NodeId": NODEID}
    MANAGING_CHANN.publish(
        exchange=Queue.INIT,
        routing_key='',
        body=json.dumps(init_msg)
    )

def get_IDs(queue: str, n: int) -> set[int]:
    clients = {NODEID}
    for _, _, body in MANAGING_CHANN.consume(queue):
        new_client = int(json.loads(body)['NodeID'])
        print(f"Cliente {new_client} fez check-in")

        if new_client not in clients:
            print(f"Cliente {new_client} é um cliente novo")
            clients.add(new_client)
            # Reenvia o check-in sempre que detecta um cliente novo
            publish_ID()

            print(f"Clientes conhecidos ({len(clients)}): {clients}")
            if len(clients) == n:
                break
    MANAGING_CHANN.cancel()
    return clients

def publish_key() -> None:
    msg = {
        "NodeID": NODEID,
        "PubKey": PUB_KEY
    }
    MANAGING_CHANN.publish(
        exchange=Queue.KEY,
        routing_key='',
        body=json.dumps(msg)
    )

def get_keys(queue: str, clients: set[int]) -> dict[int, str]:
    public_keys = {NODEID: PUB_KEY}
    for _, _, body in MANAGING_CHANN.consume(queue):
        body = json.loads(body)
        new_client = int(body['NodeID'])
        new_key = body['PubKey']
        print(f"Cliente {new_client} mandou uma chave")

        if new_client in clients and new_client not in public_keys.keys():
            print(f"A chave do cliente {new_client} é uma chave nova")
            public_keys[new_client] = new_key
            # Reenvia o check-in sempre que detecta um cliente novo
            publish_key()

            # print(f"Clientes conhecidos ({len(clients)}): {clients}")
            if len(public_keys) == n:
                break
    MANAGING_CHANN.cancel()
    return public_keys

if __name__=="__main__":
    n = input("Insira o número de participantes: ")

    init_queue = set_exchange(MANAGING_CHANN, Queue.INIT, "fanout")
    key_queue = set_exchange(MANAGING_CHANN, Queue.KEY, "fanout")

    publish_ID()
    participants = get_IDs(init_queue, n)

    publish_key()
    public_keys = get_keys(key_queue, participants)
