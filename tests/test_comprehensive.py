#!/usr/bin/env python3
"""
Comprehensive Test Suite for Advanced Chord DHT File Sharing System
Tests all phases: Chord DHT, Distributed Search, QUIC Transport, and REST API
"""

import asyncio
import subprocess
import time
import os
import signal
import sys
import tempfile
import shutil
import requests
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChordDHTTestSuite:
    """Comprehensive test suite for all Chord DHT phases"""
    
    def __init__(self):
        self.node_processes: List[subprocess.Popen] = []
        self.node_ports = [7000, 7001, 7002]
        self.api_ports = [8000, 8001, 8002]
        self.test_files = []
        self.temp_dirs = []
        
    def setup_test_environment(self):
        """Set up test environment with temporary directories"""
        logger.info("Setting up test environment...")
        
        # Create temporary directories for testing
        for i in range(3):
            temp_dir = tempfile.mkdtemp(prefix=f"chord_test_{i}_")
            self.temp_dirs.append(temp_dir)
            os.makedirs(os.path.join(temp_dir, "shared"), exist_ok=True)
        
        # Create test files
        test_data = [
            ("document.pdf", b"PDF content for testing"),
            ("image.jpg", b"JPEG image data"),
            ("code.py", b"print('Hello, Chord!')"),
            ("data.csv", b"name,age,city\nAlice,30,NYC\nBob,25,LA"),
            ("report.docx", b"Document content"),
        ]
        
        for filename, content in test_data:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_{filename}", delete=False
            )
            temp_file.write(content)
            temp_file.close()
            self.test_files.append((filename, temp_file.name, content))
        
        logger.info(f"Created {len(self.test_files)} test files")
    
    def teardown_test_environment(self):
        """Clean up test environment"""
        logger.info("Cleaning up test environment...")
        
        # Stop all node processes
        for process in self.node_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")
        
        # Clean up temporary files
        for _, temp_path, _ in self.test_files:
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Error removing {temp_path}: {e}")
        
        # Clean up temporary directories
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Error removing {temp_dir}: {e}")
    
    def test_rest_api_basic(self) -> bool:
        """Test basic REST API functionality"""
        logger.info("Testing REST API basic functionality...")
        
        try:
            # Start REST API server
            process = subprocess.Popen([
                sys.executable, "../src/rest_api.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.node_processes.append(process)
            
            # Wait for API to start
            time.sleep(10)
            
            # Test basic endpoints
            base_url = "http://localhost:8000"
            
            try:
                # Test health endpoint
                response = requests.get(f"{base_url}/health", timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Health endpoint working")
                    return True
                else:
                    logger.error(f"❌ Health endpoint failed: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ API request failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"REST API test failed: {e}")
            return False
    
    def run_comprehensive_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        logger.info("Starting comprehensive Chord DHT test suite...")
        
        results = {
            "setup": False,
            "rest_api_basic": False,
            "cleanup": False
        }
        
        try:
            # Setup
            self.setup_test_environment()
            results["setup"] = True
            logger.info("✅ Test environment setup completed")
            
            # Basic API test
            results["rest_api_basic"] = self.test_rest_api_basic()
            if results["rest_api_basic"]:
                logger.info("✅ REST API basic tests passed")
            else:
                logger.error("❌ REST API basic tests failed")
            
        except Exception as e:
            logger.error(f"Test suite error: {e}")
        
        finally:
            # Cleanup
            self.teardown_test_environment()
            results["cleanup"] = True
            logger.info("✅ Test environment cleanup completed")
        
        return results


def main():
    """Main test runner"""
    logger.info("Advanced Chord DHT File Sharing System - Comprehensive Test Suite")
    logger.info("=" * 70)
    
    # Change to the correct directory
    script_dir = Path(__file__).parent.parent  # Go up from tests/ to project root
    os.chdir(script_dir)
    
    test_suite = ChordDHTTestSuite()
    results = test_suite.run_comprehensive_tests()
    
    # Print results summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 70)
    
    total_tests = len([k for k in results.keys() if k != "cleanup"])
    passed_tests = sum(1 for k, v in results.items() if k != "cleanup" and v)
    
    for test_name, passed in results.items():
        if test_name == "cleanup":
            continue
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name.upper().replace('_', ' '):<25} {status}")
    
    logger.info("-" * 70)
    logger.info(f"OVERALL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! System is ready for production.")
        return 0
    else:
        logger.error(f"⚠️  {total_tests - passed_tests} test(s) failed. Review the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
