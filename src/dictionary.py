from blockchain import *
from constants import *
from typing import List


class Dictionary:
    def __init__(self, filename: str = ''):
        self.data = {}
        self.latestDepth = 0
        self.filename = filename
        if filename != '':
            self.restore(filename)

    def __str__(self) -> str:
        size = len(self.data)
        result = f'KVStore size: {size}'
        for i, e in enumerate(self.data):
            if i == size - 1:
                result += f'\n ({i})└──{e} --> {self.data[e]}'
            else:
                result += f'\n ({i})├──{e} --> {self.data[e]}'
        return result

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        else:
            return 'NO_KEY'

    def __setitem__(self, key, value):
        self.data[key] = value

    def update(self, blocks: List[Block], depth: int):
        # Iterate through missing blocks and execute PUT operations
        for i in range(self.latestDepth, depth):
            if blocks[i].operation.op is OpType.PUT:
                self.data[blocks[i].operation.key] = blocks[i].operation.value
                log(
                    f'Updating dictionary: ({blocks[i].operation.key}: {blocks[i].operation.value})')
        self.latestDepth = depth  # Update depth
