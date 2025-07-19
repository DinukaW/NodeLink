# 🚀 Quick Start Guide - Advanced Chord DHT File Sharing System

## 📋 Prerequisites

```bash
# Ensure you have Python 3.8+ and Docker installed
python --version  # Should be 3.8+
docker --version  # Any recent version
docker-compose --version
```

---

## � Option 1: Manual/Development Mode (RECOMMENDED FOR NOW)

### **🎯 Super Quick Start (2 commands)**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the system
python main.py api
```

### **📝 Detailed Manual Steps**

#### **Step 1: Setup Environment**
```bash
# Install dependencies
pip install -r requirements.txt

# OR use virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### **Step 2: Quick Demo**
```bash
# Run interactive demonstration (easiest way to see it working)
python main.py demo
```

#### **Step 3: Start REST API Server**
```bash
# Start REST API with integrated DHT (recommended)
python main.py api

# Access at: http://localhost:8000
# Swagger docs at: http://localhost:8000/docs
```

#### **Step 4: Test File Operations**
```bash
# In another terminal, test operations:

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

#### **Step 5: Web Interface**
Open your browser to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Interactive API**: http://localhost:8000/redoc

---

## 🐳 Option 2: Docker Deployment (EXPERIMENTAL)

**⚠️ Note**: Docker build may have network issues. Try manual mode first.

### **Basic Docker Commands**
```bash
# Build the image manually
docker build -f docker/Dockerfile . -t chord-dht:latest

# Run single container
docker run -p 8000:8000 -p 9000:9000 chord-dht:latest

# OR use docker-compose (if build works)
docker-compose -f docker/docker-compose.yml up -d
```

### **Docker Manager Script**
```bash
# If Docker works, you can use:
./scripts/docker-manager.sh build   # Build images
./scripts/docker-manager.sh start   # Start cluster
./scripts/docker-manager.sh health  # Check health
./scripts/docker-manager.sh stop    # Stop cluster
```

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
