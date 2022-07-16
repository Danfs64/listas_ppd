from dataclasses import dataclass
from random import randint
from hashlib import sha1
from time import sleep
import json
import pika

NUM_CLIENTS = 3
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
            print(f"Cliente {new_cliente} é um cliente novo")
            clients.add(new_client)
            # Reenvia o check-in sempre que detecta um cliente novo
            CHANNEL.basic_publish(
                exchange='ppd/check-in',
                routing_key='',
                body=json.dumps({"pid": MY_PID})
            )
            print(f"Clientes conhecidos ({len(clientes)}): {clients}")
            if len(clients) == NUM_CLIENTS:
                break
    CHANNEL.cancel()
    return clients

# VOTAR NO LÍDER
def leader_vote(clients: set) -> None:
    my_vote = list(clients)[randint(0, NUM_CLIENTS-1)]
    CHANNEL.basic_publish(
        exchange='ppd/voting',
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
    leader = [pid for pid, n in votes.items() if n == most_votes].sort()[0]
    print(f"VENCEDOR: {leader}")
    return leader

# GERAÇÃO DE DESAFIO
def publish_challenge(cid: int, x: int, y: int) -> None:
    CHANNEL.queue_declare(queue="challenges")
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
    while True:
        solution = minerar(challenge)
        CHANNEL.basic_publish(
            exchange='ppd/solutions',
            routing_key='',
            body=json.dumps({'sender': MY_PID, 'cid': cid, 'solution': solution})
        )

# PROCESSAR SOLUÇÕES
def process_solutions(challenge_id: int, solution_queue: str, voting_queue: str) -> None:
    for _, _, body in CHANNEL.consume(solution_queue):
        body = json.loads(json)
        cid = int(json['cid'])
        sender = int(json['sender'])
        solution = int(json['solution'])

        # Se é uma tentativa de solução do challenge correto
        if cid == challenge_id:
            solved = check_seed(solution, TRANSACTIONS[cid].challenge)
            CHANNEL.basic_publish(
                exchange='ppd/solution_voting',
                routing_key='',
                body=json.dumps({'solved': solved})
            )
            voting_result = process_voting(voting_queue)
            # Se a votação aceita a resposta, registra e retorna
            if voting_result:
                TRANSACTIONS[cid].seed = solution
                TRANSACTIONS[cid].winner = sender
                return

# RESULTADO VOTAÇÃO
def process_voting(queue: str) -> bool:
    votes = {True: 0, False: 0}
    counter = 0
    for _, _, body in CHANNEL.consume(queue):
        solved = bool(body['solved'])
        votes[solved] += 1
        counter += 1
        if counter == NUM_CLIENTS:
            break

    return votes[True] > votes[False]

if __name__ == "__main__":
    # Declaração das exchanges/filas usadas
    check_in_queue = set_exchange(CHANNEL, 'ppd/check-in', 'fanout')
    leader_queue = set_exchange(CHANNEL, 'ppd/leader', 'fanout')
    challenge_queue = set_exchange(CHANNEL, 'ppd/challenges', 'fanout')
    solution_queue = set_exchange(CHANNEL, 'ppd/solutions', 'fanout')
    voting_queue = set_exchange(CHANNEL, 'ppd/voting', 'fanout')

    check_in()
    clients = wait_others(check_in_queue)

    leader_vote(clients)
    leader = leader_result(clients, leader_queue)

    # A partir daqui, é o loop de:
    # - Líder gera challenge
    # - Clientes tentam resolver
    # - Uma resposta é aceita
    # - Volta pro início do loop
    while True:
        if leader == MY_PID: publish_challenge(len(TRANSACTIONS), 40, 40)

        # Lê mensagens da fila de challenges até receber uma válida
        for _, _, body in CHANNEL.consume(challenge_queue):
            body = json.loads(body)
            cid = int(body['cid'])
            sender = int(body['sender'])
            challenge = int(body['challenge'])
            if cid == len(TRANSACTIONS) and sender == leader:
                break

        # Registra a transação a ser resolvida
        TRANSACTIONS[cid] = Transaction(challenge, None, -1)

        # Essa função deve ser executada por um processo/thread próprio
        publish_solution(cid, challenge)
        # Você deve parar a thread/processo executando `publish_solution`
        # quando a função abaixo retornar
        process_solutions(cid, solution_queue, voting_queue)
