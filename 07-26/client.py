from random import randint, choices
import json
from hashlib import sha1
from multiprocessing import Pool
from functools import partial

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5

from rabbit_handler.handler import get
from settings import *
from domain import Queue, Transaction
from assert_doente_do_dan import get_keys

# TODO os reenvios de mensagens tem que ser de n em n tempo
# Não é difícil fazer, mas é chato

TRANSACTIONS: dict[int, Transaction] = {}
TRANSACTIONS[0] = None
LAST_TRANS = 0

PUB_KEY, PRIV_KEY = get_keys()
SIGNER = PKCS1_v1_5.new(PRIV_KEY)
PUB_KEY_TABLE: dict[int, str] = {NODEID: PUB_KEY}


def check_seed(seed: str, challenge: int) -> bool:
    byte_seed = seed.encode(ENCONDING)
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160 - target_bits)

    return solution_bits == 0


def solve_challenge(challenge: int) -> int:
    while True:
        seed = "".join(choices(SEED_ALPHABET, 15))
        if check_seed(seed, challenge):
            # TODO Talvez ao invês de retornar, essa func pode só mandar pra fila direto
            return seed


def try_to_solve_challenge(challenge: int, n_processees: int):
    with Pool(n_processees) as p:
        _ = p.map(solve_challenge, [challenge] * n_processees)


def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue="", exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    return queue_name


def publish(exchange: Queue, body: str) -> None:
    MANAGING_CHANN.publish(exchange=exchange, routing_key="", body=body)


def sign_message(msg: dict) -> str:
    msg_json = json.dumps(msg)
    msg_digest = SHA256.new(msg_json.encode(ENCONDING))
    signature = SIGNER.sign(msg_digest)
    msg.update({"Sign": signature})
    return json.dumps(msg)


def check_signature(msg: dict, signature: str) -> None:
    sender = int(msg["NodeID"])
    sender_key = PUB_KEY_TABLE[sender]
    verifier = PKCS1_v1_5.new(sender_key)

    msg_json = json.dumps(msg)
    msg_digest = SHA256.new(msg_json.encode())

    sig_bytes = bytes.fromhex(signature)

    return verifier.verify(msg_digest, sig_bytes)


def publish_ID() -> None:
    init_msg = json.dumps({"NodeId": NODEID})
    publish(Queue.INIT, init_msg)




def get_IDs(ids_queue: str, n: int) -> set[int]:
    # clients = {NODEID}
    return get(_get_IDs_wrapper, ids_queue, [n], collection={NODEID})


def _get_IDs_wrapper(body, clients, n):
    new_client = int(json.loads(body)["NodeID"])
    print(f"Cliente {new_client} fez check-in")

    if new_client not in clients:
        print(f"Cliente {new_client} é um cliente novo")
        clients.add(new_client)
        # Reenvia o check-in sempre que detecta um cliente novo
        publish_ID()

        print(f"Clientes conhecidos ({len(clients)}): {clients}")
        if len(clients) == n:
            False, clients
    return True, clients

def publish_key() -> None:
    msg = json.dumps({"NodeID": NODEID, "PubKey": PUB_KEY})
    publish(Queue.KEY, msg)


def get_keys(keys_queue: str, clients: set[int]):
    return get(_get_keys_wrapper, keys_queue, [clients], collection={NODEID: PUB_KEY})


def _get_keys_wrapper(body, public_keys: dict[int, str], clients: set[int]) -> dict[int, str]:
    # public_keys = {NODEID: PUB_KEY}

    body = json.loads(body)
    new_key = body["PubKey"]
    new_client = int(body["NodeID"])
    print(f"Cliente {new_client} mandou uma chave")

    if new_client in clients and new_client not in public_keys.keys():
        print(f"A chave do cliente {new_client} é uma chave nova")
        public_keys[new_client] = new_key
        # Reenvia a chave sempre que detecta uma nova, talvez deva ter um timer
        publish_key()

        if len(public_keys) == len(clients):
            return False, public_keys
    return True, public_keys


def vote_leader() -> None:
    election_number = randint(0, (1 << 32) - 1)
    election_msg = {"NodeID": NODEID, "ElectionNumber": election_number}
    publish(Queue.ELEC, sign_message(election_msg))

def get_leader(leader_queue: str):
    get(get_leader_wrapper, leader_queue, )
    # TODO o get acima retorna um dict, tirar o vencedor da eleição a partir desse dict (linhas 166-175)



# TODO revisar essa func
def get_leader_wrapper(body: str, pub_keys: dict[int, str]) -> int:
    election_numbers = dict()
    body: dict = json.loads(body)
    node_id = int(body["NodeID"])
    election_number = int(body["ElectionNumber"])
    signature = body.pop("Sign")

    if node_id in pub_keys.keys():
        print(f"Recebi um voto do {node_id}")
        if check_signature(body, signature):
            print(f"Voto do {node_id} é um voto válido")
            election_numbers[node_id] = election_number
            # Reenvia a chave sempre que detecta uma nova, talvez deva ter um timer
            # vote_leader() # Mas não pode ser um voto diferente. Gerar voto fora da vote_leader?

        if len(pub_keys) == len(election_numbers):
            # Define o maior election number
            maior_voto = max(election_numbers.values())
            # O vencedor é quem votou com o maior election number
            leader = [
                n_id
                for n_id, e_number in election_numbers.items()
                if e_number == maior_voto
            ]
            # O desempate é pegar o maior nodeID dos que votaram o maior election number
            return False, max(leader)
    return True, None


def publish_challenge(tid: int) -> None:
    msg = {
        "NodeID": NODEID,
        "TransactionNumber": tid,
        "Challenge": randint(1, 10),
    }
    publish(Queue.CHAL, sign_message(msg))


def get_challenge(body: str) -> int:
    body = json.loads(body)
    tid = int(body["TransactionNumber"])
    sender = int(body["NodeID"])
    challenge = int(body["Challenge"])
    signature = body.pop("Sign")

    if sender == leader and tid == LAST_TRANS and check_signature(body, signature):
        return False, challenge

    return True, None


def publish_solution(seed: str, tid: int):
    msg = {"NodeID": NODEID, "TransactionNumber": tid, "Seed": seed}
    publish(Queue.SOL, sign_message(msg))


# TODO essa função está incompleta
def vote_solutions(queue: str) -> None:
    for _, _, body in MANAGING_CHANN.consume(queue):
        body = json.loads(body)
        tid = int(body["TransactionNumber"])
        seed = body["Seed"]
        sender = int(body["NodeID"])
        signature = body.pop("Sign")
        if tid == LAST_TRANS and check_signature(body, signature):
            print(f"Votando na solução {seed} mandada por {sender}")
            issue_vote(seed)

            # TODO Checar resultado da votação

            if votacao_passou():
                break
    MANAGING_CHANN.cancel()


def votacao_passou():
    pass




def issue_vote(seed: str):
    vote_result = int(check_seed(seed))
    vote_msg = {
        "NodeID": NODEID,
        "TransactionNumber": LAST_TRANS,
        "Seed": seed,
        "Vote": vote_result
    }
    vote_json = sign_message(vote_msg)
    publish(Queue.VOTE, vote_json)


def get_votes():
    pass


if __name__ == "__main__":
    n = input("Insira o número de participantes: ")

    init_queue      = set_exchange(MANAGING_CHANN, Queue.INIT, "fanout")
    key_queue       = set_exchange(MANAGING_CHANN, Queue.KEY , "fanout")
    election_queue  = set_exchange(MANAGING_CHANN, Queue.ELEC, "fanout")
    challenge_queue = set_exchange(MANAGING_CHANN, Queue.CHAL, "fanout")
    solution_queue  = set_exchange(MANAGING_CHANN, Queue.SOL , "fanout")
    voting_queue    = set_exchange(MANAGING_CHANN, Queue.VOTE, "fanout")

    # CHECK-IN
    publish_ID()
    participants = get_IDs(init_queue, n)
    print(f"Nós que participarão: {participants}")

    # KEY EXCHANGE
    publish_key()
    public_keys = get_keys(key_queue, participants)
    print("Chaves lidas:", *public_keys.items(), sep="\n")

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
        TRANSACTIONS[LAST_TRANS] = Transaction(challenge, None, -1)
        print(f"Resolvendo o desafio {LAST_TRANS}, com dificuldade {challenge}")

        # TODO Invocar um (ou vários) processos paralelos pra resolver o problema
        solve_challenge(challenge)

        # TODO Ficar de olho na votação
        winner, seed = vote_solutions(solution_queue)

        # TODO Atualizar a tabela de transações
        TRANSACTIONS[LAST_TRANS].seed = seed
        TRANSACTIONS[LAST_TRANS].winner = winner
        LAST_TRANS += 1
