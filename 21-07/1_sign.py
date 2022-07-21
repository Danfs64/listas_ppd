#!/usr/bin/env python

#from base64 import (b64encode, b64decode)
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA


#message = "I want this stream signed"
message = input("Enter a message: ")
digest = SHA256.new()
digest.update(message.encode('utf-8'))

# Load private key previouly generated
with open ("private_key.pem", "r") as myfile:
    private_key = RSA.importKey(myfile.read())

# Sign the message
signer = PKCS1_v1_5.new(private_key)
sig = signer.sign(digest)

# sig is bytes object, so convert to hex string.
# (could convert using b64encode or any number of ways)
print("Signature: ")
print(sig.hex())
