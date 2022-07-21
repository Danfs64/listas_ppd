#!/usr/bin/env python

import sys

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA


# message = "I want this stream signed"
message = input('Enter a message: ')

digest = SHA256.new()
digest.update(message.encode('utf-8'))

#sig = 'bedc06f6b6cb0edc5c426ec7bb4aad32fbba4efe239e71804047bc0eca3081475641563250092528521879df93ca22474926ecc4baeec98aaf90dffe465ef384917ecf41fbbc332033561f40f13d130d540f9d95114c3b12f05b90351580860453876d4fa30dd6f94a96a92f9684015ccd806c7a053ebf07861091a35d057201'
sig = input('Enter signature: ')
sig = bytes.fromhex(sig)  # convert string to bytes object

# Load public key (not private key) and verify signature
public_key = RSA.importKey(open("public_key.txt").read())
verifier = PKCS1_v1_5.new(public_key)
verified = verifier.verify(digest, sig)

if verified:
    print('Successfully verified message')
else:
    print('FAILED')
