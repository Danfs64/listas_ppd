from pathlib import Path
from Crypto.PublicKey import RSA


def get_keys():
    assert (Path('.')/'public_key.txt').is_file(),\
        "Arquivo de chave pública não encontrado"
    PUB_KEY = RSA.importKey(open("public_key.txt").read())

    assert (Path('.')/'private_key.pem').is_file(),\
        "Arquivo de chave privada não encontrado"
    PRIV_KEY = RSA.importKey(open("private_key.pem").read())

    return PUB_KEY, PRIV_KEY
