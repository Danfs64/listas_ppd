from xmlrpc.server import SimpleXMLRPCServer
from hashlib import sha1

transactions = {}
last_trans = -1

def getTransactionID() -> int:
    return last_trans

def getChallenge(tid: int) -> int:
    if tid > last_trans:
        return -1

    return transactions[tid][0]

def getTransactionStatus(tid: int) -> int:
    if tid > last_trans:
        return -1

    winner = transactions[tid][2]
    return int(winner != -1)

def getWinner(tid: int) -> int:
    if tid > last_trans:
        return -1

    winner = transactions[tid][2]

    if winner == -1:
        return 0
    else:
        return winner

def getSeed(tid: int):
    if tid >= last_trans:
        return (-1, None, -1)

    challenge, seed, winner = transactions[tid]

    return (int(winner != -1), seed, challenge)

def submitChallenge(tid: int, cid: int, seed: int) -> int:
    if tid > last_trans:
        return -1
    if tid < last_trans:
        return 2

    result = check_seed(seed)

    if result == 1:
        #TODO coisas internas de submissão correta
        pass

    return result


if __name__ == "__main__":
    # server = SimpleXMLRPCServer(("localhost", 8000))
    # print("Listening on port 8000...")
    # #server.register_multicall_functions()
    # server.register_function(add, 'add')
    # server.register_function(subtract, 'subtract')
    # server.register_function(multiply, 'multiply')
    # server.register_function(divide, 'divide')
    # server.serve_forever()
    transactions[0] = (3, 1245, 1)
    transactions[1] = (5, None, -1)
    last_trans = 1
