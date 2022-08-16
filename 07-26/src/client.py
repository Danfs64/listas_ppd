import multiprocessing
from random import randint
import json
from hashlib import sha1
from multiprocessing import Pool, Process
import os, signal

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


TRANSACTIONS: dict[int, Transaction] = {}
TRANSACTIONS[0] = None
LAST_TRANS = 0

PUB_KEY_TABLE: dict[int, str] = dict()


def publish(exchange: Queue, body: str) -> None:
    MANAGING_CHANN.publish(exchange=exchange, routing_key="", body=body)


def publish_ID() -> None:
    init_msg = json.dumps({"NodeId": NODEID})
    publish(Queue.INIT, init_msg)


def get_IDs(ids_queue: str, n: int) -> set[int]:
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

    return get(_get_IDs_wrapper, ids_queue, [n], collection={NODEID})


def publish_key() -> None:
    msg = json.dumps({"NodeID": NODEID, "PubKey": PUB_KEY})
    publish(Queue.KEY, msg)


def get_keys(keys_queue: str, clients: set[int]):
    def _get_keys_wrapper(
        body, public_keys: dict[int, str], clients: set[int]
    ) -> dict[int, str]:

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
    return get(_get_keys_wrapper, keys_queue, [clients], collection={NODEID: PUB_KEY})


def vote_leader() -> None:
    election_number = randint(0, (1 << 32) - 1)
    election_msg = {"NodeID": NODEID, "ElectionNumber": election_number}
    publish(Queue.ELEC, sign_message(election_msg))


# TODO revisar essa func
def get_leader(leader_queue: str) -> int:
    def _get_leader_wrapper(body: str, pub_keys: dict[int, str]) -> int:
        election_numbers = dict()
        body: dict = json.loads(body)
        node_id = int(body["NodeID"])
        election_number = int(body["ElectionNumber"])
        signature = body.pop("Sign")

        if node_id in pub_keys:
            print(f"Recebi um voto do {node_id}")
            if check_signature(body, signature, PUB_KEY_TABLE[node_id]):
                print(f"Voto do {node_id} é um voto válido")
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
        "NodeID": NODEID,
        "TransactionNumber": tid,
        "Challenge": randint(1, 10),
    }
    publish(Queue.CHAL, sign_message(msg))


def get_challenge(chal_queue: str):
    def _get_challenge_wrapper(body: str, leader) -> int:
        body = json.loads(body)
        tid = int(body["TransactionNumber"])
        sender = int(body["NodeID"])
        challenge = int(body["Challenge"])
        signature = body.pop("Sign")

        if sender == leader and tid == LAST_TRANS and check_signature(body, signature, PUB_KEY_TABLE[sender]):
            return False, challenge

        return True, None

    return get(_get_challenge_wrapper, chal_queue, [leader])


# TODO essa função está incompleta
def vote_solutions(voting_queue: str) -> None:
    for _, _, body in MANAGING_CHANN.consume(voting_queue):
        body = json.loads(body)
        tid = int(body["TransactionNumber"])
        seed = body["Seed"]
        sender = int(body["NodeID"])
        signature = body.pop("Sign")
        if tid == LAST_TRANS and check_signature(body, signature, PUB_KEY_TABLE[sender]):
            print(f"Votando na solução {seed} mandada por {sender}")
            issue_vote(seed)

            if votacao_passou():
                MANAGING_CHANN.cancel()
                return sender, seed



def votacao_passou(voting_queue: str, clients_ids: set[int]):
    def _get_votes_wrapper(body: str, votes_dict: dict, clients_ids: set[int]):
        body: dict = json.loads(body)
        node_id = body["NodeID"]
        tid = int(body["TransactionNumber"])
        signature = body.pop("Sign")
        # essa porra raisa erro se o signature for errado
        if (
            node_id in clients_ids
            and node_id not in votes_dict
            and tid == LAST_TRANS
            and check_signature(body, signature, PUB_KEY_TABLE[node_id])
        ):
            votes_dict[node_id] = int(body["Vote"])
        if len(votes_dict) == len(clients_ids):
            return False, votes_dict
        return True, votes_dict
    votes_dict = get(_get_votes_wrapper, voting_queue, [clients_ids], collection=dict())
    if sum(map(int, votes_dict.values())) > len(votes_dict / 2):
        return True
    return False


def issue_vote(seed: str):
    vote_result = int(check_seed(seed))
    vote_msg = {
        "NodeID": NODEID,
        "TransactionNumber": LAST_TRANS,
        "Seed": seed,
        "Vote": vote_result,
    }
    vote_json = sign_message(vote_msg)
    publish(Queue.VOTE, vote_json)


if __name__ == "__main__":
    n = input("Insira o número de participantes: ")

    init_queue = set_exchange(MANAGING_CHANN, Queue.INIT, "fanout")
    key_queue = set_exchange(MANAGING_CHANN, Queue.KEY, "fanout")
    election_queue = set_exchange(MANAGING_CHANN, Queue.ELEC, "fanout")
    challenge_queue = set_exchange(MANAGING_CHANN, Queue.CHAL, "fanout")
    solution_queue = set_exchange(MANAGING_CHANN, Queue.SOL, "fanout")
    voting_queue = set_exchange(MANAGING_CHANN, Queue.VOTE, "fanout")

    # CHECK-IN
    publish_ID()
    participants = get_IDs(init_queue, n)
    print(f"Nós que participarão: {participants}")

    # KEY EXCHANGE
    publish_key()
    get_keys(key_queue, participants)
    print("Chaves lidas:", *PUB_KEY_TABLE.items(), sep="\n")

    # VOTING
    vote_leader()
    leader = get_leader(election_queue)
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

        pid = os.fork()
        if pid == 0:
            try_to_solve_challenge(challenge, 4)
        else:
            winner, seed = vote_solutions(solution_queue)

            TRANSACTIONS[LAST_TRANS].seed = seed
            TRANSACTIONS[LAST_TRANS].winner = winner
            LAST_TRANS += 1
            os.kill(pid, signal.SIGTERM)
