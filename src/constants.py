'''Global constants and helper functions'''

import sys
import socket
import string
import random
from enum import Enum

# Constants

IP = socket.gethostname()  # IP Address
NUM_CLIENTS = 3  # Number of clients
NUM_SERVERS = 5  # Number of servers

CLIENT_PORTS = [2201 + x for x in range(NUM_CLIENTS)]
SERVER_PORTS = [3201 + x for x in range(NUM_SERVERS)]

args = [str(sys.argv[1]), int(sys.argv[2])]
SELF_PID = args[1]  # Process ID of this client (passed as argument)

# Type of node (either 'client' or 'server')
if args[0].lower() in ['c', 'client']:
    SELF_TYPE = 'Client'
    SELF_PORT = CLIENT_PORTS[SELF_PID]
elif args[0].lower() in ['s', 'server']:
    SELF_TYPE = 'Server'
    SELF_PORT = SERVER_PORTS[SELF_PID]


# Shared Objects


class OpType(Enum):
    '''Dictionary operation types enumeration'''
    GET = 1
    PUT = 2


class Operation:
    '''Operation object stores operation type, key, and value (one per block)'''

    def __init__(self, op: OpType, key, value=None):
        self.op = op
        self.key = key
        self.value = value

    def __eq__(self, other):
        return [self.op, self.key] == [other.op, other.key]

    def __str__(self):
        result = f'   ├──Type: {self.op}'
        if self.op == OpType.PUT:
            result += f'\n   ├──Key: {self.key}'
            result += f'\n   └──Value: {self.value}'
        else:
            result += f'\n   └──Key: {self.key}'
        return result


# Anonymous object creator
Object = lambda **kwargs: type("Object", (), kwargs)


# Helper Functions


def log(message: str):
    print(f'({SELF_TYPE} {SELF_PID}): {message}')


def generate_random_string(length: int, acceptableChars: str = string.ascii_letters + string.digits) -> str:
    '''Generate string of random characters in "acceptableChars" of length "length"'''
    return ''.join(random.choice(acceptableChars) for _ in range(length))


def randDigits(x: int) -> str:
    '''Generate string of random digits of length "x"'''
    return generate_random_string(x, string.digits)
