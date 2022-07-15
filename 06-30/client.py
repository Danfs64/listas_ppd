from random import randint
import pika
import json

NUM_CLIENTS = 3
NUM_PROCESSES = 6
MAX_SEED = 2147483647

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

if __name__ == "__main__":
    # INICIALIZAÇÃO DE VARIÁVEIS
    ## Se for colocar os blocos de código abaixo dentro de funções,
    ## é valido colocar essas 3 variáveis como globais
    my_pid = randint(0, 1<<32)
    conn = pika.BlockingConnection(
        pika.ConnectionParameters(host="localhost", heartbeat=600)
    )
    chann = conn.channel()

    # FAZER CHECKIN NO BROKER
    #! PRECISA SER UMA QUEUE QUE TODO MUNDO RECEBE TODAS AS MSGS
    #! TALVEZ PRECISE DECLARAR COMO EXCHANGE FANOUT AO INVES DE QUEUE?
    chann.queue_declare(queue="check-in")
    chann.basic_publish(
        exchange='',
        routing_key="check-in",
        body=json.dumps({"pid": my_pid})
    )
    print(f"Eu sou o cliente {my_pid} e eu fiz meu check-in")

    # ESPERAR TODOS OS MEMBROS ENTRAREM
    clients = {my_pid}
    for _, _, body in chann.consume():
        new_client = int(json.loads(body)['pid'])
        print(f"Cliente {new_client} fez check-in")
        if new_client not in clients:
            print(f"Cliente {new_cliente} é um cliente novo")
            clients.add(new_client)
            # Reenvia o check-in sempre que detecta um cliente novo
            chann.basic_publish(
                exchange='',
                routing_key="check-in",
                body=json.dumps({"pid": my_pid})
            )
        print(f"Clientes conhecidos ({len(clientes)}): {clients}")
        if len(clients) == NUM_CLIENTS:
            break
    chann.cancel()
    exit(0)

    # VOTO NO LÍDER
    my_vote = list(clients)[randint(0, NUM_CLIENTS-1)]
    chann.queue_declare(queue="voting")
    chann.basic_publish(
        exchange='',
        routing_key="voting",
        body=json.dumps({'sender': my_pid, 'vote': my_vote})
    )
    print(f"Eu, {my_pid}, votei no {my_vote}")

    # RESULTADO DA VOTAÇÃO
    votes = {pid: 0 for pid in clients}
    counter = 0
    for _, _, body in chann.consume():
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
    chann.cancel()

    print("RESULTADO DA VOTAÇÃO:")
    print(votes)
    most_votes = max(votes.values())
    leader = [pid for pid, n in votes.items() if n == most_votes].sort()[0]
    print(f"VENCEDOR: {leader}")

    # RESOLUÇÃO DO DESAFIO
    chann.queue_declare(queue="challenges")
    ## GERAÇÃO DO DESAFIO, SE FOR O LÍDER
    if leader == my_pid:
        challenge = randint(25, 25)
        chann.basic_publish(
            exchange='',
            routing_key="challenges",
            body=json.dumps({"challenge": challenge})
        )

    ## CONSUMO E RESOLUÇÃO DO DESAFIO

    # DESAFIO RESOLVIDO
