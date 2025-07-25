# Chord DHT Performance Monitoring & Analysis

## Overview

This implementation provides comprehensive performance monitoring for the Chord DHT system using Prometheus metrics and Grafana visualization. The system tracks detailed performance metrics for analysis and reporting.

## 📊 Metrics Tracked

### Query Performance Metrics
- **Query Hop Count**: Number of hops required for query resolution
- **Query Latency**: Query response time in seconds  
- **Query Success/Failure Rate**: Total queries processed with status
- **Query Cost**: Calculated as `α × hop_count + β × latency`

### Message Traffic Metrics
- **Messages Sent/Received**: Total message counts by type and node
- **Message Processing Time**: Time spent processing different message types
- **Message Types**: Tracks all Chord protocol messages (lookup, store_index_entry, etc.)

### Node Connectivity Metrics
- **Active Neighbors**: Number of connected neighbors (successor + predecessor)
- **Successor Changes**: Count of successor relationship changes
- **Predecessor Changes**: Count of predecessor relationship changes

### Node Performance Metrics
- **Files Stored**: Number of files on each node
- **Index Entries**: Number of search index entries
- **Backup Files**: Number of backup files
- **Node Cost**: Calculated as `δ × messages_processed + ζ × processing_time`

## 🚀 Quick Start

### 1. Setup Monitoring
```bash
# Install dependencies and start monitoring stack
python3 setup_monitoring.py
```

### 2. Start the System
```bash
# Start bootstrap server
python3 bootstrap_server.py 5000

# Start nodes with metrics enabled
python3 rest_api.py 5001 8001  # Metrics exposed on port 9001
python3 rest_api.py 5002 8002  # Metrics exposed on port 9002  
python3 rest_api.py 5003 8003  # Metrics exposed on port 9003
```

### 3. Access Monitoring
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Node Metrics**: http://localhost:9001/metrics, http://localhost:9002/metrics, etc.

## 📈 Cost Calculation Parameters

The system calculates performance costs using configurable parameters:

### Query Cost Formula
```
Query Cost = α × hop_count + β × latency
```
- **α (alpha)**: Hop count weight (default: 1.0)
- **β (beta)**: Latency weight (default: 100.0)

### Node Cost Formula  
```
Node Cost = δ × messages_processed + ζ × processing_time
```
- **δ (delta)**: Message count weight (default: 0.1)
- **ζ (zeta)**: Processing time weight (default: 10.0)

## 🔧 Metrics Endpoints

### REST API Metrics Endpoint
Each REST API server exposes metrics at:
```
GET http://localhost:<api_port>/metrics
```

### Node-Level Metrics Server
Each Chord node runs a dedicated metrics server on port `node_port + 1000`:
- Node 8001 → Metrics on 9001
- Node 8002 → Metrics on 9002  
- Node 8003 → Metrics on 9003

## 📋 Sample Metrics Output

```prometheus
# HELP chord_query_hop_count Number of hops required for query resolution
# TYPE chord_query_hop_count histogram
chord_query_hop_count_bucket{node_id="localhost:8001",query_type="index_search",le="1"} 5
chord_query_hop_count_bucket{node_id="localhost:8001",query_type="index_search",le="2"} 8
chord_query_hop_count_bucket{node_id="localhost:8001",query_type="index_search",le="+Inf"} 10

# HELP chord_query_latency_seconds Query response latency in seconds
# TYPE chord_query_latency_seconds histogram
chord_query_latency_seconds_bucket{node_id="localhost:8001",query_type="index_search",le="0.005"} 2
chord_query_latency_seconds_bucket{node_id="localhost:8001",query_type="index_search",le="0.01"} 7

# HELP chord_messages_sent_total Total messages sent by this node
# TYPE chord_messages_sent_total counter
chord_messages_sent_total{node_id="localhost:8001",message_type="lookup",target_node="localhost:8002"} 15

# HELP chord_node_neighbors Number of active neighbors  
# TYPE chord_node_neighbors gauge
chord_node_neighbors{node_id="localhost:8001"} 2

# HELP chord_query_cost Calculated query cost
# TYPE chord_query_cost histogram
chord_query_cost{node_id="localhost:8001",query_type="index_search"} 2.1
```

## 🎯 Performance Testing

### Test Query Performance
```bash
# Upload files with different names to test indexing
curl -X POST -F "file=@machine_learning_notes.txt" http://localhost:5001/upload
curl -X POST -F "file=@database_systems_guide.txt" http://localhost:5002/upload

# Perform searches to generate metrics
curl "http://localhost:5001/search?q=machine"
curl "http://localhost:5002/search?q=database" 
curl "http://localhost:5003/search?q=learning"

# Check metrics
curl http://localhost:5001/metrics | grep chord_query
```

### Test Node Performance
```bash
# Trigger node leave to test cost metrics
curl -X POST http://localhost:5002/node/leave

# Observe metrics for topology changes
curl http://localhost:5001/metrics | grep chord_successor_changes
```

## 📊 Grafana Dashboard

The included dashboard provides visualization for:

1. **Query Performance Panel**: Hop count and latency trends
2. **Message Traffic Panel**: Send/receive rates by message type
3. **Node Connectivity Panel**: Neighbor count and topology changes  
4. **Cost Analysis Panel**: Query and node cost calculations
5. **Storage Statistics Panel**: File counts and distribution

### Dashboard Features
- Real-time metrics updates (5-second intervals)
- Per-node filtering and comparison
- Historical trend analysis
- Alerting capabilities (can be configured)

## 🛠️ Configuration

### Modify Cost Parameters
Edit the parameters in `chord_metrics.py`:
```python
# Cost calculation parameters
self.alpha = 1.0   # Hop count weight
self.beta = 100.0  # Latency weight  
self.delta = 0.1   # Message count weight
self.zeta = 10.0   # Processing time weight
```

### Custom Metrics Port
By default, metrics servers run on `node_port + 1000`. To customize:
```python
# In chord.py Node.__init__()
metrics_port = port + 2000  # Custom offset
self.metrics = ChordMetrics(f"{host}:{port}", metrics_port)
```

## 🔍 Troubleshooting

### Metrics Not Available
- Ensure `prometheus_client` is installed: `pip install prometheus_client`
- Check if metrics server started: Look for "Metrics server started on port X"
- Verify port accessibility: `curl http://localhost:9001/metrics`

### Grafana Dashboard Issues
- Ensure Prometheus is collecting data: Check http://localhost:9090/targets
- Verify Grafana data source: Check Grafana > Configuration > Data Sources
- Refresh dashboard: Click refresh button or set auto-refresh

### Docker Issues
- Ensure Docker is running: `docker --version`
- Check container status: `docker-compose ps`
- View logs: `docker-compose logs prometheus` or `docker-compose logs grafana`

## 📈 Performance Analysis Examples

### Query Efficiency Analysis
Monitor how query hop count changes with network size:
```prometheus
avg(chord_query_hop_count) by (node_id)
```

### Load Distribution Analysis  
Check message processing distribution:
```prometheus
rate(chord_messages_received_total[5m]) by (node_id, message_type)
```

### Cost Optimization Analysis
Identify high-cost operations:
```prometheus
chord_query_cost > 5.0
```

## 🚀 Production Deployment

For production monitoring:

1. **Scale Prometheus**: Configure retention and storage
2. **Setup Alerting**: Add Prometheus alert rules
3. **Backup Metrics**: Configure Grafana backup
4. **Security**: Add authentication and HTTPS
5. **Network**: Configure service discovery for dynamic nodes

This comprehensive monitoring system provides the foundation for thorough performance analysis and optimization of the Chord DHT system!
