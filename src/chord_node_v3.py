#!/usr/bin/env python3
"""
Phase 3: QUIC-enabled Chord DHT Implementation
Extends chord_node_v2.py with QUIC transport and Protocol Buffers.
"""

import asyncio
import threading
import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

# Import base implementation
from chord_node_v2 import (
    Node, FileRecord, TokenRecord, FileMetadata, ChordRing, FileManager,
    hash_key, in_range, in_range_inclusive, tokenize_filename, compute_relevance_score,
    M, RING_SIZE, REPLICATION_FACTOR, BOOTSTRAP_HOST, BOOTSTRAP_PORT,
    STABILIZE_INTERVAL, FIX_FINGERS_INTERVAL, CHECK_PREDECESSOR_INTERVAL
)

# Import QUIC transport layer
from quic_transport import (
    QuicChordServer, QuicChordClient, AsyncBridge,
    ProtobufMessageBuilder, ProtobufMessageParser
)
import chord_pb2

logger = logging.getLogger(__name__)


class QuicChordRing(ChordRing):
    """Chord ring with QUIC transport layer."""
    
    def __init__(self, local_node: Node, async_bridge: AsyncBridge):
        super().__init__(local_node)
        self.async_bridge = async_bridge
    
    def _remote_find_successor(self, node: Node, key_id: int) -> Optional[Node]:
        """Query a remote node to find successor using QUIC."""
        try:
            # Build protobuf message
            message = ProtobufMessageBuilder.build_find_successor_request(key_id)
            
            # Send request via QUIC
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=5.0
            )
            
            # Parse response
            response = ProtobufMessageParser.parse_find_successor_response(response_msg.payload)
            
            if response.success and response.HasField('successor'):
                return Node(
                    response.successor.node_id,
                    response.successor.address,
                    response.successor.port
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"QUIC find_successor failed for {node}: {e}")
            return None
    
    def _get_predecessor(self, node: Node) -> Optional[Node]:
        """Get the predecessor of a remote node using QUIC."""
        try:
            # Build request
            message = chord_pb2.ChordMessage()
            message.type = chord_pb2.ChordMessage.GET_PREDECESSOR
            message.payload = chord_pb2.GetPredecessorRequest().SerializeToString()
            
            # Send request
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=5.0
            )
            
            # Parse response
            response = chord_pb2.GetPredecessorResponse()
            response.ParseFromString(response_msg.payload)
            
            if response.success and response.HasField('predecessor'):
                return Node(
                    response.predecessor.node_id,
                    response.predecessor.address,
                    response.predecessor.port
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"QUIC get_predecessor failed for {node}: {e}")
            return None
    
    def _notify(self, node: Node):
        """Notify a node that we might be its predecessor using QUIC."""
        if node == self.local_node:
            return
            
        try:
            # Build notify message
            message = ProtobufMessageBuilder.build_notify_request(
                self.local_node.node_id,
                self.local_node.address, 
                self.local_node.port
            )
            
            # Send request
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=5.0
            )
            
            # Parse response
            response = chord_pb2.NotifyResponse()
            response.ParseFromString(response_msg.payload)
            
            if not response.success:
                logger.warning(f"Notify failed for {node}")
                
        except Exception as e:
            logger.warning(f"QUIC notify failed for {node}: {e}")
    
    def _ping_node(self, node: Node) -> bool:
        """Check if a node is alive using QUIC."""
        try:
            message = ProtobufMessageBuilder.build_ping_request()
            
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=3.0
            )
            
            response = chord_pb2.PingResponse()
            response.ParseFromString(response_msg.payload)
            
            return response.success
            
        except Exception:
            return False


class QuicFileManager(FileManager):
    """File manager with QUIC transport layer."""
    
    def __init__(self, local_node: Node, ring: QuicChordRing, async_bridge: AsyncBridge):
        super().__init__(local_node, ring)
        self.async_bridge = async_bridge
    
    def _remote_store_file(self, node: Node, file_record: FileRecord) -> bool:
        """Store a file on a remote node using QUIC."""
        try:
            message = ProtobufMessageBuilder.build_store_file_request(
                file_record.filename,
                file_record.content,
                file_record.file_hash
            )
            
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=10.0
            )
            
            response = chord_pb2.StoreFileResponse()
            response.ParseFromString(response_msg.payload)
            
            if response.success:
                logger.info(f"File '{file_record.filename}' stored on remote node {node.node_id}")
                return True
            else:
                logger.warning(f"Failed to store file on {node.node_id}: {response.error}")
                return False
                
        except Exception as e:
            logger.warning(f"QUIC store failed for {node}: {e}")
            return False
    
    def _remote_search_files(self, node: Node, query: str) -> List[Tuple[str, str]]:
        """Search for files on a remote node using QUIC."""
        try:
            message = ProtobufMessageBuilder.build_search_files_request(query)
            
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=10.0
            )
            
            response = chord_pb2.SearchFilesResponse()
            response.ParseFromString(response_msg.payload)
            
            if response.success:
                return [(f, node.addr_str) for f in response.files]
            else:
                return []
                
        except Exception as e:
            logger.warning(f"QUIC search failed for {node}: {e}")
            return []
    
    def _remote_store_token(self, token: str, token_hash: int, file_metadata: FileMetadata, node: Node):
        """Store a token record on a remote node using QUIC."""
        try:
            # Build file metadata protobuf
            pb_metadata = chord_pb2.FileMetadata()
            pb_metadata.filename = file_metadata.filename
            pb_metadata.file_hash = file_metadata.file_hash
            pb_metadata.node_id = file_metadata.node_id
            pb_metadata.node_address = file_metadata.node_address
            pb_metadata.all_tokens.extend(file_metadata.all_tokens)
            pb_metadata.file_size = file_metadata.file_size
            
            # Build request
            request = chord_pb2.StoreTokenRequest()
            request.token = token
            request.token_hash = token_hash
            request.file_metadata.CopyFrom(pb_metadata)
            
            message = chord_pb2.ChordMessage()
            message.type = chord_pb2.ChordMessage.STORE_TOKEN
            message.payload = request.SerializeToString()
            
            response_msg = self.async_bridge.send_request(
                node.address, node.port, message, timeout=10.0
            )
            
            response = chord_pb2.StoreTokenResponse()
            response.ParseFromString(response_msg.payload)
            
            if response.success:
                logger.debug(f"Token '{token}' stored on remote node {node.node_id}")
            else:
                logger.warning(f"Failed to store token on {node.node_id}: {response.error}")
                
        except Exception as e:
            logger.warning(f"QUIC token store failed for {node}: {e}")


class QuicChordNode:
    """Main Chord node implementation with QUIC transport."""
    
    def __init__(self, address: str, port: int):
        self.local_node = Node(hash_key(f"{address}:{port}"), address, port)
        
        # Initialize async bridge
        self.async_bridge = AsyncBridge()
        
        # Initialize components with QUIC support
        self.ring = QuicChordRing(self.local_node, self.async_bridge)
        self.file_manager = QuicFileManager(self.local_node, self.ring, self.async_bridge)
        
        # QUIC server
        self.quic_server = QuicChordServer(address, port)
        self.server_loop = None
        self.server_thread = None
        
        self.running = False
        
        # Background maintenance tasks (same as v2)
        self.stabilize_timer: Optional[threading.Timer] = None
        self.fix_fingers_timer: Optional[threading.Timer] = None
        self.check_predecessor_timer: Optional[threading.Timer] = None
        
        logger.info(f"Created QuicChordNode {self.local_node}")
        
        # Register QUIC message handlers
        self._register_quic_handlers()
    
    def _register_quic_handlers(self):
        """Register QUIC message handlers."""
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.FIND_SUCCESSOR,
            self._handle_find_successor
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.GET_PREDECESSOR, 
            self._handle_get_predecessor
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.GET_SUCCESSOR,
            self._handle_get_successor
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.NOTIFY,
            self._handle_notify
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.STORE_FILE,
            self._handle_store_file
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.SEARCH_FILES,
            self._handle_search_files
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.STORE_TOKEN,
            self._handle_store_token
        )
        self.quic_server.register_handler(
            chord_pb2.ChordMessage.PING,
            self._handle_ping
        )
    
    def _handle_find_successor(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle find successor request."""
        try:
            request = ProtobufMessageParser.parse_find_successor_request(message.payload)
            successor = self.ring.find_successor(request.key_id)
            
            return ProtobufMessageBuilder.build_find_successor_response(
                success=True,
                successor=successor
            )
            
        except Exception as e:
            return ProtobufMessageBuilder.build_find_successor_response(
                success=False,
                error=str(e)
            )
    
    def _handle_get_predecessor(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle get predecessor request."""
        response = chord_pb2.GetPredecessorResponse()
        response.success = True
        
        if self.ring.predecessor:
            response.predecessor.CopyFrom(ProtobufMessageBuilder.build_node(
                self.ring.predecessor.node_id,
                self.ring.predecessor.address,
                self.ring.predecessor.port
            ))
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.GET_PREDECESSOR
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    def _handle_get_successor(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle get successor request."""
        response = chord_pb2.GetSuccessorResponse()
        response.success = True
        
        if self.ring.successor:
            response.successor.CopyFrom(ProtobufMessageBuilder.build_node(
                self.ring.successor.node_id,
                self.ring.successor.address,
                self.ring.successor.port
            ))
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.GET_SUCCESSOR
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    def _handle_notify(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle notify request."""
        try:
            request = ProtobufMessageParser.parse_notify_request(message.payload)
            node = Node(
                request.node.node_id,
                request.node.address,
                request.node.port
            )
            
            self.ring.notify(node)
            
            response = chord_pb2.NotifyResponse()
            response.success = True
            
        except Exception as e:
            response = chord_pb2.NotifyResponse()
            response.success = False
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.NOTIFY
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    def _handle_store_file(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle store file request."""
        try:
            request = ProtobufMessageParser.parse_store_file_request(message.payload)
            
            # Store file locally
            with self.file_manager.file_lock:
                file_record = FileRecord(
                    request.filename,
                    request.content,
                    request.file_hash,
                    set()
                )
                self.file_manager.files[request.filename] = file_record
            
            logger.info(f"Stored file '{request.filename}' via QUIC")
            
            response = chord_pb2.StoreFileResponse()
            response.success = True
            
        except Exception as e:
            logger.error(f"Error storing file: {e}")
            response = chord_pb2.StoreFileResponse()
            response.success = False
            response.error = str(e)
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.STORE_FILE
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    def _handle_search_files(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle search files request."""
        try:
            request = ProtobufMessageParser.parse_search_files_request(message.payload)
            
            # Search locally
            files = []
            with self.file_manager.file_lock:
                for filename in self.file_manager.files.keys():
                    if request.query.lower() in filename.lower():
                        files.append(filename)
            
            response = chord_pb2.SearchFilesResponse()
            response.success = True
            response.files.extend(files)
            
        except Exception as e:
            response = chord_pb2.SearchFilesResponse()
            response.success = False
            response.error = str(e)
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.SEARCH_FILES
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    def _handle_store_token(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle store token request."""
        try:
            request = chord_pb2.StoreTokenRequest()
            request.ParseFromString(message.payload)
            
            # Convert protobuf to FileMetadata
            file_metadata = FileMetadata(
                filename=request.file_metadata.filename,
                file_hash=request.file_metadata.file_hash,
                node_id=request.file_metadata.node_id,
                node_address=request.file_metadata.node_address,
                all_tokens=list(request.file_metadata.all_tokens),
                file_size=request.file_metadata.file_size
            )
            
            # Store in local index
            with self.file_manager.index_lock:
                if request.token not in self.file_manager.token_index:
                    self.file_manager.token_index[request.token] = TokenRecord(
                        request.token, request.token_hash, {}
                    )
                
                self.file_manager.token_index[request.token].files[file_metadata.filename] = file_metadata
            
            logger.debug(f"Stored token '{request.token}' -> '{file_metadata.filename}' via QUIC")
            
            response = chord_pb2.StoreTokenResponse()
            response.success = True
            
        except Exception as e:
            logger.error(f"Error storing token: {e}")
            response = chord_pb2.StoreTokenResponse()
            response.success = False
            response.error = str(e)
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.STORE_TOKEN
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    def _handle_ping(self, message: chord_pb2.ChordMessage) -> chord_pb2.ChordMessage:
        """Handle ping request."""
        response = chord_pb2.PingResponse()
        response.success = True
        
        msg = chord_pb2.ChordMessage()
        msg.type = chord_pb2.ChordMessage.PING
        msg.payload = response.SerializeToString()
        msg.request_id = message.request_id
        
        return msg
    
    async def start(self, shared_folder: Optional[str] = None):
        """Start the QUIC Chord node."""
        try:
            self.running = True
            
            # Start async bridge
            self.async_bridge.start()
            
            # Start QUIC server
            await self.quic_server.start()
            
            # Load initial files if shared folder provided
            if shared_folder:
                self._load_initial_files(shared_folder)
            
            # Start background maintenance tasks
            self._start_maintenance_tasks()
            
            logger.info(f"QuicChordNode {self.local_node.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start QuicChordNode {self.local_node.node_id}: {e}")
            await self.stop()
            raise
    
    def _load_initial_files(self, shared_folder: str):
        """Load files from shared folder (same as v2)."""
        import os
        logger.info(f"Loading files from {shared_folder}")
        
        if not os.path.exists(shared_folder):
            return
            
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
        """Start background maintenance tasks (same as v2)."""
        def stabilize_task():
            if self.running:
                try:
                    self.ring.stabilize()
                except Exception as e:
                    logger.warning(f"Stabilization error: {e}")
                
                if self.running:
                    self.stabilize_timer = threading.Timer(STABILIZE_INTERVAL, stabilize_task)
                    self.stabilize_timer.start()
        
        def fix_fingers_task():
            if self.running:
                try:
                    self.ring.fix_fingers()
                except Exception as e:
                    logger.warning(f"Fix fingers error: {e}")
                
                if self.running:
                    self.fix_fingers_timer = threading.Timer(FIX_FINGERS_INTERVAL, fix_fingers_task)
                    self.fix_fingers_timer.start()
        
        def check_predecessor_task():
            if self.running:
                try:
                    self.ring.check_predecessor()
                    if not self.ring.validate_ring_consistency():
                        self.ring.heal_ring()
                except Exception as e:
                    logger.warning(f"Check predecessor error: {e}")
                
                if self.running:
                    self.check_predecessor_timer = threading.Timer(CHECK_PREDECESSOR_INTERVAL, check_predecessor_task)
                    self.check_predecessor_timer.start()
        
        # Start tasks with initial delay
        self.stabilize_timer = threading.Timer(2.0, stabilize_task)
        self.stabilize_timer.start()
        
        self.fix_fingers_timer = threading.Timer(3.0, fix_fingers_task)
        self.fix_fingers_timer.start()
        
        self.check_predecessor_timer = threading.Timer(5.0, check_predecessor_task)
        self.check_predecessor_timer.start()
    
    async def stop(self):
        """Stop the QUIC Chord node."""
        logger.info(f"Stopping QuicChordNode {self.local_node.node_id}")
        
        self.running = False
        
        # Stop timers
        if self.stabilize_timer:
            self.stabilize_timer.cancel()
        if self.fix_fingers_timer:
            self.fix_fingers_timer.cancel()
        if self.check_predecessor_timer:
            self.check_predecessor_timer.cancel()
        
        # Stop QUIC server
        if self.quic_server:
            await self.quic_server.stop()
        
        # Stop async bridge
        if self.async_bridge:
            self.async_bridge.stop()
        
        logger.info(f"QuicChordNode {self.local_node.node_id} stopped")
    
    # Public API methods (same interface as v2)
    def search(self, query: str) -> List[Tuple[str, str]]:
        """Search for files matching the query."""
        return self.file_manager.search_files(query)
    
    def list_files(self) -> List[Tuple[str, str]]:
        """List all files in the ring."""
        return self.file_manager.search_files("")
    
    def download(self, filename: str) -> Optional[bytes]:
        """Download a file."""
        return self.file_manager.download_file(filename)
    
    def get_status(self) -> dict:
        """Get node status information."""
        return {
            'node_id': self.local_node.node_id,
            'address': self.local_node.addr_str,
            'local_files': self.file_manager.list_local_files(),
            'ring_info': self.ring.get_ring_info(),
            'transport': 'QUIC'
        }
