#!/bin/bash

# Docker deployment validation script
# Tests the Docker setup without starting containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log "Validating Docker deployment setup..."

# Check if required files exist
log "Checking required files..."

required_files=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "docker-compose.prod.yml"
    "docker-manager.sh"
    ".dockerignore"
    "requirements.txt"
    "rest_api.py"
    "chord_node_v3.py"
)

missing_files=()

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        success "Found: $file"
    else
        error "Missing: $file"
        missing_files+=("$file")
    fi
done

if [[ ${#missing_files[@]} -gt 0 ]]; then
    error "Missing required files: ${missing_files[*]}"
fi

# Check if directories exist
log "Checking required directories..."

required_dirs=("shared" "shared2" "shared3")

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        success "Found directory: $dir"
    else
        warning "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Validate Dockerfile syntax
log "Validating Dockerfile syntax..."
if docker version > /dev/null 2>&1; then
    if docker build --dry-run . > /dev/null 2>&1; then
        success "Dockerfile syntax is valid"
    else
        error "Dockerfile has syntax errors"
    fi
else
    warning "Docker daemon not running - skipping Dockerfile validation"
fi

# Validate Docker Compose files
log "Validating Docker Compose files..."

compose_files=("docker-compose.yml" "docker-compose.dev.yml" "docker-compose.prod.yml")

for compose_file in "${compose_files[@]}"; do
    if command -v docker-compose > /dev/null 2>&1; then
        if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
            success "$compose_file syntax is valid"
        else
            error "$compose_file has syntax errors"
        fi
    elif docker compose version > /dev/null 2>&1; then
        if docker compose -f "$compose_file" config > /dev/null 2>&1; then
            success "$compose_file syntax is valid"
        else
            error "$compose_file has syntax errors"
        fi
    else
        warning "Docker Compose not found - skipping validation"
        break
    fi
done

# Check script permissions
log "Checking script permissions..."

if [[ -x "docker-manager.sh" ]]; then
    success "docker-manager.sh is executable"
else
    warning "Making docker-manager.sh executable"
    chmod +x docker-manager.sh
fi

# Validate Python requirements
log "Checking Python requirements..."

if [[ -f "requirements.txt" ]]; then
    required_packages=("fastapi" "uvicorn" "aioquic" "protobuf" "pydantic" "httpx")
    
    for package in "${required_packages[@]}"; do
        if grep -q "^$package" requirements.txt; then
            success "Found required package: $package"
        else
            warning "Package not found in requirements.txt: $package"
        fi
    done
else
    error "requirements.txt not found"
fi

# Check port availability (only if not in Docker)
if [[ -z "${DOCKER_ENV}" ]]; then
    log "Checking port availability..."
    
    required_ports=(8000 8001 8002 9000 9001 9002)
    
    for port in "${required_ports[@]}"; do
        if ! lsof -i :$port > /dev/null 2>&1; then
            success "Port $port is available"
        else
            warning "Port $port is already in use"
        fi
    done
fi

# Validate environment variables
log "Checking environment variables..."

if [[ -n "${DOCKER_HOST}" ]]; then
    success "DOCKER_HOST is set: ${DOCKER_HOST}"
else
    success "Using default Docker host"
fi

success "Docker deployment validation completed successfully!"

log "Ready to deploy! Use one of these commands:"
log "  ./docker-manager.sh start    # Start with management script"
log "  docker-compose up -d         # Start with Docker Compose"
log "  ./docker-manager.sh dev      # Start in development mode"
log "  ./docker-manager.sh prod     # Start in production mode"
