import pika

from string import ascii_letters, digits, punctuation
from random import randint

MIN_CHALLENGE = 20
MAX_CHALLENGE = 40
HOSTNAME = "10.9.13.101"
NODEID = randint(0, (1 << 32) - 1)

PIKA_CREDENTIALS = pika.credentials.PlainCredentials("admin", "admin")
MANAGING_CONN = pika.BlockingConnection(
    pika.ConnectionParameters(host=HOSTNAME, heartbeat=600, credentials=PIKA_CREDENTIALS)
)
FOUR_CHAN = MANAGING_CONN.channel()
MANAGING_CHANN = FOUR_CHAN

SEED_ALPHABET = ascii_letters + digits + punctuation
ENCONDING = "utf-8"
