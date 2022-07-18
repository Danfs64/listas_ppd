from dataclasses import dataclass
from multiprocessing.pool import AsyncResult
from random import randint
from hashlib import sha1
import multiprocessing
import signal
from time import sleep
import json
import pika
from multiprocessing import Pool, Process
from multiprocessing.sharedctypes import Value
from ctypes import c_int32

NUM_CLIENTS = 10
NUM_PROCESSES = 6
MAX_SEED = 2147483647

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
MY_PID = randint(0, 1<<32)

CONNECTION = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", heartbeat=600)
)
CHANNEL = CONNECTION.channel()

VOTING_CONNECTION = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", heartbeat=600)
)
VOTING_CHANNEL = VOTING_CONNECTION.channel()


def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue='', exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    return queue_name


def check_seed(seed: int, challenge: int) -> bool:
    byte_seed = seed.to_bytes(8, "little")
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160-target_bits)

    return solution_bits == 0


def solve_challenge(challenge: int, solution_pointer=None) -> int:
    while True:
        seed = randint(0, MAX_SEED)
        if check_seed(seed, challenge):
            if solution_pointer:
                solution_pointer.value = seed
            return seed


def minerar(challenge: int) -> int:
    # Challenges menores que 20 são mais rápidos que o overhead do paralelismo
    processes: list[Process] = []
        
    def kill_my_children(*args):
        children = multiprocessing.active_children()
        for child in children: child.kill()

    signal.signal(signal.SIGTERM, kill_my_children)
    if challenge < 20:
        solution = solve_challenge(challenge)
        return solution
    else:
        solution_var = Value(c_int32, -1, lock=False)
        for _ in range(NUM_PROCESSES):
            proc = Process(
                target=solve_challenge, args=(challenge,), 
                kwargs={'solution_pointer': solution_var}
                )
            processes.append(proc)
            proc.start()

        while solution_var.value == -1:
            # waits for a solution
            sleep(1)
        print(solution_var.value)
        solution = solution_var.value
        for proc in processes:
            assert isinstance(proc, Process)
            proc.terminate()
        return solution

# FAZER CHECKIN NO BROKER
def check_in() -> None:
    CHANNEL.basic_publish(
        exchange='ppd/check-in',
        routing_key='',
        body=json.dumps({"pid": MY_PID})
    )
    print(f"Eu sou o cliente {MY_PID} e eu fiz meu check-in")

# ESPERAR TODOS OS MEMBROS ENTRAREM
def wait_others(queue: str) -> set[int]:
    clients = {MY_PID}
    for _, _, body in CHANNEL.consume(queue):
        new_client = int(json.loads(body)['pid'])
        print(f"Cliente {new_client} fez check-in")

        if new_client not in clients:
            print(f"Cliente {new_client} é um cliente novo")
            clients.add(new_client)
            # Reenvia o check-in sempre que detecta um cliente novo
            CHANNEL.basic_publish(
                exchange='ppd/check-in',
                routing_key='',
                body=json.dumps({"pid": MY_PID})
            )
            print(f"Clientes conhecidos ({len(clients)}): {clients}")
            if len(clients) == NUM_CLIENTS:
                break
    CHANNEL.cancel()
    return clients

# VOTAR NO LÍDER
def leader_vote(clients: set, leader_queue: str) -> None:
    my_vote = list(clients)[randint(0, NUM_CLIENTS-1)]
    CHANNEL.basic_publish(
        exchange=leader_queue,
        routing_key='',
        body=json.dumps({'sender': MY_PID, 'vote': my_vote})
    )
    print(f"Eu votei no {my_vote}")

# RESULTADO DA VOTAÇÃO
def leader_result(clients: set, queue: str) -> int:
    votes = {pid: 0 for pid in clients}
    counter = 0
    for _, _, body in CHANNEL.consume(queue):
        body = json.loads(body)
        sender = int(body['sender'])
        voted_client = int(body['vote'])
        if sender not in clients:
            print((
                "PANIC!\n"
                f"Voto de cliente desconhecido ({sender}) recebido!\n"
                "Ignorando voto"
            ))
        else:
            votes[voted_client] += 1
            counter += 1
            if counter == NUM_CLIENTS:
                break
    CHANNEL.cancel()

    print("RESULTADO DA VOTAÇÃO:")
    print(votes)
    most_votes = max(votes.values())
    leader = [pid for pid, n in votes.items() if n == most_votes]
    leader.sort()
    leader = leader[0]
    print(f"VENCEDOR DA VOTAÇÃO: {leader}")
    return leader

# GERAÇÃO DE DESAFIO
def publish_challenge(cid: int, x: int, y: int) -> None:
    challenge = randint(x, y)
    CHANNEL.basic_publish(
        exchange='ppd/challenges',
        routing_key='',
        body=json.dumps({'sender': MY_PID, 'cid': cid, 'challenge': challenge})
    )
    print(f"Publiquei o desafio {challenge}")

# LEITURA E RESOLUÇÃO DO DESAFIO
def publish_solution(cid: int, challenge: int) -> None:
    # Entra em loop infinito tentando resolvr o challenge e mandando soluções
    # Essa função (publish_solution) deve ser parada por um processo/thread a parte
    localnnection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", heartbeat=600)
    )
    localnnel = localnnection.channel()

    while True:
        solution = minerar(challenge)
        localnnel.basic_publish(
            exchange='ppd/solutions',
            routing_key='',
            body=json.dumps({'sender': MY_PID, 'cid': cid, 'solution': solution})
        )

# PROCESSAR SOLUÇÕES
def process_solutions(challenge_id: int, solution_queue: str, voting_queue: str) -> None:
    for _, _, body in CHANNEL.consume(solution_queue):
        body = json.loads(body)
        cid = int(body['cid'])
        sender = int(body['sender'])
        solution = int(body['solution'])

        # Se é uma tentativa de solução do challenge correto
        if cid == challenge_id:
            print(f"A solução: {body} será votada")
            solved = check_seed(solution, TRANSACTIONS[cid].challenge)
            VOTING_CHANNEL.basic_publish(
                exchange='ppd/voting',
                routing_key='',
                body=json.dumps({'solved': solved})
            )
            voting_result = process_voting(voting_queue)
            # Se a votação aceita a resposta, registra e retorna
            if voting_result:
                TRANSACTIONS[cid].seed = solution
                TRANSACTIONS[cid].winner = sender
                print(TRANSACTIONS[cid])
                break
    CHANNEL.cancel()
# RESULTADO VOTAÇÃO
def process_voting(queue: str) -> bool:
    votes = {True: 0, False: 0}
    counter = 0
    for _, _, body in VOTING_CHANNEL.consume(queue):
        body = json.loads(body)
        solved = bool(body['solved'])
        votes[solved] += 1
        counter += 1
        if counter == NUM_CLIENTS:
            break
    VOTING_CHANNEL.cancel()
    return votes[True] > votes[False]

if __name__ == "__main__":
    # Declaração das exchanges/filas usadas
    check_in_queue = set_exchange(CHANNEL, 'ppd/check-in', 'fanout')
    leader_queue = set_exchange(CHANNEL, 'ppd/leader', 'fanout')
    challenge_queue = set_exchange(CHANNEL, 'ppd/challenges', 'fanout')
    solution_queue = set_exchange(CHANNEL, 'ppd/solutions', 'fanout')
    voting_queue = set_exchange(VOTING_CHANNEL, 'ppd/voting', 'fanout')

    check_in()
    clients = wait_others(check_in_queue)
    leader_vote(clients, 'ppd/leader')
    print("Iremos começar tehee")
    leader = leader_result(clients, leader_queue)

    # A partir daqui, é o loop de:
    # - Líder gera challenge
    # - Clientes tentam resolver
    # - Uma resposta é aceita
    # - Volta pro início do loop
    while True:
        if leader == MY_PID: publish_challenge(len(TRANSACTIONS), 21, 22)

        # Lê mensagens da fila de challenges até receber uma válida
        for _, _, body in CHANNEL.consume(challenge_queue):
            body = json.loads(body)
            cid = int(body['cid'])
            sender = int(body['sender'])
            challenge = int(body['challenge'])
            print(f"Resolvendo: {body}")
            if cid == len(TRANSACTIONS) and sender == leader:
                break
        CHANNEL.cancel()
        # Registra a transação a ser resolvida
        TRANSACTIONS[cid] = Transaction(challenge, None, -1)

        # Essa função deve ser executada por um processo/thread próprio
        proc = Process(target=publish_solution, args=(cid, challenge))
        proc.start()
        # Você deve parar a thread/processo executando `publish_solution`
        # quando a função abaixo retornar
        process_solutions(cid, solution_queue, voting_queue)
        proc.kill()        
