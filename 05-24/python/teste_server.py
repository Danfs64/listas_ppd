from mining_server import *

if __name__ == "__main__":
    TRANSACTIONS[0] = Transaction(3, 1245,  1)
    TRANSACTIONS[1] = Transaction(4, 21,    2)
    TRANSACTIONS[2] = Transaction(2, None, -1)
    set_last_trans(2)

    assert getTransactionID() == 2

    assert getChallenge(getTransactionID()) == 2
    assert getChallenge(0) == 3
    assert getChallenge(3) == -1

    assert getTransactionStatus(getTransactionID()) == 1
    assert getTransactionStatus(1) == 0
    assert getTransactionStatus(4) == -1

    assert getWinner(getTransactionID()) == 0
    assert getWinner(1) == 2
    assert getWinner(8) == -1

    assert getSeed(getTransactionID()) == (1, None, 2)
    assert getSeed(0) == (0, 1245,  3)
    assert getSeed(16) == (-1, None, -1)

    submitChallenge(getTransactionID(), 9, 4567)
    assert getSeed(2) == (0, 4567, 2)
    assert getTransactionID() == 3
