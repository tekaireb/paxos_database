import time
import sys
import socket
import pickle
import threading

from constants import *


# Server-Server Multi-Paxos Messages

class Ballot:
    def __init__(self, depth, num, pid):
        self.depth = depth
        self.num = num
        self.pid = pid

    # Overload '<'
    def __lt__(self, other):
        if self.depth == other.depth:
            if self.num == other.num:
                return self.pid < other.pid
            else:
                return self.num < other.num
        else:
            return self.depth < other.depth

    # Overload '=='
    def __eq__(self, other):
        return [self.depth, self.num, self.pid] == [other.depth, other.num, other.pid]

    # Overload '<='
    def __le__(self, other):
        return self < other or self == other


class PrepareRequest:
    '''Phase 1A'''

    def __init__(self, ballot: Ballot, depth: int):
        self.ballot = ballot
        self.depth = depth
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


class Promise:
    '''Phase 1B'''

    def __init__(self, ballot: Ballot, acceptNum, acceptVal, depth: int):
        self.ballot = ballot
        self.num = acceptNum
        self.value = acceptVal
        self.depth = depth
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


class AcceptRequest:
    '''Phase 2A'''

    def __init__(self, ballot: Ballot, value, depth: int):
        self.ballot = ballot
        self.value = value
        self.depth = depth
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


class Accept:
    '''Phase 2B'''

    def __init__(self, ballot: Ballot, value, depth: int):
        self.ballot = ballot
        self.value = value
        self.depth = depth
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


class Decide:
    '''Phase 3'''

    def __init__(self, ballot: Ballot, value):
        self.ballot = ballot
        self.value = value
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


# Client-Server Messages

class ClientRequest:
    def __init__(self, op: Operation, force_leader: bool = False):
        self.operation = op
        self.force_leader = force_leader
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


class ClientResponse:
    def __init__(self, op: Operation, message: str = ""):
        self.operation = op
        self.message = message
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


# Recovery Messages (resynchronization for nodes missing blocks)

class RecoveryData:
    def __init__(self, depth: int, block):
        self.depth = depth
        self.block = block
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


# Debugging Messages

class Test:
    def __init__(self, message: str):
        self.message = message
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


# Other Messages

class Quit:
    def __init__(self):
        self.pid = SELF_PID
        self.nodeType = SELF_TYPE


# Messenger class

class Messenger:
    '''Handles communication with other servers and clients'''

    def __init__(self, message_handler):
        self.clients = [None for _ in range(NUM_CLIENTS)]
        self.servers = [None for _ in range(NUM_SERVERS)]
        self.failed_links = Object(clients=[], servers=[])
        self.message_handler = message_handler
        self.connected = False

        # Prepare to receive incoming connections
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((IP, SELF_PORT))     # Bind to port
        self.s.listen(10)                # Await client connections

        threading.Thread(target=self.accept_incoming_connections).start()

    def connect(self):
        '''Initiate connections with other nodes in the system (servers and clients)'''
        if not self.connected:
            self.connected = True

            # Connect to clients
            if SELF_TYPE != 'Client':  # Clients do not connect to other clients
                for i, port in enumerate(CLIENT_PORTS):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.connect((IP, port))  # Connect to client
                        self.clients[i] = s    # Add socket to list of clients
                        log(f'Connected to client @ {IP}:{port}')
                    except:
                        log(f'Client is unreachable')

            # Connect to servers
            for i, port in enumerate(SERVER_PORTS):
                if SELF_TYPE != 'Server' or port != SELF_PORT:  # Exclude self
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.connect((IP, port))  # Connect to server
                        self.servers[i] = s    # Add socket to list of servers
                        log(f'Connected to server @ {IP}:{port}')
                    except:
                        log(f'Server is unreachable')

    def reconnect(self):
        '''Re-establish connections (find broken sockets and reconnect)'''

        # Reconnect to clients
        if SELF_TYPE != 'Client':  # Clients do not connect to other clients
            for i, (client, port) in enumerate(zip(self.clients, CLIENT_PORTS)):
                try:
                    client.sendall(self.serialize_message('PING'))
                except:
                    # Recreate socket and reconnect
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((IP, port))    # Connect to client
                    self.clients[i] = s      # Add socket to list of clients
                    log(f'Reconnected to client @ {IP}:{port}')
                    return

        # Reconnect to servers
        for i, (server, port) in enumerate(zip(self.servers, SERVER_PORTS)):
            if SELF_TYPE != 'Server' or port != SELF_PORT:  # Exclude self
                try:
                    server.sendall(self.serialize_message('PING'))
                except:
                    # Recreate socket and reconnect
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((IP, port))    # Connect to server
                    self.servers[i] = s      # Add socket to list of server
                    log(f'Reconnected to server @ {IP}:{port}')
                    return

    def close(self):
        '''Close all connections, outgoing and incoming'''

        self.send_message(Quit(), recipientType="All")

        for client in self.clients:
            if client is not None:
                client.close()
        for server in self.servers:
            if server is not None:
                server.close()

        self.s.close()

    def fail_link(self, nodeType, pid):
        '''Simulate connection failure by ignoring incoming/outgoing messages for specified server process ID'''
        if nodeType == 'Server':
            if pid not in self.failed_links.servers:
                self.failed_links.servers.append(pid)
        elif nodeType == 'Client':
            if pid not in self.failed_links.clients:
                self.failed_links.clients.append(pid)

        log(f'Failed link with {nodeType} #{pid}')
        log(f'Failed servers: {self.failed_links.servers}')
        log(f'Failed clients: {self.failed_links.clients}')

    def fix_link(self, nodeType, pid):
        '''Remove simulated connection failure'''
        if nodeType == 'Server':
            self.failed_links.servers = [
                l for l in self.failed_links.servers if l != pid]
        elif nodeType == 'Client':
            self.failed_links.clients = [
                l for l in self.failed_links.clients if l != pid]
        log(f'Fixed link {pid}')

    def is_failed(self, nodeType, pid):
        if nodeType in ['Server', 'All'] and pid in self.failed_links.servers:
            return True
        if nodeType in ['Client', 'All'] and pid in self.failed_links.clients:
            return True
        return False

    def accept_incoming_connections(self):
        '''Accept connections from servers and clients (initiates auto-connect sequence to find other nodes as well)'''
        while True:
            conn, addr = self.s.accept()  # Establish connection

            if not self.connected:  # Auto-connect upon receiving first incoming connection
                self.connect()
            else:
                self.reconnect()

            threading.Thread(
                target=self.incoming_connection_handler,
                args=(conn, addr)
            ).start()

    def incoming_connection_handler(self, connection, address):
        log(f'Incoming connection from client @ {address}')

        while True:
            try:
                # Receive data from client
                message = connection.recv(1024)
                if not message:
                    log(f'Node @ {address} disconnected.')
                    connection.close()
                    break

                message = self.deserialize_message(message)

                # Close outgoing connection if node quits
                if type(message) is Quit:
                    index = message.pid
                    if message.nodeType == 'Server':
                        log('Closing outgoing server connection')
                        self.servers[index].close()
                        self.servers[index] = None
                    else:
                        log('Closing outgoing client connection')
                        self.clients[index].close()
                        self.clients[index] = None

                # Handle message (check failed_links to simulate failures)
                elif hasattr(message, 'pid') and hasattr(message, 'nodeType'):
                    if not self.is_failed(message.nodeType, message.pid):
                        threading.Thread(
                            target=self.message_handler,
                            args=[message]
                        ).start()

            # Close client connection
            except socket.error as e:
                log(f'Node @ {address} forcibly disconnected with {e}.')
                connection.close()
                break

    def send_message(self, message, pid=-1, recipientType='Server'):
        '''Send message to node of given process ID (or all servers if none is specified)'''
        if not self.connected:
            log('Not connected')
            return

        if pid == -1:
            if recipientType == 'All':
                log(f'Sending message to all nodes ({str(type(message))})')
            else:
                log(
                    f'Sending message to all {recipientType.lower()}s ({str(type(message))})')
        else:
            log(f'Sending message to {recipientType} #{pid} ({str(type(message))})')

        threading.Thread(
            target=self.send_message_thread,
            args=[message, pid, recipientType]
        ).start()

    def send_message_thread(self, message, pid=-1, recipientType='Server'):
        time.sleep(2)  # Simulated network delays

        try:
            # If receipient PID is specified, send to single recipient
            if pid != -1:
                if not self.is_failed(recipientType, pid):
                    if recipientType in ['Server', 'All']:
                        self.servers[pid].sendall(
                            self.serialize_message(message))
                    elif recipientType in ['Client', 'All']:
                        self.clients[pid].sendall(
                            self.serialize_message(message))

            # If not PID is specified, send to all clients
            else:
                if recipientType in ['Server', 'All']:
                    for i, server in enumerate(self.servers):
                        if server is not None and not self.is_failed('Server', i):
                            server.sendall(self.serialize_message(message))
                if recipientType in ['Client', 'All']:
                    for i, client in enumerate(self.clients):
                        if client is not None and not self.is_failed('Client', i):
                            client.sendall(self.serialize_message(message))
        except Exception as e:
            log(e)

    def serialize_message(self, message):
        '''Serialize message prior to transmission'''
        return pickle.dumps(message)

    def deserialize_message(self, message):
        '''Deserialize message upon receipt'''
        try:
            return pickle.loads(message)
        except Exception as e:
            print('FAILED TO DESERIALIZE:', e)
            print(len(message))


# Basic Paxos
# Concurrency
    # Two clients requesting same server
# Failed links (continue to work with majority)
