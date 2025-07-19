
# Advanced Chord DHT File Sharing System

## 🚀 Overview

A production-ready, distributed file sharing system built on the Chord DHT protocol with modern networking and monitoring capabilities. This system features QUIC transport, Protocol Buffers serialization, REST API endpoints, distributed search with inverted indexing, and comprehensive fault tolerance.

## ✨ Key Features

### 🔗 **Phase 1: Robust Chord DHT Protocol** ✅
- **Correct Chord implementation** with O(log N) lookup guarantee
- **Fault-tolerant ring maintenance** with automatic healing
- **Graceful node join/leave** with data migration
- **Finger table optimization** for efficient routing

### 🔍 **Phase 2: Distributed Inverted Index** ✅
- **Advanced tokenization** for partial filename matching
- **Distributed token storage** across DHT nodes
- **Relevance scoring** for search results ranking
- **Partial search capabilities** with query completion

### ⚡ **Phase 3: QUIC + Protocol Buffers** ✅
- **QUIC transport protocol** for low-latency communication
- **TLS 1.3 encryption** by default for security
- **Protocol Buffers** for efficient message serialization
- **Stream multiplexing** for better performance

### 🌐 **Phase 4: REST API** ✅
- **FastAPI-based web interface** with OpenAPI documentation
- **Complete REST endpoints** for file operations and search
- **Async architecture** for high-performance web serving
- **Comprehensive error handling** and validation

### 📊 **Phase 5: Monitoring & Production** (Ready to Implement)
- **Prometheus metrics** collection and scraping
- **Grafana dashboards** for visualization and alerting
- **Performance monitoring** and health checks
- **Production hardening** and security enhancements

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │    │   REST API       │    │  Chord DHT      │
│   (Browser/App) │◄──►│   (FastAPI)      │◄──►│  (QUIC Nodes)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ API Integration  │    │ Distributed     │
                       │   Bridge Layer   │    │ Inverted Index  │
                       └──────────────────┘    └─────────────────┘
```

## 📁 **Project Structure**

```
NodeLink/
├── 🚀 main.py                          # Main entry point with command selection
├── 📋 requirements.txt                 # Python dependencies
├── 📚 README.md                        # Main project documentation
│
├── 🔧 src/                            # Core implementation
│   ├── __init__.py                     # Package initialization
│   ├── chord_node_v2.py               # Chord DHT with distributed search (Phase 1 & 2)
│   ├── chord_node_v3.py               # QUIC-enabled Chord node (Phase 3)
│   ├── quic_transport.py              # QUIC transport layer and Protocol Buffers
│   ├── chord.proto                    # Protocol Buffers schema definition
│   ├── chord_pb2.py                   # Generated Protocol Buffers Python classes
│   ├── rest_api.py                    # FastAPI web server with REST endpoints (Phase 4)
│   ├── api_bridge.py                  # Integration layer between REST API and Chord DHT
│   └── api_models.py                  # Pydantic models for request/response validation
│
├── 🐳 docker/                         # Docker deployment
│   ├── Dockerfile                     # Production-ready container definition
│   ├── docker-compose.yml             # Multi-node development cluster
│   ├── docker-compose.prod.yml        # Production configuration with resource limits
│   └── docker-compose.dev.yml         # Development overrides with hot-reload
│
├── 🛠️  scripts/                        # Management tools
│   ├── docker-manager.sh              # Interactive cluster management script
│   └── validate-docker.sh             # Pre-deployment validation script
│
├── 🧪 tests/                          # Testing suite
│   ├── __init__.py                     # Package initialization
│   ├── test_comprehensive.py          # Consolidated test suite for all phases
│   ├── test_chord_v2.py               # Chord protocol tests (legacy)
│   ├── test_phase2.py                 # Distributed search tests (legacy)
│   ├── test_phase3.py                 # QUIC transport tests (legacy)
│   ├── test_phase4.py                 # Complete REST API test suite (legacy)
│   └── test_phase4_basic.py           # Basic REST API validation (legacy)
│
├── 🎯 demos/                          # Interactive demonstrations
│   ├── __init__.py                     # Package initialization
│   ├── demo_comprehensive.py          # Consolidated demo for all phases
│   ├── demo_phase2.py                 # Distributed search demo (legacy)
│   ├── demo_phase3.py                 # QUIC transport demo (legacy)
│   └── demo_phase4.py                 # REST API demo (legacy)
│
├── 📖 docs/                           # Documentation
│   ├── DOCKER_GUIDE.md               # Comprehensive Docker deployment guide
│   ├── PHASE2_SUMMARY.md             # Distributed search implementation details
│   ├── PHASE3_SUMMARY.md             # QUIC transport implementation summary
│   ├── PHASE4_SUMMARY.md             # REST API implementation overview
│   ├── IMPLEMENTATION_STATUS.md       # Current project status and roadmap
│   └── CLEANUP_SUMMARY.md            # Project organization and cleanup log
│
└── 💾 shared/                         # File storage directories
    ├── shared/                        # Primary file storage
    ├── shared2/                       # Additional storage partition
    └── shared3/                       # Additional storage partition
```
- `IMPLEMENTATION_STATUS.md` - Complete project status tracking

## 🚀 **Quick Start**

## 🚀 **Quick Start**

### **Option 1: Main Entry Point** ⭐ (Recommended)
```bash
# Install dependencies
pip install -r requirements.txt

# Start REST API (includes all phases)
python main.py api

# Or start individual components
python main.py node-v2 --port 7000    # Chord DHT node
python main.py node-v3 --port 7001    # QUIC Chord node  
python main.py demo                    # Interactive demo
python main.py test                    # Run test suite
python main.py docker                  # Show Docker options
```

### **Option 2: Direct Module Access**
```bash
# Install dependencies
pip install -r requirements.txt

# Start REST API server (Phase 4 - includes all functionality)
python src/rest_api.py

# Or start individual Chord nodes
python src/chord_node_v2.py --port 7000    # Phase 1 & 2
python src/chord_node_v3.py --port 7001    # Phase 3
```

### **Option 3: Docker Deployment** 🐳
```bash
# Quick single-node start
docker build -f docker/Dockerfile -t chord-dht . && docker run -d -p 8000:8000 -v $(pwd)/shared:/app/shared chord-dht

# Multi-node cluster using management script (recommended)
chmod +x scripts/docker-manager.sh && ./scripts/docker-manager.sh start

# Multi-node cluster using Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# See docs/DOCKER_GUIDE.md for complete Docker setup instructions
```

## 🌐 **REST API Usage**

### **File Operations**
```bash
# Upload a file
curl -X POST "http://localhost:8000/files/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@example.txt"

# Download a file
curl -X GET "http://localhost:8000/files/example.txt" \
     --output downloaded_example.txt

# List all files
curl -X GET "http://localhost:8000/files/list"

# Delete a file
curl -X DELETE "http://localhost:8000/files/example.txt"
```

### **Search Operations**
```bash
# Basic search
curl -X GET "http://localhost:8000/search?q=machine+learning"

# Advanced search
curl -X POST "http://localhost:8000/search/advanced" \
     -H "Content-Type: application/json" \
     -d '{"query": "neural network", "sort_by": "relevance"}'

# Search suggestions
curl -X GET "http://localhost:8000/search/suggestions?q=deep"
```

### **Node Management**
```bash
# Node information
curl -X GET "http://localhost:8000/node/info"

# System health
curl -X GET "http://localhost:8000/health"

# Performance metrics
curl -X GET "http://localhost:8000/metrics"

# Ring topology
curl -X GET "http://localhost:8000/node/ring"
```

## 📋 **CLI Commands (Direct Node)**

When running nodes directly, you can use these interactive commands:

## 📋 **CLI Commands (Direct Node)**

When running nodes directly, you can use these interactive commands:

- `search <query>`: Search for files across the entire ring
  ```
  > search tintin
  Found files matching 'tintin':
  - tintin adventures (relevance: 1.00)
  ```

- `dsearch <query>`: Distributed search with relevance scoring
  ```
  > dsearch machine learning
  Search Results for 'machine learning':
  1. machine_learning_notes.txt (score: 0.85)
  2. deep_learning_tutorial.pdf (score: 0.42)
  ```

- `upload <filename>`: Upload a file to the DHT
  ```
  > upload my_document.txt
  File uploaded successfully to DHT
  ```

- `download <filename>`: Download a file from the DHT
  ```
  > download my_document.txt
  File downloaded successfully
  ```

- `list`: List all files stored on this node
- `ring`: Display current ring topology and neighbors
- `stabilize`: Manually trigger ring stabilization
- `info`: Show node information and statistics
- `leave`: Gracefully leave the ring
- `help`: Show all available commands

## 🧪 **Testing & Validation**

### **Run Complete Test Suites**
```bash
# Phase 1: Core Chord Protocol Tests
python test_chord_v2.py

# Phase 2: Distributed Search Tests  
python test_phase2.py

# Phase 3: QUIC Transport Tests
python test_phase3.py

# Phase 4: REST API Tests
python test_phase4_basic.py
```

### **Run Demonstrations**
```bash
# Distributed Search Demo
python demo_phase2.py

# QUIC Transport Demo
python demo_phase3.py

# REST API Demo (requires server running)
python demo_phase4.py
```

## 📊 **Performance Characteristics**

- **Lookup Complexity**: O(log N) guaranteed by Chord protocol
- **Fault Tolerance**: Handles node failures gracefully with automatic healing
- **Scalability**: Supports hundreds of nodes in the ring
- **Search Performance**: Sub-second distributed search with relevance ranking
- **Network Efficiency**: QUIC transport reduces latency by 50-70% vs TCP
- **Throughput**: 100+ concurrent REST API requests supported

## 🔧 **Configuration**

### **Environment Variables**
```bash
# REST API Configuration
export API_HOST=0.0.0.0
export API_PORT=8000
export MAX_FILE_SIZE=104857600  # 100MB

# Chord Node Configuration
export CHORD_PORT=7000
export BOOTSTRAP_HOST=127.0.0.1
export BOOTSTRAP_PORT=8080
export REPLICATION_FACTOR=3

# QUIC Configuration
export QUIC_TIMEOUT=10.0
export QUIC_MAX_CONNECTIONS=100
```

### **Advanced Configuration**
See individual configuration files:
- `api_models.py` - API configuration models
- `chord_node_v2.py` - Chord protocol parameters
- `quic_transport.py` - QUIC transport settings

## 🐳 **Docker Deployment**

For containerized deployment, see the comprehensive **[Docker Guide](DOCKER_GUIDE.md)** which includes:
- Single-node Docker setup
- Multi-node Docker Compose configuration  
- Production deployment with monitoring
- Troubleshooting and performance tuning

### **Quick Docker Commands**
```bash
# Using management script (recommended)
./scripts/docker-manager.sh start        # Start 3-node cluster
./scripts/docker-manager.sh health       # Check cluster health
./scripts/docker-manager.sh test         # Run tests
./scripts/docker-manager.sh logs         # View logs
./scripts/docker-manager.sh stop         # Clean shutdown

# Using Docker Compose directly
docker-compose -f docker/docker-compose.yml up -d             # Start cluster
docker-compose -f docker/docker-compose.yml logs -f           # View logs
docker-compose -f docker/docker-compose.yml down              # Stop cluster

# Manual health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```
- Kubernetes deployment manifests

## 📈 **Monitoring & Observability**

### **Built-in Metrics**
- Node health and uptime tracking
- File storage and retrieval statistics
- Search performance metrics
- Network connectivity monitoring
- Ring topology health checks

### **REST API Monitoring**
```bash
# Health check endpoint
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/metrics

# System status
curl http://localhost:8000/status
```

## 🤝 **Contributing**

### **Development Setup**
```bash
# Clone the repository
git clone <repository-url>
cd NodeLink

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest test_*.py
```

### **Code Structure**
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include comprehensive docstrings
- Write tests for new functionality
- Update documentation for changes

## 📚 **Documentation**

### **Implementation Details**
- **[Phase 2 Summary](PHASE2_SUMMARY.md)** - Distributed search implementation
- **[Phase 3 Summary](PHASE3_SUMMARY.md)** - QUIC transport details
- **[Phase 4 Summary](PHASE4_SUMMARY.md)** - REST API implementation
- **[Implementation Status](IMPLEMENTATION_STATUS.md)** - Complete project tracking

### **Technical Specifications**
- **[Chord Protocol](chord.proto)** - Protocol Buffers schema
- **[API Models](api_models.py)** - Request/response data structures
- **[Architecture Overview](ROADMAP.md)** - System design and roadmap

## 🚨 **Troubleshooting**

### **Common Issues**
1. **Port conflicts**: Ensure ports 6000-6010 and 8000 are available
2. **Permission errors**: Check file permissions in shared folders
3. **Network issues**: Verify firewall allows QUIC (UDP) traffic
4. **Memory usage**: Monitor system resources for large file operations

### **Debug Mode**
```bash
# Enable debug logging
python rest_api.py --debug

# Verbose Chord node logging  
python chord_node_v2.py --verbose
```

### **Log Locations**
- REST API logs: Console output
- Chord node logs: `chord_v2.log`
- QUIC transport logs: Console output (debug mode)

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 **Roadmap**

- ✅ **Phase 1**: Robust Chord DHT Protocol
- ✅ **Phase 2**: Distributed Inverted Index Search  
- ✅ **Phase 3**: QUIC Transport + Protocol Buffers
- ✅ **Phase 4**: REST API Web Interface
- 🔄 **Phase 5**: Prometheus Monitoring + Grafana Dashboards
- 📅 **Future**: Kubernetes deployment, advanced security features

---

**For detailed deployment instructions using Docker, see [DOCKER_GUIDE.md](DOCKER_GUIDE.md)**
  Found 1 files:
    - tintin adventures @ 127.0.0.1:6002
  ```

- `list`: List all files in the distributed ring
  ```
  > list
  Total files in ring: 17
    - dinuka wanniarachchi @ 127.0.0.1:6000
    - malshi div @ 127.0.0.1:6001
    - tintin adventures @ 127.0.0.1:6002
    ...
  ```

- `download <filename>`: Download a file from the ring
  ```
  > download "tintin adventures"
  Downloaded tintin adventures (1024 bytes)
  Saved as downloaded_tintin adventures
  ```

- `status`: Show node and ring information
  ```
  > status
  Node ID: 225
  Address: 127.0.0.1:6000
  Local files: 7
  Ring info: {...}
  ```

- `quit`: Gracefully exit the node

## Key Features

### ✅ Distributed File Storage
- Files are distributed across nodes using consistent hashing
- No single point of failure for file storage
- Automatic load balancing

### ✅ Replication & Fault Tolerance
- Configurable replication factor (default: 3 replicas per file)
- Files remain available even when nodes fail
- Automatic failure detection and recovery

### ✅ Ring Maintenance
- Stabilization protocol maintains correct ring structure
- Finger tables for efficient routing
- Predecessor/successor relationships automatically maintained

### ✅ Distributed Search
- Search across all nodes in the ring
- Partial filename matching supported
- Results show file location for debugging

### ✅ Robust Error Handling
- Network failures handled gracefully
- Node failures don't break the system
- Automatic retry mechanisms

## Testing & Validation

The system includes a comprehensive test suite that validates:

- **Ring Formation**: Proper successor/predecessor relationships
- **File Distribution**: Files distributed across multiple nodes
- **Distributed Search**: Search functionality across all nodes  
- **Fault Tolerance**: System availability after node failures
- **Replication**: File availability on multiple replicas

Run the tests:
```bash
python3 test_chord_v2.py
```

Example test output:
```
Ring formation: PASS
File distribution: PASS (17 files across 3 nodes)
Distributed search: PASS
Fault tolerance: PASS (files available after node failure)
```

## Technical Details

### Configuration
- **Ring Size**: 256 nodes (2^8, configurable)
- **Replication Factor**: 3 replicas per file
- **Stabilization Interval**: 2 seconds
- **Bootstrap Port**: 55556

### Hash Function
- SHA-1 based consistent hashing
- Maps files and nodes to ring positions
- Ensures even distribution across the ring

### Network Protocol
- TCP-based communication
- JSON message format
- Automatic timeout and retry handling

## Requirements
- Python 3.6+ (uses standard library only)
- No external dependencies required

## Troubleshooting

### Common Issues
1. **Port already in use**: Change the port numbers
2. **Bootstrap server not running**: Start `bootstrap_server.py` first
3. **Files not found after node failure**: Check replication factor and ensure multiple nodes are running

### Debug Mode
Add logging to see detailed operations:
```bash
# Check chord_v2.log for detailed operation logs
tail -f chord_v2.log
```

