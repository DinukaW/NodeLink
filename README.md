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
- For Monitoring: `pip install prometheus_client` + Docker

### Setup

1. **Start Bootstrap Server**
   ```bash
   python3 bootstrap_server.py 5000
   ```

2. **Start CLI Nodes**
   ```bash
   python3 chord_cli.py localhost <NODE_PORT>

   python3 chord_cli.py localhost 8001
   python3 chord_cli.py localhost 8002
   python3 chord_cli.py localhost 8003
   ```

3. **Or Start REST API Nodes**
   ```bash
   python3 rest_api.py <API_PORT> <NODE_PORT>

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
- `GET /metrics` - Prometheus metrics endpoint

## Performance Monitoring

The system includes comprehensive Prometheus metrics and Grafana dashboards:

```bash
# Setup monitoring stack
python3 setup_monitoring.py

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

**Metrics tracked:**
- Query hop count and latency
- Message traffic and processing time  
- Node connectivity and topology changes
- Query cost: α × hop_count + β × latency
- Node cost: δ × messages + ζ × processing_time

See `MONITORING.md` for detailed documentation.

### Example Usage

**CLI:**
```bash
[localhost:8001]> put document.txt
[localhost:8001]> search document
[localhost:8001]> get document.txt
```

**REST API Examples:**

**1. Health & Status Endpoints**
```bash
# Health check
curl http://localhost:<API_PORT>/health 

# Node status (detailed network info)
curl http://localhost:<API_PORT>/node/status 

# Bootstrap server status
curl http://localhost:<API_PORT>/bootstrap/status 

# Prometheus metrics (NEW!)
curl http://localhost:<API_PORT>/metrics
```
**2. File Operations**
```bash
# Upload a file
curl -X POST -F "file=@document.txt" http://localhost:<API_PORT>/upload

# If you're in the main project directory and file is in files/
curl -X POST -F "file=@files/document.txt" http://localhost:<API_PORT>/upload

# List all files on node
curl http://localhost:<API_PORT>/files/list

```
**3. File Search**
```bash
# Search for files containing "machine"
curl "http://localhost:<API_PORT>/search?q=machine"

# Search with multiple terms
curl "http://localhost:<API_PORT>/search?q=protocol+design"

```
**4. File Download**
```bash
# Download a file
curl -O http://localhost:<API_PORT>/download/document.txt

# Download with custom filename
curl -o my_document.txt http://localhost:<API_PORT>/download/document.txt

```
**5. Network Management**
```bash
# Make node leave network gracefully (shuts down server)
curl -X POST http://localhost:<API_PORT>/node/leave

# Leave with verbose output
curl -X POST http://localhost:<API_PORT>/node/leave -v
```
**6. Performance Monitoring**
```bash
# Get Prometheus metrics
curl http://localhost:<API_PORT>/metrics

# Get specific metric categories
curl http://localhost:<API_PORT>/metrics | grep chord_query
curl http://localhost:<API_PORT>/metrics | grep chord_message
curl http://localhost:<API_PORT>/metrics | grep chord_node

# Query cost metrics
curl http://localhost:<API_PORT>/metrics | grep chord_query_cost

# Node cost metrics  
curl http://localhost:<API_PORT>/metrics | grep chord_node_cost
```
## Files

- `chord.py` - Core Chord DHT implementation
- `chord_cli.py` - Command line interface
- `rest_api.py` - REST API server
- `bootstrap_server.py` - Network coordination server


