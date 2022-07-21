from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
import pika

import subprocess
import json
import sys

assert len(sys.argv) == 2, f"Proper Usage: {sys.argv[0]} <client ID>"
cid = sys.argv[1]

conn = pika.BlockingConnection()
chann = conn.channel()
chann.queue_declare('ppd/pubkey')

if cid == '1':
    # Generate private key file
    subprocess.run(['bash', 'generate_key.sh', f'{cid}'])
    private_key_filename = f'private_key_{cid}.pem'

    # Generate public key
    with open(private_key_filename, "r") as src:
        private_key = RSA.importKey(src.read())
    public_key = private_key.publickey().exportKey().decode('utf-8')

    chann.basic_publish(
        exchange='',
        routing_key='ppd/pubkey',
        body=json.dumps({
            'pubkey': public_key,
            'client': cid
        })
    )

    # Load private key
    with open(private_key_filename, "r") as f:
        private_key = RSA.importKey(f.read())

    while True:
        msg = input("Insira uma mensagem para enviar: ")
        digest = SHA256.new()
        digest.update(msg.encode('utf-8'))


        # Sign the message
        signer = PKCS1_v1_5.new(private_key)
        signature = signer.sign(digest)

        chann.basic_publish(
            exchange='',
            routing_key='ppd/pubkey',
            body=json.dumps({
                'message': msg,
                'signature': signature.hex()
            })
        )
        print(f"Enviada msg {msg} com assinatura {signature.hex()}")

elif cid == '2':
    for _, _, body in chann.consume('ppd/pubkey'):
        body = json.loads(body)
        try:
            client = body['client']
            pubkey = body['pubkey']

            with open(f'public_key_{client}.txt', 'w') as out:
                out.write(pubkey)
            break
        except KeyError:
            continue
           
    chann.cancel()

    def callback(ch, method, properties, body):
        body = json.loads(body)
        message = body['message']
        signature = body['signature']
        signature = bytes.fromhex(signature)

        digest = SHA256.new()
        digest.update(message.encode('utf-8'))

        # Load public key (not private key) and verify signature
        public_key = RSA.importKey(open(f"public_key_{client}.txt").read())
        verifier = PKCS1_v1_5.new(public_key)
        verified = verifier.verify(digest, signature)

        if verified:
            print(f'Message recieved: {message}')
        else:
            print('Wrongfully signed message received')

    chann.basic_consume(
        queue='ppd/pubkey',
        on_message_callback=callback
    )
    chann.start_consuming()
