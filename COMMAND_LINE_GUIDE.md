# Command Line Steps to Start Chord DHT Nodes with Bootstrap Server

## Prerequisites

### 1. Start the Bootstrap Server (Required First Step)
```bash
# Start bootstrap server on default port 5000
python3 bootstrap_server.py

# Or start on custom port
python3 bootstrap_server.py 9001
```

### 2. Create test directories and files:
```bash
mkdir -p localhost_8001 localhost_8002 localhost_8003 localhost_8004
echo "Test content 1" > localhost_8001/test1.txt
echo "Test content 2" > localhost_8002/test2.txt
echo "Test content 3" > localhost_8003/test3.txt
```

## Quick Start Commands

### Step 1: Start the Bootstrap Server
```bash
# Terminal 1 - Bootstrap Server
python3 bootstrap_server.py
# Keep this running - it coordinates the network
```

### Step 2: Start Chord Nodes (in separate terminals)
```bash
# Terminal 2 - First Node
python3 chord_cli.py localhost 8001

# Terminal 3 - Second Node  
python3 chord_cli.py localhost 8002

# Terminal 4 - Third Node
python3 chord_cli.py localhost 8003

# Terminal 5 - Fourth Node
python3 chord_cli.py localhost 8004
```

## Complete Example Session

### Terminal 1 - Bootstrap Server
```bash
cd /Users/dinukawanniarachchi/Sysco/Chord-DHT-file-sharing-system
python3 bootstrap_server.py
# Bootstrap server running on localhost:5000
# Commands: status, stop
> status  # Check network status
> 
```

### Terminal 2 - First Node
```bash
cd /Users/dinukawanniarachchi/Sysco/Chord-DHT-file-sharing-system
python3 chord_cli.py localhost 8001
# Node will register with bootstrap server
# Try commands: put test1.txt, get test1.txt, status
```

### Terminal 3 - Second Node
```bash
cd /Users/dinukawanniarachchi/Sysco/Chord-DHT-file-sharing-system  
python3 chord_cli.py localhost 8002
# Node will automatically join through bootstrap server
```

### Terminal 4 - Third Node
```bash
cd /Users/dinukawanniarachchi/Sysco/Chord-DHT-file-sharing-system
python3 chord_cli.py localhost 8003
# Node will automatically join through bootstrap server
```

## Testing File Operations

### In any node terminal:
```bash
# Store a file
put example.txt

# Retrieve a file
get example.txt

# Check node status
status

# Leave network gracefully
leave

# Or force quit
quit
```

## Bootstrap Server Commands

### In bootstrap server terminal:
```bash
# Check network status
status

# Stop the server
stop

# Show help
help
```

## Usage Examples

### Custom Bootstrap Server:
```bash
# Start bootstrap on custom port
python3 bootstrap_server.py 9001

# Connect nodes to custom bootstrap
python3 chord_cli.py localhost 8001 localhost 9001
python3 chord_cli.py localhost 8002 localhost 9001
```

### Test file sharing:
1. Start bootstrap server
2. Start 3 nodes as shown above
3. In node 8001: `put test1.txt`
4. In node 8002: `get test1.txt` (should retrieve from network)
5. In node 8003: `put test3.txt`
6. In node 8001: `get test3.txt` (should retrieve from network)
7. Check bootstrap server: `status` (shows all nodes)

## Advantages of Bootstrap Server Architecture

### 1. **Resilient Network Formation**
- No single point of failure for joining
- Bootstrap server maintains network topology
- Automatic failure detection and recovery

### 2. **Simplified Node Management**
- Nodes don't need to know other node addresses
- Automatic load balancing during joins
- Centralized monitoring and health checks

### 3. **Better Fault Tolerance**
- Bootstrap server detects failed nodes
- Automatic network repair
- Heartbeat monitoring

## Network Topology

```
Bootstrap Server (localhost:5000)
    ↓ (coordinates)
Node 8001 ←→ Node 8002 ←→ Node 8003 ←→ Node 8004 ←→ (back to 8001)
```

The bootstrap server:
- Tracks all nodes and their positions
- Handles join/leave operations
- Monitors node health via heartbeats
- Provides network status information

## Stopping the System

### Graceful shutdown:
1. In each node: `leave` then `quit`
2. In bootstrap server: `stop`

### Force shutdown:
- Use Ctrl+C in each terminal
- Bootstrap server will detect node failures

## Troubleshooting

### Common Issues:
1. **Bootstrap server not running**: Start it first before any nodes
2. **Connection refused**: Check if bootstrap server is on correct port
3. **Node registration failed**: Ensure unique host:port combinations
4. **Network partition**: Restart bootstrap server and rejoin nodes

### Debug Tips:
- Check bootstrap server status regularly with `status` command
- Monitor bootstrap server terminal for error messages
- Use unique ports for each node
- Ensure all nodes can reach the bootstrap server
