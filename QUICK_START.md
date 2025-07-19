# 🚀 Quick Start Guide - Advanced Chord DHT File Sharing System

## 📋 Prerequisites

```bash
# Ensure you have Python 3.8+ and Docker installed
python --version  # Should be 3.8+
docker --version  # Any recent version
docker-compose --version
```

---

## 🐳 Option 1: Docker Deployment (Recommended)

### **🎯 Super Quick Start (3 commands)**
```bash
# 1. Start 3-node cluster
./scripts/docker-manager.sh start

# 2. Check health
./scripts/docker-manager.sh health

# 3. View logs
./scripts/docker-manager.sh logs
```

### **📝 Detailed Docker Steps**

#### **Step 1: Start the Cluster**
```bash
# Start multi-node cluster (3 nodes with REST API)
./scripts/docker-manager.sh start

# OR manually with docker-compose
docker-compose -f docker/docker-compose.yml up -d
```

#### **Step 2: Verify Cluster Health**
```bash
# Check all nodes are running
./scripts/docker-manager.sh health

# OR manually check
docker-compose -f docker/docker-compose.yml ps
```

#### **Step 3: Access the System**
- **REST API**: http://localhost:8000
- **Node 1 API**: http://localhost:8000  
- **Node 2 API**: http://localhost:8001
- **Node 3 API**: http://localhost:8002

#### **Step 4: Test File Operations**
```bash
# Upload a file via REST API
curl -X POST -F "file=@test.txt" http://localhost:8000/files/upload

# List files
curl http://localhost:8000/files/list

# Download a file
curl http://localhost:8000/files/download/test.txt -o downloaded.txt
```

#### **Step 5: Monitor System**
```bash
# View real-time logs
./scripts/docker-manager.sh logs

# Check cluster status
./scripts/docker-manager.sh health

# Stop cluster when done
./scripts/docker-manager.sh stop
```

---

## 🔧 Option 2: Manual/Development Mode

### **Step 1: Setup Environment**
```bash
# Install dependencies
pip install -r requirements.txt

# OR use virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### **Step 2: Quick Demo**
```bash
# Run interactive demonstration (easiest way to see it working)
python main.py demo
```

### **Step 3: Start Individual Components**

#### **Option A: REST API Server (All-in-one)**
```bash
# Start REST API with integrated DHT (recommended)
python main.py api

# Access at: http://localhost:8000
# Swagger docs at: http://localhost:8000/docs
```

#### **Option B: Individual Node Testing**
```bash
# Terminal 1: Start first Chord node (Phase 1 & 2)
python main.py node-v2 --port 7000

# Terminal 2: Start second node joining the first
python main.py node-v2 --port 7001

# Terminal 3: Start QUIC node (Phase 3)
python main.py node-v3 --port 7002
```

### **Step 4: Test the System**
```bash
# Run comprehensive tests
python main.py test

# OR run specific test phases
python -m pytest tests/test_chord_v2.py -v
python -m pytest tests/test_phase4.py -v
```

---

## 🎮 Interactive Testing

### **File Operations via REST API**
```bash
# 1. Start the API server
python main.py api

# 2. In another terminal, test operations:

# Upload a file
curl -X POST -F "file=@README.md" http://localhost:8000/files/upload

# List all files
curl http://localhost:8000/files/list

# Search for files
curl "http://localhost:8000/files/search?query=README"

# Download a file  
curl http://localhost:8000/files/download/README.md -o test_download.md

# Get node info
curl http://localhost:8000/nodes/info
```

### **Web Interface**
Open your browser to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Interactive API**: http://localhost:8000/redoc

---

## 🔍 Troubleshooting

### **Docker Issues**
```bash
# Check if containers are running
docker ps

# View logs for specific service
docker-compose -f docker/docker-compose.yml logs chord-node-1

# Rebuild containers
./scripts/docker-manager.sh build

# Clean restart
./scripts/docker-manager.sh clean
./scripts/docker-manager.sh start
```

### **Manual Mode Issues**
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Test imports
python -c "import sys; sys.path.append('src'); import chord_node_v2, rest_api; print('OK')"

# Check port availability
lsof -i :8000  # Should be empty if port is free
```

---

## 📊 Quick Commands Reference

| Action | Docker | Manual |
|--------|---------|---------|
| **Start System** | `./scripts/docker-manager.sh start` | `python main.py api` |
| **Run Demo** | Access http://localhost:8000 | `python main.py demo` |
| **Run Tests** | `./scripts/docker-manager.sh test` | `python main.py test` |
| **View Logs** | `./scripts/docker-manager.sh logs` | Check terminal output |
| **Stop System** | `./scripts/docker-manager.sh stop` | `Ctrl+C` |

---

## 🎯 Recommended Workflow

1. **First Time**: Try `python main.py demo` to see the system in action
2. **Development**: Use `python main.py api` for single-node testing
3. **Production Testing**: Use `./scripts/docker-manager.sh start` for multi-node cluster
4. **API Testing**: Visit http://localhost:8000/docs for interactive API

**🎉 You're ready to explore the Advanced Chord DHT File Sharing System!**
