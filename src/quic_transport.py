#!/usr/bin/env python3
"""
QUIC Communication Layer for Chord DHT
Implements QUIC-based communication with Protocol Buffers serialization.
"""

import asyncio
import logging
import ssl
from typing import Optional, Dict, Any, Tuple
from concurrent.futures import Future
import uuid
import time

from aioquic.asyncio import connect, serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated

import chord_pb2

logger = logging.getLogger(__name__)

class ChordQuicProtocol(QuicConnectionProtocol):
    """QUIC protocol handler for Chord communications."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_requests: Dict[int, Future] = {}
        self.request_counter = 0
        self.message_handlers = {}
        
    def quic_event_received(self, event: QuicEvent):
        """Handle QUIC events."""
        if isinstance(event, StreamDataReceived):
            self._handle_stream_data(event)
        elif isinstance(event, ConnectionTerminated):
            self._handle_connection_terminated(event)
    
    def _handle_stream_data(self, event: StreamDataReceived):
        """Handle incoming stream data."""
        try:
            # Parse the message
            message = chord_pb2.ChordMessage()
            message.ParseFromString(event.data)
            
            # Check if this is a response to a pending request
            if message.request_id in self.pending_requests:
                future = self.pending_requests.pop(message.request_id)
                if not future.done():
                    future.set_result(message)
                return
            
            # Handle as new request
            response = self._process_request(message)
            if response:
                # Send response back on the same stream
                response_data = response.SerializeToString()
                self._quic.send_stream_data(event.stream_id, response_data, end_stream=True)
                
        except Exception as e:
            logger.error(f"Error handling stream data: {e}")
    
    def _handle_connection_terminated(self, event: ConnectionTerminated):
        """Handle connection termination."""
        # Cancel all pending requests
        for future in self.pending_requests.values():
            if not future.done():
                future.set_exception(ConnectionError("Connection terminated"))
        self.pending_requests.clear()
    
    def _process_request(self, message: chord_pb2.ChordMessage) -> Optional[chord_pb2.ChordMessage]:
        """Process incoming request message."""
        handler = self.message_handlers.get(message.type)
        if handler:
            try:
                return handler(message)
            except Exception as e:
                logger.error(f"Error processing request {message.type}: {e}")
        else:
            logger.warning(f"No handler for message type: {message.type}")
        
        return None
    
    def register_handler(self, message_type: chord_pb2.ChordMessage.MessageType, handler):
        """Register a message handler."""
        self.message_handlers[message_type] = handler
    
    async def send_request(self, message: chord_pb2.ChordMessage, timeout: float = 10.0) -> chord_pb2.ChordMessage:
        """Send a request and wait for response."""
        # Assign request ID
        self.request_counter += 1
        message.request_id = self.request_counter
        
        # Create future for response
        future = Future()
        self.pending_requests[message.request_id] = future
        
        try:
            # Send message on new stream
            stream_id = self._quic.get_next_available_stream_id()
            message_data = message.SerializeToString()
            self._quic.send_stream_data(stream_id, message_data, end_stream=True)
            
            # Wait for response with timeout
            response = await asyncio.wait_for(
                asyncio.wrap_future(future),
                timeout=timeout
            )
            
            return response
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(message.request_id, None)
            raise TimeoutError(f"Request {message.request_id} timed out")
        except Exception as e:
            self.pending_requests.pop(message.request_id, None)
            raise


class QuicChordClient:
    """QUIC client for Chord node communications."""
    
    def __init__(self):
        self.connections: Dict[str, ChordQuicProtocol] = {}
        self.connection_locks: Dict[str, asyncio.Lock] = {}
        
    async def get_connection(self, host: str, port: int) -> ChordQuicProtocol:
        """Get or create connection to a host."""
        address = f"{host}:{port}"
        
        if address not in self.connection_locks:
            self.connection_locks[address] = asyncio.Lock()
        
        async with self.connection_locks[address]:
            if address in self.connections:
                return self.connections[address]
            
            # Create new connection
            configuration = QuicConfiguration(is_client=True)
            configuration.verify_mode = ssl.CERT_NONE  # For development
            
            try:
                protocol = await connect(
                    host, port,
                    configuration=configuration,
                    create_protocol=ChordQuicProtocol
                )
                
                self.connections[address] = protocol
                return protocol
                
            except Exception as e:
                logger.error(f"Failed to connect to {address}: {e}")
                raise
    
    async def send_request(self, host: str, port: int, message: chord_pb2.ChordMessage, timeout: float = 10.0) -> chord_pb2.ChordMessage:
        """Send request to a node."""
        try:
            protocol = await self.get_connection(host, port)
            return await protocol.send_request(message, timeout)
        except Exception as e:
            # Remove failed connection
            address = f"{host}:{port}"
            self.connections.pop(address, None)
            raise
    
    async def close_all_connections(self):
        """Close all connections."""
        for protocol in self.connections.values():
            protocol.close()
        self.connections.clear()


class QuicChordServer:
    """QUIC server for Chord node communications."""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.protocol_factory = None
        self.message_handlers = {}
        
    def register_handler(self, message_type: chord_pb2.ChordMessage.MessageType, handler):
        """Register a message handler."""
        self.message_handlers[message_type] = handler
    
    def _create_protocol(self, *args, **kwargs) -> ChordQuicProtocol:
        """Create protocol instance with registered handlers."""
        protocol = ChordQuicProtocol(*args, **kwargs)
        for msg_type, handler in self.message_handlers.items():
            protocol.register_handler(msg_type, handler)
        return protocol
    
    async def start(self):
        """Start the QUIC server."""
        configuration = QuicConfiguration(is_client=False)
        
        # Generate self-signed certificate for development
        try:
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as cert_file, \
                 tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as key_file:
                
                # Generate self-signed certificate
                subprocess.run([
                    'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-keyout', key_file.name,
                    '-out', cert_file.name, '-days', '365', '-nodes', '-subj', '/CN=localhost'
                ], check=True, capture_output=True)
                
                configuration.load_cert_chain(cert_file.name, key_file.name)
                
        except Exception as e:
            logger.warning(f"Could not generate certificate: {e}")
            # Use a minimal configuration without certificates for development
            pass
        
        self.server = await serve(
            self.host, self.port,
            configuration=configuration,
            create_protocol=self._create_protocol
        )
        
        logger.info(f"QUIC server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the QUIC server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None


# Protocol buffer message builders and parsers
class ProtobufMessageBuilder:
    """Helper class to build protobuf messages."""
    
    @staticmethod
    def build_node(node_id: int, address: str, port: int) -> chord_pb2.Node:
        """Build a Node protobuf message."""
        node = chord_pb2.Node()
        node.node_id = node_id
        node.address = address
        node.port = port
        return node
    
    @staticmethod
    def build_find_successor_request(key_id: int) -> chord_pb2.ChordMessage:
        """Build find successor request."""
        request = chord_pb2.FindSuccessorRequest()
        request.key_id = key_id
        
        message = chord_pb2.ChordMessage()
        message.type = chord_pb2.ChordMessage.FIND_SUCCESSOR
        message.payload = request.SerializeToString()
        
        return message
    
    @staticmethod
    def build_find_successor_response(success: bool, successor=None, error: str = "") -> chord_pb2.ChordMessage:
        """Build find successor response."""
        response = chord_pb2.FindSuccessorResponse()
        response.success = success
        if successor:
            response.successor.CopyFrom(ProtobufMessageBuilder.build_node(
                successor.node_id, successor.address, successor.port
            ))
        if error:
            response.error = error
        
        message = chord_pb2.ChordMessage()
        message.type = chord_pb2.ChordMessage.FIND_SUCCESSOR
        message.payload = response.SerializeToString()
        
        return message
    
    @staticmethod
    def build_notify_request(node_id: int, address: str, port: int) -> chord_pb2.ChordMessage:
        """Build notify request."""
        request = chord_pb2.NotifyRequest()
        request.node.CopyFrom(ProtobufMessageBuilder.build_node(node_id, address, port))
        
        message = chord_pb2.ChordMessage()
        message.type = chord_pb2.ChordMessage.NOTIFY
        message.payload = request.SerializeToString()
        
        return message
    
    @staticmethod
    def build_store_file_request(filename: str, content: bytes, file_hash: int) -> chord_pb2.ChordMessage:
        """Build store file request."""
        request = chord_pb2.StoreFileRequest()
        request.filename = filename
        request.content = content
        request.file_hash = file_hash
        
        message = chord_pb2.ChordMessage()
        message.type = chord_pb2.ChordMessage.STORE_FILE
        message.payload = request.SerializeToString()
        
        return message
    
    @staticmethod
    def build_search_files_request(query: str) -> chord_pb2.ChordMessage:
        """Build search files request."""
        request = chord_pb2.SearchFilesRequest()
        request.query = query
        
        message = chord_pb2.ChordMessage()
        message.type = chord_pb2.ChordMessage.SEARCH_FILES
        message.payload = request.SerializeToString()
        
        return message
    
    @staticmethod
    def build_ping_request() -> chord_pb2.ChordMessage:
        """Build ping request."""
        request = chord_pb2.PingRequest()
        
        message = chord_pb2.ChordMessage()
        message.type = chord_pb2.ChordMessage.PING
        message.payload = request.SerializeToString()
        
        return message


class ProtobufMessageParser:
    """Helper class to parse protobuf messages."""
    
    @staticmethod
    def parse_find_successor_request(payload: bytes) -> chord_pb2.FindSuccessorRequest:
        """Parse find successor request."""
        request = chord_pb2.FindSuccessorRequest()
        request.ParseFromString(payload)
        return request
    
    @staticmethod
    def parse_find_successor_response(payload: bytes) -> chord_pb2.FindSuccessorResponse:
        """Parse find successor response."""
        response = chord_pb2.FindSuccessorResponse()
        response.ParseFromString(payload)
        return response
    
    @staticmethod
    def parse_notify_request(payload: bytes) -> chord_pb2.NotifyRequest:
        """Parse notify request."""
        request = chord_pb2.NotifyRequest()
        request.ParseFromString(payload)
        return request
    
    @staticmethod
    def parse_store_file_request(payload: bytes) -> chord_pb2.StoreFileRequest:
        """Parse store file request."""
        request = chord_pb2.StoreFileRequest()
        request.ParseFromString(payload)
        return request
    
    @staticmethod
    def parse_search_files_request(payload: bytes) -> chord_pb2.SearchFilesRequest:
        """Parse search files request."""
        request = chord_pb2.SearchFilesRequest()
        request.ParseFromString(payload)
        return request


# Async/sync bridge for backward compatibility
class AsyncBridge:
    """Bridge between async QUIC layer and sync Chord implementation."""
    
    def __init__(self):
        self.loop = None
        self.client = None
        
    def start(self):
        """Start the async event loop in background thread."""
        if self.loop is None:
            import threading
            
            def run_loop():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.client = QuicChordClient()
                self.loop.run_forever()
            
            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()
            
            # Wait for loop to start
            while self.loop is None:
                time.sleep(0.01)
    
    def stop(self):
        """Stop the async event loop."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.client.close_all_connections(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop = None
    
    def send_request(self, host: str, port: int, message: chord_pb2.ChordMessage, timeout: float = 10.0) -> chord_pb2.ChordMessage:
        """Send request synchronously."""
        if not self.loop:
            raise RuntimeError("AsyncBridge not started")
        
        future = asyncio.run_coroutine_threadsafe(
            self.client.send_request(host, port, message, timeout),
            self.loop
        )
        
        return future.result(timeout + 1.0)  # Add small buffer to timeout
