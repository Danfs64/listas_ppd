from multiprocessing import Pool, Process
from asyncio import Lock
from time import sleep
from hashlib import sha1
from random import randint
import sys
import json

import pika
import psutil

CLIENT_ID = None

NUM_PROCESSES = 6
MAX_SEED = 2147483647
PROC_DICT = {}
CHAL_PROCESS_PID = None
LOCK = Lock()


CONNECTION = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=600))
CHANNEL = CONNECTION.channel()


def set_chal_exchange(chann):
    return set_exchange(chann, 'ppd/challenge', 'fanout')


def set_result_exchange(chann):
    queue_name = set_exchange(chann, 'ppd/result', 'fanout')
    print(queue_name)
    return queue_name

def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue='', exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    print(queue_name)
    return queue_name


def chal_callback(ch, method, properties, body: str):
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
    except Exception as e:
        print(e)
        ch.basic_nack(delivery_tag=method.delivery_tag)


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

def chal_consume():
    conn = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=600))
    channel = conn.channel()
    chal_queue_name = set_chal_exchange(channel)
    print("will start")
    channel.basic_consume(queue=chal_queue_name, on_message_callback=chal_callback, auto_ack=False)
    channel.start_consuming()


def resul_callback(ch, method, properties, body: str):
    resul_dict = json.loads(body)
    if resul_dict['cid'] != CLIENT_ID:
        global CHAL_PROCESS_PID
        if CHAL_PROCESS_PID:
            print(f"Killing process {CHAL_PROCESS_PID} because the challenge was solved by another client")
            parent = psutil.Process(CHAL_PROCESS_PID)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            chal_p = Process(target=chal_consume)
            chal_p.start()
            CHAL_PROCESS_PID = chal_p.pid


if __name__ == "__main__":
    assert len(sys.argv) == 2, f"Uso correto: {sys.argv[0]} <clientID>"
    CLIENT_ID = int(sys.argv[1])

    resul_queue_name = set_result_exchange(CHANNEL)
    chal_p = Process(target=chal_consume)
    chal_p.start()
    CHAL_PROCESS_PID = chal_p.pid
    print(CHAL_PROCESS_PID)
    CHANNEL.basic_consume(queue=resul_queue_name, on_message_callback=resul_callback, auto_ack=True)
    CHANNEL.start_consuming()



