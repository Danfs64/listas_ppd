from hashlib import sha1
from multiprocessing import Pool
from random import choices

from settings import *
from domain import Queue
from rabbit_handler.handler import *

def check_seed(seed: str, challenge: int) -> bool:
    byte_seed = seed.encode(ENCONDING)
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160 - target_bits)

    return solution_bits == 0

def publish_solution(seed: str, tid: int):
    msg = {"NodeID": NODEID, "TransactionNumber": tid, "Seed": seed}
    publish(Queue.SOL, sign_message(msg))


def solve_challenge(challenge: int, transaction_id: int) -> int:
    conn = pika.BlockingConnection()
    chann = conn.channel()
    solution_queue = set_exchange(chann, Queue.SOL, "fanout")
    while True:
        seed = "".join(choices(SEED_ALPHABET, 15))
        if check_seed(seed, challenge):
            publish_solution(seed, transaction_id)


def try_to_solve_challenge(challenge: int, n_processees: int):
    with Pool(n_processees) as p:
        _ = p.map(solve_challenge, [challenge] * n_processees)
