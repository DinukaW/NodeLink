#!/usr/bin/env python3
"""
Core Chord DHT Utilities
Essential constants, classes, and functions for the Chord DHT implementation
"""

import hashlib
import logging
import os
import time
import threading
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Chord DHT Constants
M = 8  # 2^8 = 256 node identifier space (reduced for demo purposes)
RING_SIZE = 2 ** M
REPLICATION_FACTOR = 3
BOOTSTRAP_HOST = "127.0.0.1"
BOOTSTRAP_PORT = 55556

# Timing intervals (in seconds)
STABILIZE_INTERVAL = 30
FIX_FINGERS_INTERVAL = 20
CHECK_PREDECESSOR_INTERVAL = 15

def hash_key(key: str) -> int:
    """Generate consistent hash for given key"""
    return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16) % RING_SIZE

def in_range(key: int, start: int, end: int) -> bool:
    """Check if key is in (start, end) range on circular hash ring"""
    if start == end:
        return key != start
    elif start < end:
        return start < key < end
    else:  # Range wraps around
        return key > start or key < end

def in_range_inclusive(key: int, start: int, end: int) -> bool:
    """Check if key is in [start, end] range on circular hash ring"""
    if start == end:
        return True
    elif start < end:
        return start <= key <= end
    else:  # Range wraps around
        return key >= start or key <= end

def tokenize_filename(filename: str) -> List[str]:
    """Tokenize filename into searchable keywords"""
    import re
    # Remove file extension and split by common separators
    name_without_ext = os.path.splitext(filename)[0]
    tokens = re.split(r'[_\-\s\.]', name_without_ext.lower())
    
    # Filter out empty tokens and very short ones
    tokens = [token.strip() for token in tokens if token.strip() and len(token.strip()) > 1]
    
    # Add the full filename (without extension) as a token too
    if name_without_ext.lower() not in tokens:
        tokens.append(name_without_ext.lower())
    
    return list(set(tokens))  # Remove duplicates

def compute_relevance_score(query_tokens: List[str], file_tokens: List[str]) -> float:
    """Compute relevance score between query and file tokens"""
    if not query_tokens or not file_tokens:
        return 0.0
    
    query_set = set(token.lower().strip() for token in query_tokens)
    file_set = set(token.lower().strip() for token in file_tokens)
    
    # Calculate intersection
    intersection = query_set.intersection(file_set)
    
    if not intersection:
        # Check for partial matches
        partial_matches = 0
        for q_token in query_set:
            for f_token in file_set:
                if q_token in f_token or f_token in q_token:
                    partial_matches += 1
                    break
        
        return partial_matches / len(query_set) * 0.5  # Partial match gets 50% weight
    
    # Full match scoring
    return len(intersection) / len(query_set)

@dataclass
class Node:
    """Represents a node in the Chord ring"""
    id: int
    host: str
    port: int
    
    def __str__(self) -> str:
        return f"Node({self.id}, {self.host}:{self.port})"
    
    def __hash__(self) -> int:
        return hash((self.id, self.host, self.port))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Node):
            return False
        return self.id == other.id and self.host == other.host and self.port == other.port

@dataclass
class FileRecord:
    """Represents a file record in the DHT"""
    filename: str
    node_id: int
    host: str
    port: int
    timestamp: float = field(default_factory=time.time)
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filename': self.filename,
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'timestamp': self.timestamp,
            'file_hash': self.file_hash,
            'file_size': self.file_size
        }

@dataclass
class TokenRecord:
    """Represents a search token record"""
    token: str
    filename: str
    node_id: int
    host: str
    port: int
    relevance: float = 1.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'token': self.token,
            'filename': self.filename,
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'relevance': self.relevance,
            'timestamp': self.timestamp
        }

@dataclass
class FileMetadata:
    """File metadata for advanced operations"""
    filename: str
    size: int
    hash: str
    timestamp: float
    mime_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filename': self.filename,
            'size': self.size,
            'hash': self.hash,
            'timestamp': self.timestamp,
            'mime_type': self.mime_type,
            'tags': self.tags
        }

class ChordRing:
    """Manages the Chord ring structure and operations"""
    
    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.lock = threading.RLock()
    
    def add_node(self, node: Node) -> None:
        """Add a node to the ring"""
        with self.lock:
            self.nodes[node.id] = node
    
    def remove_node(self, node_id: int) -> None:
        """Remove a node from the ring"""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
    
    def get_node(self, node_id: int) -> Optional[Node]:
        """Get node by ID"""
        with self.lock:
            return self.nodes.get(node_id)
    
    def get_successor(self, key: int) -> Optional[Node]:
        """Find the successor node for a given key"""
        with self.lock:
            if not self.nodes:
                return None
            
            # Sort nodes by ID
            sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.id)
            
            # Find first node with ID >= key
            for node in sorted_nodes:
                if node.id >= key:
                    return node
            
            # If no node found, return first node (ring wraps around)
            return sorted_nodes[0]
    
    def get_all_nodes(self) -> List[Node]:
        """Get all nodes in the ring"""
        with self.lock:
            return list(self.nodes.values())

class FileManager:
    """Manages file operations and storage"""
    
    def __init__(self, shared_folder: str = "shared"):
        self.shared_folder = shared_folder
        os.makedirs(shared_folder, exist_ok=True)
        
    def store_file(self, filename: str, content: bytes) -> bool:
        """Store file content locally"""
        try:
            filepath = os.path.join(self.shared_folder, filename)
            with open(filepath, 'wb') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to store file {filename}: {e}")
            return False
    
    def retrieve_file(self, filename: str) -> Optional[bytes]:
        """Retrieve file content"""
        try:
            filepath = os.path.join(self.shared_folder, filename)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to retrieve file {filename}: {e}")
        return None
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists locally"""
        filepath = os.path.join(self.shared_folder, filename)
        return os.path.exists(filepath)
    
    def get_file_size(self, filename: str) -> Optional[int]:
        """Get file size"""
        try:
            filepath = os.path.join(self.shared_folder, filename)
            if os.path.exists(filepath):
                return os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"Failed to get size for {filename}: {e}")
        return None
    
    def list_files(self) -> List[str]:
        """List all files in shared folder"""
        try:
            return [f for f in os.listdir(self.shared_folder) 
                   if os.path.isfile(os.path.join(self.shared_folder, f))]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def compute_file_hash(self, filename: str) -> Optional[str]:
        """Compute SHA-256 hash of file"""
        try:
            filepath = os.path.join(self.shared_folder, filename)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute hash for {filename}: {e}")
        return None
