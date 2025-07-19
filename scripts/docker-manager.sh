#!/bin/bash

# Advanced Chord DHT Docker Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
COMPOSE_FILE="docker/docker-compose.yml"
PROJECT_NAME="chord-dht"

print_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start       Start the cluster"
    echo "  stop        Stop the cluster"
    echo "  restart     Restart the cluster"
    echo "  build       Build Docker images"
    echo "  logs        Show cluster logs"
    echo "  health      Check cluster health"
    echo "  test        Run cluster tests"
    echo "  clean       Clean up containers and volumes"
    echo "  dev         Start in development mode"
    echo "  prod        Start in production mode"
    echo ""
    echo "Options:"
    echo "  -f FILE     Use specific docker-compose file"
    echo "  -p NAME     Set project name"
    echo "  -h          Show this help"
}

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
    fi
}

build_images() {
    log "Building Docker images..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build
    success "Images built successfully"
}

start_cluster() {
    log "Starting Chord DHT cluster..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    sleep 5
    check_health
    success "Cluster started successfully"
    log "API endpoints:"
    log "  Node 1: http://localhost:8000"
    log "  Node 2: http://localhost:8001"
    log "  Node 3: http://localhost:8002"
}

stop_cluster() {
    log "Stopping Chord DHT cluster..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    success "Cluster stopped successfully"
}

restart_cluster() {
    log "Restarting Chord DHT cluster..."
    stop_cluster
    start_cluster
}

show_logs() {
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f "$@"
}

check_health() {
    log "Checking cluster health..."
    local healthy=0
    local total=0
    
    for port in 8000 8001 8002; do
        total=$((total + 1))
        if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
            success "Node on port $port: HEALTHY"
            healthy=$((healthy + 1))
        else
            warning "Node on port $port: UNHEALTHY"
        fi
    done
    
    if [ $healthy -eq $total ]; then
        success "All nodes are healthy ($healthy/$total)"
    else
        warning "Only $healthy/$total nodes are healthy"
    fi
    
    # Check cluster formation
    log "Checking cluster formation..."
    if curl -f -s "http://localhost:8000/nodes" | jq -e '.nodes | length > 0' > /dev/null 2>&1; then
        local node_count=$(curl -s "http://localhost:8000/nodes" | jq '.nodes | length')
        success "Cluster formed with $node_count nodes"
    else
        warning "Unable to verify cluster formation"
    fi
}

run_tests() {
    log "Running cluster tests..."
    
    # Test file upload
    echo "test content" > test_file.txt
    if curl -f -s -X POST -F "file=@test_file.txt" "http://localhost:8000/files/upload" > /dev/null; then
        success "File upload test: PASSED"
    else
        error "File upload test: FAILED"
    fi
    
    # Test search
    if curl -f -s "http://localhost:8000/search?query=test" > /dev/null; then
        success "Search test: PASSED"
    else
        error "Search test: FAILED"
    fi
    
    # Test file listing
    if curl -f -s "http://localhost:8000/files" > /dev/null; then
        success "File listing test: PASSED"
    else
        error "File listing test: FAILED"
    fi
    
    # Cleanup
    rm -f test_file.txt
    success "All tests passed"
}

clean_cluster() {
    log "Cleaning up containers and volumes..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v --remove-orphans
    docker system prune -f
    success "Cleanup completed"
}

start_dev() {
    COMPOSE_FILE="docker/docker-compose.yml:docker/docker-compose.dev.yml"
    log "Starting in development mode with hot reload..."
    start_cluster
}

start_prod() {
    COMPOSE_FILE="docker/docker-compose.prod.yml"
    log "Starting in production mode..."
    start_cluster
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -p)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        start|stop|restart|build|logs|health|test|clean|dev|prod)
            COMMAND="$1"
            shift
            break
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Check prerequisites
check_docker

# Execute command
case "${COMMAND:-start}" in
    start)
        build_images
        start_cluster
        ;;
    stop)
        stop_cluster
        ;;
    restart)
        restart_cluster
        ;;
    build)
        build_images
        ;;
    logs)
        show_logs "$@"
        ;;
    health)
        check_health
        ;;
    test)
        run_tests
        ;;
    clean)
        clean_cluster
        ;;
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    *)
        error "Unknown command: $COMMAND"
        ;;
esac
