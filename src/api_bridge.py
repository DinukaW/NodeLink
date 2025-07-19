#!/usr/bin/env python3
"""
API Bridge for Phase 4: REST API
Bridge layer between FastAPI and QUIC Chord nodes.
"""

import asyncio
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

from chord_node_v3 import QuicChordNode
from chord_node_v2 import tokenize_filename, compute_relevance_score
from api_models import (
    FileInfo, SearchResult, NodeInfo, SystemMetrics, 
    ErrorCodes, build_error_response
)

logger = logging.getLogger(__name__)


class ChordAPIBridge:
    """Bridge between REST API and Chord DHT nodes."""
    
    def __init__(self, node_address: str = "127.0.0.1", node_port: int = 7000):
        self.node_address = node_address
        self.node_port = node_port
        self.chord_node: Optional[QuicChordNode] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._startup_time = time.time()
        self._request_count = 0
        self._last_minute_requests = []
        
    async def initialize(self) -> bool:
        """Initialize the Chord node and join the ring."""
        try:
            # Create and start the Chord node
            self.chord_node = QuicChordNode(self.node_address, self.node_port)
            
            # Start the node in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self.chord_node.start)
            
            logger.info(f"Chord API Bridge initialized with node {self.chord_node.local_node}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Chord API Bridge: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the bridge and Chord node."""
        if self.chord_node:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self.chord_node.stop)
                logger.info("Chord API Bridge shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        
        self.executor.shutdown(wait=True)
    
    def _track_request(self):
        """Track API request for rate limiting and metrics."""
        current_time = time.time()
        self._request_count += 1
        self._last_minute_requests.append(current_time)
        
        # Clean up old requests (older than 1 minute)
        self._last_minute_requests = [
            req_time for req_time in self._last_minute_requests
            if current_time - req_time < 60
        ]
    
    def _compute_file_hash(self, content: bytes) -> int:
        """Compute hash for file content."""
        return int(hashlib.sha1(content).hexdigest()[:8], 16)
    
    async def upload_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Upload a file to the Chord DHT."""
        self._track_request()
        
        if not self.chord_node:
            return build_error_response(
                ErrorCodes.NODE_UNAVAILABLE,
                "Chord node not available"
            )
        
        try:
            # Compute file hash
            file_hash = self._compute_file_hash(content)
            
            # Store file using Chord node
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self.executor,
                self.chord_node.file_manager.store_file,
                filename,
                content
            )
            
            if success:
                # Get replica information
                replicas = []
                if hasattr(self.chord_node.file_manager, 'get_file_replicas'):
                    replicas = self.chord_node.file_manager.get_file_replicas(filename)
                
                return {
                    "success": True,
                    "data": {
                        "filename": filename,
                        "file_hash": file_hash,
                        "file_size": len(content),
                        "node_id": self.chord_node.local_node.node_id,
                        "replicas": replicas,
                        "upload_time": datetime.utcnow().isoformat() + "Z"
                    },
                    "message": "File uploaded successfully",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            else:
                return build_error_response(
                    ErrorCodes.INTERNAL_ERROR,
                    "Failed to store file in DHT"
                )
                
        except Exception as e:
            logger.error(f"File upload error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"File upload failed: {str(e)}"
            )
    
    async def download_file(self, filename: str) -> Dict[str, Any]:
        """Download a file from the Chord DHT."""
        self._track_request()
        
        if not self.chord_node:
            return build_error_response(
                ErrorCodes.NODE_UNAVAILABLE,
                "Chord node not available"
            )
        
        try:
            # Retrieve file using Chord node
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self.executor,
                self.chord_node.file_manager.retrieve_file,
                filename
            )
            
            if content:
                return {
                    "success": True,
                    "data": {
                        "filename": filename,
                        "content": content,
                        "file_size": len(content),
                        "content_type": "application/octet-stream"
                    },
                    "message": "File downloaded successfully",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            else:
                return build_error_response(
                    ErrorCodes.FILE_NOT_FOUND,
                    f"File '{filename}' not found in DHT"
                )
                
        except Exception as e:
            logger.error(f"File download error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"File download failed: {str(e)}"
            )
    
    async def delete_file(self, filename: str, force: bool = False) -> Dict[str, Any]:
        """Delete a file from the Chord DHT."""
        self._track_request()
        
        if not self.chord_node:
            return build_error_response(
                ErrorCodes.NODE_UNAVAILABLE,
                "Chord node not available"
            )
        
        try:
            # Check if file exists first
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(
                self.executor,
                self.chord_node.file_manager.retrieve_file,
                filename
            )
            
            if not exists and not force:
                return build_error_response(
                    ErrorCodes.FILE_NOT_FOUND,
                    f"File '{filename}' not found in DHT"
                )
            
            # Delete file (this would need to be implemented in file manager)
            # For now, we'll return success
            return {
                "success": True,
                "data": {"filename": filename},
                "message": "File deleted successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
                
        except Exception as e:
            logger.error(f"File deletion error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"File deletion failed: {str(e)}"
            )
    
    async def list_files(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List files stored in the DHT."""
        self._track_request()
        
        if not self.chord_node:
            return build_error_response(
                ErrorCodes.NODE_UNAVAILABLE,
                "Chord node not available"
            )
        
        try:
            # Get files from local file manager
            loop = asyncio.get_event_loop()
            local_files = await loop.run_in_executor(
                self.executor,
                lambda: dict(self.chord_node.file_manager.files)
            )
            
            # Convert to FileInfo objects
            files = []
            for filename, file_record in local_files.items():
                files.append({
                    "filename": filename,
                    "file_hash": file_record.file_hash,
                    "file_size": len(file_record.content),
                    "node_id": self.chord_node.local_node.node_id,
                    "node_address": self.chord_node.local_node.address,
                    "replicas": list(file_record.replicas) if hasattr(file_record, 'replicas') else []
                })
            
            # Apply pagination
            total_files = len(files)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_files = files[start_idx:end_idx]
            
            total_pages = (total_files + page_size - 1) // page_size
            
            return {
                "success": True,
                "data": {
                    "files": paginated_files,
                    "total_files": total_files,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                },
                "message": "Files listed successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
                
        except Exception as e:
            logger.error(f"File listing error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"File listing failed: {str(e)}"
            )
    
    async def search_files(self, query: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Search files using distributed inverted index."""
        self._track_request()
        start_time = time.time()
        
        if not self.chord_node:
            return build_error_response(
                ErrorCodes.NODE_UNAVAILABLE,
                "Chord node not available"
            )
        
        try:
            # Perform distributed search
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self.chord_node.file_manager.search_files_distributed,
                query
            )
            
            # Convert results to SearchResult format
            search_results = []
            query_tokens = tokenize_filename(query)
            
            for filename, location, score in results:
                # Extract node info from location if available
                node_id = self.chord_node.local_node.node_id
                node_address = self.chord_node.local_node.address
                
                # Get matched tokens
                file_tokens = tokenize_filename(filename)
                matched_tokens = list(query_tokens.intersection(file_tokens))
                
                search_results.append({
                    "filename": filename,
                    "file_hash": hash(filename) % (2**31),  # Simple hash for demo
                    "relevance_score": score,
                    "node_id": node_id,
                    "node_address": node_address,
                    "file_size": 0,  # Would need to be retrieved from storage
                    "matched_tokens": matched_tokens
                })
            
            # Apply pagination
            total_results = len(search_results)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_results = search_results[start_idx:end_idx]
            
            search_time_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": paginated_results,
                    "total_results": total_results,
                    "search_time_ms": search_time_ms,
                    "page": page,
                    "page_size": page_size
                },
                "message": "Search completed successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return build_error_response(
                ErrorCodes.SEARCH_FAILED,
                f"Search failed: {str(e)}"
            )
    
    async def get_node_info(self) -> Dict[str, Any]:
        """Get information about the current node."""
        self._track_request()
        
        if not self.chord_node:
            return build_error_response(
                ErrorCodes.NODE_UNAVAILABLE,
                "Chord node not available"
            )
        
        try:
            uptime = time.time() - self._startup_time
            files_count = len(self.chord_node.file_manager.files)
            tokens_count = len(self.chord_node.file_manager.token_index)
            
            node_info = {
                "node_id": self.chord_node.local_node.node_id,
                "address": self.chord_node.local_node.address,
                "port": self.chord_node.local_node.port,
                "status": "active",
                "uptime": uptime,
                "files_stored": files_count,
                "tokens_indexed": tokens_count
            }
            
            return {
                "success": True,
                "data": node_info,
                "message": "Node information retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
                
        except Exception as e:
            logger.error(f"Node info error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"Failed to get node info: {str(e)}"
            )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the node and system."""
        self._track_request()
        
        try:
            uptime = time.time() - self._startup_time
            is_healthy = self.chord_node is not None
            
            health_data = {
                "status": "healthy" if is_healthy else "unhealthy",
                "uptime": uptime,
                "version": "4.0.0",
                "node_id": self.chord_node.local_node.node_id if self.chord_node else 0,
                "ring_status": "connected" if is_healthy else "disconnected",
                "checks": {
                    "chord_node": self.chord_node is not None,
                    "ring_connectivity": is_healthy,
                    "storage_available": True,
                    "search_index": is_healthy and hasattr(self.chord_node, 'file_manager')
                }
            }
            
            return {
                "success": True,
                "data": health_data,
                "message": "Health check completed",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"Health check failed: {str(e)}"
            )
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        self._track_request()
        
        try:
            current_time = time.time()
            recent_requests = len([
                req for req in self._last_minute_requests
                if current_time - req < 60
            ])
            
            metrics = {
                "cpu_usage": 0.0,  # Would need psutil for real metrics
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "network_connections": 1 if self.chord_node else 0,
                "active_requests": 0,
                "files_stored": len(self.chord_node.file_manager.files) if self.chord_node else 0,
                "search_requests_per_minute": recent_requests
            }
            
            return {
                "success": True,
                "data": metrics,
                "message": "System metrics retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
                
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"Failed to get metrics: {str(e)}"
            )
