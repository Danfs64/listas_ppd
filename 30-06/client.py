from http.server import executable
from multiprocessing import _LockType, Pool, Process, Lock
from asyncio import Lock
import traceback
from time import sleep
from hashlib import sha1
from random import randint
from functools import partial
import sys
import json
from typing import Callable

import pika
import psutil

CLIENT_ID = None

NUM_PROCESSES = 6
MAX_SEED = 2147483647
PROC_DICT = {}
CHAL_PROCESS_PID = None

CONNECTION = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=600))
CHANNEL = CONNECTION.channel()


def set_chal_exchange(chann):
    return set_exchange(chann, 'ppd/challenge', 'fanout')


def set_result_exchange(chann):
    queue_name = set_exchange(chann, 'ppd/result', 'fanout')
    return queue_name

def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue='', exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    return queue_name


def chal_callback(ch, method, properties, body: str, lock: _LockType=None):
    print("consuming...")
    ch.basic_ack(delivery_tag=method.delivery_tag)
    try:
        message_dict = json.loads(body)
        try:
            tid = int(message_dict['tid'])
            challenge = int(message_dict['challenge'])
        except KeyError:
            print("Algum retardado mandou mensagem no formato errado")
            exit(1)

        #TODO colocar daqui pra baixo num processo spawnante
        print(f"Resolvendo com challenge {challenge}")
        solution = minerar(challenge)
        print(solution)
        seed_json = json.dumps({
            "cid": CLIENT_ID,
            "tid": tid,
            "seed": solution,
        })
        print(f"Sending {seed_json} as a solution")
        CHANNEL.basic_publish(
            exchange='',
            routing_key='ppd/seed',
            body=seed_json,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        exit(0)
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag)
        print(traceback.format_exc())
        exit(1)

def check_seed(seed: int, challenge: int) -> bool:
    byte_seed = seed.to_bytes(8, "little")
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160-target_bits)

    return solution_bits == 0


def solve_challenge(challenge: int) -> int:
    while True:
        seed = randint(0, MAX_SEED)
        if check_seed(seed, challenge):
            return seed


def minerar(challenge: int) -> int:

    # Challenges menores que 20 são mais rápidos que o overhead do paralelismo
    if challenge < 20:
        solution = solve_challenge(challenge)
    else:
        with Pool(processes=NUM_PROCESSES) as pool:
            processes = []
            for _ in range(NUM_PROCESSES):
                proc = pool.apply_async(solve_challenge, args=(challenge,))
                processes.append(proc)

            # processes = [
            #     pool.apply_async(solve_challenge, args=(challenge,))
            #     for _ in range(NUM_PROCESSES)
            # ]
            
            solved = False
            while not solved:
                sleep(1)
                for proc in processes:
                    if proc.ready():
                        solution = proc.get()
                        solved = True
                        break
    return solution

def chal_consume(lock):
    conn = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost', heartbeat=600)
    )
    channel = conn.channel()
    chal_queue_name = set_chal_exchange(channel)
    channel.basic_consume(queue=chal_queue_name, on_message_callback=partial(chal_callback, lock=lock), auto_ack=False)
    channel.start_consuming()


def resul_callback(ch, method, properties, body: str, lock: _LockType=None, challenge_process: Process = None):
    resul_dict = json.loads(body)
    #TODO matar processos se outro cliente resolver
    if True == False:
        challenge_process.kill()
        #TODO atualizar tabela de challenges
        #TODO recriar se outro cliente resolver, ou se recusarem a solução desse cliente
        challenge_process = Process(target=chal_consume, args=lock)
        challenge_process.start()


if __name__ == "__main__":
    assert len(sys.argv) == 2, f"Uso correto: {sys.argv[0]} <clientID>"
    CLIENT_ID = int(sys.argv[1])
    lock = Lock()
    resul_queue_name = set_result_exchange(CHANNEL)
    chal_p = Process(target=chal_consume, args=lock)
    chal_p.start()
    CHANNEL.basic_consume(queue=resul_queue_name, on_message_callback=partial(resul_callback, lock=lock, challenge_process=chal_p), auto_ack=True)
    CHANNEL.start_consuming()