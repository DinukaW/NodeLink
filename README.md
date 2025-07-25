# Chord DHT File Sharing System

A robust distributed hash table (DHT) based file sharing system implementing the Chord protocol with automatic file discovery, fault tolerance, and reliable file transfer.

## Features

### 🚀 **Core Functionality**
- **Distributed File Storage**: Files are distributed across nodes using consistent hashing
- **Automatic File Discovery**: Files are automatically detected and distributed without manual commands
- **Fault Tolerant**: Files are preserved even when nodes crash or leave unexpectedly
- **Bootstrap Server**: Centralized coordination for network topology management
- **Real-time Topology Updates**: Network adapts automatically when nodes join/leave

### 🛡️ **Reliability Features**
- **File-Safe Exit**: Both `quit` and `leave` commands transfer files before shutdown
- **Backup System**: Files are backed up on predecessor nodes
- **Crash Recovery**: Files are retrievable from backup even if primary nodes fail
- **Random Distribution**: Files are distributed randomly to prevent hotspots
- **Network Healing**: Topology updates automatically when nodes become unavailable

### 🔧 **Advanced Features**
- **Consistent Hashing**: Uses MD5 hashing with 16-bit key space (65,536 positions)
- **File Lookup**: Efficient O(log N) lookup time for file location
- **Multi-threaded**: Concurrent handling of multiple operations
- **Interactive CLI**: User-friendly command-line interface for each node

## Architecture

### System Components

1. **Bootstrap Server** (`bootstrap_server.py`)
   - Manages network topology and node registration
   - Handles heartbeat monitoring and failure detection
   - Coordinates topology updates when nodes join/leave

2. **Chord Node** (`chord.py`)
   - Implements the Chord DHT protocol
   - Handles file storage, retrieval, and transfer
   - Manages successor/predecessor relationships
   - Automatic file discovery and distribution

3. **Command Line Interface** (`chord_cli.py`)
   - Interactive interface for node operations
   - Supports file operations and network commands
   - Handles graceful shutdown with file transfer

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- No external dependencies required (uses only standard library)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/programmer-xyz/Chord-DHT-file-sharing-system.git
   cd Chord-DHT-file-sharing-system
   ```

2. **Start the Bootstrap Server**
   ```bash
   python3 bootstrap_server.py 5000
   ```

3. **Start Chord Nodes**
   ```bash
   # Terminal 1 - First node
   python3 chord_cli.py localhost 8001
   
   # Terminal 2 - Second node  
   python3 chord_cli.py localhost 8002
   
   # Terminal 3 - Third node
   python3 chord_cli.py localhost 8003
   ```

4. **Add Files**
   Simply drop files into the node directories (e.g., `localhost_8001/`, `localhost_8002/`) and they will be automatically discovered and distributed.

## Usage

### Node Commands

- **`put <filename>`** - Manually store a file in the network
- **`get <filename>`** - Retrieve a file from the network
- **`status`** - Show node information and file lists
- **`leave`** - Gracefully leave the network (transfers files)
- **`quit`** - Fast exit with file transfer (recommended)

### Example Session

```bash
[localhost:8001]> status
Node Key: 58795
Successor: ('localhost', 8002)
Predecessor: ('localhost', 8003)
Files: ['document.txt', 'image.jpg']
Backup Files: ['backup1.txt', 'backup2.txt']

[localhost:8001]> get shared_file.txt
File 'shared_file.txt' retrieved successfully

[localhost:8001]> quit
Shutting down node and transferring files...
Transferring document.txt to successor ('localhost', 8002)
Successfully transferred document.txt to ('localhost', 8002)
Node shutdown complete
```

### Automatic File Discovery

The system automatically discovers files placed in node directories:

```bash
# Add a file to any node directory
echo "Hello World" > localhost_8001/hello.txt

# The system will automatically:
# 1. Discover the file
# 2. Calculate which node should store it
# 3. Transfer it to the correct node
# 4. Make it available for retrieval from any node
```

## Network Topology

The system uses a ring topology where each node maintains:
- **Successor**: Next node in the ring (clockwise)
- **Predecessor**: Previous node in the ring (counter-clockwise)
- **Key**: MD5 hash of node address (host + port)

Files are stored on the node whose key is equal to or immediately follows the file's hash key in the ring.

## File Distribution Strategy

1. **Primary Storage**: Files are stored on the responsible node (determined by hash)
2. **Backup Storage**: Files are also backed up on the predecessor node
3. **Transfer on Leave**: When nodes leave, files are randomly distributed to successor and predecessor
4. **Recovery**: Files can be retrieved from backup if primary node fails

## Error Handling

The system handles various failure scenarios:

- **Node Crashes**: Files are recoverable from backup nodes
- **Network Partitions**: Bootstrap server coordinates healing
- **File Transfer Failures**: Continues with other files, keeps local copy
- **Bootstrap Server Down**: Nodes can operate with cached topology

## Configuration

### Default Settings
- Bootstrap Server: `localhost:5000`
- Hash Space: 16-bit (65,536 positions)
- File Discovery Interval: 5 seconds
- Heartbeat Interval: 3 seconds
- Connection Timeout: 10 seconds

### Custom Configuration
```bash
# Custom bootstrap server
python3 chord_cli.py localhost 8001 custom_host 9000

# Different ports
python3 bootstrap_server.py 6000
```

## Troubleshooting

### Common Issues

1. **"Bootstrap server not available"**
   - Ensure bootstrap server is running
   - Check host/port configuration

2. **Files not found after node leaves**
   - Files should be automatically transferred
   - Check other nodes with `get` command
   - Files may be in backup storage

3. **Connection errors**
   - Verify all nodes are running
   - Check network connectivity
   - Ensure no port conflicts

### Debug Information
Use the `status` command to check:
- Node connectivity (successor/predecessor)
- File distribution (files vs backup files)
- Network topology health

## Performance

- **Lookup Time**: O(log N) where N is number of nodes
- **Storage Overhead**: Each file stored on 1-2 nodes (primary + backup)
- **Network Messages**: Minimal due to efficient routing
- **Scalability**: Supports hundreds of nodes efficiently

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Feel free to use, modify, and distribute.

## Authors

- **programmer-xyz** - Initial implementation
- **Contributors** - Various improvements and bug fixes

---

**Note**: This implementation is designed for educational and research purposes. For production use, consider additional security measures and performance optimizations.
