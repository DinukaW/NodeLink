#!/usr/bin/env python3
"""
REST API for Phase 4: Chord DHT Web Interface
FastAPI application providing REST endpoints for the Chord DHT system.
"""

import asyncio
import logging
import time
import uuid
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from pydantic import BaseModel
import io

from api_bridge import ChordAPIBridge
from api_models import (
    APIResponse, ErrorResponse, FileUploadResponse, FileInfo, FileListResponse,
    SearchRequest, SearchResponse, SearchResult, AdvancedSearchRequest,
    NodeInfo, HealthResponse, SystemMetrics, StatusResponse,
    JoinRingRequest, FileDeleteRequest, ErrorCodes, StatusMessages,
    build_success_response, build_error_response
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bridge instance
bridge: Optional[ChordAPIBridge] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global bridge
    
    # Startup
    logger.info("Starting Chord DHT REST API...")
    bridge = ChordAPIBridge()
    
    initialized = await bridge.initialize()
    if not initialized:
        logger.error("Failed to initialize Chord API Bridge")
        raise RuntimeError("Failed to initialize Chord API Bridge")
    
    logger.info("Chord DHT REST API started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Chord DHT REST API...")
    if bridge:
        await bridge.shutdown()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Chord DHT REST API",
    description="REST API for Chord Distributed Hash Table file sharing system with QUIC transport",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


def get_bridge() -> ChordAPIBridge:
    """Dependency to get the API bridge instance."""
    if not bridge:
        raise HTTPException(status_code=503, detail="Service unavailable")
    return bridge


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


# Health and Status Endpoints
@app.get("/health", response_model=dict, tags=["Health"])
async def health_check(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Health check endpoint."""
    try:
        response = await api_bridge.get_health_status()
        return response
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            "Health check failed"
        )


@app.get("/metrics", response_model=dict, tags=["Health"])
async def get_metrics(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Get system metrics."""
    try:
        response = await api_bridge.get_system_metrics()
        return response
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            "Failed to retrieve metrics"
        )


@app.get("/status", response_model=dict, tags=["Health"])
async def get_status(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Get detailed system status."""
    try:
        health_response = await api_bridge.get_health_status()
        metrics_response = await api_bridge.get_system_metrics()
        node_response = await api_bridge.get_node_info()
        
        if all(resp["success"] for resp in [health_response, metrics_response, node_response]):
            return build_success_response({
                "health": health_response["data"],
                "metrics": metrics_response["data"], 
                "node_info": node_response["data"],
                "ring_info": {"status": "connected"}  # Placeholder
            })
        else:
            return build_error_response(
                ErrorCodes.INTERNAL_ERROR,
                "Failed to retrieve complete status"
            )
    except Exception as e:
        logger.error(f"Status retrieval failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            "Status retrieval failed"
        )


# File Operations
@app.post("/files/upload", response_model=dict, tags=["Files"])
async def upload_file(
    file: UploadFile = File(...),
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """Upload a file to the Chord DHT."""
    try:
        # Read file content
        content = await file.read()
        
        # Check file size (100MB limit)
        if len(content) > 100 * 1024 * 1024:
            return build_error_response(
                ErrorCodes.FILE_TOO_LARGE,
                "File size exceeds 100MB limit"
            )
        
        # Upload file
        response = await api_bridge.upload_file(file.filename, content)
        return response
        
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"File upload failed: {str(e)}"
        )


@app.get("/files/{filename}", tags=["Files"])
async def download_file(
    filename: str,
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """Download a file from the Chord DHT."""
    try:
        response = await api_bridge.download_file(filename)
        
        if response["success"]:
            content = response["data"]["content"]
            file_size = response["data"]["file_size"]
            
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Length": str(file_size)
                }
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=response["error"]["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="File download failed"
        )


@app.delete("/files/{filename}", response_model=dict, tags=["Files"])
async def delete_file(
    filename: str,
    force: bool = Query(False, description="Force deletion even if file not found"),
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """Delete a file from the Chord DHT."""
    try:
        response = await api_bridge.delete_file(filename, force)
        return response
        
    except Exception as e:
        logger.error(f"File deletion failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"File deletion failed: {str(e)}"
        )


@app.get("/files/list", response_model=dict, tags=["Files"])
async def list_files(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of files per page"),
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """List files stored in the DHT."""
    try:
        response = await api_bridge.list_files(page, page_size)
        return response
        
    except Exception as e:
        logger.error(f"File listing failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"File listing failed: {str(e)}"
        )


# Search Operations
@app.get("/search", response_model=dict, tags=["Search"])
async def search_files(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """Search files by filename using distributed inverted index."""
    try:
        if not q.strip():
            return build_error_response(
                ErrorCodes.INVALID_REQUEST,
                "Search query cannot be empty"
            )
        
        response = await api_bridge.search_files(q, page, page_size)
        return response
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return build_error_response(
            ErrorCodes.SEARCH_FAILED,
            f"Search failed: {str(e)}"
        )


@app.get("/search/suggestions", response_model=dict, tags=["Search"])
async def get_search_suggestions(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions")
):
    """Get search suggestions for autocomplete."""
    try:
        start_time = time.time()
        
        # Simple suggestion logic based on query
        suggestions = []
        if q.strip():
            # Generate simple suggestions based on common patterns
            base_suggestions = [
                "machine learning", "deep learning", "neural network",
                "data science", "artificial intelligence", "computer vision",
                "natural language processing", "python programming"
            ]
            
            suggestions = [
                suggestion for suggestion in base_suggestions
                if q.lower() in suggestion.lower()
            ][:limit]
        
        response_time = (time.time() - start_time) * 1000
        
        return build_success_response({
            "query": q,
            "suggestions": suggestions,
            "response_time_ms": response_time
        })
        
    except Exception as e:
        logger.error(f"Suggestions failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"Failed to get suggestions: {str(e)}"
        )


@app.post("/search/advanced", response_model=dict, tags=["Search"])
async def advanced_search(
    search_request: AdvancedSearchRequest,
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """Perform advanced search with filters."""
    try:
        # For now, delegate to basic search
        response = await api_bridge.search_files(search_request.query, 1, 50)
        
        if response["success"]:
            results = response["data"]["results"]
            
            # Apply filters
            if search_request.file_types:
                # Filter by file types if specified
                filtered_results = []
                for result in results:
                    filename = result["filename"]
                    ext = filename.split(".")[-1].lower() if "." in filename else ""
                    if "*" in search_request.file_types or ext in search_request.file_types:
                        filtered_results.append(result)
                results = filtered_results
            
            # Apply sorting
            if search_request.sort_by == "filename":
                results.sort(
                    key=lambda x: x["filename"],
                    reverse=(search_request.sort_order == "desc")
                )
            elif search_request.sort_by == "size":
                results.sort(
                    key=lambda x: x["file_size"],
                    reverse=(search_request.sort_order == "desc")
                )
            # Default is relevance, which should already be sorted
            
            response["data"]["results"] = results
            response["data"]["total_results"] = len(results)
            
        return response
        
    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        return build_error_response(
            ErrorCodes.SEARCH_FAILED,
            f"Advanced search failed: {str(e)}"
        )


# Node Management
@app.get("/node/info", response_model=dict, tags=["Node"])
async def get_node_info(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Get information about the current node."""
    try:
        response = await api_bridge.get_node_info()
        return response
        
    except Exception as e:
        logger.error(f"Node info retrieval failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"Failed to get node info: {str(e)}"
        )


@app.get("/node/neighbors", response_model=dict, tags=["Node"])
async def get_node_neighbors(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Get information about node's neighbors in the ring."""
    try:
        # This would need to be implemented in the bridge
        return build_success_response({
            "current_node": {"node_id": 1, "address": "127.0.0.1", "port": 7000},
            "successor": None,
            "predecessor": None,
            "finger_table": []
        })
        
    except Exception as e:
        logger.error(f"Neighbors info failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"Failed to get neighbors info: {str(e)}"
        )


@app.get("/node/ring", response_model=dict, tags=["Node"])
async def get_ring_topology(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Get ring topology information."""
    try:
        # Placeholder for ring topology
        return build_success_response({
            "ring_size": 160,  # 2^m where m=5 for demo
            "total_nodes": 1,
            "nodes": [{"node_id": 1, "address": "127.0.0.1", "port": 7000, "status": "active"}],
            "ring_health": 1.0
        })
        
    except Exception as e:
        logger.error(f"Ring topology failed: {e}")
        return build_error_response(
            ErrorCodes.INTERNAL_ERROR,
            f"Failed to get ring topology: {str(e)}"
        )


@app.post("/node/join", response_model=dict, tags=["Node"])
async def join_ring(
    join_request: JoinRingRequest,
    api_bridge: ChordAPIBridge = Depends(get_bridge)
):
    """Join an existing Chord ring."""
    try:
        # This would need to be implemented in the bridge
        return build_success_response(
            {"status": "joined", "ring_address": f"{join_request.bootstrap_address}:{join_request.bootstrap_port}"},
            StatusMessages.RING_JOINED
        )
        
    except Exception as e:
        logger.error(f"Ring join failed: {e}")
        return build_error_response(
            ErrorCodes.RING_OPERATION_FAILED,
            f"Failed to join ring: {str(e)}"
        )


@app.post("/node/leave", response_model=dict, tags=["Node"])
async def leave_ring(api_bridge: ChordAPIBridge = Depends(get_bridge)):
    """Leave the Chord ring gracefully."""
    try:
        # This would need to be implemented in the bridge
        return build_success_response(
            {"status": "left"},
            StatusMessages.RING_LEFT
        )
        
    except Exception as e:
        logger.error(f"Ring leave failed: {e}")
        return build_error_response(
            ErrorCodes.RING_OPERATION_FAILED,
            f"Failed to leave ring: {str(e)}"
        )


# API Information
@app.get("/", response_model=dict, tags=["Info"])
async def root():
    """API information and welcome message."""
    return build_success_response({
        "service": "Chord DHT REST API",
        "version": "4.0.0",
        "description": "REST API for Chord Distributed Hash Table with QUIC transport",
        "docs": "/docs",
        "redoc": "/redoc",
        "features": [
            "File upload/download",
            "Distributed search",
            "Node management",
            "Health monitoring",
            "QUIC transport",
            "Protocol Buffers"
        ]
    }, "Welcome to Chord DHT REST API")


def run_server(host: str = "127.0.0.1", port: int = 8000, debug: bool = False):
    """Run the FastAPI server."""
    uvicorn.run(
        "rest_api:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Chord DHT REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    print(f"Starting Chord DHT REST API server on {args.host}:{args.port}")
    run_server(args.host, args.port, args.debug)
