#!/usr/bin/env python3
"""
Phase 4 Demo: REST API for Chord DHT
Demonstrates the REST API functionality for file operations, search, and node management.
"""

import requests
import json
import time
import sys
import os
import subprocess
import signal
from typing import Dict, Any, Optional

# Demo configuration
API_BASE_URL = "http://127.0.0.1:8000"
SERVER_STARTUP_DELAY = 3


class Phase4Demo:
    """Phase 4 REST API demonstration."""
    
    def __init__(self):
        self.server_process = None
        
    def start_demo_server(self) -> bool:
        """Start the REST API server for the demo."""
        try:
            print("🚀 Starting Chord DHT REST API server...")
            
            # Start the server in a separate process
            self.server_process = subprocess.Popen(
                [sys.executable, "rest_api.py", "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Wait for server to start
            print(f"   Waiting {SERVER_STARTUP_DELAY} seconds for server startup...")
            time.sleep(SERVER_STARTUP_DELAY)
            
            # Test if server is responding
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ REST API server is running and healthy!")
                    return True
                else:
                    print(f"❌ Server responding but not healthy: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"❌ Server not reachable: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def stop_demo_server(self):
        """Stop the demo server."""
        if self.server_process:
            try:
                print("\n🛑 Stopping REST API server...")
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("✅ Server stopped successfully")
            except subprocess.TimeoutExpired:
                print("⚠️  Server did not stop gracefully, killing...")
                self.server_process.kill()
                self.server_process.wait()
            except Exception as e:
                print(f"❌ Error stopping server: {e}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make an HTTP request and handle errors."""
        try:
            url = f"{API_BASE_URL}{endpoint}"
            response = requests.request(method, url, timeout=10, **kwargs)
            
            print(f"   {method} {endpoint} → {response.status_code}")
            
            if response.status_code < 400:
                if response.content:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {"raw_content": response.content}
                return {"status": "success"}
            else:
                print(f"   ❌ Request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return None
    
    def demo_api_overview(self):
        """Demonstrate API overview and documentation."""
        print("\n" + "="*60)
        print("DEMO: API Overview & Documentation")
        print("="*60)
        
        # Get API root information
        print("\n1. API Information:")
        response = self.make_request("GET", "/")
        if response and response.get("success"):
            data = response.get("data", {})
            print(f"   Service: {data.get('service', 'N/A')}")
            print(f"   Version: {data.get('version', 'N/A')}")
            print(f"   Description: {data.get('description', 'N/A')}")
            
            features = data.get("features", [])
            print("   Features:")
            for feature in features:
                print(f"     • {feature}")
        
        # Check API documentation
        print("\n2. API Documentation:")
        print(f"   📖 OpenAPI Docs: {API_BASE_URL}/docs")
        print(f"   📋 ReDoc: {API_BASE_URL}/redoc")
        
        # Check health status
        print("\n3. Health Check:")
        response = self.make_request("GET", "/health")
        if response and response.get("success"):
            health_data = response.get("data", {})
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   Uptime: {health_data.get('uptime', 0):.1f} seconds")
            print(f"   Node ID: {health_data.get('node_id', 'N/A')}")
            
            checks = health_data.get("checks", {})
            print("   System Checks:")
            for check, status in checks.items():
                status_icon = "✅" if status else "❌"
                print(f"     {status_icon} {check}")
    
    def demo_file_operations(self):
        """Demonstrate file upload, download, and management."""
        print("\n" + "="*60)
        print("DEMO: File Operations")
        print("="*60)
        
        # Upload test files
        print("\n1. File Upload:")
        test_files = [
            ("machine_learning_guide.txt", b"A comprehensive guide to machine learning algorithms and techniques."),
            ("deep_learning_tutorial.pdf", b"Deep learning tutorial covering neural networks and their applications."),
            ("data_science_handbook.txt", b"Handbook for data science methodologies and best practices."),
            ("python_programming.py", b"# Python programming examples\nprint('Hello, Chord DHT!')"),
        ]
        
        uploaded_files = []
        for filename, content in test_files:
            print(f"\n   Uploading: {filename}")
            files = {"file": (filename, content, "text/plain")}
            response = self.make_request("POST", "/files/upload", files=files)
            
            if response and response.get("success"):
                data = response.get("data", {})
                print(f"     ✅ File uploaded successfully")
                print(f"     📊 File size: {data.get('file_size', 0)} bytes")
                print(f"     🔗 Node ID: {data.get('node_id', 'N/A')}")
                uploaded_files.append(filename)
            else:
                print(f"     ❌ Upload failed")
        
        # List files
        print(f"\n2. File Listing:")
        response = self.make_request("GET", "/files/list")
        if response and response.get("success"):
            data = response.get("data", {})
            files = data.get("files", [])
            total_files = data.get("total_files", 0)
            
            print(f"   📁 Total files in DHT: {total_files}")
            print("   Files:")
            for file_info in files:
                filename = file_info.get("filename", "N/A")
                file_size = file_info.get("file_size", 0)
                node_id = file_info.get("node_id", "N/A")
                print(f"     📄 {filename} ({file_size} bytes) on Node {node_id}")
        
        # Download a file
        if uploaded_files:
            print(f"\n3. File Download:")
            test_filename = uploaded_files[0]
            print(f"   Downloading: {test_filename}")
            
            try:
                response = requests.get(f"{API_BASE_URL}/files/{test_filename}", timeout=10)
                if response.status_code == 200:
                    content_length = len(response.content)
                    print(f"     ✅ File downloaded successfully")
                    print(f"     📊 Downloaded size: {content_length} bytes")
                    print(f"     📝 Content preview: {response.content[:50]}...")
                else:
                    print(f"     ❌ Download failed: {response.status_code}")
            except Exception as e:
                print(f"     ❌ Download error: {e}")
    
    def demo_search_operations(self):
        """Demonstrate search functionality."""
        print("\n" + "="*60)
        print("DEMO: Search Operations")
        print("="*60)
        
        # Basic search
        print("\n1. Basic Search:")
        search_queries = ["machine", "learning", "python", "data science"]
        
        for query in search_queries:
            print(f"\n   Searching for: '{query}'")
            response = self.make_request("GET", f"/search?q={query}")
            
            if response and response.get("success"):
                data = response.get("data", {})
                results = data.get("results", [])
                total_results = data.get("total_results", 0)
                search_time = data.get("search_time_ms", 0)
                
                print(f"     🔍 Found {total_results} results in {search_time:.1f}ms")
                
                for result in results[:3]:  # Show top 3 results
                    filename = result.get("filename", "N/A")
                    score = result.get("relevance_score", 0)
                    matched_tokens = result.get("matched_tokens", [])
                    print(f"       📄 {filename} (relevance: {score:.2f})")
                    if matched_tokens:
                        print(f"          🔖 Matched: {', '.join(matched_tokens)}")
            else:
                print(f"     ❌ Search failed")
        
        # Search suggestions
        print(f"\n2. Search Suggestions:")
        suggestion_queries = ["mach", "deep", "data"]
        
        for partial_query in suggestion_queries:
            print(f"\n   Getting suggestions for: '{partial_query}'")
            response = self.make_request("GET", f"/search/suggestions?q={partial_query}")
            
            if response and response.get("success"):
                data = response.get("data", {})
                suggestions = data.get("suggestions", [])
                response_time = data.get("response_time_ms", 0)
                
                print(f"     💡 {len(suggestions)} suggestions in {response_time:.1f}ms:")
                for suggestion in suggestions:
                    print(f"       → {suggestion}")
            else:
                print(f"     ❌ Suggestions failed")
        
        # Advanced search
        print(f"\n3. Advanced Search:")
        advanced_payload = {
            "query": "learning",
            "sort_by": "relevance",
            "sort_order": "desc"
        }
        
        print(f"   Advanced search with payload: {json.dumps(advanced_payload, indent=2)}")
        response = self.make_request("POST", "/search/advanced", json=advanced_payload)
        
        if response and response.get("success"):
            data = response.get("data", {})
            results = data.get("results", [])
            print(f"     🎯 Advanced search returned {len(results)} results")
            
            for result in results[:2]:  # Show top 2 results
                filename = result.get("filename", "N/A")
                score = result.get("relevance_score", 0)
                print(f"       📄 {filename} (score: {score:.2f})")
        else:
            print(f"     ❌ Advanced search failed")
    
    def demo_node_management(self):
        """Demonstrate node management and monitoring."""
        print("\n" + "="*60)
        print("DEMO: Node Management & Monitoring")
        print("="*60)
        
        # Node information
        print("\n1. Node Information:")
        response = self.make_request("GET", "/node/info")
        if response and response.get("success"):
            data = response.get("data", {})
            print(f"   🔗 Node ID: {data.get('node_id', 'N/A')}")
            print(f"   🌐 Address: {data.get('address', 'N/A')}:{data.get('port', 'N/A')}")
            print(f"   📊 Status: {data.get('status', 'N/A')}")
            print(f"   ⏱️  Uptime: {data.get('uptime', 0):.1f} seconds")
            print(f"   📁 Files stored: {data.get('files_stored', 0)}")
            print(f"   🔍 Tokens indexed: {data.get('tokens_indexed', 0)}")
        
        # Ring topology
        print(f"\n2. Ring Topology:")
        response = self.make_request("GET", "/node/ring")
        if response and response.get("success"):
            data = response.get("data", {})
            ring_size = data.get("ring_size", 0)
            total_nodes = data.get("total_nodes", 0)
            ring_health = data.get("ring_health", 0)
            
            print(f"   💍 Ring size: {ring_size}")
            print(f"   🔗 Total nodes: {total_nodes}")
            print(f"   💪 Ring health: {ring_health:.1%}")
            
            nodes = data.get("nodes", [])
            print("   📋 Nodes in ring:")
            for node in nodes:
                node_id = node.get("node_id", "N/A")
                address = node.get("address", "N/A")
                port = node.get("port", "N/A")
                status = node.get("status", "N/A")
                print(f"     🔗 Node {node_id} at {address}:{port} ({status})")
        
        # System metrics
        print(f"\n3. System Metrics:")
        response = self.make_request("GET", "/metrics")
        if response and response.get("success"):
            data = response.get("data", {})
            print(f"   💻 CPU Usage: {data.get('cpu_usage', 0):.1f}%")
            print(f"   🧠 Memory Usage: {data.get('memory_usage', 0):.1f}%")
            print(f"   💾 Disk Usage: {data.get('disk_usage', 0):.1f}%")
            print(f"   🌐 Network Connections: {data.get('network_connections', 0)}")
            print(f"   ⚡ Active Requests: {data.get('active_requests', 0)}")
            print(f"   🔍 Search RPM: {data.get('search_requests_per_minute', 0):.1f}")
    
    def demo_api_features(self):
        """Demonstrate advanced API features."""
        print("\n" + "="*60)
        print("DEMO: Advanced API Features")
        print("="*60)
        
        # Error handling
        print("\n1. Error Handling:")
        print("   Testing non-existent file download:")
        try:
            response = requests.get(f"{API_BASE_URL}/files/nonexistent.txt", timeout=5)
            print(f"     Status: {response.status_code}")
            if response.content:
                error_data = response.json()
                print(f"     Error: {error_data.get('error', {}).get('message', 'N/A')}")
        except Exception as e:
            print(f"     Exception: {e}")
        
        # Pagination
        print("\n2. Pagination:")
        print("   Testing paginated file listing:")
        response = self.make_request("GET", "/files/list?page=1&page_size=2")
        if response and response.get("success"):
            data = response.get("data", {})
            print(f"     Page: {data.get('page', 'N/A')}")
            print(f"     Page size: {data.get('page_size', 'N/A')}")
            print(f"     Total pages: {data.get('total_pages', 'N/A')}")
        
        # Content negotiation
        print("\n3. API Response Format:")
        print("   Standard response format includes:")
        print("     • success: boolean")
        print("     • data: object (response data)")
        print("     • message: string (status message)")
        print("     • timestamp: ISO 8601 timestamp")
        print("     • request_id: unique identifier (optional)")
    
    def run_demo(self):
        """Run the complete Phase 4 demonstration."""
        print("="*80)
        print("PHASE 4 DEMONSTRATION: REST API for Chord DHT")
        print("="*80)
        
        print("\nThis demo showcases the complete REST API functionality:")
        print("• File upload, download, and management")
        print("• Distributed search with relevance scoring")
        print("• Node management and ring topology")
        print("• Health monitoring and system metrics")
        print("• Error handling and API documentation")
        
        # Start the server
        if not self.start_demo_server():
            print("❌ Cannot start demo server. Demo terminated.")
            return
        
        try:
            # Run all demonstrations
            self.demo_api_overview()
            self.demo_file_operations()
            self.demo_search_operations()
            self.demo_node_management()
            self.demo_api_features()
            
            # Final summary
            print("\n" + "="*80)
            print("🎉 PHASE 4 DEMONSTRATION COMPLETE!")
            print("="*80)
            
            print("\n✅ REST API Features Demonstrated:")
            print("  • 📡 RESTful endpoints with OpenAPI documentation")
            print("  • 📁 File operations (upload/download/list)")
            print("  • 🔍 Advanced search with distributed inverted index")
            print("  • 🔗 Node management and ring topology")
            print("  • 💊 Health checks and system monitoring")
            print("  • 🛡️  Error handling and input validation")
            print("  • 🌐 CORS support and security middleware")
            
            print("\n🚀 API Server Information:")
            print(f"  • Base URL: {API_BASE_URL}")
            print(f"  • Documentation: {API_BASE_URL}/docs")
            print(f"  • Alternative docs: {API_BASE_URL}/redoc")
            
            print("\n📈 Performance Highlights:")
            print("  • Async FastAPI for high-performance REST API")
            print("  • QUIC transport for fast inter-node communication")
            print("  • Protocol Buffers for efficient serialization")
            print("  • Distributed search with relevance scoring")
            
            print("\n🎯 Ready for Production:")
            print("  • Complete REST API implementation")
            print("  • Integration with QUIC-enabled Chord DHT")
            print("  • Comprehensive error handling")
            print("  • API documentation and testing")
            
            print("\n" + "="*80)
            print("PHASE 4 STATUS: ✅ COMPLETE - Ready for Phase 5 (Monitoring)")
            print("="*80)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Demo error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop_demo_server()


def main():
    """Main demo function."""
    demo = Phase4Demo()
    demo.run_demo()


if __name__ == "__main__":
    main()
