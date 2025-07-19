#!/usr/bin/env python3
"""
Advanced Chord DHT File Sharing System

A production-ready, distributed file sharing system built on the Chord DHT protocol 
with modern networking and monitoring capabilities.

Modules:
- chord_node_v2: Chord DHT with distributed search (Phase 1 & 2)
- chord_node_v3: QUIC-enabled Chord node (Phase 3)  
- quic_transport: QUIC transport layer and Protocol Buffers
- rest_api: FastAPI web server with REST endpoints (Phase 4)
- api_bridge: Integration layer between REST API and Chord DHT
- api_models: Pydantic models for request/response validation
"""

__version__ = "4.0.0"
__author__ = "Advanced Chord DHT Team"
__description__ = "Advanced Chord DHT File Sharing System"

# Module imports for easier access
try:
    from .chord_node_v2 import ChordNode
    from .chord_node_v3 import QuicChordNode
    from .quic_transport import QuicTransport
    from .api_models import FileInfo, SearchResult, NodeInfo, SystemMetrics
except ImportError:
    # Handle case when running as scripts
    pass

__all__ = [
    "ChordNode",
    "QuicChordNode", 
    "QuicTransport",
    "FileInfo",
    "SearchResult",
    "NodeInfo", 
    "SystemMetrics"
]
