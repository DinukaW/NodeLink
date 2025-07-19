#!/usr/bin/env python3
"""
API Models for Phase 4: REST API
Pydantic models for request/response validation and serialization.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ErrorDetail(BaseModel):
    """Error detail information."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: ErrorDetail
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


# File Operation Models
class FileUploadResponse(BaseModel):
    """Response for file upload operations."""
    filename: str
    file_hash: int
    file_size: int
    node_id: int
    replicas: List[int]
    upload_time: datetime


class FileInfo(BaseModel):
    """File information model."""
    filename: str
    file_hash: int
    file_size: int
    node_id: int
    node_address: str
    upload_time: Optional[datetime] = None
    replicas: List[int] = []


class FileListResponse(BaseModel):
    """Response for file listing operations."""
    files: List[FileInfo]
    total_files: int
    page: int
    page_size: int
    total_pages: int


class FileDownloadResponse(BaseModel):
    """Response model for file download info (metadata)."""
    filename: str
    file_size: int
    content_type: str
    node_location: str


# Search Operation Models
class SearchResult(BaseModel):
    """Individual search result."""
    filename: str
    file_hash: int
    relevance_score: float
    node_id: int
    node_address: str
    file_size: int
    matched_tokens: List[str]


class SearchResponse(BaseModel):
    """Response for search operations."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    page: int
    page_size: int


class SearchSuggestionsResponse(BaseModel):
    """Response for search suggestions."""
    query: str
    suggestions: List[str]
    response_time_ms: float


class AdvancedSearchRequest(BaseModel):
    """Advanced search request parameters."""
    query: str
    file_types: Optional[List[str]] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    node_ids: Optional[List[int]] = None
    sort_by: Optional[str] = "relevance"  # relevance, size, filename
    sort_order: Optional[str] = "desc"    # asc, desc


# Node Management Models
class NodeInfo(BaseModel):
    """Node information model."""
    node_id: int
    address: str
    port: int
    status: str
    uptime: float
    files_stored: int
    tokens_indexed: int


class NodeNeighbors(BaseModel):
    """Node neighbor information."""
    current_node: NodeInfo
    successor: Optional[NodeInfo]
    predecessor: Optional[NodeInfo]
    finger_table: List[NodeInfo]


class RingTopology(BaseModel):
    """Ring topology information."""
    ring_size: int
    total_nodes: int
    nodes: List[NodeInfo]
    ring_health: float  # 0.0 to 1.0


class JoinRingRequest(BaseModel):
    """Request to join a ring."""
    bootstrap_address: str
    bootstrap_port: int
    
    @validator('bootstrap_port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


# Health and Status Models
class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Health check response."""
    status: HealthStatus
    uptime: float
    version: str
    node_id: int
    ring_status: str
    checks: Dict[str, bool]


class SystemMetrics(BaseModel):
    """System metrics model."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_connections: int
    active_requests: int
    files_stored: int
    search_requests_per_minute: float


class StatusResponse(BaseModel):
    """Detailed system status response."""
    health: HealthResponse
    metrics: SystemMetrics
    node_info: NodeInfo
    ring_info: Dict[str, Any]


# Request Models
class FileDeleteRequest(BaseModel):
    """Request to delete a file."""
    filename: str
    force: bool = False


class SearchRequest(BaseModel):
    """Basic search request."""
    query: str = Field(..., min_length=1, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


# Utility Models
class PaginationInfo(BaseModel):
    """Pagination information."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


# Configuration Models
class APIConfig(BaseModel):
    """API configuration model."""
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = ["*"]
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


# Response Building Utilities
def build_success_response(data: Any = None, message: str = "Operation successful") -> Dict[str, Any]:
    """Build a standard success response."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def build_error_response(
    code: str, 
    message: str, 
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build a standard error response."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# Common Error Codes
class ErrorCodes:
    """Standard error codes for the API."""
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    NODE_UNAVAILABLE = "NODE_UNAVAILABLE"
    SEARCH_FAILED = "SEARCH_FAILED"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED = "UNAUTHORIZED"
    RING_OPERATION_FAILED = "RING_OPERATION_FAILED"


# Response Status Messages
class StatusMessages:
    """Standard status messages."""
    FILE_UPLOADED = "File uploaded successfully"
    FILE_DOWNLOADED = "File downloaded successfully"
    FILE_DELETED = "File deleted successfully"
    SEARCH_COMPLETED = "Search completed successfully"
    NODE_INFO_RETRIEVED = "Node information retrieved successfully"
    RING_JOINED = "Successfully joined the ring"
    RING_LEFT = "Successfully left the ring"
    HEALTH_CHECK_OK = "System is healthy"
