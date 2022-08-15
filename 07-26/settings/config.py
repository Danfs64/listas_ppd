import pika

from string import ascii_letters, digits, punctuation
from random import randint

HOSTNAME = "localhost"
NODEID = randint(0, (1 << 32) - 1)

MANAGING_CONN = pika.BlockingConnection(host=HOSTNAME)
FOUR_CHAN = MANAGING_CONN.channel()
MANAGING_CHANN = FOUR_CHAN

SEED_ALPHABET = ascii_letters + digits + punctuation

ENCONDING = "utf-8"
