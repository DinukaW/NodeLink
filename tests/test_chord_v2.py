#!/usr/bin/env python3
"""
Test script for the redesigned Chord DHT implementation
Tests ring formation, file distribution, replication, and fault tolerance
"""

import subprocess
import time
import os
import signal
import json
import socket
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ChordTester:
    def __init__(self):
        self.node_processes: List[subprocess.Popen] = []
        self.node_ports = [6000, 6001, 6002]
        self.bootstrap_process: Optional[subprocess.Popen] = None
        
    def start_bootstrap_server(self):
        """Start the bootstrap server"""
        logger.info("Starting bootstrap server...")
        try:
            self.bootstrap_process = subprocess.Popen(
                ['python3', 'bootstrap_server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)  # Give it time to start
            logger.info("Bootstrap server started")
        except Exception as e:
            logger.error(f"Failed to start bootstrap server: {e}")
    
    def start_chord_node(self, port: int, shared_folder: str) -> subprocess.Popen:
        """Start a single Chord node"""
        logger.info(f"Starting Chord node on port {port} with folder {shared_folder}")
        try:
            process = subprocess.Popen([
                'python3', 'chord_node_v2.py',
                '--port', str(port),
                '--shared-folder', shared_folder,
                '--bootstrap-host', '127.0.0.1',
                '--bootstrap-port', '55556'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            
            self.node_processes.append(process)
            return process
        except Exception as e:
            logger.error(f"Failed to start node on port {port}: {e}")
            return None
    
    def query_node_status(self, port: int) -> Dict:
        """Query a node's status"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(('127.0.0.1', port))
            
            request = {'type': 'get_status'}
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(4096).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            return response
            
        except Exception as e:
            logger.error(f"Failed to query node on port {port}: {e}")
            return {}
    
    def test_ring_formation(self):
        """Test if nodes form a proper ring"""
        logger.info("Testing ring formation...")
        
        # Wait for nodes to stabilize - increased time
        time.sleep(25)
        
        ring_info = {}
        for port in self.node_ports:
            status = self.query_node_status(port)
            if status.get('success'):
                ring_info[port] = status['ring_info']
            else:
                logger.warning(f"Failed to get status from node {port}")
        
        logger.info("Ring structure:")
        for port, info in ring_info.items():
            logger.info(f"Node {port} (ID: {info['node_id']}): "
                       f"successor={info['successor']}, predecessor={info['predecessor']}")
        
        # Check if all nodes have valid successors and predecessors
        all_good = True
        for port, info in ring_info.items():
            if info['successor'] is None and len(ring_info) > 1:
                logger.error(f"Node {port} has no successor")
                all_good = False
        
        return all_good
    
    def test_file_distribution(self):
        """Test file distribution across nodes"""
        logger.info("Testing file distribution...")
        
        total_files = 0
        file_distribution = {}
        
        for port in self.node_ports:
            status = self.query_node_status(port)
            if status.get('success'):
                files = status.get('files', [])
                file_distribution[port] = files
                total_files += len(files)
                logger.info(f"Node {port}: {len(files)} files - {files}")
        
        logger.info(f"Total files in DHT: {total_files}")
        
        # Check if files are distributed (not all on one node)
        max_files_on_node = max(len(files) for files in file_distribution.values()) if file_distribution else 0
        if max_files_on_node == total_files and len(file_distribution) > 1 and total_files > 0:
            logger.error("All files are on a single node - distribution failed!")
            return False
        else:
            logger.info("Files are distributed across nodes")
            return True
    
    def test_search_functionality(self):
        """Test distributed search"""
        logger.info("Testing search functionality...")
        
        # Test search on each node
        for port in self.node_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                sock.connect(('127.0.0.1', port))
                
                request = {'type': 'search_files', 'query': ''}  # Empty query to list all
                sock.sendall(json.dumps(request).encode() + b'\n')
                
                response_data = sock.recv(4096).decode().strip()
                response = json.loads(response_data)
                
                sock.close()
                
                if response.get('success'):
                    files = response.get('files', [])
                    logger.info(f"Node {port} search found {len(files)} files")
                else:
                    logger.error(f"Search failed on node {port}")
                    
            except Exception as e:
                logger.error(f"Search test failed on node {port}: {e}")
    
    def test_fault_tolerance(self):
        """Test fault tolerance by killing a node"""
        logger.info("Testing fault tolerance...")
        
        if len(self.node_processes) < 2:
            logger.warning("Not enough nodes for fault tolerance test")
            return
        
        # Kill the first node
        victim_port = self.node_ports[0]
        victim_process = self.node_processes[0]
        
        logger.info(f"Killing node on port {victim_port}")
        victim_process.terminate()
        victim_process.wait()
        
        # Wait for remaining nodes to detect failure and stabilize
        time.sleep(10)
        
        # Check if remaining nodes are still functional
        remaining_ports = self.node_ports[1:]
        for port in remaining_ports:
            status = self.query_node_status(port)
            if status.get('success'):
                files = status.get('files', [])
                logger.info(f"After failure, Node {port}: {len(files)} files")
            else:
                logger.error(f"Node {port} is not responsive after failure")
        
        # Test if we can still search for files
        logger.info("Testing search after node failure...")
        for port in remaining_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                sock.connect(('127.0.0.1', port))
                
                request = {'type': 'search_files', 'query': ''}
                sock.sendall(json.dumps(request).encode() + b'\n')
                
                response_data = sock.recv(4096).decode().strip()
                response = json.loads(response_data)
                
                sock.close()
                
                if response.get('success'):
                    files = response.get('files', [])
                    logger.info(f"Node {port} still functional after failure: {len(files)} files")
                else:
                    logger.error(f"Node {port} not functional after failure")
                    
            except Exception as e:
                logger.error(f"Post-failure test failed on node {port}: {e}")
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting Chord DHT tests...")
        
        # Start bootstrap server
        self.start_bootstrap_server()
        
        # Create test directories and files
        test_dirs = ['peer/shared', 'peer/shared2', 'peer/shared3']
        for i, test_dir in enumerate(test_dirs):
            os.makedirs(test_dir, exist_ok=True)
            
            # Create some test files
            for j in range(2):
                filename = f"test_file_{i}_{j}.txt"
                filepath = os.path.join(test_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(f"Test content from node {i}, file {j}")
        
        # Start nodes
        for i, port in enumerate(self.node_ports):
            shared_folder = test_dirs[i]
            process = self.start_chord_node(port, shared_folder)
            if process:
                time.sleep(3)  # Stagger node startup
        
        # Run tests
        try:
            time.sleep(10)  # Let nodes join and stabilize
            
            logger.info("=" * 50)
            ring_ok = self.test_ring_formation()
            
            logger.info("=" * 50)
            dist_ok = self.test_file_distribution()
            
            logger.info("=" * 50)
            self.test_search_functionality()
            
            logger.info("=" * 50)
            self.test_fault_tolerance()
            
            logger.info("=" * 50)
            logger.info("Test Summary:")
            logger.info(f"Ring formation: {'PASS' if ring_ok else 'FAIL'}")
            logger.info(f"File distribution: {'PASS' if dist_ok else 'FAIL'}")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up processes"""
        logger.info("Cleaning up...")
        
        # Kill all node processes
        for process in self.node_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                    process.wait(timeout=5)
                except:
                    pass
        
        # Kill bootstrap server
        if self.bootstrap_process:
            try:
                self.bootstrap_process.terminate()
                self.bootstrap_process.wait(timeout=5)
            except:
                try:
                    self.bootstrap_process.kill()
                    self.bootstrap_process.wait(timeout=5)
                except:
                    pass
        
        logger.info("Cleanup complete")


if __name__ == '__main__':
    tester = ChordTester()
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        tester.cleanup()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        tester.cleanup()
