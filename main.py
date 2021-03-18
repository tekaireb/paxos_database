import os
import threading
import string
import random

from messages import *
from blockchain import *
from server import *
from client import *

from constants import *

s = Server() if SELF_TYPE == 'Server' else Client()


def handle_input():
    '''Handle user input (from command line)'''

    print('Ready for user input:\n')

    while True:
        i = input()

        if i in ['connect', 'c']:
            s.connect()

        # Random: Create and send a new request (randomly generated)
        if i == 'random':
            if SELF_TYPE == 'Client':
                log('Generating random request')
                request = Operation(
                    op=random.choice([OpType.GET, OpType.PUT]),
                    key=f'{randDigits(7)}_netid',
                    value={
                        'phone_number': f'({randDigits(3)}) {randDigits(3)}-{randDigits(4)}'}
                )
                s.send_request(request)
                print(f'Request generated: \n{request}\n')

        # Kill the process
        if i == 'q':
            s.close()
            log('Goodbye ✌️')
            os._exit(1)

        # Broadcast [TYPE]: Send a test message to all nodes (servers, clients, or both)
        if 'broadcast' in i:
            if len(i.split(' ')) > 1:
                target = i.split(' ')[1]
                if target.lower() in ['s', 'servers']:
                    s.send_message(Test('Hello there'), recipientType='Server')
                if target.lower() in ['c', 'clients']:
                    s.send_message(Test('Hello there'), recipientType='Client')
                if target.lower() in ['a', 'all']:
                    s.send_message(Test('Hello there'), recipientType='All')
            else:
                s.send_message(Test("Hello there"), 'All')

        # Unicast [TYPE] [PID]: Send a test message to a particular node (server or client)
        if 'unicast' in i:
            recipientType, target = i.split(' ')[1:]
            if recipientType.lower() in ['s', 'server']:
                s.send_message(Test("Hello there"), int(target), 'Server')
            if recipientType.lower() in ['c', 'client']:
                s.send_message(Test("Hello there"), int(target), 'Client')

        # 1 -- operation [OP] [KEY] [VALUE]: Issue PUT/GET request (client expects response with result or acknowledgement)
        if i.startswith('op'):
            if SELF_TYPE == 'Client':
                user_input = i.split(' ')
                if len(user_input) == 3:
                    user_input += [None]
                command, op, key, value = user_input
                op = OpType.GET if op.lower() == 'get' else OpType.PUT
                s.send_request(Operation(op, key, value))

        # 2 -- failLink [TYPE] [DEST]: Simulates communication failure between self and destination node (ignores incoming/outgoing messages)
        if 'failLink' in i:
            command, nodeType, destination = i.split(' ')
            nt = 'Server' if nodeType.lower() in ['s', 'server'] else 'Client'
            s.m.fail_link(nt, int(destination))

        # 3 -- fixLink [TYPE] [DEST]: Fixes (simulated) broken communication link
        if 'fixLink' in i:
            command, nodeType, destination = i.split(' ')
            nt = 'Server' if nodeType.lower() in ['s', 'server'] else 'Client'
            s.m.fix_link(nt, int(destination))

        # 4 -- failProcess: Fail all connections
        if i == 'failProcess':
            s.m.failed_links.servers = [x for x in range(NUM_SERVERS)]
            log('Failed process')
        if i == 'fixProcess':
            s.m.failed_links.servers = []
            log('Fixed process')

        # 5 -- printBlockchain: Print the local copy of the blockchain
        if i in ['printBlockchain', 'pb']:
            if SELF_TYPE == 'Server':
                print(str(s.b))

        # 6 -- printKVStore: Print the local key value store
        if i in ['printKVStore', 'pk']:
            if SELF_TYPE == 'Server':
                print(str(s.d))

        # 7 -- printQueue: Print the pending operations present on the queue
        if i in ['printQueue', 'pq']:
            if SELF_TYPE == 'Server':
                print(f'Queue size: {len(s.queue)}')
                for i, op in enumerate(s.queue):
                    print(f'   Operation #{i}:', end='')
                    print(str(op))


threading.Thread(target=handle_input).start()
