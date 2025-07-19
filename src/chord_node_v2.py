#!/usr/bin/env python3
"""
Redesigned Chord DHT Implementation
Inspired by the Go chord-kv implementation for robust distributed file sharing.

Key improvements:
- Proper ring maintenance with stabilization
- Correct file distribution and replication
- Better error handling and recovery
- Modular design with clear separation of concerns
"""

import hashlib
import threading
import socket
import json
import os
import time
import logging
import argparse
import sys
import signal
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chord_v2.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Chord configuration
M = 8  # Number of bits for the Chord ring (0-255)
RING_SIZE = 2 ** M
REPLICATION_FACTOR = 3  # Number of replicas per file

# Network configuration
BOOTSTRAP_HOST = '127.0.0.1'
BOOTSTRAP_PORT = 55556
STABILIZE_INTERVAL = 2.0  # seconds
FIX_FINGERS_INTERVAL = 3.0  # seconds
CHECK_PREDECESSOR_INTERVAL = 5.0  # seconds


def hash_key(key: str) -> int:
    """Compute hash of a key to map it to the ring."""
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % RING_SIZE


def in_range(key: int, start: int, end: int) -> bool:
    """Check if key is in the range (start, end] on the ring."""
    if start < end:
        return start < key <= end
    else:  # Wrap around case
        return key > start or key <= end


def in_range_inclusive(key: int, start: int, end: int) -> bool:
    """Check if key is in the range [start, end] on the ring."""
    if start == end:
        return True
    if start < end:
        return start <= key <= end
    else:  # Wrap around case
        return key >= start or key <= end


@dataclass
class Node:
    """Represents a node in the Chord ring."""
    node_id: int
    address: str
    port: int
    
    @property
    def addr_str(self) -> str:
        return f"{self.address}:{self.port}"
    
    def __str__(self) -> str:
        return f"Node({self.node_id}, {self.addr_str})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Node):
            return False
        return self.node_id == other.node_id
    
    def __hash__(self) -> int:
        return hash(self.node_id)


@dataclass
class FileRecord:
    """Represents a file stored in the DHT."""
    filename: str
    content: bytes
    file_hash: int
    replicas: Set[int]  # Set of node IDs that store this file
    
    def to_dict(self) -> dict:
        return {
            'filename': self.filename,
            'content': self.content.decode('utf-8', errors='replace'),
            'file_hash': self.file_hash,
            'replicas': list(self.replicas)
        }


@dataclass
class TokenRecord:
    """Represents a token in the inverted index."""
    token: str
    token_hash: int
    files: Dict[str, 'FileMetadata']  # filename -> metadata
    
    def to_dict(self) -> dict:
        return {
            'token': self.token,
            'token_hash': self.token_hash,
            'files': {filename: meta.to_dict() for filename, meta in self.files.items()}
        }

@dataclass
class FileMetadata:
    """Metadata about a file containing a token."""
    filename: str
    file_hash: int
    node_id: int
    node_address: str
    all_tokens: List[str]  # All tokens in the file for relevance scoring
    file_size: int
    
    def to_dict(self) -> dict:
        return {
            'filename': self.filename,
            'file_hash': self.file_hash,
            'node_id': self.node_id,
            'node_address': self.node_address,
            'all_tokens': self.all_tokens,
            'file_size': self.file_size
        }


def tokenize_filename(filename: str) -> List[str]:
    """
    Tokenize a filename into searchable tokens.
    Handles various filename formats and extensions.
    """
    import re
    
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Split on common delimiters and convert to lowercase
    tokens = re.split(r'[\s\-_\.]+', name_without_ext.lower())
    
    # Remove empty tokens and very short tokens
    tokens = [token for token in tokens if len(token) >= 2]
    
    # Add partial tokens for better search experience
    partial_tokens = []
    for token in tokens:
        if len(token) > 3:
            # Add prefixes of length 3 and above
            for i in range(3, len(token)):
                partial_tokens.append(token[:i])
    
    # Combine original tokens with partial tokens
    all_tokens = list(set(tokens + partial_tokens))
    
    return all_tokens


def compute_relevance_score(query_tokens: List[str], file_tokens: List[str]) -> float:
    """Compute relevance score for a file based on query tokens."""
    if not query_tokens or not file_tokens:
        return 0.0
    
    # Count matches
    matches = 0
    for query_token in query_tokens:
        if query_token in file_tokens:
            matches += 1
    
    # Return normalized score
    return matches / len(query_tokens)


class ChordRing:
    """Manages the Chord ring structure and operations."""
    
    def __init__(self, local_node: Node):
        self.local_node = local_node
        self.successor: Optional[Node] = local_node  # Initially point to self
        self.predecessor: Optional[Node] = None
        self.finger_table: List[Optional[Node]] = [None] * M
        self.next_finger = 0
        self.ring_lock = threading.RLock()
        
    def find_successor(self, key_id: int) -> Optional[Node]:
        """Find the successor node responsible for the given key."""
        with self.ring_lock:
            # If we're the only node, we're responsible
            if self.successor == self.local_node:
                return self.local_node
            
            # Check if key is between us and our successor
            if in_range(key_id, self.local_node.node_id, self.successor.node_id):
                return self.successor
            
            # Use finger table to find closest preceding node
            closest = self._closest_preceding_node(key_id)
            if closest == self.local_node:
                return self.successor
            
            # Forward the query to the closest node
            try:
                return self._remote_find_successor(closest, key_id)
            except Exception as e:
                logger.warning(f"Failed to query {closest} for successor of {key_id}: {e}")
                return self.successor
    
    def _closest_preceding_node(self, key_id: int) -> Node:
        """Find the closest preceding node in the finger table for O(log N) lookup."""
        # Search finger table in reverse order for the closest preceding node
        for i in range(M - 1, -1, -1):
            finger = self.finger_table[i]
            if (finger and 
                finger != self.local_node and
                self._is_between(finger.node_id, self.local_node.node_id, key_id)):
                return finger
        
        # If no finger table entry is suitable, return self
        return self.local_node
    
    def _is_between(self, key: int, start: int, end: int) -> bool:
        """Check if key is between start and end (exclusive) on the ring."""
        if start == end:
            return key != start
        elif start < end:
            return start < key < end
        else:  # Wrap around case
            return key > start or key < end
    
    def _remote_find_successor(self, node: Node, key_id: int) -> Optional[Node]:
        """Query a remote node to find successor."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'find_successor',
                'key_id': key_id
            }
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(4096).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success'):
                node_info = response.get('successor')
                return Node(node_info['node_id'], node_info['address'], node_info['port'])
            return None
            
        except Exception as e:
            logger.warning(f"Remote find_successor failed for {node}: {e}")
            return None
    
    def join(self, existing_node: Optional[Node]) -> bool:
        """Join the Chord ring through an existing node."""
        with self.ring_lock:
            if existing_node is None:
                # Create new ring
                self.successor = self.local_node
                self.predecessor = None
                logger.info(f"Node {self.local_node.node_id} created new ring")
                return True
            
            try:
                # Find our successor
                successor = self._remote_find_successor(existing_node, self.local_node.node_id)
                if successor:
                    self.successor = successor
                    self.predecessor = None
                    logger.info(f"Node {self.local_node.node_id} joined ring, successor: {successor.node_id}")
                    return True
                else:
                    logger.error("Failed to find successor when joining ring")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to join ring: {e}")
                return False
    
    def stabilize(self):
        """Stabilize the ring by checking successor's predecessor."""
        with self.ring_lock:
            if self.successor == self.local_node:
                return
            
            try:
                # Get successor's predecessor
                pred = self._get_predecessor(self.successor)
                
                # If successor has a predecessor between us and it, update our successor
                if (pred and pred != self.local_node and 
                    in_range(pred.node_id, self.local_node.node_id, self.successor.node_id)):
                    old_successor = self.successor
                    self.successor = pred
                    logger.info(f"Stabilized: updated successor from {old_successor.node_id} to {pred.node_id}")
                
                # Notify our successor that we might be its predecessor
                self._notify(self.successor)
                
                # Also try to fix any broken ring connections
                if self.successor and self.successor != self.local_node:
                    # Ensure our successor knows about us
                    self._notify(self.successor)
                
            except Exception as e:
                logger.warning(f"Stabilization failed: {e}")
                # Try to recover by finding a new successor
                self._recover_successor()
    
    def _get_predecessor(self, node: Node) -> Optional[Node]:
        """Get the predecessor of a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((node.address, node.port))
            
            request = {'type': 'get_predecessor'}
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(4096).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success') and response.get('predecessor'):
                pred_info = response['predecessor']
                return Node(pred_info['node_id'], pred_info['address'], pred_info['port'])
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get predecessor from {node}: {e}")
            return None
    
    def _notify(self, node: Node):
        """Notify a node that we might be its predecessor."""
        if node == self.local_node:
            return
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'notify',
                'node': {
                    'node_id': self.local_node.node_id,
                    'address': self.local_node.address,
                    'port': self.local_node.port
                }
            }
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
        except Exception as e:
            logger.warning(f"Failed to notify {node}: {e}")
    
    def notify(self, node: Node):
        """Handle notification from another node."""
        with self.ring_lock:
            if (self.predecessor is None or 
                in_range(node.node_id, self.predecessor.node_id, self.local_node.node_id)):
                old_pred = self.predecessor
                self.predecessor = node
                if old_pred:
                    logger.info(f"Updated predecessor from {old_pred.node_id} to {node.node_id}")
                else:
                    logger.info(f"Set predecessor to {node.node_id}")
    
    def fix_fingers(self):
        """Fix one finger table entry using correct Chord formula."""
        with self.ring_lock:
            if self.successor == self.local_node:
                return
            
            self.next_finger = (self.next_finger + 1) % M
            
            # Correct Chord formula: start = (n + 2^(i-1)) mod 2^m
            # Note: next_finger is 0-based, so we use (next_finger) instead of (next_finger-1)
            start = (self.local_node.node_id + 2**self.next_finger) % RING_SIZE
            
            try:
                successor = self.find_successor(start)
                if successor:
                    old_finger = self.finger_table[self.next_finger]
                    self.finger_table[self.next_finger] = successor
                    
                    if old_finger != successor:
                        logger.debug(f"Updated finger[{self.next_finger}]: {old_finger.node_id if old_finger else None} -> {successor.node_id}")
                    
            except Exception as e:
                logger.warning(f"Failed to fix finger {self.next_finger}: {e}")
    
    def check_predecessor(self):
        """Check if predecessor is still alive."""
        with self.ring_lock:
            if self.predecessor is None:
                return
            
            try:
                if not self._ping_node(self.predecessor):
                    logger.info(f"Predecessor {self.predecessor.node_id} failed, removing")
                    self.predecessor = None
                    
            except Exception as e:
                logger.warning(f"Failed to check predecessor: {e}")
                self.predecessor = None
    
    def _ping_node(self, node: Node) -> bool:
        """Check if a node is alive."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((node.address, node.port))
            
            request = {'type': 'ping'}
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            return response.get('success', False)
            
        except Exception:
            return False
    
    def _recover_successor(self):
        """Try to find a new successor when current one fails."""
        with self.ring_lock:
            logger.info(f"Attempting to recover successor for node {self.local_node.node_id}")
            
            # Try finger table entries
            for i, finger in enumerate(self.finger_table):
                if finger and finger != self.local_node and finger != self.successor:
                    if self._ping_node(finger):
                        old_successor = self.successor
                        self.successor = finger
                        logger.info(f"Recovered successor: {finger.node_id} (was {old_successor.node_id if old_successor else None})")
                        return
            
            # Try to find any live node by asking predecessor
            if self.predecessor and self.predecessor != self.local_node:
                if self._ping_node(self.predecessor):
                    try:
                        pred_successor = self._get_successor(self.predecessor)
                        if pred_successor and pred_successor != self.local_node and self._ping_node(pred_successor):
                            old_successor = self.successor
                            self.successor = pred_successor
                            logger.info(f"Recovered successor via predecessor: {pred_successor.node_id}")
                            return
                    except Exception as e:
                        logger.warning(f"Could not get successor from predecessor: {e}")
            
            # If no fingers work, we become our own successor (singleton)
            old_successor = self.successor
            self.successor = self.local_node
            logger.info(f"No live successor found, becoming singleton (was {old_successor.node_id if old_successor else None})")
    
    def get_ring_info(self) -> dict:
        """Get information about the ring structure."""
        with self.ring_lock:
            return {
                'node_id': self.local_node.node_id,
                'successor': self.successor.node_id if self.successor else None,
                'predecessor': self.predecessor.node_id if self.predecessor else None,
                'finger_table': [f.node_id if f else None for f in self.finger_table]
            }
    
    def validate_ring_consistency(self) -> bool:
        """Validate ring consistency and detect issues."""
        with self.ring_lock:
            issues = []
            
            # Check if we have valid successor
            if not self.successor:
                issues.append("No successor")
            elif self.successor == self.local_node and self.predecessor is not None:
                issues.append("Self-successor but has predecessor")
            
            # Check if successor is reachable
            if self.successor and self.successor != self.local_node:
                if not self._ping_node(self.successor):
                    issues.append(f"Successor {self.successor.node_id} not reachable")
            
            # Check if predecessor is reachable
            if self.predecessor:
                if not self._ping_node(self.predecessor):
                    issues.append(f"Predecessor {self.predecessor.node_id} not reachable")
            
            # Check finger table health
            dead_fingers = 0
            for i, finger in enumerate(self.finger_table):
                if finger and finger != self.local_node:
                    if not self._ping_node(finger):
                        dead_fingers += 1
                        self.finger_table[i] = None  # Clear dead finger
            
            if dead_fingers > 0:
                issues.append(f"{dead_fingers} dead finger table entries cleared")
            
            if issues:
                logger.warning(f"Ring consistency issues: {'; '.join(issues)}")
                return False
            else:
                logger.debug("Ring consistency check passed")
                return True
    
    def heal_ring(self):
        """Attempt to heal ring inconsistencies."""
        logger.info("Attempting to heal ring inconsistencies")
        
        with self.ring_lock:
            # If successor is dead, try to find a new one
            if self.successor and self.successor != self.local_node:
                if not self._ping_node(self.successor):
                    logger.warning(f"Successor {self.successor.node_id} is dead, attempting recovery")
                    self._recover_successor()
            
            # If we have no predecessor but we're not alone, try to find one
            if not self.predecessor and self.successor != self.local_node:
                # Ask successor for its predecessor
                try:
                    succ_pred = self._get_predecessor(self.successor)
                    if succ_pred and succ_pred != self.local_node:
                        # Check if we should be between pred and successor
                        if in_range_inclusive(self.local_node.node_id, succ_pred.node_id, self.successor.node_id):
                            self.predecessor = succ_pred
                            logger.info(f"Recovered predecessor: {succ_pred.node_id}")
                except Exception as e:
                    logger.warning(f"Failed to recover predecessor: {e}")

class FileManager:
    """Manages file storage and retrieval with replication and distributed inverted index."""
    
    def __init__(self, local_node: Node, ring: ChordRing):
        self.local_node = local_node
        self.ring = ring
        self.files: Dict[str, FileRecord] = {}
        self.file_lock = threading.RLock()
        
        # Distributed inverted index
        self.token_index: Dict[str, TokenRecord] = {}  # Local portion of inverted index
        self.index_lock = threading.RLock()
        
    def store_file(self, filename: str, content: bytes) -> bool:
        """Store a file in the DHT with replication and build inverted index."""
        file_hash = hash_key(filename)
        
        with self.file_lock:
            # Find responsible node
            responsible_node = self.ring.find_successor(file_hash)
            if not responsible_node:
                logger.error(f"Could not find responsible node for {filename}")
                return False
            
            logger.info(f"File '{filename}' (hash={file_hash}) -> responsible node {responsible_node.node_id}")
            
            # Create file record
            file_record = FileRecord(filename, content, file_hash, set())
            
            # Store file on responsible node and replicas
            success_count = 0
            replica_nodes = self._get_replica_nodes(file_hash)
            
            for node in replica_nodes:
                if self._store_file_on_node(node, file_record):
                    success_count += 1
                    file_record.replicas.add(node.node_id)
            
            if success_count > 0:
                # Build inverted index for the file
                self._build_inverted_index(filename, replica_nodes[0] if replica_nodes else self.local_node, content)
                logger.info(f"File '{filename}' stored successfully on {success_count} nodes")
                return True
            else:
                logger.error(f"Failed to store file '{filename}' on any node")
                return False
    
    def _get_replica_nodes(self, file_hash: int) -> List[Node]:
        """Get the list of nodes that should store replicas of the file."""
        nodes = []
        current_id = file_hash
        
        for _ in range(REPLICATION_FACTOR):
            node = self.ring.find_successor(current_id)
            if node and node not in nodes:
                nodes.append(node)
                current_id = (node.node_id + 1) % RING_SIZE
            else:
                break
        
        return nodes
    
    def _store_file_on_node(self, node: Node, file_record: FileRecord) -> bool:
        """Store a file on a specific node."""
        if node == self.local_node:
            # Store locally
            with self.file_lock:
                self.files[file_record.filename] = file_record
                logger.info(f"Stored file '{file_record.filename}' locally")
                return True
        else:
            # Store remotely
            return self._remote_store_file(node, file_record)
    
    def _remote_store_file(self, node: Node, file_record: FileRecord) -> bool:
        """Store a file on a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'store_file',
                'filename': file_record.filename,
                'content': file_record.content.decode('utf-8', errors='replace'),
                'file_hash': file_record.file_hash
            }
            
            data = json.dumps(request).encode() + b'\n'
            sock.sendall(data)
            
            response_data = sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success'):
                logger.info(f"File '{file_record.filename}' stored on remote node {node.node_id}")
                return True
            else:
                logger.warning(f"Failed to store file on {node.node_id}: {response.get('error')}")
                return False
                
        except Exception as e:
            logger.warning(f"Remote store failed for {node}: {e}")
            return False
    
    def search_files(self, query: str) -> List[Tuple[str, str]]:
        """Search for files across the ring."""
        results = []
        visited_nodes = set()
        
        # Start from local node and traverse the ring
        current_node = self.local_node
        max_visits = 10  # Prevent infinite loops
        visit_count = 0
        
        while current_node and current_node.node_id not in visited_nodes and visit_count < max_visits:
            visited_nodes.add(current_node.node_id)
            visit_count += 1
            
            # Search on current node
            node_results = self._search_on_node(current_node, query)
            results.extend(node_results)
            
            # Get the next node (successor)
            next_node = None
            if current_node == self.local_node:
                next_node = self.ring.successor
            else:
                # Get successor of remote node
                next_node = self._get_successor(current_node)
            
            # If next node is None or we've come back to start, we're done
            if not next_node or next_node.node_id == self.local_node.node_id:
                break
                
            current_node = next_node
        
        logger.info(f"Search for '{query}' completed. Visited {len(visited_nodes)} nodes, found {len(results)} matches")
        return results
    
    def _search_on_node(self, node: Node, query: str) -> List[Tuple[str, str]]:
        """Search for files on a specific node."""
        if node == self.local_node:
            # Search locally
            results = []
            with self.file_lock:
                for filename in self.files.keys():
                    if query.lower() in filename.lower():
                        results.append((filename, node.addr_str))
            return results
        else:
            # Search remotely
            return self._remote_search_files(node, query)
    
    def _remote_search_files(self, node: Node, query: str) -> List[Tuple[str, str]]:
        """Search for files on a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'search_files',
                'query': query
            }
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(4096).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success'):
                return [(f, node.addr_str) for f in response.get('files', [])]
            else:
                return []
                
        except Exception as e:
            logger.warning(f"Remote search failed for {node}: {e}")
            return []
    
    def _get_successor(self, node: Node) -> Optional[Node]:
        """Get the successor of a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((node.address, node.port))
            
            request = {'type': 'get_successor'}
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(4096).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success') and response.get('successor'):
                succ_info = response['successor']
                return Node(succ_info['node_id'], succ_info['address'], succ_info['port'])
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get successor from {node}: {e}")
            return None
    
    def download_file(self, filename: str) -> Optional[bytes]:
        """Download a file from the DHT."""
        file_hash = hash_key(filename)
        
        # Find nodes that might have the file
        replica_nodes = self._get_replica_nodes(file_hash)
        
        for node in replica_nodes:
            content = self._download_from_node(node, filename)
            if content:
                return content
        
        logger.warning(f"File '{filename}' not found on any replica")
        return None
    
    def _download_from_node(self, node: Node, filename: str) -> Optional[bytes]:
        """Download a file from a specific node."""
        if node == self.local_node:
            # Get locally
            with self.file_lock:
                if filename in self.files:
                    return self.files[filename].content
                return None
        else:
            # Get remotely
            return self._remote_download_file(node, filename)
    
    def _remote_download_file(self, node: Node, filename: str) -> Optional[bytes]:
        """Download a file from a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'get_file',
                'filename': filename
            }
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(8192).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success'):
                return response.get('content', '').encode('utf-8')
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Remote download failed from {node}: {e}")
            return None
    
    def list_local_files(self) -> List[str]:
        """List files stored locally."""
        with self.file_lock:
            return list(self.files.keys())
    
    # ==================== DISTRIBUTED INVERTED INDEX METHODS ====================
    
    def _build_inverted_index(self, filename: str, primary_node: Node, content: bytes):
        """Build inverted index entries for a file and distribute them across the ring."""
        # Tokenize filename
        tokens = tokenize_filename(filename)
        file_size = len(content)
        
        # Create file metadata
        file_metadata = FileMetadata(
            filename=filename,
            file_hash=hash_key(filename),
            node_id=primary_node.node_id,
            node_address=primary_node.addr_str,
            all_tokens=tokens,
            file_size=file_size
        )
        
        # Distribute each token to its responsible node
        for token in tokens:
            token_hash = hash_key(token)
            responsible_node = self.ring.find_successor(token_hash)
            
            if responsible_node:
                self._store_token_record(token, token_hash, file_metadata, responsible_node)
    
    def _store_token_record(self, token: str, token_hash: int, file_metadata: FileMetadata, responsible_node: Node):
        """Store a token record on the responsible node."""
        if responsible_node == self.local_node:
            # Store locally
            with self.index_lock:
                if token not in self.token_index:
                    self.token_index[token] = TokenRecord(token, token_hash, {})
                
                self.token_index[token].files[file_metadata.filename] = file_metadata
                logger.debug(f"Stored token '{token}' -> '{file_metadata.filename}' locally")
        else:
            # Store remotely
            self._remote_store_token(token, token_hash, file_metadata, responsible_node)
    
    def _remote_store_token(self, token: str, token_hash: int, file_metadata: FileMetadata, node: Node):
        """Store a token record on a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'store_token',
                'token': token,
                'token_hash': token_hash,
                'file_metadata': file_metadata.to_dict()
            }
            
            data = json.dumps(request).encode() + b'\n'
            sock.sendall(data)
            
            response_data = sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success'):
                logger.debug(f"Stored token '{token}' on remote node {node.node_id}")
            else:
                logger.warning(f"Failed to store token on {node.node_id}: {response.get('error')}")
                
        except Exception as e:
            logger.warning(f"Remote token store failed for {node}: {e}")
    
    def search_files_distributed(self, query: str) -> List[Tuple[str, str, float]]:
        """Search for files using distributed inverted index with relevance scoring."""
        if not query.strip():
            # Empty query - fall back to traditional search
            traditional_results = self.search_files(query)
            return [(filename, location, 1.0) for filename, location in traditional_results]
        
        # Tokenize query
        query_tokens = tokenize_filename(query)
        if not query_tokens:
            return []
        
        # Collect file candidates from token lookups
        file_candidates: Dict[str, Tuple[FileMetadata, Set[str]]] = {}
        
        for token in query_tokens:
            token_records = self._lookup_token(token)
            for token_record in token_records:
                for filename, file_metadata in token_record.files.items():
                    if filename not in file_candidates:
                        file_candidates[filename] = (file_metadata, set())
                    file_candidates[filename][1].add(token)
        
        # Compute relevance scores and prepare results
        results = []
        for filename, (file_metadata, matched_tokens) in file_candidates.items():
            relevance = compute_relevance_score(query_tokens, file_metadata.all_tokens)
            results.append((filename, file_metadata.node_address, relevance))
        
        # Sort by relevance (descending)
        results.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Distributed search for '{query}' found {len(results)} files")
        return results
    
    def _lookup_token(self, token: str) -> List[TokenRecord]:
        """Look up a token in the distributed inverted index."""
        token_hash = hash_key(token)
        responsible_node = self.ring.find_successor(token_hash)
        
        if not responsible_node:
            return []
        
        if responsible_node == self.local_node:
            # Search locally
            with self.index_lock:
                if token in self.token_index:
                    return [self.token_index[token]]
                else:
                    return []
        else:
            # Search remotely
            return self._remote_lookup_token(token, responsible_node)
    
    def _remote_lookup_token(self, token: str, node: Node) -> List[TokenRecord]:
        """Look up a token on a remote node."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((node.address, node.port))
            
            request = {
                'type': 'lookup_token',
                'token': token
            }
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(8192).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            if response.get('success') and response.get('token_record'):
                tr_data = response['token_record']
                # Reconstruct TokenRecord from dict
                files = {}
                for fname, fmeta_dict in tr_data.get('files', {}).items():
                    files[fname] = FileMetadata(
                        filename=fmeta_dict['filename'],
                        file_hash=fmeta_dict['file_hash'],
                        node_id=fmeta_dict['node_id'],
                        node_address=fmeta_dict['node_address'],
                        all_tokens=fmeta_dict['all_tokens'],
                        file_size=fmeta_dict['file_size']
                    )
                
                token_record = TokenRecord(
                    token=tr_data['token'],
                    token_hash=tr_data['token_hash'],
                    files=files
                )
                return [token_record]
            else:
                return []
                
        except Exception as e:
            logger.warning(f"Remote token lookup failed for {node}: {e}")
            return []
    
class ChordNode:
    """Main Chord node implementation."""
    
    def __init__(self, address: str, port: int):
        self.local_node = Node(hash_key(f"{address}:{port}"), address, port)
        self.ring = ChordRing(self.local_node)
        self.file_manager = FileManager(self.local_node, self.ring)
        
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Background threads
        self.stabilize_timer: Optional[threading.Timer] = None
        self.fix_fingers_timer: Optional[threading.Timer] = None
        self.check_predecessor_timer: Optional[threading.Timer] = None
        
        logger.info(f"Created ChordNode {self.local_node}")
    
    def start(self, shared_folder: Optional[str] = None):
        """Start the Chord node."""
        try:
            self.running = True
            
            # Start server
            self._start_server()
            
            # Load initial files if shared folder provided
            if shared_folder and os.path.exists(shared_folder):
                self._load_initial_files(shared_folder)
            
            # Start background maintenance tasks
            self._start_maintenance_tasks()
            
            logger.info(f"ChordNode {self.local_node.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start ChordNode {self.local_node.node_id}: {e}")
            logger.error(traceback.format_exc())
            self.stop()
            raise
    
    def _start_server(self):
        """Start the server socket."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.local_node.address, self.local_node.port))
        self.server_socket.listen(10)
        
        # Start accepting connections
        self.executor.submit(self._accept_connections)
    
    def _accept_connections(self):
        """Accept and handle incoming connections."""
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                self.executor.submit(self._handle_client, client_sock, addr)
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
                break
    
    def _handle_client(self, client_sock: socket.socket, addr):
        """Handle a client request."""
        try:
            data = client_sock.recv(8192).decode().strip()
            if not data:
                return
            
            request = json.loads(data)
            response = self._process_request(request)
            
            client_sock.sendall(json.dumps(response).encode() + b'\n')
            
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
            error_response = {'success': False, 'error': str(e)}
            try:
                client_sock.sendall(json.dumps(error_response).encode() + b'\n')
            except:
                pass
        finally:
            try:
                client_sock.close()
            except:
                pass
    
    def _process_request(self, request: dict) -> dict:
        """Process a request and return response."""
        req_type = request.get('type')
        
        if req_type == 'ping':
            return {'success': True}
        
        elif req_type == 'find_successor':
            key_id = request.get('key_id')
            successor = self.ring.find_successor(key_id)
            if successor:
                return {
                    'success': True,
                    'successor': {
                        'node_id': successor.node_id,
                        'address': successor.address,
                        'port': successor.port
                    }
                }
            return {'success': False, 'error': 'No successor found'}
        
        elif req_type == 'get_predecessor':
            if self.ring.predecessor:
                return {
                    'success': True,
                    'predecessor': {
                        'node_id': self.ring.predecessor.node_id,
                        'address': self.ring.predecessor.address,
                        'port': self.ring.predecessor.port
                    }
                }
            return {'success': True, 'predecessor': None}
        
        elif req_type == 'get_successor':
            if self.ring.successor:
                return {
                    'success': True,
                    'successor': {
                        'node_id': self.ring.successor.node_id,
                        'address': self.ring.successor.address,
                        'port': self.ring.successor.port
                    }
                }
            return {'success': False, 'error': 'No successor'}
        
        elif req_type == 'notify':
            node_info = request.get('node')
            node = Node(node_info['node_id'], node_info['address'], node_info['port'])
            self.ring.notify(node)
            return {'success': True}
        
        elif req_type == 'store_file':
            filename = request.get('filename')
            content = request.get('content', '').encode('utf-8')
            file_hash = request.get('file_hash')
            
            with self.file_manager.file_lock:
                file_record = FileRecord(filename, content, file_hash, set())
                self.file_manager.files[filename] = file_record
            
            logger.info(f"Stored file '{filename}' locally")
            return {'success': True}
        
        elif req_type == 'search_files':
            query = request.get('query', '')
            files = []
            with self.file_manager.file_lock:
                for filename in self.file_manager.files.keys():
                    if query.lower() in filename.lower():
                        files.append(filename)
            return {'success': True, 'files': files}
        
        elif req_type == 'get_file':
            filename = request.get('filename')
            with self.file_manager.file_lock:
                if filename in self.file_manager.files:
                    content = self.file_manager.files[filename].content.decode('utf-8', errors='replace')
                    return {'success': True, 'content': content}
            return {'success': False, 'error': 'File not found'}
        
        elif req_type == 'get_status':
            return {
                'success': True,
                'node_id': self.local_node.node_id,
                'files': list(self.file_manager.files.keys()),
                'ring_info': self.ring.get_ring_info()
            }
        
        elif req_type == 'transfer_file':
            filename = request.get('filename')
            content = request.get('content', '').encode('utf-8')
            file_hash = request.get('file_hash')
            from_node = request.get('from_node')
            
            logger.info(f"Receiving file transfer: {filename} from node {from_node}")
            
            with self.file_manager.file_lock:
                file_record = FileRecord(filename, content, file_hash, set())
                self.file_manager.files[filename] = file_record
            
            return {'success': True}
        
        elif req_type == 'update_successor':
            new_successor_info = request.get('new_successor')
            if new_successor_info:
                new_successor = Node(
                    new_successor_info['node_id'],
                    new_successor_info['address'],
                    new_successor_info['port']
                )
                with self.ring.ring_lock:
                    old_successor = self.ring.successor
                    self.ring.successor = new_successor
                    logger.info(f"Updated successor from {old_successor.node_id if old_successor else None} to {new_successor.node_id}")
            
            return {'success': True}
        
        elif req_type == 'update_predecessor':
            new_predecessor_info = request.get('new_predecessor')
            if new_predecessor_info:
                new_predecessor = Node(
                    new_predecessor_info['node_id'],
                    new_predecessor_info['address'],
                    new_predecessor_info['port']
                )
                with self.ring.ring_lock:
                    old_predecessor = self.ring.predecessor
                    self.ring.predecessor = new_predecessor
                    logger.info(f"Updated predecessor from {old_predecessor.node_id if old_predecessor else None} to {new_predecessor.node_id}")
            else:
                # Predecessor left, clear our predecessor
                with self.ring.ring_lock:
                    self.ring.predecessor = None
                    logger.info("Cleared predecessor (node left)")
            
            return {'success': True}
        
        elif req_type == 'transfer_file':
            # New request type for file transfer
            filename = request.get('filename')
            content = request.get('content', '').encode('utf-8')
            file_hash = request.get('file_hash')
            from_node_id = request.get('from_node')
            
            # Store the file locally
            with self.file_manager.file_lock:
                file_record = FileRecord(filename, content, file_hash, set())
                self.file_manager.files[filename] = file_record
            
            logger.info(f"Received and stored file '{filename}' from node {from_node_id}")
            return {'success': True}
        
        elif req_type == 'store_token':
            # Store a token in the local inverted index
            token = request.get('token')
            token_hash = request.get('token_hash')
            file_metadata_dict = request.get('file_metadata')
            
            if token and file_metadata_dict:
                # Reconstruct FileMetadata from dict
                file_metadata = FileMetadata(
                    filename=file_metadata_dict['filename'],
                    file_hash=file_metadata_dict['file_hash'],
                    node_id=file_metadata_dict['node_id'],
                    node_address=file_metadata_dict['node_address'],
                    all_tokens=file_metadata_dict['all_tokens'],
                    file_size=file_metadata_dict['file_size']
                )
                
                # Store in local index
                with self.file_manager.index_lock:
                    if token not in self.file_manager.token_index:
                        self.file_manager.token_index[token] = TokenRecord(token, token_hash, {})
                    
                    self.file_manager.token_index[token].files[file_metadata.filename] = file_metadata
                
                logger.debug(f"Stored token '{token}' -> '{file_metadata.filename}' in local index")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Invalid token data'}
        
        elif req_type == 'lookup_token':
            # Look up a token in the local inverted index
            token = request.get('token')
            
            if token:
                with self.file_manager.index_lock:
                    if token in self.file_manager.token_index:
                        token_record = self.file_manager.token_index[token]
                        return {'success': True, 'token_record': token_record.to_dict()}
                    else:
                        return {'success': True, 'token_record': None}
            else:
                return {'success': False, 'error': 'Token not provided'}
        
        else:
            return {'success': False, 'error': f'Unknown request type: {req_type}'}
    
    def _load_initial_files(self, shared_folder: str):
        """Load files from shared folder."""
        logger.info(f"Loading files from {shared_folder}")
        
        for filename in os.listdir(shared_folder):
            filepath = os.path.join(shared_folder, filename)
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    
                    # Store in DHT
                    success = self.file_manager.store_file(filename, content)
                    if success:
                        logger.info(f"Loaded and distributed file: {filename}")
                    else:
                        logger.warning(f"Failed to distribute file: {filename}")
                        
                except Exception as e:
                    logger.error(f"Failed to load file {filename}: {e}")
    
    def _start_maintenance_tasks(self):
        """Start background maintenance tasks."""
        def stabilize_task():
            if self.running:
                try:
                    self.ring.stabilize()
                except Exception as e:
                    logger.warning(f"Stabilization error: {e}")
                
                if self.running:  # Check again before scheduling next
                    self.stabilize_timer = threading.Timer(STABILIZE_INTERVAL, stabilize_task)
                    self.stabilize_timer.start()
        
        def fix_fingers_task():
            if self.running:
                try:
                    self.ring.fix_fingers()
                except Exception as e:
                    logger.warning(f"Fix fingers error: {e}")
                
                if self.running:  # Check again before scheduling next
                    self.fix_fingers_timer = threading.Timer(FIX_FINGERS_INTERVAL, fix_fingers_task)
                    self.fix_fingers_timer.start()
        
        def check_predecessor_task():
            if self.running:
                try:
                    self.ring.check_predecessor()
                    # Also validate ring consistency periodically
                    if not self.ring.validate_ring_consistency():
                        self.ring.heal_ring()
                except Exception as e:
                    logger.warning(f"Check predecessor error: {e}")
                
                if self.running:  # Check again before scheduling next
                    self.check_predecessor_timer = threading.Timer(CHECK_PREDECESSOR_INTERVAL, check_predecessor_task)
                    self.check_predecessor_timer.start()
        
        # Start tasks with initial delay to allow for proper startup
        self.stabilize_timer = threading.Timer(2.0, stabilize_task)  # Initial delay
        self.stabilize_timer.start()
        
        self.fix_fingers_timer = threading.Timer(3.0, fix_fingers_task)  # Initial delay
        self.fix_fingers_timer.start()
        
        self.check_predecessor_timer = threading.Timer(5.0, check_predecessor_task)  # Initial delay
        self.check_predecessor_timer.start()
    
    def join_ring(self, bootstrap_address: str, bootstrap_port: int) -> bool:
        """Join an existing Chord ring."""
        try:
            # Register with bootstrap server
            peers = self._register_with_bootstrap(bootstrap_address, bootstrap_port)
            
            if peers:
                # Try to join through each peer until successful
                for peer_addr in peers:
                    try:
                        # Create node object for the peer
                        peer_parts = peer_addr.split(':')
                        peer_node = Node(
                            hash_key(peer_addr),
                            peer_parts[0],
                            int(peer_parts[1])
                        )
                        
                        # Try to join through this peer
                        success = self.ring.join(peer_node)
                        if success:
                            logger.info(f"Joined ring through {peer_node}")
                            
                            # Give some time for stabilization
                            time.sleep(1)
                            
                            # Force initial stabilization
                            self.ring.stabilize()
                            return True
                        else:
                            logger.warning(f"Failed to join through {peer_node}, trying next peer")
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Error joining through {peer_addr}: {e}")
                        continue
                
                # If no peers worked, create new ring
                logger.info("Could not join through any peer, creating new ring")
                success = self.ring.join(None)
                logger.info("Created new ring")
                return success
            else:
                # Create new ring
                success = self.ring.join(None)
                logger.info("Created new ring")
                return success
                
        except Exception as e:
            logger.error(f"Failed to join ring: {e}")
            return False
    
    def _register_with_bootstrap(self, bootstrap_address: str, bootstrap_port: int) -> List[str]:
        """Register with bootstrap server."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # Add timeout
            sock.connect((bootstrap_address, bootstrap_port))
            
            msg = f'REG {self.local_node.address} {self.local_node.port}'
            sock.sendall(msg.encode())
            
            data = sock.recv(1024).decode()
            sock.close()
            
            tokens = data.strip().split()
            if len(tokens) >= 2:
                if tokens[0] == 'REGOK':
                    n = int(tokens[1])
                    peers = []
                    for i in range(n):
                        if 2 + 2 * i + 1 < len(tokens):
                            peer_ip = tokens[2 + 2 * i]
                            peer_port = tokens[3 + 2 * i]
                            peer_addr = f"{peer_ip}:{peer_port}"
                            # Don't include ourselves in the peer list
                            if peer_addr != self.local_node.addr_str:
                                peers.append(peer_addr)
                    
                    logger.info(f"Registered with bootstrap, got {len(peers)} existing peers")
                    return peers
                elif 'AlreadyRegistered' in data:
                    logger.warning(f"Already registered with bootstrap, proceeding anyway")
                    return []  # Return empty list to create new ring
                else:
                    logger.warning(f"Bootstrap registration failed: {data}")
                    return []
            else:
                logger.warning(f"Invalid bootstrap response: {data}")
                return []
                
        except Exception as e:
            logger.error(f"Bootstrap registration failed: {e}")
            return []
    
    def stop(self):
        """Stop the Chord node gracefully."""
        logger.info(f"Stopping ChordNode {self.local_node.node_id}")
        
        # Attempt graceful leave if we're part of a ring
        if self.running:
            try:
                self.graceful_leave()
            except Exception as e:
                logger.warning(f"Error during graceful leave: {e}")
        
        self.running = False
        
        # Stop timers
        if self.stabilize_timer:
            self.stabilize_timer.cancel()
        if self.fix_fingers_timer:
            self.fix_fingers_timer.cancel()
        if self.check_predecessor_timer:
            self.check_predecessor_timer.cancel()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info(f"ChordNode {self.local_node.node_id} stopped")
    
    def search(self, query: str) -> List[Tuple[str, str]]:
        """Search for files matching the query using distributed inverted index."""
        # Use distributed inverted index for better partial search
        distributed_results = self.file_manager.search_files_distributed(query)
        # Convert to expected format (filename, location) - ignore relevance score for CLI simplicity
        return [(filename, location) for filename, location, score in distributed_results]
    
    def list_files(self) -> List[Tuple[str, str]]:
        """List all files in the ring."""
        return self.file_manager.search_files("")  # Empty query matches all files
    
    def download(self, filename: str) -> Optional[bytes]:
        """Download a file."""
        return self.file_manager.download_file(filename)
    
    def get_status(self) -> dict:
        """Get node status information."""
        return {
            'node_id': self.local_node.node_id,
            'address': self.local_node.addr_str,
            'local_files': self.file_manager.list_local_files(),
            'ring_info': self.ring.get_ring_info()
        }
    
    def graceful_leave(self):
        """Gracefully leave the ring by transferring data to successor."""
        logger.info(f"Node {self.local_node.node_id} initiating graceful leave")
        
        with self.ring.ring_lock:
            if self.ring.successor and self.ring.successor != self.local_node:
                # Transfer all files to successor
                files_transferred = 0
                with self.file_manager.file_lock:
                    for filename, file_record in self.file_manager.files.items():
                        success = self._transfer_file_to_successor(file_record)
                        if success:
                            files_transferred += 1
                        else:
                            logger.warning(f"Failed to transfer file {filename} to successor")
                
                logger.info(f"Transferred {files_transferred} files to successor {self.ring.successor.node_id}")
                
                # Notify predecessor about successor
                if self.ring.predecessor and self.ring.predecessor != self.local_node:
                    self._notify_predecessor_of_departure()
                
                # Notify successor about predecessor
                self._notify_successor_of_departure()
            
            else:
                logger.info("No successor to transfer data to (single node or ring broken)")
    
    def _transfer_file_to_successor(self, file_record: 'FileRecord') -> bool:
        """Transfer a single file to the successor node."""
        if not self.ring.successor or self.ring.successor == self.local_node:
            return False
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((self.ring.successor.address, self.ring.successor.port))
            
            request = {
                'type': 'transfer_file',
                'filename': file_record.filename,
                'content': file_record.content.decode('utf-8', errors='replace'),
                'file_hash': file_record.file_hash,
                'from_node': self.local_node.node_id
            }
            
            sock.sendall(json.dumps(request).encode() + b'\n')
            
            response_data = sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            sock.close()
            
            return response.get('success', False)
            
        except Exception as e:
            logger.error(f"Failed to transfer file {file_record.filename} to successor: {e}")
            return False
    
    def _notify_predecessor_of_departure(self):
        """Notify predecessor that we're leaving and update its successor."""
        if not self.ring.predecessor or self.ring.predecessor == self.local_node:
            return
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.ring.predecessor.address, self.ring.predecessor.port))
            
            request = {
                'type': 'update_successor',
                'new_successor': {
                    'node_id': self.ring.successor.node_id,
                    'address': self.ring.successor.address,
                    'port': self.ring.successor.port
                } if self.ring.successor != self.local_node else None
            }
            
            sock.sendall(json.dumps(request).encode() + b'\n')
            sock.recv(1024)  # Acknowledge
            sock.close()
            
            logger.info(f"Notified predecessor {self.ring.predecessor.node_id} of departure")
            
        except Exception as e:
            logger.warning(f"Failed to notify predecessor of departure: {e}")
    
    def _notify_successor_of_departure(self):
        """Notify successor that we're leaving and update its predecessor."""
        if not self.ring.successor or self.ring.successor == self.local_node:
            return
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.ring.successor.address, self.ring.successor.port))
            
            request = {
                'type': 'update_predecessor',
                'new_predecessor': {
                    'node_id': self.ring.predecessor.node_id,
                    'address': self.ring.predecessor.address,
                    'port': self.ring.predecessor.port
                } if self.ring.predecessor and self.ring.predecessor != self.local_node else None
            }
            
            sock.sendall(json.dumps(request).encode() + b'\n')
            sock.recv(1024)  # Acknowledge
            sock.close()
            
            logger.info(f"Notified successor {self.ring.successor.node_id} of departure")
            
        except Exception as e:
            logger.warning(f"Failed to notify successor of departure: {e}")

def main():
    parser = argparse.ArgumentParser(description='Chord DHT Node')
    parser.add_argument('--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('--shared-folder', type=str, help='Shared folder to load files from')
    parser.add_argument('--bootstrap-host', type=str, default=BOOTSTRAP_HOST, help='Bootstrap server host')
    parser.add_argument('--bootstrap-port', type=int, default=BOOTSTRAP_PORT, help='Bootstrap server port')
    
    args = parser.parse_args()
    
    # Create and start node
    node = ChordNode('127.0.0.1', args.port)
    
    def signal_handler(signum, frame):
        logger.info("Received signal, shutting down...")
        node.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start node
        node.start(args.shared_folder)
        
        # Join ring
        success = node.join_ring(args.bootstrap_host, args.bootstrap_port)
        if not success:
            logger.error("Failed to join ring, but continuing anyway")
        
        # CLI loop
        print(f"\nChord Node {node.local_node.node_id} is running on port {args.port}")
        print("Commands: search <query>, dsearch <query>, list, download <filename>, status, debug, leave, quit")
        
        while True:
            try:
                cmd = input("\n> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == 'quit':
                    break
                elif cmd[0] == 'search':
                    query = ' '.join(cmd[1:]) if len(cmd) > 1 else ''
                    results = node.search(query)
                    print(f"Found {len(results)} files:")
                    for filename, location in results:
                        print(f"  - {filename} @ {location}")
                
                elif cmd[0] == 'dsearch':
                    # Distributed search with relevance scoring
                    query = ' '.join(cmd[1:]) if len(cmd) > 1 else ''
                    results = node.file_manager.search_files_distributed(query)
                    print(f"Distributed search found {len(results)} files:")
                    for filename, location, score in results:
                        print(f"  - {filename} @ {location} (relevance: {score:.2f})")
                
                elif cmd[0] == 'list':
                    results = node.list_files()
                    print(f"Total files in ring: {len(results)}")
                    for filename, location in results:
                        print(f"  - {filename} @ {location}")
                
                elif cmd[0] == 'download':
                    if len(cmd) < 2:
                        print("Usage: download <filename>")
                        continue
                    
                    filename = cmd[1]
                    content = node.download(filename)
                    if content:
                        print(f"Downloaded {filename} ({len(content)} bytes)")
                        # Save to local file
                        with open(f"downloaded_{filename}", 'wb') as f:
                            f.write(content)
                        print(f"Saved as downloaded_{filename}")
                    else:
                        print(f"File {filename} not found")
                
                elif cmd[0] == 'status':
                    status = node.get_status()
                    print(f"Node ID: {status['node_id']}")
                    print(f"Address: {status['address']}")
                    print(f"Local files: {len(status['local_files'])}")
                    for filename in status['local_files']:
                        print(f"  - {filename}")
                    print(f"Ring info:")
                    ring_info = status['ring_info']
                    print(f"  Successor: {ring_info.get('successor')}")
                    print(f"  Predecessor: {ring_info.get('predecessor')}")
                    print(f"  Finger table: {ring_info.get('finger_table')}")
                
                elif cmd[0] == 'leave':
                    print("Initiating graceful leave...")
                    node.ring.graceful_leave()
                    print("Graceful leave completed. Node is still running but disconnected from ring.")
                    print("Use 'quit' to fully exit.")
                
                elif cmd[0] == 'debug':
                    # Additional debug command
                    print("=== RING DEBUG INFO ===")
                    status = node.get_status()
                    ring_info = status['ring_info']
                    print(f"Local Node: {status['node_id']}")
                    print(f"Successor: {ring_info.get('successor')}")
                    print(f"Predecessor: {ring_info.get('predecessor')}")
                    
                    # Test connectivity
                    if node.ring.successor and node.ring.successor != node.local_node:
                        alive = node.ring._ping_node(node.ring.successor)
                        print(f"Successor alive: {alive}")
                    if node.ring.predecessor:
                        alive = node.ring._ping_node(node.ring.predecessor)
                        print(f"Predecessor alive: {alive}")
                    
                    # Ring consistency
                    consistent = node.ring.validate_ring_consistency()
                    print(f"Ring consistent: {consistent}")
                    print("=======================")
                
                else:
                    print("Unknown command")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    finally:
        node.stop()


if __name__ == '__main__':
    main()
