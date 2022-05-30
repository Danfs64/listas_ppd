import xmlrpc.client
import sys
from multiprocessing import Pool
from time import sleep
from hashlib import sha1
from random import randint


NUM_PROCESSES = 6
# MAX_SEED = abs(~(1 << 31))
MAX_SEED = 2147483647

def getTransactionID(proxy: xmlrpc.client.ServerProxy, _: int) -> int:
    transactionID = proxy.getTransactionID()
    print(f"\nTransação atual: {transactionID}")
    return transactionID

def getChallenge(proxy: xmlrpc.client.ServerProxy, transactionID: int) -> int:
    challenge = proxy.getChallenge(transactionID)
    print(f"\nChallenge da transação {transactionID}: {challenge}")
    return challenge

def getTransactionStatus(proxy: xmlrpc.client.ServerProxy, transactionID: int):
    challenge = proxy.getChallenge(transactionID)
    print(f"\nStatus da transação {transactionID}: {challenge}")
    return challenge

def getWinner(proxy: xmlrpc.client.ServerProxy, transactionID: int):
    winner = proxy.getWinner(transactionID)
    print(f"\nVencedor da transação {transactionID}: {winner}")
    return winner

def getSeed(proxy: xmlrpc.client.ServerProxy, transactionID: int) -> tuple[int, int, int]:
    seed = proxy.getSeed(transactionID)
    if not seed[0]:
        print(f"\nA transação {transactionID} tem status {seed[0]}, seed {seed[1]} e challenge {seed[2]}\n")
    else:
        print(f"\nA transação {transactionID} ainda não foi resolvida")

    return seed


def check_seed(seed: int, challenge: int) -> int:
    byte_seed = seed.to_bytes(8, "little")
    sha1_bytes = sha1(byte_seed).hexdigest()
    target_bits = challenge
    solution_bits = int(sha1_bytes, 16) >> (160-target_bits)

    return int(solution_bits == 0)


def solve_challenge(challenge: int) -> int:
    while True:
        seed = randint(0, MAX_SEED)
        if check_seed(seed, challenge):
            return seed


def minerar(proxy: xmlrpc.client.ServerProxy, _: int) -> None:
    curr_trans = getTransactionID(proxy, _)
    challenge = getChallenge(proxy, curr_trans)

    # Challenges menores que 20 são mais rápidos que o overhead do paralelismo
    if challenge < 20:
        solution = solve_challenge(challenge)
    else:
        with Pool(processes=NUM_PROCESSES) as pool:
            processes = []
            for idx in range(NUM_PROCESSES):
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

    print(f"Seed encontrada que resolve o challenge: {solution}")
    pong = proxy.submitChallenge(curr_trans, 666, solution)

    if   pong ==  1: print(f"A seed {solution} resolveu o challenge!")
    elif pong ==  0: print(f"A seed {solution} não resolve o challenge")
    elif pong == -1: print(f"A TransactionID {curr_trans} é inválida")
    elif pong ==  2: print(f"A TransactionID {curr_trans} já fora resolvido")


if __name__ == "__main__":
    # Nº de argumentos
    n = len(sys.argv)
    assert n==3, f"Uso correto: {sys.argv[0]} <host> <port>"

    # Conexão com o servidor
    rpcServerAddr = f"http://{sys.argv[1]}:{sys.argv[2]}/"
    proxy = xmlrpc.client.ServerProxy(rpcServerAddr)

    function_table = {
        1: minerar,
        2: getTransactionID,
        3: getChallenge,
        4: getTransactionStatus,
        5: getWinner,
        6: getSeed
    }

    menu_str = (
        "\nMENU\n"
        "Escolha o número equivalente a função que você quer rodar:\n\n"
        "1 - Minerar\n"
        "2 - getTransactionID\n"
        "3 - getChallenge\n"
        "4 - getTransactionStatus\n"
        "5 - getWinner\n"
        "6 - getSeed\n"
        "> "
    )

    input_tid = "Digite qual TransactionID você deseja buscar:\n> "

    tid = 0
    while True:
        opt = int(input(menu_str))
        assert (0 < opt < 7), "Opção inválida"

        if 2 < opt: tid = int(input(input_tid))

        function_table[opt](proxy, tid)
