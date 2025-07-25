#!/usr/bin/env python3
"""
Performance Monitoring Setup for Chord DHT System
Installs required dependencies and starts monitoring stack
"""

import subprocess
import sys
import os

def install_prometheus_client():
    """Install prometheus_client library"""
    print("📦 Installing prometheus_client...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'prometheus_client'])
        print("✅ prometheus_client installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install prometheus_client: {e}")
        return False

def check_docker():
    """Check if Docker is available"""
    try:
        subprocess.check_output(['docker', '--version'])
        subprocess.check_output(['docker-compose', '--version'])
        print("✅ Docker and Docker Compose are available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker or Docker Compose not found")
        print("   Please install Docker Desktop from https://www.docker.com/products/docker-desktop")
        return False

def start_monitoring_stack():
    """Start Prometheus and Grafana using Docker Compose"""
    print("🚀 Starting monitoring stack...")
    try:
        subprocess.check_call(['docker-compose', 'up', '-d'])
        print("✅ Monitoring stack started successfully")
        print("\n📊 Access URLs:")
        print("   - Prometheus: http://localhost:9090")
        print("   - Grafana: http://localhost:3000 (admin/admin)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start monitoring stack: {e}")
        return False

def main():
    print("🔧 Chord DHT Performance Monitoring Setup")
    print("=" * 50)
    
    # Install Python dependencies
    if not install_prometheus_client():
        print("❌ Setup failed - could not install dependencies")
        return False
    
    # Check Docker
    if not check_docker():
        print("❌ Setup failed - Docker not available")
        return False
    
    # Start monitoring stack
    if not start_monitoring_stack():
        print("❌ Setup failed - could not start monitoring")
        return False
    
    print("\n🎉 Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. Start Bootstrap Server:")
    print("   python3 bootstrap_server.py 5000")
    print("\n2. Start Chord Nodes with Metrics:")
    print("   python3 rest_api.py 5001 8001  # Metrics on port 9001")
    print("   python3 rest_api.py 5002 8002  # Metrics on port 9002")
    print("   python3 rest_api.py 5003 8003  # Metrics on port 9003")
    print("\n3. Access Grafana Dashboard:")
    print("   Open http://localhost:3000")
    print("   Login: admin/admin")
    print("   Open 'Chord DHT Performance Metrics' dashboard")
    print("\n4. Test the system and observe metrics!")
    
    return True

if __name__ == "__main__":
    main()
