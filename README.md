# raft-sample
A demo of a distributed, RAFT based key value store for better understanding the protocol.

# Preconditions
* Python3 and the requirements from `requirements.txt` must be installed on all Nodes where the script should be run
* All Nodes in the network must be able to communicate with each other via http
* Environment variables containing the other Nodes in the network must be set
* The script must be passed a unique node_id on each machine

# Installation

Assuming we have three virtual linux machines with the following IP address ranges:

```
10.1.0.15/24
10.1.0.16/24
10.1.0.17/24
```
We can then configure each machine by setting the ip addresses of the neighbours in an environment variable and run the script with a unique `node_id`.

# Configure each Node

### 1. Machine 1 (10.1.0.15):
#### Command to Run:
```
export NODES="10.1.0.15:8000,10.1.0.16:8001,10.1.0.17:8002"
python raft-node.py 0
```
* The NODES environment variable lists all the nodes in the cluster.
* 0 is the node_id for this machine.

### 2. Machine 2 (10.1.0.16):
#### Command to Run:
```
export NODES="10.1.0.15:8000,10.1.0.16:8001,10.1.0.17:8002"
python raft-node.py 1
```
* The NODES environment variable remains the same.
* 1 is the node_id for this machine.

### 3. Machine 2 (10.1.0.17):
#### Command to Run:
```
export NODES="10.1.0.15:8000,10.1.0.16:8001,10.1.0.17:8002"
python raft-node.py 2
```
* The NODES environment variable remains the same.
* 2 is the node_id for this machine.

# Additional Notes
* The machines must be able to communicate over the network,    
  with ports `8000,8001,8002`, etc., open for the respective 
  nodes.
* The `NODES` environment variable must be identical on all 
  nodes to ensure they are aware of each other.
* Check the logs (logger.debug) to verify the state transitions 
  and communication between nodes.