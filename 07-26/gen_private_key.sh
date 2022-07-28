#!/usr/bin/env bash

# Generate RSA private key
openssl genrsa -out private_key_$1.pem 1024
