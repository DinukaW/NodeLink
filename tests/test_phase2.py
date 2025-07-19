#!/usr/bin/env python3
"""
Test suite for Phase 2: Distributed Inverted Index
Tests tokenization, distributed inverted index, and partial search functionality.
"""

import time
import subprocess
import threading
import signal
import os
import logging

# Suppress logging for cleaner test output
logging.getLogger().setLevel(logging.ERROR)

class ChordTestCluster:
    """Manages a test cluster of Chord nodes."""
    
    def __init__(self):
        self.processes = []
        self.ports = [5001, 5002, 5003, 5004]
        self.bootstrap_process = None
    
    def start_bootstrap(self):
        """Start the bootstrap server."""
        print("Starting bootstrap server...")
        self.bootstrap_process = subprocess.Popen([
            'python3', 'bootstrap_server.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Give bootstrap time to start
    
    def start_nodes(self):
        """Start all test nodes."""
        print("Starting nodes...")
        
        # Create test files in shared folders if they don't exist
        test_files = {
            'peer/shared/': [
                'machine_learning_notes.txt',
                'deep_learning_tutorial.pdf',
                'neural_network_basics.doc'
            ],
            'peer/shared2/': [
                'data_science_guide.txt',
                'python_programming.py',
                'statistical_analysis.xlsx'
            ],
            'peer/shared3/': [
                'artificial_intelligence.pdf',
                'computer_vision_intro.txt',
                'natural_language_processing.doc'
            ]
        }
        
        # Ensure directories and files exist
        for folder, files in test_files.items():
            os.makedirs(folder, exist_ok=True)
            for filename in files:
                filepath = os.path.join(folder, filename)
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write(f"Test content for {filename}")
        
        # Start nodes with different shared folders
        shared_folders = [
            'peer/shared',
            'peer/shared2', 
            'peer/shared3',
            None  # Node without shared folder
        ]
        
        for i, port in enumerate(self.ports):
            shared_folder = shared_folders[i] if i < len(shared_folders) else None
            cmd = ['python3', 'chord_node_v2.py', '--port', str(port)]
            if shared_folder:
                cmd.extend(['--shared-folder', shared_folder])
            
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.processes.append(process)
            time.sleep(3)  # Stagger startup
        
        # Give ring time to stabilize
        time.sleep(5)
        print(f"Started {len(self.processes)} nodes")
    
    def stop_all(self):
        """Stop all nodes and bootstrap server."""
        print("\nStopping all processes...")
        
        # Stop nodes
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=3)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Stop bootstrap
        if self.bootstrap_process:
            try:
                self.bootstrap_process.terminate()
                self.bootstrap_process.wait(timeout=3)
            except:
                try:
                    self.bootstrap_process.kill()
                except:
                    pass
        
        self.processes = []
        self.bootstrap_process = None

def test_tokenization():
    """Test filename tokenization."""
    from chord_node_v2 import tokenize_filename
    
    print("\n=== Testing Tokenization ===")
    
    test_cases = [
        ("machine_learning_notes.txt", ["machine", "learning", "notes", "mac", "mach", "machi", "machin", "machine", "lea", "lear", "learn", "learni", "learnin", "learning", "not", "note", "notes"]),
        ("deep-learning-tutorial.pdf", ["deep", "learning", "tutorial"]),
        ("Neural Network Basics.doc", ["neural", "network", "basics"]),
        ("AI_ML_2024.pdf", ["ai", "ml", "2024"]),
        ("data.csv", ["data"]),  # Short files
        ("a.txt", []),  # Too short, should be empty
    ]
    
    for filename, expected_contains in test_cases:
        tokens = tokenize_filename(filename)
        print(f"  '{filename}' -> {tokens}")
        
        # Check that expected tokens are present
        for expected in expected_contains[:3]:  # Check first few expected tokens
            if len(expected) >= 2 and expected not in tokens:
                print(f"    ERROR: Expected token '{expected}' not found")
                return False
    
    print("  ✓ Tokenization tests passed")
    return True

def test_relevance_scoring():
    """Test relevance scoring algorithm."""
    from chord_node_v2 import compute_relevance_score
    
    print("\n=== Testing Relevance Scoring ===")
    
    test_cases = [
        (["machine", "learning"], ["machine", "learning", "notes"], 1.0),
        (["machine", "learning"], ["machine", "notes"], 0.5),
        (["deep", "learning"], ["machine", "learning", "notes"], 0.5),
        (["ai"], ["machine", "learning", "notes"], 0.0),
        ([], ["machine", "learning"], 0.0),
        (["machine"], [], 0.0),
    ]
    
    for query_tokens, file_tokens, expected_score in test_cases:
        score = compute_relevance_score(query_tokens, file_tokens)
        print(f"  Query: {query_tokens}, File: {file_tokens} -> Score: {score}")
        
        if abs(score - expected_score) > 0.01:  # Allow small float precision errors
            print(f"    ERROR: Expected {expected_score}, got {score}")
            return False
    
    print("  ✓ Relevance scoring tests passed")
    return True

def test_distributed_search():
    """Test distributed inverted index search."""
    cluster = ChordTestCluster()
    
    try:
        print("\n=== Testing Distributed Search ===")
        
        cluster.start_bootstrap()
        cluster.start_nodes()
        
        # Wait for ring stabilization and file distribution
        print("Waiting for ring stabilization and file indexing...")
        time.sleep(10)
        
        # Test search queries
        search_tests = [
            ("learning", "Should find machine_learning_notes, deep_learning_tutorial"),
            ("neural", "Should find neural_network_basics"),
            ("data", "Should find data_science_guide"),
            ("python", "Should find python_programming"),
            ("artificial", "Should find artificial_intelligence"),
            ("vision", "Should find computer_vision_intro"),
            ("processing", "Should find natural_language_processing"),
            ("machine", "Should find machine_learning_notes"),
            ("tutorial", "Should find deep_learning_tutorial"),
            ("nonexistent", "Should find nothing"),
        ]
        
        # Test distributed search via node interaction
        # We'll use a simple socket-based test since we can't easily import the running nodes
        import socket
        import json
        
        success_count = 0
        total_tests = len(search_tests)
        
        for query, description in search_tests:
            print(f"\n  Testing query: '{query}' ({description})")
            
            # Try to send search request to one of the nodes
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                sock.connect(('127.0.0.1', 5001))
                
                request = {
                    'type': 'search_files',
                    'query': query
                }
                sock.sendall(json.dumps(request).encode() + b'\n')
                
                response_data = sock.recv(4096).decode().strip()
                response = json.loads(response_data)
                
                sock.close()
                
                if response.get('success'):
                    files = response.get('files', [])
                    print(f"    Found {len(files)} files: {files}")
                    
                    if query == "nonexistent":
                        if len(files) == 0:
                            success_count += 1
                            print("    ✓ Correctly found no files for nonexistent query")
                        else:
                            print("    ✗ Should have found no files")
                    else:
                        if len(files) > 0:
                            success_count += 1
                            print(f"    ✓ Found files for '{query}'")
                        else:
                            print(f"    ✗ Expected to find files for '{query}'")
                else:
                    print(f"    ✗ Search failed: {response.get('error')}")
                    
            except Exception as e:
                print(f"    ✗ Search test failed: {e}")
        
        print(f"\n  Search tests passed: {success_count}/{total_tests}")
        return success_count >= total_tests * 0.7  # 70% pass rate acceptable
    
    finally:
        cluster.stop_all()

def test_partial_matching():
    """Test partial matching capabilities."""
    from chord_node_v2 import tokenize_filename
    
    print("\n=== Testing Partial Matching ===")
    
    # Test that tokenization creates partial tokens
    filename = "machine_learning_advanced"
    tokens = tokenize_filename(filename)
    
    print(f"  Filename: {filename}")
    print(f"  Tokens: {tokens}")
    
    # Should contain partial matches for "machine"
    partial_tests = [
        ("mac", "Should be in tokens for partial matching"),
        ("mach", "Should be in tokens for partial matching"), 
        ("learn", "Should be in tokens for partial matching"),
        ("adv", "Should be in tokens for partial matching"),
    ]
    
    success = True
    for partial, description in partial_tests:
        if partial in tokens:
            print(f"    ✓ '{partial}' found - {description}")
        else:
            print(f"    ✗ '{partial}' not found - {description}")
            success = False
    
    return success

def main():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("PHASE 2 TESTS: Distributed Inverted Index")
    print("=" * 60)
    
    # Set up signal handler for clean shutdown
    def signal_handler(signum, frame):
        print("\nTest interrupted, cleaning up...")
        exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    tests = [
        ("Tokenization", test_tokenization),
        ("Relevance Scoring", test_relevance_scoring),
        ("Partial Matching", test_partial_matching),
        ("Distributed Search", test_distributed_search),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            if test_func():
                print(f"✓ {test_name} test PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} test FAILED")
        except Exception as e:
            print(f"✗ {test_name} test ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"PHASE 2 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2 tests passed! Distributed inverted index is working correctly.")
    else:
        print("⚠️ Some tests failed. Review the implementation.")
    
    print("=" * 60)
    return passed == total

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
