# Chord DHT File Sharing System

A distributed hash table (DHT) implementation of the Chord protocol for file sharing with both CLI and REST API interfaces.

## Features

- **Distributed File Storage**: Files stored across nodes using consistent hashing
- **File Search**: Search for files by filename keywords
- **Fault Tolerance**: Files backed up on multiple nodes
- **CLI Interface**: Interactive command-line interface
- **REST API**: HTTP endpoints for web-based operations
- **Bootstrap Server**: Network coordination and node management

## Quick Start

### Prerequisites
- Python 3.7+
- For REST API: `pip install flask werkzeug requests`

### Setup

1. **Start Bootstrap Server**
   ```bash
   python3 bootstrap_server.py 5000
   ```

2. **Start CLI Nodes**
   ```bash
   python3 chord_cli.py localhost 8001
   python3 chord_cli.py localhost 8002
   python3 chord_cli.py localhost 8003
   ```

3. **Or Start REST API Nodes**
   ```bash
   python3 rest_api.py 5001 8001
   python3 rest_api.py 5002 8002
   ```

## Usage

### CLI Commands
- `put <filename>` - Store a file
- `get <filename>` - Retrieve a file  
- `search <term>` - Search for files
- `status` - Show node info
- `quit` - Exit node

### REST API Endpoints
- `POST /upload` - Upload file
- `GET /search?q=<term>` - Search files
- `GET /download/<filename>` - Download file
- `GET /node/status` - Node status
- `GET /health` - Health check

### Example Usage

**CLI:**
```bash
[localhost:8001]> put document.txt
[localhost:8001]> search document
[localhost:8001]> get document.txt
```

**REST API:**
```bash
curl -X POST -F "file=@doc.txt" http://localhost:5001/upload
curl "http://localhost:5001/search?q=document"
curl -O http://localhost:5001/download/doc.txt
```

## Files

- `chord.py` - Core Chord DHT implementation
- `chord_cli.py` - Command line interface
- `rest_api.py` - REST API server
- `bootstrap_server.py` - Network coordination server

## License

Open source project for educational purposes.
