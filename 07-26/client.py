from random import randint, choices
import json
from hashlib import sha1

import pika
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5

from settings import *
from domain import Queue, Transaction
from assert_doente_do_dan import get_keys


TRANSACTIONS: dict[int, Transaction] = {}
TRANSACTIONS[0] = None

PUB_KEY, PRIV_KEY = get_keys()
SIGNER = PKCS1_v1_5.new(PRIV_KEY)
PUB_KEY_TABLE: dict[int, str] = {NODEID: PUB_KEY}

def check_seed(seed: str, challenge: int) -> bool:
    byte_seed = seed.encode()
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160-target_bits)

    return solution_bits == 0

def solve_challenge(challenge: int) -> int:
    while True:
        seed = ''.join(choices(SEED_ALPHABET, 15))
        if check_seed(seed, challenge):
            # TODO Talvez ao invês de retornar, essa func pode só mandar pra fila direto
            return seed

def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue='', exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    return queue_name

def publish(exchange: Queue, body: str) -> None:
    MANAGING_CHANN.publish(
        exchange=exchange,
        routing_key='',
        body=body
    )

def sign_message(msg: str) -> str:
    msg_digest = SHA256.new(msg.encode())
    signature = SIGNER.sign(msg_digest)


def publish_ID() -> None:
    init_msg = json.dumps({"NodeId": NODEID})
    publish(Queue.INIT, init_msg)

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
    msg = json.dumps({
        "NodeID": NODEID,
        "PubKey": PUB_KEY
    })
    publish(Queue.KEY, msg)

def get_keys(queue: str, clients: set[int]) -> dict[int, str]:
    public_keys = {NODEID: PUB_KEY}
    for _, _, body in MANAGING_CHANN.consume(queue):
        body = json.loads(body)
        new_key = body['PubKey']
        new_client = int(body['NodeID'])
        print(f"Cliente {new_client} mandou uma chave")

        if new_client in clients and new_client not in public_keys.keys():
            print(f"A chave do cliente {new_client} é uma chave nova")
            public_keys[new_client] = new_key
            # Reenvia a chave sempre que detecta uma nova, talvez deva ter um timer
            publish_key()

            if len(public_keys) == len(clients):
                break
    MANAGING_CHANN.cancel()
    return public_keys

def vote_leader() -> None:
    # TODO garantir que a ordem dos campos está correta
    election_number = randint(0, (1 << 32)-1)
    election_msg = json.dumps({
        "NodeID": NODEID,
        "ElectionNumber": election_number
    })

    # TODO assinar e enviar a mensagem
    pass

# TODO revisar essa func
def get_leader(queue: str, pub_keys: dict[int, str]) -> int:
    election_numbers = dict()
    for _, _, body in MANAGING_CHANN.consume(queue):
        body = json.loads(body)
        node_id = int(body['NodeID'])
        election_number = int(body['ElectionNumber'])
        signature = body['Sign']

        if node_id in pub_keys.keys():
            print(f"Recebi um voto do {node_id}")
            if assinatura_valida():
                print(f"Voto do {node_id} é um voto válido")
                election_numbers[node_id] = election_number
                # Reenvia a chave sempre que detecta uma nova, talvez deva ter um timer
                publish_key()

            if len(pub_keys) == len(election_numbers):
                break
    MANAGING_CHANN.cancel()

    # Define o maior election number
    maior_voto = max(election_numbers.values())
    # O vencedor é quem votou com o maior election number
    leader = [
        n_id
        for n_id, e_number in election_numbers.items()
        if e_number == maior_voto
    ]
    # O desempate é pegar o maior nodeID dos que votaram o maior election number
    return max(leader)

def publish_challenge() -> None:
    msg = json.dumps({
        "NodeID": NODEID,
        "Challenge": randint(1, 10),
    })

    # TODO assinar e enviar a mensagem
    pass

def get_challenge(queue: str) -> int:
    for _, _, body in MANAGING_CHANN.consume(queue):
        body = json.loads(body)
        # cid = int(body['cid'])
        sender = int(body['NodeID'])
        challenge = int(body['Challenge'])
        signature = body['Sign']
        if sender == leader and assinatura_valida():
            print(f"Resolvendo dificuldade {challenge}")
            break
    MANAGING_CHANN.cancel()
    return challenge

# TODO checar essa função
def vote_solutions(queue: str) -> None:
    for _, _, body in MANAGING_CHANN.consume(queue):
        body = json.loads(body)
        # cid = int(body['cid'])
        seed = body['seed']
        sender = int(body['NodeID'])
        signature = body['Sign']
        if assinatura_valida():
            print(f"Votando na solução {seed} mandada por {sender}")
            if check_solution(seed):
                send_vote(True)
            else:
                send_vote(False)
            
            # TODO Checar resultado da votação

            if votacao_passou():
                break
    MANAGING_CHANN.cancel()

if __name__=="__main__":
    n = input("Insira o número de participantes: ")

    init_queue      = set_exchange(MANAGING_CHANN, Queue.INIT, "fanout")
    key_queue       = set_exchange(MANAGING_CHANN, Queue.KEY,  "fanout")
    election_queue  = set_exchange(MANAGING_CHANN, Queue.ELEC, "fanout")
    challenge_queue = set_exchange(MANAGING_CHANN, Queue.CHAL, "fanout")
    solution_queue  = set_exchange(MANAGING_CHANN, Queue.SOL,  "fanout")
    voting_queue    = set_exchange(MANAGING_CHANN, Queue.VOTE, "fanout")

    # CHECK-IN
    publish_ID()
    participants = get_IDs(init_queue, n)
    print(f"Nós que participarão: {participants}")

    # KEY EXCHANGE
    publish_key()
    public_keys = get_keys(key_queue, participants)
    print("Chaves lidas:", *public_keys.items(), sep='\n')

    # VOTING
    vote_leader()
    leader = get_leader(election_queue, public_keys)
    print(f"O nó {leader} venceu a eleição")

    # ENDLESS LOOP
    while True:
        # PUBLISHING CHALLENGE IF LEADER
        if NODEID == leader:
            publish_challenge()

        challenge = get_challenge(challenge_queue)

        # TODO Invocar um (ou vários) processos paralelos pra resolver o problema
        solve_challenge(challenge)

        # TODO Ficar de olho na votação
        vote_solutions(solution_queue)
