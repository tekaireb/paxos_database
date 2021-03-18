# Paxos Database
<b>Fault-tolerant decentralized database using the Multi-Paxos consensus algorithm.</b>

## Description
This is a distributed key-value database in Python with full replication across nodes. It uses the Multi-Paxos algorithm to reach consensus among server nodes, and as long as a majority are live, the system can make progress and service requests. The data is backed by private blockchain and disk backup to prevent tampering and ensure fault-tolerance.

There are separate server and client nodes, so some users (clients) can interact with the database without hosting any data. All requests are queued and serialized to prevent race conditions and forks.

Paxos leader election only takes place at startup or when a leader is unreachable, so the round is generally skipped during normal operation, allowing the system to process more requests. Nodes keep track of the leader and forward requests, so requests can be made from any endpoint (requester address is saved in order to return the result to the original sender). Nodes detect discrepancies among their peers and send data to new nodes and revived nodes for resynchronization.

## Screenshots

<p align="center">
  <br/><br/><span>Blockchain synchronized across nodes</span><br/>
  <img alt="Blockchain in sync" src="https://raw.githubusercontent.com/tekaireb/paxos_database/main/screenshots/Blockchain in sync.png">
  <br/><br/><span>Database synchronized across nodes</span><br/>
  <img alt="Database in sync" src="https://raw.githubusercontent.com/tekaireb/paxos_database/main/screenshots/Database in sync.png">
  <br/><br/><span>Data automatically restored from file backup</span><br/>
  <img alt="Restore from backup" src="https://raw.githubusercontent.com/tekaireb/paxos_database/main/screenshots/Restore from backup.png">
  <br/><br/><span>Client data retrieval request fulfilled</span><br/>
  <img alt="Client request fulfilled" src="https://raw.githubusercontent.com/tekaireb/paxos_database/main/screenshots/Client request fulfilled.png">
  <br/><br/><span>Server node (non-leader) log while servicing requests</span><br/>
  <img alt="Server handling requests" src="https://raw.githubusercontent.com/tekaireb/paxos_database/main/screenshots/Server handling requests.png">
</p>
