from queue import Queue
import math
from threading import Lock

from messages import *
from blockchain import *
from dictionary import *
from constants import *

promise_lock = Lock()
accept_lock = Lock()


class Server:
    def __init__(self):
        self.m = Messenger(self.message_handler)
        self.b = Blockchain(filename=f'blockchain_backup_{SELF_PID}.txt')
        self.d = Dictionary()
        self.update_dictionary()

        # Acceptor data
        # Latest ballot in which server was involved (phase 1)
        self.ballot = Ballot(0, 0, 0)
        # Latest ballot in which server accepted value (phase 2)
        self.acceptNum = Ballot(0, 0, 0)
        # Latest accepted value (phase 2)
        self.acceptVal = None
        self.leaderID = -1

        # Leader data
        self.value = None
        self.promise_responses = 0
        self.accept_responses = 0
        self.queue = Queue()

    def connect(self):
        self.m.connect()

    def close(self):
        self.m.close()

    def send_message(self, message, pid=-1, recipientType='Server'):
        self.m.send_message(message, pid, recipientType)

    def tentative(self, block: Block):
        block.tentative = True
        if self.b.is_tentative():
            self.b.update(block)
        else:
            self.b.append(block)

    def decide(self, block: Block):
        block.tentative = False
        if self.b.is_tentative():
            self.b.update(block)
        else:
            self.b.append(block)
        self.update_dictionary()

    def fulfill(self, request: ClientRequest):
        # Fulfill GET request with data from key-value store
        if request.operation.op == OpType.GET:
            response = ClientResponse(
                op=request.operation,
                message=self.d[request.operation.key]
            )
        # Fulfill PUT request with acknowledgement
        else:
            response = ClientResponse(
                op=request.operation,
                message="It will be done, my lord."
            )

        self.send_message(response, request.pid, 'Client')

    def update_dictionary(self):
        self.d.update(self.b.blocks, self.b.depth)

    # def propose(self, op: Operation):
    #     self.value = self.b.generate_next_block(op)
    #     print('New block generated:')
    #     print(str(self.value))
    #     self.ballot = Ballot(self.b.depth, self.ballot.num + 1, SELF_PID)
    #     self.send_message(PrepareRequest(self.ballot))

    def send_prepare_request(self, value: Operation):
        self.accept_responses = 0
        self.promise_responses = 0
        self.ballot = Ballot(self.b.depth, self.ballot.num + 1, SELF_PID)
        self.value = self.b.generate_next_block(value)
        print('New block generated:')
        print(str(self.value))
        self.send_message(PrepareRequest(self.ballot, self.b.depth))

    def send_accept_request(self, value: Operation):
        self.accept_responses = 0
        self.promise_responses = 0
        self.ballot = Ballot(self.b.depth, self.ballot.num + 1, SELF_PID)
        self.value = self.b.generate_next_block(value)
        print('New block generated:')
        print(str(self.value))
        self.send_message(AcceptRequest(self.ballot, self.value, self.b.depth))

    def send_recovery_data(self, pid: int, depth: int):
        # Send recovery data (if necessary)
        if depth < self.b.depth - 1:
            log(f'Sending recovery data to Server #{pid}')
            for i in range(depth, self.b.depth):
                self.send_message(
                    RecoveryData(i + 1, self.b.blocks[i]),
                    pid
                )

    def majority_responded(self, responses: int):
        return responses >= math.ceil(NUM_SERVERS / 2) - 1

    def message_handler(self, msg):
        # log(f'Message received ({str(type(msg))})')

        # Client Request (GET or PUT operation)
        if type(msg) is ClientRequest:
            # This server is the leader
            if self.leaderID == SELF_PID:
                self.queue.put(msg)
                if len(self.queue.queue) == 1:
                    self.send_accept_request(msg.operation)

            # No leader has been chosen (or client is forcing leader selection)
            elif self.leaderID == -1 or msg.force_leader:
                self.queue.put(msg)
                self.send_prepare_request(msg.operation)

            # Another server is the leader
            else:
                self.send_message(msg, msg.pid)

        # Phase 1B
        if type(msg) is PrepareRequest:
            if msg.ballot >= self.ballot:
                self.leaderID = msg.ballot.pid
                self.ballot = msg.ballot
                self.send_message(
                    Promise(msg.ballot, self.acceptNum,
                            self.acceptVal, self.b.depth),
                    msg.ballot.pid
                )
            # Send recovery data (if necessary)
            self.send_recovery_data(msg.pid, msg.depth)

        # Phase 2A
        elif type(msg) is Promise:
            with promise_lock:
                self.promise_responses += 1
                if msg.ballot > self.ballot and msg.value is not None:
                    self.value = msg.value
                if self.majority_responded(self.promise_responses):
                    self.responses = -NUM_SERVERS
                    self.leaderID = msg.ballot.pid
                    self.send_message(AcceptRequest(
                        self.ballot, self.value, self.b.depth))

            # Send recovery data (if necessary)
            self.send_recovery_data(msg.pid, msg.depth)

        # Phase 2B
        elif type(msg) is AcceptRequest:
            if msg.ballot >= self.ballot:
                self.acceptNum = msg.ballot
                self.acceptVal = msg.value
                self.tentative(msg.value)
                self.send_message(
                    Accept(msg.ballot, msg.value, self.b.depth),
                    msg.ballot.pid
                )

            # Send recovery data (if necessary)
            self.send_recovery_data(msg.pid, msg.depth)

        # Phase 3A
        elif type(msg) is Accept:
            with accept_lock:
                self.accept_responses += 1
                if self.majority_responded(self.accept_responses):
                    self.accept_responses = -NUM_SERVERS
                    self.send_message(
                        Decide(self.ballot, self.value), recipientType='All')
                    self.decide(self.value)
                    self.fulfill(self.queue.get())
                    if not self.queue.empty():
                        self.send_accept_request(
                            self.queue.queue[0].operation)

            # Send recovery data (if necessary)
            self.send_recovery_data(msg.pid, msg.depth)

        # Phase 3B
        elif type(msg) is Decide:
            log(f'Value in block received: {msg.value.operation.value}')
            self.decide(msg.value)

        # Recover Data (Repair blockchain with missing blocks)
        elif type(msg) is RecoveryData:
            if self.b.depth == msg.depth - 1:
                log('Received recovery data')
                self.b.append(msg.block)
                self.update_dictionary()
                # If leader, recalculate next block after repairing blockchain
                if self.leaderID == SELF_PID:
                    self.value = self.b.generate_next_block(
                        self.value.operation)

        # Test
        elif type(msg) is Test:
            log(f'Test message: {msg.message}')
