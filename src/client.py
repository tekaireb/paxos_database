import time
import random

from messages import *
from blockchain import *
from dictionary import *
from constants import *


class Client:
    def __init__(self):
        self.m = Messenger(self.message_handler)
        self.leaderID = 0
        self.requests = []
        self.WAIT_TIME = 30

    def connect(self):
        self.m.connect()

    def close(self):
        self.m.close()

    def send_message(self, message, pid: int = -1, recipientType: str = 'Server'):
        self.m.send_message(message, pid, recipientType)

    def send_request(self, op: Operation):
        threading.Thread(
            target=self.send_request_thread,
            args=[op]
        ).start()

    def send_request_thread(self, op: Operation):
        self.requests.append(op)
        self.send_message(ClientRequest(op), self.leaderID)
        log(f'Sent request to server {self.leaderID}, waiting {self.WAIT_TIME} seconds...')
        while True:
            time.sleep(self.WAIT_TIME)
            if op in self.requests:
                log(f'Request timed out, sending new request with leader hint...')
                pid = random.randint(0, NUM_SERVERS - 1)
                self.leaderID = pid
                self.send_message(ClientRequest(op, force_leader=True), pid)
                log(
                    f'Sent request to server {self.leaderID}, waiting {self.WAIT_TIME} seconds...')
            else:
                break

    def request_fulfilled(self, response: ClientResponse):
        o = response.operation
        if o.op == OpType.GET:
            log(f'Request fulfilled: GET {o.key}')
        else:
            log(f'Request fulfilled: PUT {o.key} --> {o.value}')
        log(f'Response: {response.message}')
        self.requests = [r for r in self.requests if r != o]

    def message_handler(self, msg):
        log(f'Message received ({str(type(msg))})')

        # Response to client request
        if type(msg) is ClientResponse:
            # PRINT RESPONSE
            self.request_fulfilled(msg)

        # Update Leader
        elif type(msg) is Decide:
            self.leaderID = msg.ballot.pid

        # Test
        elif type(msg) is Test:
            log(f'Test message: {msg.message}')
