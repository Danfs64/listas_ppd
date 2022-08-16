from enum import Enum


class Queue(Enum):
    INIT = "ppd/init"
    KEY  = "ppd/pubkey"
    ELEC = "ppd/election"
    CHAL = "ppd/challenge"
    SOL  = "ppd/solution"
    VOTE = "ppd/voting"
