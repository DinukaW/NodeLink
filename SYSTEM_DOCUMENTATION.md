# Chord DHT File Sharing System - Documentation

## Overview

This is a distributed hash table (DHT) based file sharing system implemented using the Chord protocol. The system allows multiple nodes to form a decentralized peer-to-peer network where files can be stored, retrieved, and shared across nodes without a central server.

## System Architecture

### Core Components

1. **Node Class**: Each participant in the network is represented by a Node instance
2. **Chord Ring**: Nodes are organized in a circular overlay network (ring structure)
3. **Consistent Hashing**: Files and nodes are assigned positions using MD5 hashing
4. **Fault Tolerance**: Includes failure detection, recovery mechanisms, and backup storage

### Key Parameters

- **M = 16**: Hash space size parameter (2^16 = 65536 possible positions)
- **Hash Function**: MD5-based consistent hashing
- **Port-based Communication**: TCP sockets for inter-node communication

## System Capabilities

### 1. Node Management
- **Join Network**: New nodes can join an existing Chord ring
- **Leave Network**: Nodes can gracefully leave while maintaining data integrity
- **Failure Detection**: Automatic detection of failed nodes through periodic pinging
- **Self-Organization**: Dynamic ring maintenance as nodes join/leave

### 2. File Operations
- **Put (Store)**: Store files in the network with automatic placement
- **Get (Retrieve)**: Retrieve files from any node in the network
- **Lookup**: Find the responsible node for a given file or key
- **Backup Storage**: Automatic file replication for fault tolerance

### 3. Network Features
- **Distributed Storage**: Files distributed across multiple nodes based on hash values
- **Load Balancing**: Even distribution of files using consistent hashing
- **Scalability**: Support for dynamic network size changes
- **Fault Tolerance**: Redundant storage and automatic recovery

## How to Use the System

### Prerequisites

```bash
# Ensure Python 3.x is installed
python3 --version

# Required modules (built-in):
# - socket
# - threading  
# - os
# - time
# - hashlib
```

### Basic Usage

#### 1. Creating and Starting Nodes

```python
from chord import Node

# Create first node (bootstrap node)
node1 = Node("localhost", 8001)

# Create additional nodes
node2 = Node("localhost", 8002)  
node3 = Node("localhost", 8003)
```

#### 2. Building the Network

```python
# First node joins empty network
node1.join("")  # Empty string means create new ring

# Additional nodes join existing network
node2.join(("localhost", 8001))  # Join through node1
node3.join(("localhost", 8001))  # Join through node1
```

#### 3. File Operations

```python
# Store a file (ensure file exists in node's directory)
node1.put("example.txt")

# Retrieve a file
result = node2.get("example.txt")
if result:
    print(f"File retrieved: {result}")
else:
    print("File not found")

# Leave the network
node1.leave()
```

## Manual Testing Guide

### Test Environment Setup

1. **Create Test Directory Structure**:
```bash
mkdir chord_test
cd chord_test
# Place chord.py in this directory
```

2. **Create Test Files**:
```bash
mkdir localhost_8001
mkdir localhost_8002  
mkdir localhost_8003
echo "Test content 1" > localhost_8001/test1.txt
echo "Test content 2" > localhost_8002/test2.txt
```

### Test Scenarios

#### Test 1: Single Node Network
```python
# test_single_node.py
from chord import Node
import time

# Create single node
node = Node("localhost", 8001)
node.join("")  # Create new ring

# Test file operations
node.put("test1.txt")
result = node.get("test1.txt")
print(f"Single node test result: {result}")

# Cleanup
node.kill()
```

#### Test 2: Multi-Node Network
```python
# test_multi_node.py
from chord import Node
import time

# Create nodes
node1 = Node("localhost", 8001)
node2 = Node("localhost", 8002)
node3 = Node("localhost", 8003)

# Build network
node1.join("")
time.sleep(1)
node2.join(("localhost", 8001))
time.sleep(1) 
node3.join(("localhost", 8001))
time.sleep(2)

# Test cross-node file operations
node1.put("test1.txt")
time.sleep(1)
result = node2.get("test1.txt")  # Get from different node
print(f"Cross-node retrieval: {result}")

# Test file distribution
node2.put("test2.txt")
time.sleep(1)
result = node3.get("test2.txt")
print(f"Distributed file retrieval: {result}")

# Cleanup
node1.kill()
node2.kill()
node3.kill()
```

#### Test 3: Node Failure and Recovery
```python
# test_failure_recovery.py
from chord import Node
import time

# Setup 3-node network
nodes = []
for i in range(3):
    node = Node("localhost", 8001 + i)
    nodes.append(node)
    if i == 0:
        node.join("")
    else:
        node.join(("localhost", 8001))
    time.sleep(1)

# Store files across network
nodes[0].put("test1.txt")
nodes[1].put("test2.txt")
time.sleep(2)

# Simulate node failure
print("Simulating node failure...")
nodes[1].kill()  # Kill middle node
time.sleep(3)

# Test if network still functions
result = nodes[0].get("test1.txt")
print(f"File retrieval after failure: {result}")

# Cleanup remaining nodes
nodes[0].kill()
nodes[2].kill()
```

### Manual Testing Steps

1. **Network Formation Test**:
   - Start nodes one by one
   - Verify each node joins successfully
   - Check network connectivity

2. **File Storage Test**:
   - Store files from different nodes
   - Verify files are placed on correct nodes based on hash
   - Check backup file creation

3. **File Retrieval Test**:
   - Retrieve files from nodes that didn't store them
   - Verify lookup mechanism works correctly
   - Test file not found scenarios

4. **Network Dynamics Test**:
   - Add new nodes to existing network
   - Remove nodes gracefully using leave()
   - Verify file redistribution occurs

5. **Failure Tolerance Test**:
   - Kill nodes abruptly (simulate crashes)
   - Verify remaining nodes detect failures
   - Check if files remain accessible through backups

### Debugging and Monitoring

#### Enable Debug Output
```python
# Add print statements to monitor operations
def debug_node_state(node, name):
    print(f"{name} - Key: {node.key}")
    print(f"{name} - Successor: {node.successor}")
    print(f"{name} - Predecessor: {node.predecessor}")
    print(f"{name} - Files: {node.files}")
    print(f"{name} - Backup Files: {node.backUpFiles}")
    print("---")
```

#### Monitor Network Traffic
```python
# Use socket timeouts to prevent hanging
import socket
socket.setdefaulttimeout(5.0)  # 5 second timeout
```

## Expected Behavior

### Normal Operations
- Files stored on nodes responsible for their hash values
- Automatic file backup on predecessor nodes
- Successful cross-node file retrieval
- Graceful network join/leave operations

### Error Conditions
- Network partitions may cause temporary unavailability
- Node failures trigger automatic successor updates
- Missing files return None from get() operations
- Socket errors may require retry mechanisms

## Performance Considerations

- **Network Size**: Optimal for small to medium networks (10-100 nodes)
- **File Size**: Best suited for small to medium files (< 100MB)
- **Latency**: Lookup operations require O(N) hops in worst case
- **Storage**: Each file stored with one backup copy

## Troubleshooting

### Common Issues
1. **Port Already in Use**: Ensure unique ports for each node
2. **File Not Found**: Check if file exists in node's directory before put()
3. **Network Timeout**: Increase sleep delays between operations
4. **Socket Errors**: Implement retry logic for network operations

### Debug Tips
- Use small test networks (2-3 nodes) initially
- Add logging to track message flow
- Monitor directory contents to verify file movements
- Check node state variables for consistency

This documentation provides a comprehensive guide to understanding, deploying, and testing the Chord DHT file sharing system.
