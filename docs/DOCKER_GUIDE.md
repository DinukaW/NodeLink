# 🐳 Docker Deployment Guide

This guide provides comprehensive instructions for deploying the Advanced Chord DHT File Sharing System using Docker and Docker Compose.

## 📋 Prerequisites

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- At least **2GB RAM** available for containers
- Ports **8000-8005** and **9000-9005** available on your host

### Installation

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker

# Or download from: https://docs.docker.com/desktop/mac/install/
```

#### Ubuntu/Linux
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

#### Verify Installation
```bash
docker --version
docker compose version
```

## 🚀 Quick Start

### Option 1: Management Script (Recommended)

Use the provided management script for easy cluster operations:

```bash
# Validate setup first (optional)
chmod +x validate-docker.sh && ./validate-docker.sh

# Make script executable (first time only)
chmod +x docker-manager.sh

# Start the cluster
./docker-manager.sh start

# Check cluster health
./docker-manager.sh health

# View logs
./docker-manager.sh logs

# Run tests
./docker-manager.sh test

# Stop cluster
./docker-manager.sh stop

# See all available commands
./docker-manager.sh -h
```

### Option 2: Single Node with REST API

For testing and development, start a single node with REST API:

```bash
# Build the image
docker build -t chord-dht .

# Run single node with REST API
docker run -d \
  --name chord-node-api \
  -p 8000:8000 \
  -v $(pwd)/shared:/app/shared \
  chord-dht

# Check if it's running
curl http://localhost:8000/health
```

### Option 3: Multi-Node Network

For a complete distributed system, use Docker Compose:

```bash
# Create the multi-node network
docker-compose up -d

# Verify all nodes are running
docker-compose ps

# Check cluster status
curl http://localhost:8000/nodes
```

## 📁 Project Structure

```
NodeLink/
├── Dockerfile                  # Main container definition
├── docker-compose.yml          # Development multi-node setup
├── docker-compose.prod.yml     # Production configuration
├── docker-compose.dev.yml      # Development overrides
├── docker-manager.sh           # Cluster management script
├── validate-docker.sh          # Setup validation script
├── .dockerignore              # Files to exclude from build
├── requirements.txt           # Python dependencies
├── shared/                    # Shared files (mounted as volume)
├── rest_api.py               # REST API entry point
├── chord_node_v3.py          # Chord DHT implementation
└── ...
```

## 🔧 Configuration Files

### Dockerfile

The main Dockerfile is already created and optimized for production:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create shared directory for file storage
RUN mkdir -p shared shared2 shared3

# Expose ports (REST API and DHT)
EXPOSE 8000 9000

# Default command: Start REST API
CMD ["python", "rest_api.py"]
```

### Docker Compose Configuration

Create `docker-compose.yml` for multi-node deployment:

```yaml
version: '3.8'

services:
  chord-node-1:
    build: .
    container_name: chord-node-1
    ports:
      - "8000:8000"  # REST API
      - "9000:9000"  # DHT port
    environment:
      - NODE_ID=1
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - DHT_PORT=9000
      - BOOTSTRAP_NODES=""
    volumes:
      - ./shared:/app/shared
      - ./shared2:/app/shared2
      - ./shared3:/app/shared3
    networks:
      - chord-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  chord-node-2:
    build: .
    container_name: chord-node-2
    ports:
      - "8001:8000"  # REST API
      - "9001:9000"  # DHT port
    environment:
      - NODE_ID=2
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - DHT_PORT=9000
      - BOOTSTRAP_NODES=chord-node-1:9000
    volumes:
      - ./shared:/app/shared
      - ./shared2:/app/shared2
      - ./shared3:/app/shared3
    networks:
      - chord-network
    depends_on:
      - chord-node-1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  chord-node-3:
    build: .
    container_name: chord-node-3
    ports:
      - "8002:8000"  # REST API
      - "9002:9000"  # DHT port
    environment:
      - NODE_ID=3
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - DHT_PORT=9000
      - BOOTSTRAP_NODES=chord-node-1:9000,chord-node-2:9000
    volumes:
      - ./shared:/app/shared
      - ./shared2:/app/shared2
      - ./shared3:/app/shared3
    networks:
      - chord-network
    depends_on:
      - chord-node-1
      - chord-node-2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  chord-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  shared-data:
    driver: local
```

### .dockerignore

Create `.dockerignore` to exclude unnecessary files:

```
# Version control
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Documentation (except Docker files)
*.md
!README.md
!DOCKER_GUIDE.md

# Test files (optional - remove if you want tests in container)
test_*.py
demo_*.py

# Temporary files
*.tmp
*.temp
```

## 📊 Deployment Scenarios

### Scenario 1: Development Environment

For local development with hot-reloading:

```bash
# Use development override
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Or mount source code for live editing
docker run -it \
  -p 8000:8000 \
  -v $(pwd):/app \
  -v $(pwd)/shared:/app/shared \
  chord-dht \
  python rest_api.py --reload
```

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  chord-node-1:
    volumes:
      - .:/app
    command: ["python", "rest_api.py", "--reload"]
    environment:
      - DEBUG=1

  chord-node-2:
    volumes:
      - .:/app
    command: ["python", "rest_api.py", "--reload"]
    environment:
      - DEBUG=1

  chord-node-3:
    volumes:
      - .:/app
    command: ["python", "rest_api.py", "--reload"]
    environment:
      - DEBUG=1
```

### Scenario 2: Production Environment

For production deployment with resource limits:

```yaml
version: '3.8'

services:
  chord-node-1:
    # ... (base configuration)
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"

  # ... (similar for other nodes)
```

### Scenario 3: Scaled Deployment

For larger networks, use scaling:

```bash
# Scale to 5 nodes
docker-compose up -d --scale chord-node-2=3

# Or use Docker Swarm for production scaling
docker swarm init
docker stack deploy -c docker-compose.yml chord-stack
```

## 🔧 Management Commands

### Using the Management Script (Recommended)

The `docker-manager.sh` script provides a convenient interface for all operations:

```bash
# Start cluster in development mode
./docker-manager.sh dev

# Start cluster in production mode  
./docker-manager.sh prod

# Check cluster health and status
./docker-manager.sh health

# View real-time logs
./docker-manager.sh logs

# Run comprehensive tests
./docker-manager.sh test

# Restart the entire cluster
./docker-manager.sh restart

# Clean up everything (containers, volumes, images)
./docker-manager.sh clean
```

### Manual Docker Commands

For advanced users who prefer direct Docker commands:

```bash
# Build the image
docker build -t chord-dht .

# Build with custom tag
docker build -t chord-dht:v1.0 .

# Build without cache
docker build --no-cache -t chord-dht .

# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d chord-node-1

# View logs
docker-compose logs -f chord-node-1

# Follow all logs
docker-compose logs -f
```

### Monitoring and Debugging

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats

# Execute commands in running container
docker exec -it chord-node-1 bash

# Check container health
docker inspect --format='{{.State.Health.Status}}' chord-node-1

# View container configuration
docker inspect chord-node-1
```

### Data Management

```bash
# Backup shared data
docker run --rm -v chord_shared-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/backup.tar.gz -C /data .

# Restore shared data
docker run --rm -v chord_shared-data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/backup.tar.gz -C /data

# Clean up volumes
docker-compose down -v
```

## 🧪 Testing the Deployment

### Health Checks

```bash
# Check all nodes are healthy
for port in 8000 8001 8002; do
  echo "Node $port status:"
  curl -s http://localhost:$port/health | jq
done

# Check cluster formation
curl -s http://localhost:8000/nodes | jq

# Test file upload
curl -X POST -F "file=@test.txt" http://localhost:8000/files/upload

# Test search functionality
curl "http://localhost:8000/search?query=test"
```

### Load Testing

```bash
# Install testing tools
pip install httpx pytest-asyncio

# Simple load test
for i in {1..10}; do
  curl -X POST -F "file=@test$i.txt" http://localhost:8000/files/upload &
done
wait

# Check distribution
curl http://localhost:8000/files | jq length
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check which process is using port
   lsof -i :8000
   
   # Use different ports
   docker run -p 8080:8000 chord-dht
   ```

2. **Permission Issues**
   ```bash
   # Fix shared directory permissions
   sudo chown -R $USER:$USER shared/
   chmod -R 755 shared/
   ```

3. **Memory Issues**
   ```bash
   # Check Docker memory limit
   docker system df
   docker system prune
   
   # Increase Docker Desktop memory
   # Docker Desktop -> Settings -> Resources -> Advanced
   ```

4. **Network Issues**
   ```bash
   # Check network connectivity
   docker network ls
   docker network inspect chord_chord-network
   
   # Test inter-container communication
   docker exec chord-node-1 ping chord-node-2
   ```

### Debug Mode

Enable debug logging:

```bash
# Set debug environment
docker run -e DEBUG=1 -e LOG_LEVEL=DEBUG chord-dht

# Or in docker-compose.yml
environment:
  - DEBUG=1
  - LOG_LEVEL=DEBUG
```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check container logs for performance issues
docker-compose logs chord-node-1 | grep -i "slow\|timeout\|error"

# Profile the application
docker exec chord-node-1 python -m cProfile -o profile.stats rest_api.py
```

## 🚀 Production Considerations

### Security

1. **Use secrets for sensitive data**:
   ```yaml
   services:
     chord-node-1:
       secrets:
         - chord_secret_key
   
   secrets:
     chord_secret_key:
       external: true
   ```

2. **Run with non-root user**:
   ```dockerfile
   RUN adduser --disabled-password --gecos '' appuser
   USER appuser
   ```

3. **Enable TLS for external access**:
   ```bash
   # Use nginx or traefik as reverse proxy
   # Enable HTTPS with Let's Encrypt
   ```

### Scalability

1. **Use Docker Swarm or Kubernetes**
2. **Implement horizontal pod autoscaling**
3. **Use external load balancer**
4. **Separate data storage (external volumes)**

### Monitoring

1. **Add health check endpoints**
2. **Use Prometheus for metrics collection**
3. **Set up alerting with Grafana**
4. **Monitor logs with ELK stack**

## 📈 Next Steps

1. **Set up monitoring** with Prometheus and Grafana
2. **Implement CI/CD pipeline** for automated deployments  
3. **Add Kubernetes manifests** for cloud deployment
4. **Create Helm charts** for easy installation
5. **Implement backup and disaster recovery**

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI in Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Python Docker Best Practices](https://testdriven.io/blog/docker-best-practices/)

---

For issues or questions about Docker deployment, please refer to the main [README.md](README.md) or create an issue in the repository.
