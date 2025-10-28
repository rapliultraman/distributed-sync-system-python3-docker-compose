import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Any

class MetricsCollector:
    """Centralized metrics collection for the distributed system"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.metrics = defaultdict(lambda: defaultdict(float))
        self.counters = defaultdict(int)
        self.histograms = defaultdict(lambda: deque(maxlen=1000))
        self.start_time = time.time()
        
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self.counters[key] += value
        
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        key = self._make_key(name, labels)
        self.metrics['gauge'][key] = value
        
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
        
    def record_timing(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record timing information"""
        self.record_histogram(f"{name}_duration", duration, labels)
        
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key for the metric"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics"""
        uptime = time.time() - self.start_time
        
        summary = {
            'node_id': self.node_id,
            'uptime_seconds': uptime,
            'counters': dict(self.counters),
            'gauges': dict(self.metrics['gauge']),
            'histograms': {}
        }
        
        # Calculate histogram statistics
        for key, values in self.histograms.items():
            if values:
                summary['histograms'][key] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'p50': self._percentile(values, 50),
                    'p95': self._percentile(values, 95),
                    'p99': self._percentile(values, 99)
                }
        
        return summary
    
    def _percentile(self, values: deque, percentile: int) -> float:
        """Calculate percentile of histogram values"""
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

class PerformanceMonitor:
    """Performance monitoring decorators and utilities"""
    
    @staticmethod
    def timing_metric(metrics_collector: MetricsCollector, metric_name: str):
        """Decorator to record timing metrics"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    metrics_collector.record_timing(metric_name, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    metrics_collector.record_timing(f"{metric_name}_error", duration)
                    raise
            return async_wrapper
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_timing(metric_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_timing(f"{metric_name}_error", duration)
                raise
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class SystemMetrics:
    """System-level metrics collection"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.metrics = MetricsCollector(node_id)
        
    async def start_background(self, app):
        """Start background metrics collection"""
        app.loop.create_task(self._metrics_collection_loop())
        
    async def _metrics_collection_loop(self):
        """Background loop for collecting system metrics"""
        while True:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(10)  # Collect every 10 seconds
            except Exception as e:
                print(f"Error collecting metrics: {e}")
                await asyncio.sleep(10)
        
    async def collect_system_metrics(self):
        """Collect system-level metrics"""
        import psutil
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics.set_gauge('cpu_usage_percent', cpu_percent)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        self.metrics.set_gauge('memory_usage_percent', memory.percent)
        self.metrics.set_gauge('memory_available_mb', memory.available / 1024 / 1024)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        self.metrics.set_gauge('disk_usage_percent', disk.percent)
        self.metrics.set_gauge('disk_free_mb', disk.free / 1024 / 1024)
        
        # Network metrics
        network = psutil.net_io_counters()
        self.metrics.set_gauge('network_bytes_sent', network.bytes_sent)
        self.metrics.set_gauge('network_bytes_recv', network.bytes_recv)
        
    def get_metrics_endpoint_data(self) -> Dict[str, Any]:
        """Get metrics data formatted for Prometheus-style endpoint"""
        summary = self.metrics.get_metrics_summary()
        
        # Format for Prometheus exposition format
        lines = []
        lines.append(f"# HELP node_uptime_seconds Node uptime in seconds")
        lines.append(f"# TYPE node_uptime_seconds gauge")
        lines.append(f"node_uptime_seconds{{node=\"{self.node_id}\"}} {summary['uptime_seconds']}")
        
        # Add counters
        for key, value in summary['counters'].items():
            lines.append(f"# HELP {key} Counter metric")
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")
        
        # Add gauges
        for key, value in summary['gauges'].items():
            lines.append(f"# HELP {key} Gauge metric")
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")
        
        # Add histograms
        for key, stats in summary['histograms'].items():
            lines.append(f"# HELP {key} Histogram metric")
            lines.append(f"# TYPE {key} histogram")
            lines.append(f"{key}_count {stats['count']}")
            lines.append(f"{key}_sum {stats['avg'] * stats['count']}")
            lines.append(f"{key}_bucket{{le=\"+Inf\"}} {stats['count']}")
        
        return {
            'prometheus_format': '\n'.join(lines),
            'json_format': summary
        }
