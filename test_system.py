#!/usr/bin/env python3
"""
Test script for the Chord DHT system with bootstrap server
"""

import subprocess
import time
import os
import signal
import sys

def create_test_files():
    """Create test directories and files"""
    dirs = ["localhost_8001", "localhost_8002", "localhost_8003"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        with open(f"{dir_name}/test_{dir_name.split('_')[1]}.txt", "w") as f:
            f.write(f"Test content from {dir_name}")

def run_test():
    """Run a basic test of the system"""
    processes = []
    
    try:
        print("=== Chord DHT Bootstrap Server Test ===")
        
        # Create test files
        print("1. Creating test files...")
        create_test_files()
        
        # Start bootstrap server
        print("2. Starting bootstrap server...")
        bootstrap_proc = subprocess.Popen([
            sys.executable, "bootstrap_server.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(bootstrap_proc)
        time.sleep(2)
        
        # Test if bootstrap server is running
        if bootstrap_proc.poll() is not None:
            print("Bootstrap server failed to start!")
            return False
            
        print("   Bootstrap server started successfully")
        
        # Create nodes (they will join automatically)
        print("3. Creating and joining nodes...")
        
        # We'll just test the joining process programmatically
        from chord import Node
        
        # Create nodes
        node1 = Node("localhost", 8001)
        time.sleep(1)
        result1 = node1.join(None)
        time.sleep(1)
        
        node2 = Node("localhost", 8002) 
        time.sleep(1)
        result2 = node2.join(None)
        time.sleep(1)
        
        node3 = Node("localhost", 8003)
        time.sleep(1)
        result3 = node3.join(None)
        time.sleep(2)
        
        if not all([result1, result2, result3]):
            print("   Some nodes failed to join!")
            return False
            
        print("   All nodes joined successfully")
        
        # Test network status
        print("4. Testing network connectivity...")
        print(f"   Node 1: key={node1.key}, succ={node1.successor}, pred={node1.predecessor}")
        print(f"   Node 2: key={node2.key}, succ={node2.successor}, pred={node2.predecessor}")  
        print(f"   Node 3: key={node3.key}, succ={node3.successor}, pred={node3.predecessor}")
        
        # Clean shutdown
        print("5. Cleaning up...")
        node1.leave()
        time.sleep(1)
        node2.leave()
        time.sleep(1)
        node3.leave()
        time.sleep(1)
        
        print("=== Test completed successfully! ===")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False
        
    finally:
        # Clean up processes
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
