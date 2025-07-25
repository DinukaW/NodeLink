#!/usr/bin/env python3
"""
Prometheus Metrics Module for Chord DHT Performance Monitoring
Tracks query performance, message traffic, and node connectivity metrics
"""

import time
import threading
from collections import defaultdict, deque
from datetime import datetime
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("Warning: prometheus_client not installed. Metrics will be disabled.")
    print("Install with: pip install prometheus-client")

class ChordMetrics:
    """Prometheus metrics collector for Chord DHT nodes"""
    
    def __init__(self, node_id, metrics_port=None):
        self.node_id = node_id
        self.metrics_port = metrics_port
        self.enabled = PROMETHEUS_AVAILABLE
        
        if not self.enabled:
            return
            
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # Query Performance Metrics
        self.query_hop_count = Histogram(
            'chord_query_hop_count',
            'Number of hops required for query resolution',
            ['node_id', 'query_type'],
            registry=self.registry,
            buckets=[1, 2, 3, 5, 8, 10, 15, 20, float('inf')]
        )
        
        self.query_latency = Histogram(
            'chord_query_latency_seconds',
            'Query response latency in seconds',
            ['node_id', 'query_type'],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf')]
        )
        
        self.query_total = Counter(
            'chord_queries_total',
            'Total number of queries processed',
            ['node_id', 'query_type', 'status'],
            registry=self.registry
        )
        
        # Message Traffic Metrics
        self.messages_sent = Counter(
            'chord_messages_sent_total',
            'Total messages sent by this node',
            ['node_id', 'message_type', 'target_node'],
            registry=self.registry
        )
        
        self.messages_received = Counter(
            'chord_messages_received_total',
            'Total messages received by this node',
            ['node_id', 'message_type', 'source_node'],
            registry=self.registry
        )
        
        self.message_processing_time = Histogram(
            'chord_message_processing_seconds',
            'Time spent processing different message types',
            ['node_id', 'message_type'],
            registry=self.registry,
            buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, float('inf')]
        )
        
        # Node Connectivity Metrics
        self.node_neighbors = Gauge(
            'chord_node_neighbors',
            'Number of active neighbors',
            ['node_id'],
            registry=self.registry
        )
        
        self.successor_changes = Counter(
            'chord_successor_changes_total',
            'Total number of successor changes',
            ['node_id'],
            registry=self.registry
        )
        
        self.predecessor_changes = Counter(
            'chord_predecessor_changes_total',
            'Total number of predecessor changes',
            ['node_id'],
            registry=self.registry
        )
        
        # Node Performance Metrics
        self.files_stored = Gauge(
            'chord_files_stored',
            'Number of files stored on this node',
            ['node_id'],
            registry=self.registry
        )
        
        self.index_entries = Gauge(
            'chord_index_entries',
            'Number of index entries on this node',
            ['node_id'],
            registry=self.registry
        )
        
        self.backup_files = Gauge(
            'chord_backup_files',
            'Number of backup files on this node',
            ['node_id'],
            registry=self.registry
        )
        
        # Cost Metrics (calculated)
        self.query_cost = Histogram(
            'chord_query_cost',
            'Calculated query cost (α × hop_count + β × latency)',
            ['node_id', 'query_type'],
            registry=self.registry
        )
        
        self.node_cost = Gauge(
            'chord_node_cost',
            'Calculated node cost (δ × messages + ζ × processing_time)',
            ['node_id'],
            registry=self.registry
        )
        
        # Tracking variables for cost calculations
        self.query_contexts = {}  # Track ongoing queries
        self.message_count = 0
        self.total_processing_time = 0.0
        self.lock = threading.Lock()
        
        # Cost calculation parameters (configurable)
        self.alpha = 1.0  # Hop count weight
        self.beta = 100.0  # Latency weight (to scale seconds to reasonable units)
        self.delta = 0.1   # Message count weight
        self.zeta = 10.0   # Processing time weight
        
        # Start metrics server if port specified
        if self.metrics_port:
            self.start_metrics_server()
    
    def start_metrics_server(self):
        """Start Prometheus metrics HTTP server"""
        if not self.enabled:
            return
            
        try:
            start_http_server(self.metrics_port, registry=self.registry)
            print(f"📊 Metrics server started on port {self.metrics_port}")
            print(f"   Visit http://localhost:{self.metrics_port}/metrics")
        except Exception as e:
            print(f"Failed to start metrics server: {e}")
    
    def get_metrics(self):
        """Get metrics in Prometheus format"""
        if not self.enabled:
            return "# Metrics disabled - prometheus_client not available\n"
        return generate_latest(self.registry).decode('utf-8')
    
    # Query Performance Tracking
    def start_query(self, query_id, query_type):
        """Start tracking a query"""
        if not self.enabled:
            return
            
        with self.lock:
            self.query_contexts[query_id] = {
                'start_time': time.time(),
                'query_type': query_type,
                'hop_count': 0
            }
    
    def increment_query_hops(self, query_id):
        """Increment hop count for a query"""
        if not self.enabled:
            return
            
        with self.lock:
            if query_id in self.query_contexts:
                self.query_contexts[query_id]['hop_count'] += 1
    
    def end_query(self, query_id, status='success'):
        """End query tracking and record metrics"""
        if not self.enabled:
            return
            
        with self.lock:
            if query_id not in self.query_contexts:
                return
                
            context = self.query_contexts.pop(query_id)
            latency = time.time() - context['start_time']
            hop_count = context['hop_count']
            query_type = context['query_type']
            
            # Record metrics
            self.query_latency.labels(
                node_id=self.node_id,
                query_type=query_type
            ).observe(latency)
            
            self.query_hop_count.labels(
                node_id=self.node_id,
                query_type=query_type
            ).observe(hop_count)
            
            self.query_total.labels(
                node_id=self.node_id,
                query_type=query_type,
                status=status
            ).inc()
            
            # Calculate and record query cost
            query_cost = self.alpha * hop_count + self.beta * latency
            self.query_cost.labels(
                node_id=self.node_id,
                query_type=query_type
            ).observe(query_cost)
    
    # Message Traffic Tracking
    def record_message_sent(self, message_type, target_node):
        """Record a sent message"""
        if not self.enabled:
            return
            
        self.messages_sent.labels(
            node_id=self.node_id,
            message_type=message_type,
            target_node=target_node
        ).inc()
        
        with self.lock:
            self.message_count += 1
            self.update_node_cost()
    
    def record_message_received(self, message_type, source_node):
        """Record a received message"""
        if not self.enabled:
            return
            
        self.messages_received.labels(
            node_id=self.node_id,
            message_type=message_type,
            source_node=source_node
        ).inc()
    
    def record_message_processing_time(self, message_type, processing_time):
        """Record message processing time"""
        if not self.enabled:
            return
            
        self.message_processing_time.labels(
            node_id=self.node_id,
            message_type=message_type
        ).observe(processing_time)
        
        with self.lock:
            self.total_processing_time += processing_time
            self.update_node_cost()
    
    # Node State Tracking
    def update_neighbors_count(self, count):
        """Update neighbor count"""
        if not self.enabled:
            return
            
        self.node_neighbors.labels(node_id=self.node_id).set(count)
    
    def record_successor_change(self):
        """Record successor change"""
        if not self.enabled:
            return
            
        self.successor_changes.labels(node_id=self.node_id).inc()
    
    def record_predecessor_change(self):
        """Record predecessor change"""
        if not self.enabled:
            return
            
        self.predecessor_changes.labels(node_id=self.node_id).inc()
    
    def update_file_counts(self, files_count, index_count, backup_count):
        """Update file-related counts"""
        if not self.enabled:
            return
            
        self.files_stored.labels(node_id=self.node_id).set(files_count)
        self.index_entries.labels(node_id=self.node_id).set(index_count)
        self.backup_files.labels(node_id=self.node_id).set(backup_count)
    
    def update_node_cost(self):
        """Update calculated node cost"""
        if not self.enabled:
            return
            
        # Calculate node cost: δ × messages + ζ × processing_time
        node_cost = self.delta * self.message_count + self.zeta * self.total_processing_time
        self.node_cost.labels(node_id=self.node_id).set(node_cost)
    
    # Context managers for easy timing
    def time_query(self, query_type):
        """Context manager for timing queries"""
        return QueryTimer(self, query_type)
    
    def time_message_processing(self, message_type):
        """Context manager for timing message processing"""
        return MessageTimer(self, message_type)

class QueryTimer:
    """Context manager for query timing"""
    
    def __init__(self, metrics, query_type):
        self.metrics = metrics
        self.query_type = query_type
        self.query_id = None
    
    def __enter__(self):
        self.query_id = f"{self.metrics.node_id}_{time.time()}_{self.query_type}"
        self.metrics.start_query(self.query_id, self.query_type)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        status = 'success' if exc_type is None else 'error'
        self.metrics.end_query(self.query_id, status)
    
    def add_hop(self):
        """Add a hop to this query"""
        if self.query_id:
            self.metrics.increment_query_hops(self.query_id)

class MessageTimer:
    """Context manager for message processing timing"""
    
    def __init__(self, metrics, message_type):
        self.metrics = metrics
        self.message_type = message_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            processing_time = time.time() - self.start_time
            self.metrics.record_message_processing_time(self.message_type, processing_time)
