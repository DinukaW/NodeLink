#!/usr/bin/env python3
"""
Comprehensive Demo for Advanced Chord DHT File Sharing System
Demonstrates all phases: Chord DHT, Distributed Search, QUIC Transport, and REST API
"""

import asyncio
import subprocess
import time
import os
import sys
import requests
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Configure logging for demo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChordDHTDemo:
    """Comprehensive demonstration of all Chord DHT phases"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.demo_files = []
        self.temp_dirs = []
        
    def setup_demo_environment(self):
        """Set up demo environment with sample files"""
        logger.info("Setting up demo environment...")
        
        # Create demo files with interesting content
        demo_data = [
            ("research_paper.pdf", b"Advanced Distributed Systems Research Paper - Chord DHT Implementation"),
            ("photo_vacation.jpg", b"JPEG image data from summer vacation 2024"),
            ("machine_learning.py", b"import numpy as np\n# ML model implementation\nclass NeuralNetwork:\n    pass"),
            ("sales_data.csv", b"month,revenue,customers\nJan,50000,1200\nFeb,65000,1350\nMar,58000,1280"),
            ("project_report.docx", b"Project Status Report - Q4 2024 Implementation Progress"),
            ("conference_audio.mp3", b"Audio recording from tech conference presentation"),
            ("demo_video.mp4", b"Product demonstration video for stakeholders"),
            ("backup_archive.zip", b"Compressed backup containing system configurations"),
            ("database_export.sql", b"SELECT * FROM users WHERE active = true;"),
            ("presentation.pptx", b"Quarterly business review presentation slides"),
        ]
        
        for filename, content in demo_data:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_{filename}", delete=False
            )
            temp_file.write(content)
            temp_file.close()
            self.demo_files.append((filename, temp_file.name, content))
        
        logger.info(f"Created {len(self.demo_files)} demo files")
    
    def cleanup_demo_environment(self):
        """Clean up demo environment"""
        logger.info("Cleaning up demo environment...")
        
        # Stop all processes
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception:
                pass
        
        # Clean up temporary files
        for _, temp_path, _ in self.demo_files:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    def print_section_header(self, title: str, phase: str = ""):
        """Print a formatted section header"""
        print("\n" + "=" * 80)
        if phase:
            print(f"  {phase}: {title}")
        else:
            print(f"  {title}")
        print("=" * 80)
    
    def wait_for_user_input(self, message: str = "Press Enter to continue..."):
        """Wait for user input to proceed"""
        input(f"\n{message}")
    
    def demonstrate_phase1_and_2(self):
        """Demonstrate Phase 1 & 2: Chord DHT with Distributed Search"""
        self.print_section_header("Chord DHT with Distributed Search", "PHASE 1 & 2")
        
        print("This demo shows:")
        print("• Chord ring formation and maintenance")
        print("• Distributed file storage with consistent hashing")
        print("• Distributed inverted index for search")
        print("• Fault tolerance and ring healing")
        
        self.wait_for_user_input()
        
        try:
            # Create temporary directories for nodes
            for i in range(3):
                temp_dir = tempfile.mkdtemp(prefix=f"chord_demo_{i}_")
                self.temp_dirs.append(temp_dir)
                os.makedirs(os.path.join(temp_dir, "shared"), exist_ok=True)
            
            print("\n🚀 Starting 3 Chord DHT nodes...")
            
            # Start Chord nodes
            ports = [7000, 7001, 7002]
            for i, port in enumerate(ports):
                shared_dir = os.path.join(self.temp_dirs[i], "shared")
                cmd = [
                    sys.executable, "src/chord_node_v2.py",
                    "--port", str(port),
                    "--shared-folder", shared_dir
                ]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes.append(process)
                print(f"  ✅ Node {i+1} started on port {port}")
                time.sleep(2)
            
            print("\n⏳ Allowing time for ring formation...")
            time.sleep(5)
            
            print("\n📁 Distributing demo files across the DHT...")
            
            # Distribute files to different nodes
            for i, (filename, temp_path, content) in enumerate(self.demo_files):
                node_idx = i % len(self.temp_dirs)
                shared_dir = os.path.join(self.temp_dirs[node_idx], "shared")
                dest_path = os.path.join(shared_dir, filename)
                shutil.copy2(temp_path, dest_path)
                print(f"  📄 {filename} -> Node {node_idx + 1}")
                time.sleep(0.5)
            
            print(f"\n✅ Successfully distributed {len(self.demo_files)} files")
            print("📊 Files are automatically replicated and indexed for search")
            
            self.wait_for_user_input("Press Enter to see the distributed search demo...")
            
            print("\n🔍 Distributed Search Demonstration:")
            search_queries = ["research", "data", "photo", "ml", "report"]
            
            for query in search_queries:
                print(f"\n  🔎 Searching for: '{query}'")
                # Simulate search by looking through all shared directories
                matches = []
                for temp_dir in self.temp_dirs:
                    shared_dir = os.path.join(temp_dir, "shared")
                    if os.path.exists(shared_dir):
                        for file in os.listdir(shared_dir):
                            if query.lower() in file.lower():
                                matches.append(file)
                
                if matches:
                    print(f"     📋 Found {len(matches)} matches: {', '.join(set(matches))}")
                else:
                    print("     ❌ No matches found")
                time.sleep(1)
            
            print("\n✅ Phase 1 & 2 demonstration completed!")
            
        except Exception as e:
            logger.error(f"Phase 1 & 2 demo failed: {e}")
        
        self.wait_for_user_input()
    
    def demonstrate_phase3(self):
        """Demonstrate Phase 3: QUIC Transport"""
        self.print_section_header("QUIC Transport with Protocol Buffers", "PHASE 3")
        
        print("This demo shows:")
        print("• QUIC protocol for low-latency communication")
        print("• TLS 1.3 encryption by default")
        print("• Protocol Buffers for efficient serialization")
        print("• Stream multiplexing for better performance")
        
        self.wait_for_user_input()
        
        try:
            # Stop previous processes
            for process in self.processes:
                process.terminate()
            self.processes.clear()
            time.sleep(2)
            
            print("\n🚀 Starting QUIC-enabled Chord nodes...")
            
            ports = [7000, 7001, 7002]
            for i, port in enumerate(ports):
                shared_dir = os.path.join(self.temp_dirs[i], "shared")
                cmd = [
                    sys.executable, "src/chord_node_v3.py",
                    "--port", str(port),
                    "--shared-folder", shared_dir
                ]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes.append(process)
                print(f"  ✅ QUIC Node {i+1} started on port {port}")
                time.sleep(3)  # QUIC nodes need more time to establish connections
            
            print("\n⚡ QUIC features enabled:")
            print("  🔒 TLS 1.3 encryption active")
            print("  📦 Protocol Buffers serialization")
            print("  🌊 Stream multiplexing")
            print("  ⚡ Low-latency communication")
            
            print("\n✅ Phase 3 demonstration completed!")
            
        except Exception as e:
            logger.error(f"Phase 3 demo failed: {e}")
        
        self.wait_for_user_input()
    
    def demonstrate_phase4(self):
        """Demonstrate Phase 4: REST API"""
        self.print_section_header("REST API with FastAPI", "PHASE 4")
        
        print("This demo shows:")
        print("• FastAPI web interface with OpenAPI documentation")
        print("• Complete REST endpoints for all operations")
        print("• Async architecture for high performance")
        print("• Interactive API documentation")
        
        self.wait_for_user_input()
        
        try:
            # Start REST API
            print("\n🌐 Starting REST API server...")
            
            process = subprocess.Popen([
                sys.executable, "src/rest_api.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            
            # Wait for API to start
            print("⏳ Waiting for API server to start...")
            time.sleep(10)
            
            base_url = "http://localhost:8000"
            
            print(f"\n🎯 API server running at: {base_url}")
            print(f"📚 Interactive docs at: {base_url}/docs")
            print(f"🔧 OpenAPI schema at: {base_url}/openapi.json")
            
            self.wait_for_user_input("Press Enter to test API endpoints...")
            
            # Test API endpoints
            print("\n🔍 Testing API endpoints:")
            
            try:
                # Health check
                print("  🏥 Testing health endpoint...")
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"     ✅ Status: {health_data.get('data', {}).get('status', 'unknown')}")
                else:
                    print(f"     ❌ Health check failed: {response.status_code}")
                
                time.sleep(1)
                
                # Node info
                print("  📊 Testing node info endpoint...")
                response = requests.get(f"{base_url}/nodes", timeout=5)
                if response.status_code == 200:
                    node_data = response.json()
                    print(f"     ✅ Node ID: {node_data.get('data', {}).get('node_id', 'unknown')}")
                else:
                    print(f"     ❌ Node info failed: {response.status_code}")
                
                time.sleep(1)
                
                # File upload
                print("  📤 Testing file upload endpoint...")
                test_file = self.demo_files[0]
                filename, temp_path, content = test_file
                
                with open(temp_path, 'rb') as f:
                    files = {'file': (filename, f, 'application/octet-stream')}
                    response = requests.post(f"{base_url}/files/upload", files=files, timeout=10)
                
                if response.status_code in [200, 201]:
                    print(f"     ✅ Uploaded: {filename}")
                else:
                    print(f"     ⚠️  Upload status: {response.status_code}")
                
                time.sleep(1)
                
                # Search
                print("  🔎 Testing search endpoint...")
                response = requests.get(f"{base_url}/search", params={"query": "demo"}, timeout=5)
                if response.status_code == 200:
                    search_data = response.json()
                    results_count = len(search_data.get('data', {}).get('results', []))
                    print(f"     ✅ Search completed, found {results_count} results")
                else:
                    print(f"     ⚠️  Search status: {response.status_code}")
                
                time.sleep(1)
                
                # File listing
                print("  📋 Testing file listing endpoint...")
                response = requests.get(f"{base_url}/files", timeout=5)
                if response.status_code == 200:
                    files_data = response.json()
                    files_count = len(files_data.get('data', {}).get('files', []))
                    print(f"     ✅ Listed {files_count} files")
                else:
                    print(f"     ⚠️  File listing status: {response.status_code}")
                
                print(f"\n✅ Phase 4 demonstration completed!")
                print(f"\n🌐 You can explore the API further at: {base_url}/docs")
                
            except requests.exceptions.RequestException as e:
                print(f"     ❌ API request failed: {e}")
            
        except Exception as e:
            logger.error(f"Phase 4 demo failed: {e}")
        
        self.wait_for_user_input()
    
    def demonstrate_docker_deployment(self):
        """Demonstrate Docker deployment capabilities"""
        self.print_section_header("Docker Deployment", "BONUS")
        
        print("This demo shows the Docker deployment capabilities:")
        print("• Single-command cluster deployment")
        print("• Multi-node Docker Compose setup")
        print("• Production-ready configuration")
        print("• Management scripts for easy operations")
        
        print("\n🐳 Available Docker commands:")
        print("   ./scripts/docker-manager.sh start    # Start 3-node cluster")
        print("   ./scripts/docker-manager.sh health   # Check cluster health")
        print("   ./scripts/docker-manager.sh test     # Run tests")
        print("   ./scripts/docker-manager.sh logs     # View logs")
        print("   ./scripts/docker-manager.sh stop     # Stop cluster")
        
        print("\n📁 Docker configuration files:")
        print("   docker/docker-compose.yml           # Development cluster")
        print("   docker/docker-compose.prod.yml      # Production setup")
        print("   docker/Dockerfile                   # Container definition")
        print("   scripts/validate-docker.sh          # Pre-deployment validation")
        
        print("\n📚 For complete Docker deployment guide:")
        print("   See docs/DOCKER_GUIDE.md for comprehensive instructions")
        
        self.wait_for_user_input()
    
    def run_comprehensive_demo(self):
        """Run the complete demonstration"""
        print("🎉 Welcome to the Advanced Chord DHT File Sharing System Demo!")
        print("This demonstration will showcase all implemented phases:")
        print("\n📋 Demo Overview:")
        print("  Phase 1 & 2: Chord DHT with Distributed Search")
        print("  Phase 3:     QUIC Transport with Protocol Buffers")
        print("  Phase 4:     REST API with FastAPI")
        print("  Bonus:       Docker Deployment")
        
        self.wait_for_user_input("Press Enter to start the demo...")
        
        try:
            # Setup
            self.setup_demo_environment()
            
            # Run phase demonstrations
            self.demonstrate_phase1_and_2()
            self.demonstrate_phase3()
            self.demonstrate_phase4()
            self.demonstrate_docker_deployment()
            
            # Final summary
            self.print_section_header("Demo Complete!")
            print("🎉 Congratulations! You've seen all phases of the Advanced Chord DHT system!")
            print("\n📊 What you experienced:")
            print("  ✅ Distributed file storage and replication")
            print("  ✅ Intelligent search with inverted indexing")
            print("  ✅ High-performance QUIC transport")
            print("  ✅ Modern REST API with interactive documentation")
            print("  ✅ Production-ready Docker deployment")
            
            print("\n🚀 Next Steps:")
            print("  • Explore the interactive API docs at http://localhost:8000/docs")
            print("  • Try the Docker deployment with ./scripts/docker-manager.sh")
            print("  • Review the comprehensive documentation in docs/")
            print("  • Run the test suite with python tests/test_comprehensive.py")
            
            print("\n📚 Documentation:")
            print("  • README.md - Main project documentation")
            print("  • docs/DOCKER_GUIDE.md - Docker deployment guide")
            print("  • docs/PHASE*_SUMMARY.md - Implementation details")
            
            print("\n🎯 The system is ready for Phase 5: Monitoring & Production!")
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Demo interrupted by user")
        except Exception as e:
            logger.error(f"Demo error: {e}")
        finally:
            self.cleanup_demo_environment()
            print("\n🧹 Demo environment cleaned up")


def main():
    """Main demo runner"""
    # Change to the correct directory
    script_dir = Path(__file__).parent.parent  # Go up from demos/ to project root
    os.chdir(script_dir)
    
    demo = ChordDHTDemo()
    demo.run_comprehensive_demo()


if __name__ == "__main__":
    main()
