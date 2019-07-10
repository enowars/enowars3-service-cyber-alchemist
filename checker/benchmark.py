#!/usr/bin/env python3

import requests

# run checker multiple times to detect problems with unlikely cases
for i in range(1000):
    r = requests.post('http://localhost:7878/', json={
        "method": "putflag",
        "address": "gunicorn"
    }).json()
    print(r)
    if r['result'] != 'OK':
        print(i)
        break
    r = requests.post('http://localhost:7878/', json={
        "method": "getflag",
        "address": "gunicorn"
    }).json()
    print(r)
    if r['result'] != 'OK':
        print(i)
        break






