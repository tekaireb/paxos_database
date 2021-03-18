import os
try:
    import cPickle as pickle
except:
    import pickle
from hashlib import sha256
from constants import *
from threading import Lock

a_lock = Lock()


class Block:
    '''Block represents one block in the blockchain (stores operation, hash pointer to previous block, and nonce)'''

    def __init__(self, operation: Operation, hash_pointer: str, tentative: bool = False):
        self.operation = operation
        self.hash_pointer = hash_pointer
        self.nonce = self.calculate_nonce()
        self.tentative = tentative

    def __str__(self) -> str:
        result = f'   ├──{self.operation.op}: {self.operation.key}'
        if self.operation.value:
            result += f' --> {self.operation.value}'
        result += f'\n   ├──Hash pointer: {self.hash_pointer}'
        result += f'\n   └──Nonce: {self.nonce}'
        return result

    def calculate_nonce(self) -> str:
        h = nonce = 0

        # Repeat until last digit of h is between 0 and 2
        while True:
            nonce = generate_random_string(10)
            # Hash current operation concatenated with nonce
            h = sha256((str(self.operation) + nonce).encode()).hexdigest()
            # Ensure last digit is between 0 and 2
            if int(h, base=16) % 10 <= 2:
                return nonce


class Blockchain:
    '''Append-only data structure which holds each operation in a block'''

    def __init__(self, filename: str = ''):
        self.blocks = []
        self.depth = 0
        self.filename = filename
        if filename != '':
            self.restore(filename)

    def __str__(self) -> str:
        result = f'Blockchain depth: {self.depth}'
        for i, b in enumerate(self.blocks):
            result += f'\n   Block #{i}:\n'
            result += str(b)
        return result

    def restore(self, filename: str = ''):
        try:
            with (open(filename, "rb")) as f:
                log('Restoring blockchain from file...')
                while True:
                    try:
                        # Load block and append to blockchain
                        self.blocks.append(pickle.load(f))
                        self.depth += 1
                        log(f'+ added block #{len(self.blocks)}')
                    except EOFError:  # Reached end of file
                        break
        except IOError:  # File does not exist
            return
        return

    def generate_next_block(self, op: Operation) -> Block:
        if len(self.blocks):
            ptr = sha256(str(self.blocks[-1]).encode()).hexdigest()
        else:
            ptr = 0

        return Block(
            operation=op,
            hash_pointer=ptr
        )

    def _add_to_file(self, block: Block):
        with open(self.filename, "ab") as f:
            pickle.dump(block, f)

    def is_tentative(self):
        '''Determine whether or not last block in blockchain is tentative'''
        return len(self.blocks) and self.blocks[-1].tentative

    def append(self, block: Block):
        with a_lock:
            # If attempting to append same block, abort
            if len(self.blocks) and block.hash_pointer == self.blocks[-1].hash_pointer:
                return

            log(f'Appending block #{len(self.blocks)}')

            # Verify validity of block
            # Check hash pointer
            if len(self.blocks):
                ptr = sha256(str(self.blocks[-1]).encode()).hexdigest()
            else:
                ptr = 0
            if ptr != block.hash_pointer:  # Abort if hash pointer is incorrect
                log('Aborting append operation: invalid hash pointer')
                return
            # Check nonce
            h = sha256((str(block.operation) +
                        block.nonce).encode()).hexdigest()
            if int(h, base=16) % 10 > 2:  # Abort if last digit of nonce exceeds 2
                log('Aborting append operation: invalid nonce')
                return

            # Add block to blockchain
            self.blocks.append(block)
            self.depth += 1

            # Add block to backup file
            self._add_to_file(block)

    def update(self, block: Block):
        log(f'Updating block #{len(self.blocks) - 1}')
        # Replace last block in blockchain
        self.blocks[-1] = block

        # Erase contents of backup file
        open(self.filename, 'wb').close()

        # Rewrite backup
        for b in self.blocks:
            self._add_to_file(b)

        # # Delete last line of file
        # with open(self.filename, 'rb+') as f:
        #     f.seek(0, os.SEEK_END)
        #     pos = f.tell() - 1
        #     while pos > 0 and f.read(1) != b'\n':
        #         pos -= 1
        #         f.seek(pos, os.SEEK_SET)
        #     if pos > 0:
        #         f.seek(pos, os.SEEK_SET)
        #         f.truncate()

        # # Replace with updated block
        # self._add_to_file(block)
