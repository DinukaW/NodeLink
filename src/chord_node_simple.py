#!/usr/bin/env python3
"""
Simplified Chord DHT Node for REST API Integration
Focused on core functionality without complex QUIC transport
"""

import asyncio
import json
import logging
import socket
import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import asdict

from chord_utils import (
    Node, FileRecord, TokenRecord, FileMetadata, ChordRing, FileManager,
    hash_key, in_range, in_range_inclusive, tokenize_filename, compute_relevance_score,
    M, RING_SIZE, REPLICATION_FACTOR, BOOTSTRAP_HOST, BOOTSTRAP_PORT,
    STABILIZE_INTERVAL, FIX_FINGERS_INTERVAL, CHECK_PREDECESSOR_INTERVAL
)

logger = logging.getLogger(__name__)

class SimpleChordNode:
    """Simplified Chord DHT Node for REST API integration"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7000, shared_folder: str = "shared"):
        self.host = host
        self.port = port
        self.node_id = hash_key(f"{host}:{port}")
        
        # Core components
        self.ring = ChordRing()
        self.file_manager = FileManager(shared_folder)
        
        # Data storage
        self.files: Dict[str, FileRecord] = {}
        self.tokens: Dict[str, List[TokenRecord]] = {}
        self.file_metadata: Dict[str, FileMetadata] = {}
        
        # Network state
        self.successor: Optional[Node] = None
        self.predecessor: Optional[Node] = None
        self.finger_table: List[Optional[Node]] = [None] * M
        
        # Synchronization
        self.lock = threading.RLock()
        self.running = False
        
        # Statistics
        self.stats = {
            'files_stored': 0,
            'searches_performed': 0,
            'uploads': 0,
            'downloads': 0,
            'start_time': time.time()
        }
        
        logger.info(f"Initialized SimpleChordNode {self.node_id} at {host}:{port}")
    
    def start(self) -> None:
        """Start the Chord node"""
        self.running = True
        
        # Create self node
        self_node = Node(self.node_id, self.host, self.port)
        self.ring.add_node(self_node)
        
        # Initialize as single node (for API use)
        self.successor = self_node
        self.predecessor = self_node
        self.finger_table[0] = self_node
        
        logger.info(f"Started Chord node {self.node_id}")
    
    def stop(self) -> None:
        """Stop the Chord node"""
        self.running = False
        logger.info(f"Stopped Chord node {self.node_id}")
    
    async def store_file(self, filename: str, content: bytes, metadata: Optional[Dict] = None) -> bool:
        """Store a file in the DHT"""
        try:
            # Store file locally
            if not self.file_manager.store_file(filename, content):
                return False
            
            # Create file record
            file_record = FileRecord(
                filename=filename,
                node_id=self.node_id,
                host=self.host,
                port=self.port,
                file_hash=self.file_manager.compute_file_hash(filename),
                file_size=len(content)
            )
            
            # Store file metadata
            with self.lock:
                self.files[filename] = file_record
                
                if metadata:
                    self.file_metadata[filename] = FileMetadata(
                        filename=filename,
                        size=len(content),
                        hash=file_record.file_hash or "",
                        timestamp=file_record.timestamp,
                        mime_type=metadata.get('mime_type'),
                        tags=metadata.get('tags', [])
                    )
            
            # Index file tokens for search
            await self._index_file_tokens(filename)
            
            self.stats['files_stored'] += 1
            self.stats['uploads'] += 1
            
            logger.info(f"Stored file: {filename} (size: {len(content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error storing file {filename}: {e}")
            return False
    
    async def retrieve_file(self, filename: str) -> Optional[bytes]:
        """Retrieve a file from the DHT"""
        try:
            with self.lock:
                if filename not in self.files:
                    return None
            
            content = self.file_manager.retrieve_file(filename)
            if content:
                self.stats['downloads'] += 1
                logger.info(f"Retrieved file: {filename}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving file {filename}: {e}")
            return None
    
    async def delete_file(self, filename: str) -> bool:
        """Delete a file from the DHT"""
        try:
            with self.lock:
                if filename not in self.files:
                    return False
                
                # Remove from indexes
                del self.files[filename]
                if filename in self.file_metadata:
                    del self.file_metadata[filename]
                
                # Remove token records
                tokens_to_remove = []
                for token, records in self.tokens.items():
                    self.tokens[token] = [r for r in records if r.filename != filename]
                    if not self.tokens[token]:
                        tokens_to_remove.append(token)
                
                for token in tokens_to_remove:
                    del self.tokens[token]
            
            # Remove physical file
            import os
            filepath = os.path.join(self.file_manager.shared_folder, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            logger.info(f"Deleted file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False
    
    async def search_files(self, query: str) -> List[Dict[str, Any]]:
        """Search for files matching the query"""
        try:
            query_tokens = tokenize_filename(query)
            results = []
            
            with self.lock:
                # Score all files
                for filename, record in self.files.items():
                    file_tokens = tokenize_filename(filename)
                    relevance = compute_relevance_score(query_tokens, file_tokens)
                    
                    if relevance > 0:
                        result = record.to_dict()
                        result['relevance'] = relevance
                        results.append(result)
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance'], reverse=True)
            
            self.stats['searches_performed'] += 1
            logger.info(f"Search for '{query}' returned {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """List all files in the DHT"""
        with self.lock:
            return [record.to_dict() for record in self.files.values()]
    
    async def get_file_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific file"""
        with self.lock:
            if filename in self.file_metadata:
                return self.file_metadata[filename].to_dict()
            elif filename in self.files:
                return self.files[filename].to_dict()
        return None
    
    async def get_node_info(self) -> Dict[str, Any]:
        """Get information about this node"""
        with self.lock:
            return {
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port,
                'files_count': len(self.files),
                'tokens_count': len(self.tokens),
                'stats': self.stats.copy(),
                'uptime': time.time() - self.stats['start_time'],
                'status': 'running' if self.running else 'stopped'
            }
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network topology information"""
        return {
            'ring_size': RING_SIZE,
            'nodes_in_ring': len(self.ring.get_all_nodes()),
            'successor': self.successor.to_dict() if self.successor else None,
            'predecessor': self.predecessor.to_dict() if self.predecessor else None,
            'replication_factor': REPLICATION_FACTOR
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Basic health metrics
            files_accessible = 0
            total_files = len(self.files)
            
            for filename in list(self.files.keys()):
                if self.file_manager.file_exists(filename):
                    files_accessible += 1
            
            health_score = files_accessible / total_files if total_files > 0 else 1.0
            
            return {
                'status': 'healthy' if health_score >= 0.8 else 'degraded',
                'uptime': time.time() - self.stats['start_time'],
                'files_accessible': files_accessible,
                'total_files': total_files,
                'health_score': health_score,
                'memory_usage': self._get_memory_usage()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _index_file_tokens(self, filename: str) -> None:
        """Index file tokens for search"""
        tokens = tokenize_filename(filename)
        
        with self.lock:
            for token in tokens:
                if token not in self.tokens:
                    self.tokens[token] = []
                
                # Create token record
                token_record = TokenRecord(
                    token=token,
                    filename=filename,
                    node_id=self.node_id,
                    host=self.host,
                    port=self.port,
                    relevance=1.0  # Base relevance
                )
                
                self.tokens[token].append(token_record)
    
    def _get_memory_usage(self) -> Dict[str, int]:
        """Get approximate memory usage"""
        import sys
        
        files_size = sum(sys.getsizeof(record) for record in self.files.values())
        tokens_size = sum(sys.getsizeof(records) for records in self.tokens.values())
        metadata_size = sum(sys.getsizeof(meta) for meta in self.file_metadata.values())
        
        return {
            'files': files_size,
            'tokens': tokens_size,
            'metadata': metadata_size,
            'total': files_size + tokens_size + metadata_size
        }

# Create a simple alias for compatibility
QuicChordNode = SimpleChordNode

# For backward compatibility, create the expected async methods
class AsyncChordNode(SimpleChordNode):
    """Async wrapper for SimpleChordNode"""
    
    async def initialize(self) -> None:
        """Initialize the node asynchronously"""
        self.start()
    
    async def shutdown(self) -> None:
        """Shutdown the node asynchronously"""
        self.stop()

# Main entry point for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Chord DHT Node")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=7000, help="Port to bind to")
    parser.add_argument("--shared-folder", default="shared", help="Shared folder for files")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start node
    node = SimpleChordNode(args.host, args.port, args.shared_folder)
    node.start()
    
    print(f"🔗 Simple Chord DHT Node started on {args.host}:{args.port}")
    print(f"📁 Shared folder: {args.shared_folder}")
    print(f"🆔 Node ID: {node.node_id}")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        node.stop()
