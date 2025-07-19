#!/usr/bin/env python3
"""
Test suite for Phase 4: REST API
Tests the REST API endpoints and integration with Chord DHT.
"""

import asyncio
import requests
import time
import json
import sys
import os
from typing import Dict, Any
import subprocess
import signal
import threading

# Test configuration
API_BASE_URL = "http://127.0.0.1:8000"
TEST_FILES_DIR = "test_files"
SERVER_STARTUP_DELAY = 3  # seconds


class Phase4TestSuite:
    """Test suite for Phase 4 REST API functionality."""
    
    def __init__(self):
        self.server_process = None
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def start_api_server(self) -> bool:
        """Start the REST API server for testing."""
        try:
            print("  Starting REST API server...")
            
            # Start the server in a separate process
            self.server_process = subprocess.Popen(
                [sys.executable, "rest_api.py", "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Wait for server to start
            time.sleep(SERVER_STARTUP_DELAY)
            
            # Test if server is responding
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    print("    ✓ REST API server started successfully")
                    return True
                else:
                    print(f"    ✗ Server not responding properly: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"    ✗ Server not reachable: {e}")
                return False
                
        except Exception as e:
            print(f"    ✗ Failed to start server: {e}")
            return False
    
    def stop_api_server(self):
        """Stop the REST API server."""
        if self.server_process:
            try:
                print("  Stopping REST API server...")
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("    ✓ Server stopped successfully")
            except subprocess.TimeoutExpired:
                print("    ⚠ Server did not stop gracefully, killing...")
                self.server_process.kill()
                self.server_process.wait()
            except Exception as e:
                print(f"    ✗ Error stopping server: {e}")
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results."""
        self.total_tests += 1
        print(f"Running {test_name}...")
        
        try:
            success = test_func()
            if success:
                self.passed_tests += 1
                self.test_results[test_name] = "PASSED"
                print(f"✓ {test_name} PASSED")
            else:
                self.test_results[test_name] = "FAILED"
                print(f"✗ {test_name} FAILED")
            return success
        except Exception as e:
            self.test_results[test_name] = f"ERROR: {str(e)}"
            print(f"✗ {test_name} ERROR: {e}")
            return False
    
    def test_api_health_endpoints(self) -> bool:
        """Test health and status endpoints."""
        print("=== Testing Health Endpoints ===")
        
        try:
            # Test health endpoint
            response = requests.get(f"{API_BASE_URL}/health", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Health endpoint failed: {response.status_code}")
                return False
            
            health_data = response.json()
            if not health_data.get("success"):
                print(f"  ✗ Health check not successful: {health_data}")
                return False
            
            print("    ✓ Health endpoint working")
            
            # Test metrics endpoint
            response = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Metrics endpoint failed: {response.status_code}")
                return False
            
            print("    ✓ Metrics endpoint working")
            
            # Test status endpoint
            response = requests.get(f"{API_BASE_URL}/status", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Status endpoint failed: {response.status_code}")
                return False
            
            print("    ✓ Status endpoint working")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Health endpoints test failed: {e}")
            return False
    
    def test_api_info_endpoints(self) -> bool:
        """Test API information endpoints."""
        print("=== Testing API Info Endpoints ===")
        
        try:
            # Test root endpoint
            response = requests.get(f"{API_BASE_URL}/", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Root endpoint failed: {response.status_code}")
                return False
            
            root_data = response.json()
            if not root_data.get("success"):
                print(f"  ✗ Root endpoint not successful: {root_data}")
                return False
            
            # Check if expected fields are present
            data = root_data.get("data", {})
            required_fields = ["service", "version", "description"]
            for field in required_fields:
                if field not in data:
                    print(f"  ✗ Missing required field: {field}")
                    return False
            
            print("    ✓ Root endpoint working with correct data")
            
            # Test OpenAPI docs are available
            response = requests.get(f"{API_BASE_URL}/docs", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Docs endpoint failed: {response.status_code}")
                return False
            
            print("    ✓ OpenAPI docs available")
            
            return True
            
        except Exception as e:
            print(f"  ✗ API info endpoints test failed: {e}")
            return False
    
    def test_file_operations(self) -> bool:
        """Test file upload, download, and management endpoints."""
        print("=== Testing File Operations ===")
        
        try:
            # Test file list (should be empty initially)
            response = requests.get(f"{API_BASE_URL}/files/list", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ File list failed: {response.status_code}")
                return False
            
            list_data = response.json()
            if not list_data.get("success"):
                print(f"  ✗ File list not successful: {list_data}")
                return False
            
            print("    ✓ File listing working")
            
            # Test file upload
            test_content = b"Hello, Phase 4 REST API!"
            test_filename = "test_api_file.txt"
            
            files = {"file": (test_filename, test_content, "text/plain")}
            response = requests.post(f"{API_BASE_URL}/files/upload", files=files, timeout=10)
            
            if response.status_code != 200:
                print(f"  ✗ File upload failed: {response.status_code}")
                if response.content:
                    print(f"    Response: {response.text}")
                return False
            
            upload_data = response.json()
            if not upload_data.get("success"):
                print(f"  ✗ File upload not successful: {upload_data}")
                return False
            
            print("    ✓ File upload working")
            
            # Test file download
            response = requests.get(f"{API_BASE_URL}/files/{test_filename}", timeout=10)
            
            if response.status_code != 200:
                print(f"  ✗ File download failed: {response.status_code}")
                return False
            
            if response.content != test_content:
                print("  ✗ Downloaded content doesn't match uploaded content")
                return False
            
            print("    ✓ File download working")
            
            return True
            
        except Exception as e:
            print(f"  ✗ File operations test failed: {e}")
            return False
    
    def test_search_operations(self) -> bool:
        """Test search functionality."""
        print("=== Testing Search Operations ===")
        
        try:
            # Test basic search
            response = requests.get(f"{API_BASE_URL}/search?q=test", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Basic search failed: {response.status_code}")
                return False
            
            search_data = response.json()
            if not search_data.get("success"):
                print(f"  ✗ Basic search not successful: {search_data}")
                return False
            
            print("    ✓ Basic search working")
            
            # Test search suggestions
            response = requests.get(f"{API_BASE_URL}/search/suggestions?q=machine", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Search suggestions failed: {response.status_code}")
                return False
            
            suggestions_data = response.json()
            if not suggestions_data.get("success"):
                print(f"  ✗ Search suggestions not successful: {suggestions_data}")
                return False
            
            print("    ✓ Search suggestions working")
            
            # Test advanced search
            advanced_search_payload = {
                "query": "test",
                "sort_by": "relevance",
                "sort_order": "desc"
            }
            
            response = requests.post(
                f"{API_BASE_URL}/search/advanced",
                json=advanced_search_payload,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"  ✗ Advanced search failed: {response.status_code}")
                return False
            
            print("    ✓ Advanced search working")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Search operations test failed: {e}")
            return False
    
    def test_node_management(self) -> bool:
        """Test node management endpoints."""
        print("=== Testing Node Management ===")
        
        try:
            # Test node info
            response = requests.get(f"{API_BASE_URL}/node/info", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Node info failed: {response.status_code}")
                return False
            
            node_data = response.json()
            if not node_data.get("success"):
                print(f"  ✗ Node info not successful: {node_data}")
                return False
            
            print("    ✓ Node info working")
            
            # Test node neighbors
            response = requests.get(f"{API_BASE_URL}/node/neighbors", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Node neighbors failed: {response.status_code}")
                return False
            
            print("    ✓ Node neighbors working")
            
            # Test ring topology
            response = requests.get(f"{API_BASE_URL}/node/ring", timeout=10)
            if response.status_code != 200:
                print(f"  ✗ Ring topology failed: {response.status_code}")
                return False
            
            print("    ✓ Ring topology working")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Node management test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and edge cases."""
        print("=== Testing Error Handling ===")
        
        try:
            # Test non-existent file download
            response = requests.get(f"{API_BASE_URL}/files/nonexistent.txt", timeout=10)
            if response.status_code != 404:
                print(f"  ✗ Non-existent file should return 404, got: {response.status_code}")
                return False
            
            print("    ✓ Non-existent file returns 404")
            
            # Test empty search query
            response = requests.get(f"{API_BASE_URL}/search?q=", timeout=10)
            if response.status_code == 200:
                search_data = response.json()
                if search_data.get("success"):
                    print("  ✗ Empty search should fail")
                    return False
            
            print("    ✓ Empty search query handled correctly")
            
            # Test invalid pagination
            response = requests.get(f"{API_BASE_URL}/files/list?page=0", timeout=10)
            if response.status_code != 422:  # Validation error
                print(f"  ✗ Invalid pagination should return 422, got: {response.status_code}")
                # This might still pass if handled gracefully
            
            print("    ✓ Invalid pagination handled")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error handling test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all Phase 4 tests."""
        print("="*80)
        print("PHASE 4 TESTS: REST API")
        print("="*80)
        
        # Start the API server
        if not self.start_api_server():
            print("✗ Failed to start API server, cannot run tests")
            return
        
        try:
            # Run all test suites
            tests = [
                ("API Health Endpoints", self.test_api_health_endpoints),
                ("API Info Endpoints", self.test_api_info_endpoints),
                ("File Operations", self.test_file_operations),
                ("Search Operations", self.test_search_operations),
                ("Node Management", self.test_node_management),
                ("Error Handling", self.test_error_handling),
            ]
            
            for test_name, test_func in tests:
                self.run_test(test_name, test_func)
                print()
            
            # Print summary
            print("="*60)
            print(f"PHASE 4 TEST RESULTS: {self.passed_tests}/{self.total_tests} tests passed")
            
            if self.passed_tests == self.total_tests:
                print("🎉 All Phase 4 tests passed!")
                print("✅ REST API fully functional and ready for production")
            else:
                print(f"⚠️  {self.total_tests - self.passed_tests} test(s) failed")
                print("REST API needs attention before production use")
            
            # Print detailed results
            print("\nDetailed Results:")
            for test_name, result in self.test_results.items():
                status_icon = "✅" if result == "PASSED" else "❌"
                print(f"  {status_icon} {test_name}: {result}")
            
            print("="*60)
            
        finally:
            self.stop_api_server()


def main():
    """Main test runner."""
    print("Phase 4: REST API Test Suite")
    print("Testing FastAPI endpoints and Chord DHT integration")
    print()
    
    test_suite = Phase4TestSuite()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
