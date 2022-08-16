import json

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5

from settings import ENCONDING
from pathlib import Path
from Crypto.PublicKey import RSA

def import_keys():
    assert (
        Path(".") / "public_key.txt"
    ).is_file(), "Arquivo de chave pública não encontrado"
    pub_key = RSA.importKey(open("public_key.txt").read())

    assert (
        Path(".") / "private_key.pem"
    ).is_file(), "Arquivo de chave privada não encontrado"
    priv_key = RSA.importKey(open("private_key.pem").read())

    return pub_key, priv_key

PUB_KEY, PRIV_KEY = import_keys()
SIGNER = PKCS1_v1_5.new(PRIV_KEY)

def sign_message(msg: dict) -> str:
    msg_json = json.dumps(msg)
    msg_digest = SHA256.new(msg_json.encode(ENCONDING))

    signature = SIGNER.sign(msg_digest)
    msg.update({"Sign": signature})
    return json.dumps(msg)


def check_signature(msg: dict, signature: str, sender_key) -> bool:
    verifier = PKCS1_v1_5.new(sender_key)

    msg_json = json.dumps(msg)
    msg_digest = SHA256.new(msg_json.encode())

    sig_bytes = bytes.fromhex(signature)
    try:
        verifier.verify(msg_digest, sig_bytes)
        return True
    except ValueError:
        print("Mensagem não condiz com assinatura")
        return False

