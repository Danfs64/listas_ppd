from hashlib import sha1
from multiprocessing import Pool
from random import choices

from settings import *
from domain import Queue
from rabbit_handler.handler import *
from signature import sign_message

def check_seed(seed: str, challenge: int) -> bool:
    byte_seed = seed.encode(ENCONDING)
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160 - target_bits)

    return solution_bits == 0

def publish_solution(chann, seed: str, tid: int):
    msg = {"NodeId": NODEID, "TransactionNumber": tid, "Seed": seed}
    msg_json = sign_message(msg)
    chann.basic_publish(
        exchange=Queue.SOL.value,
        routing_key='',
        body=msg_json
    )    


def solve_challenge(tupla) -> int:
    challenge, transaction_id = tupla
    conn = pika.BlockingConnection(
        pika.ConnectionParameters(host=HOSTNAME, heartbeat=600, credentials=PIKA_CREDENTIALS)
    )
    chann = conn.channel()
    solution_queue = set_exchange(chann, Queue.SOL.value, "fanout")
    while True:
        seed = "".join(choices(SEED_ALPHABET, k=15))
        if check_seed(seed, challenge):
            publish_solution(chann, seed, transaction_id)


def try_to_solve_challenge(challenge: int, transaction_id: int, n_processees: int):
    with Pool(n_processees) as p:
        _ = p.map(solve_challenge, [(challenge, transaction_id)] * n_processees)
