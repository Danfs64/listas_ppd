import multiprocessing
from random import randint
import json
from hashlib import sha1
from multiprocessing import Pool, Process
import os, signal

from Crypto.PublicKey import RSA

from rabbit_handler.handler import get, set_exchange
from settings import *
from domain import Queue, Transaction

from solver import *
from signature import sign_message, check_signature, PUB_KEY

# TODO os reenvios de mensagens tem que ser de n em n tempo
# Não é difícil fazer, mas é chato


def kill_children():
    children = multiprocessing.active_children()
    for child in children:
        child.kill()
signal.signal(signal.SIGTERM, kill_children)


TRANSACTIONS = dict()#: dict[int, Transaction] = {}
TRANSACTIONS[0] = None
LAST_TRANS = 0

PUB_KEY_TABLE = dict() #: dict[int, str] = dict()


def publish(exchange: Queue, body: str) -> None:
    MANAGING_CHANN.basic_publish(exchange=exchange, routing_key="", body=body)


def publish_ID() -> None:
    init_msg = json.dumps({"NodeId": NODEID})
    publish(Queue.INIT.value, init_msg)


def get_IDs(ids_queue: str, n: int):# -> set[int]:
    def _get_IDs_wrapper(body, clients, n):
        new_client = int(json.loads(body)["NodeId"])
        print(f"Cliente {new_client} fez check-in")

        if new_client not in clients:
            print(f"Cliente {new_client} é um cliente novo")
            clients.add(new_client)
            # Reenvia o check-in sempre que detecta um cliente novo
            publish_ID()

            print(f"Clientes conhecidos ({len(clients)}): {clients}")
            # print(n, len(clients), n == len(clients))
            if len(clients) == n:
                return False, clients
        return True, clients

    return get(_get_IDs_wrapper, ids_queue, [n], collection=set())


def publish_key() -> None:
    msg = json.dumps({
        "NodeId": NODEID,
        "PubKey": PUB_KEY.export_key("PEM").decode(ENCONDING)
    })
    publish(Queue.KEY.value, msg)


def get_keys(
    keys_queue: str,
    clients#: set[int]
):
    def _get_keys_wrapper(
        body,
        public_keys,#: dict[int, str],
        clients,#: set[int]
    ):# -> dict[int, str]:

        body = json.loads(body)
        new_key = body["PubKey"]
        new_client = int(body["NodeId"])
        print(f"Cliente {new_client} mandou uma chave")

        if new_client in clients and new_client not in public_keys.keys():
            print(f"A chave do cliente {new_client} é uma chave nova")
            public_keys[new_client] = RSA.import_key(new_key)
            # Reenvia a chave sempre que detecta uma nova, talvez deva ter um timer
            publish_key()

            if len(public_keys) == len(clients):
                return False, public_keys
        return True, public_keys
    return get(_get_keys_wrapper, keys_queue, [clients], collection=dict())


def vote_leader() -> None:
    election_number = randint(0, (1 << 32) - 1)
    election_msg = {"NodeId": NODEID, "ElectionNumber": election_number}
    publish(Queue.ELEC.value, sign_message(election_msg))


def get_leader(leader_queue: str) -> int:
    def _get_leader_wrapper(
        body: str,
        election_numbers,#: dict()
        pub_keys#: dict[int, str]
    ) -> int:
        body: dict = json.loads(body)
        node_id = int(body["NodeId"])
        election_number = int(body["ElectionNumber"])
        signature = body.pop("Sign")

        if node_id in pub_keys:
            print(f"Recebi um voto do {node_id}")
            if (node_id in pub_keys and
                node_id not in election_numbers and
                check_signature(body, signature, pub_keys[node_id])
            ):
                print(f"{node_id} votou validamente em um líder")
                election_numbers[node_id] = election_number
                # Reenvia a chave sempre que detecta uma nova, talvez deva ter um timer
                # vote_leader() # Mas não pode ser um voto diferente. Gerar voto fora da vote_leader?

            if len(pub_keys) == len(election_numbers):
                return False, election_numbers
        return True, election_numbers

    votes = get(_get_leader_wrapper, leader_queue, [PUB_KEY_TABLE], collection=dict())
    # Define o maior election number
    maior_voto = max(votes.values())
    # O vencedor é quem votou com o maior election number
    leader = [n_id for n_id, e_number in votes.items() if e_number == maior_voto]
    # O desempate é pegar o maior nodeID dos que votaram o maior election number
    return max(leader)


def publish_challenge(tid: int) -> None:
    msg = {
        "NodeId": NODEID,
        "TransactionNumber": tid,
        "Challenge": randint(MIN_CHALLENGE, MAX_CHALLENGE-10),
    }
    publish(Queue.CHAL.value, sign_message(msg))


def get_challenge(chal_queue: str):
    def _get_challenge_wrapper(body: str, leader: int) -> int:
        body = json.loads(body)
        tid = int(body["TransactionNumber"])
        sender = int(body["NodeId"])
        challenge = int(body["Challenge"])
        signature = body.pop("Sign")

        if sender == leader and tid == LAST_TRANS and check_signature(body, signature, PUB_KEY_TABLE[sender]):
            return False, challenge

        return True, None

    return get(_get_challenge_wrapper, chal_queue, [leader])


def vote_solutions(voting_queue: str) -> None:
    credentials = pika.credentials.PlainCredentials("admin", "admin")
    read_solution_conn = pika.BlockingConnection(
        pika.ConnectionParameters(host=HOSTNAME, heartbeat=600, credentials=credentials)
    )
    read_solution_chann = read_solution_conn.channel()
    solution_queue = set_exchange(read_solution_chann, Queue.SOL.value, "fanout")

    for _, _, body in read_solution_chann.consume(solution_queue):
        body = json.loads(body)
        tid = int(body["TransactionNumber"])
        seed = body["Seed"]
        sender = int(body["NodeId"])
        signature = body.pop("Sign")
        if tid == LAST_TRANS and check_signature(body, signature, PUB_KEY_TABLE[sender]):
            print(f"Votando na solução {seed} mandada por {sender}")
            issue_vote(seed, TRANSACTIONS[tid].challenge)

            if votacao_passou(voting_queue):
                break
    read_solution_chann.cancel()
    return sender, seed



def votacao_passou(
    voting_queue: str,
):
    def _get_votes_wrapper(
        body: str,
        votes_dict: dict,
    ):
        body: dict = json.loads(body)
        node_id = body["NodeId"]
        tid = int(body["TransactionNumber"])
        signature = body.pop("Sign")
        if (
            node_id in PUB_KEY_TABLE
            and node_id not in votes_dict
            and tid == LAST_TRANS
            and check_signature(body, signature, PUB_KEY_TABLE[node_id])
        ):
            votes_dict[node_id] = int(body["Vote"])
        if len(votes_dict) == len(PUB_KEY_TABLE):
            return False, votes_dict
        return True, votes_dict
    votes_dict = get(_get_votes_wrapper, voting_queue, [], collection=dict())
    if sum(map(int, votes_dict.values())) > len(votes_dict)/2:
        return True
    return False


def issue_vote(seed: str, challenge: int):
    vote_result = int(check_seed(seed, challenge))
    vote_msg = {
        "NodeId": NODEID,
        "TransactionNumber": LAST_TRANS,
        "Seed": seed,
        "Vote": vote_result,
    }
    vote_json = sign_message(vote_msg)
    publish(Queue.VOTE.value, vote_json)


if __name__ == "__main__":
    n = int(input("Insira o número de participantes: "))

    init_queue = set_exchange(MANAGING_CHANN, Queue.INIT.value, "fanout")
    key_queue = set_exchange(MANAGING_CHANN, Queue.KEY.value, "fanout")
    election_queue = set_exchange(MANAGING_CHANN, Queue.ELEC.value, "fanout")
    challenge_queue = set_exchange(MANAGING_CHANN, Queue.CHAL.value, "fanout")
    solution_queue = set_exchange(MANAGING_CHANN, Queue.SOL.value, "fanout")
    voting_queue = set_exchange(MANAGING_CHANN, Queue.VOTE.value, "fanout")

    # CHECK-IN
    publish_ID()
    participants = get_IDs(init_queue, n)
    print(f"Nós que participarão: {participants}")

    # KEY EXCHANGE
    publish_key()
    PUB_KEY_TABLE = get_keys(key_queue, participants)
    print("Chaves lidas:", *PUB_KEY_TABLE.items(), sep="\n")

    # VOTING
    vote_leader()
    leader = get_leader(election_queue)
    print(f"O nó {leader} venceu a eleição")

    # ENDLESS LOOP
    while True:
        # PUBLISHING CHALLENGE IF LEADER
        if NODEID == leader:
            publish_challenge(LAST_TRANS)

        challenge = get_challenge(challenge_queue)
        TRANSACTIONS[LAST_TRANS] = Transaction(challenge, None, -1)
        print(f"Resolvendo o desafio {LAST_TRANS}, com dificuldade {challenge}")

        pid = os.fork()
        if pid == 0:
            try_to_solve_challenge(challenge, LAST_TRANS, 4)
        else:
            winner, seed = vote_solutions(voting_queue)

            TRANSACTIONS[LAST_TRANS].seed = seed
            TRANSACTIONS[LAST_TRANS].winner = winner
            LAST_TRANS += 1
            os.kill(pid, signal.SIGTERM)
