#!/usr/bin/env python3
"""
Phase 2 Demo: Distributed Inverted Index
Demonstrates the tokenization, inverted index, and distributed search functionality.
"""

import sys
import os
sys.path.append('.')
from chord_node_v2 import ChordNode, tokenize_filename, compute_relevance_score
import time
import threading

def demo_tokenization():
    """Demonstrate filename tokenization."""
    print("\n" + "="*60)
    print("DEMO: Filename Tokenization")
    print("="*60)
    
    test_files = [
        "machine_learning_notes.txt",
        "deep-learning-tutorial.pdf", 
        "neural_network_basics.doc",
        "artificial_intelligence.pdf",
        "computer_vision_intro.txt",
        "natural_language_processing.doc",
        "data_science_guide.txt",
        "python_programming.py"
    ]
    
    for filename in test_files:
        tokens = tokenize_filename(filename)
        print(f"'{filename}'")
        print(f"  Tokens: {sorted(tokens)[:10]}...")  # Show first 10 tokens
        print()

def demo_relevance_scoring():
    """Demonstrate relevance scoring."""
    print("\n" + "="*60)
    print("DEMO: Relevance Scoring")
    print("="*60)
    
    # Example files and their tokens
    files = {
        "machine_learning_notes.txt": tokenize_filename("machine_learning_notes.txt"),
        "deep_learning_tutorial.pdf": tokenize_filename("deep_learning_tutorial.pdf"),
        "neural_network_basics.doc": tokenize_filename("neural_network_basics.doc"),
        "data_science_guide.txt": tokenize_filename("data_science_guide.txt")
    }
    
    queries = ["machine learning", "neural", "deep", "data science"]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        query_tokens = tokenize_filename(query)
        
        scores = []
        for filename, file_tokens in files.items():
            score = compute_relevance_score(query_tokens, file_tokens)
            scores.append((filename, score))
        
        # Sort by relevance
        scores.sort(key=lambda x: x[1], reverse=True)
        
        for filename, score in scores:
            if score > 0:
                print(f"  {filename:<30} (relevance: {score:.2f})")

def demo_inverted_index():
    """Demonstrate inverted index functionality with a single node."""
    print("\n" + "="*60)
    print("DEMO: Distributed Inverted Index (Single Node)")
    print("="*60)
    
    # Create a test node
    node = ChordNode('127.0.0.1', 7000)
    
    try:
        node.start()
        print("✓ Node started")
        
        # Store some test files
        test_files = [
            ("machine_learning_notes.txt", b"Notes about machine learning algorithms and techniques."),
            ("deep_learning_tutorial.pdf", b"A comprehensive tutorial on deep learning with neural networks."),
            ("neural_network_basics.doc", b"Basic concepts of neural networks and their applications."),
            ("data_science_guide.txt", b"A guide to data science methodologies and tools."),
            ("python_programming.py", b"Python programming examples and best practices.")
        ]
        
        print("\nStoring files and building inverted index...")
        for filename, content in test_files:
            success = node.file_manager.store_file(filename, content)
            if success:
                print(f"  ✓ Stored: {filename}")
            else:
                print(f"  ✗ Failed: {filename}")
        
        # Wait for index building
        time.sleep(1)
        
        # Show token index stats
        with node.file_manager.index_lock:
            total_tokens = len(node.file_manager.token_index)
            print(f"\n✓ Inverted index built: {total_tokens} unique tokens")
            
            # Show some example tokens
            print("\nSample token entries:")
            sample_tokens = ['machine', 'learning', 'neural', 'data', 'python']
            for token in sample_tokens:
                if token in node.file_manager.token_index:
                    record = node.file_manager.token_index[token]
                    files = list(record.files.keys())
                    print(f"  '{token}' -> {files}")
        
        # Test distributed search
        print("\nTesting distributed search:")
        queries = ["machine", "learning", "neural network", "data science", "python"]
        
        for query in queries:
            results = node.file_manager.search_files_distributed(query)
            print(f"\n  Query: '{query}'")
            if results:
                for filename, location, score in results[:3]:  # Top 3 results
                    print(f"    {filename:<25} (score: {score:.2f})")
            else:
                print("    No results found")
        
    finally:
        node.stop()
        print("\n✓ Node stopped")

def main():
    """Run all Phase 2 demonstrations."""
    print("="*80)
    print("PHASE 2 IMPLEMENTATION DEMO: Distributed Inverted Index")
    print("="*80)
    
    print("\nThis demo shows the key Phase 2 features:")
    print("1. Advanced filename tokenization with partial matching")
    print("2. Relevance scoring for search results")
    print("3. Distributed inverted index storage and retrieval")
    print("4. Token-based partial search functionality")
    
    try:
        demo_tokenization()
        demo_relevance_scoring()
        demo_inverted_index()
        
        print("\n" + "="*80)
        print("🎉 PHASE 2 DEMO COMPLETE!")
        print("✓ Tokenization: Advanced filename parsing with partial tokens")
        print("✓ Inverted Index: Distributed token storage across DHT")
        print("✓ Partial Search: Query tokens matched against distributed index")
        print("✓ Relevance Scoring: Results ranked by token match percentage")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
