"""
Sandbox Resource Monitoring Module

This module provides utilities for monitoring resource usage of sandboxed processes.
"""

import os
import time
import threading
import psutil
from typing import Dict, List, Any, Optional, Union, Callable

from app.sandbox.base import ResourceLimits


class ResourceUsage:
    """Class representing resource usage statistics."""
    
    def __init__(self):
        """Initialize resource usage statistics."""
        self.cpu_percent = 0.0
        self.memory_bytes = 0
        self.peak_memory_bytes = 0
        self.io_read_bytes = 0
        self.io_write_bytes = 0
        self.io_read_count = 0
        self.io_write_count = 0
        self.thread_count = 0
        self.open_files_count = 0
        self.network_bytes_sent = 0
        self.network_bytes_recv = 0
        self.network_connections = 0
        self.elapsed_time = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource usage to a dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_bytes": self.memory_bytes,
            "peak_memory_bytes": self.peak_memory_bytes,
            "io_read_bytes": self.io_read_bytes,
            "io_write_bytes": self.io_write_bytes,
            "io_read_count": self.io_read_count,
            "io_write_count": self.io_write_count,
            "thread_count": self.thread_count,
            "open_files_count": self.open_files_count,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "network_connections": self.network_connections,
            "elapsed_time": self.elapsed_time
        }
    
    def __str__(self) -> str:
        """String representation of resource usage."""
        return (
            f"CPU: {self.cpu_percent:.1f}%, "
            f"Memory: {self.memory_bytes / (1024 * 1024):.1f} MB (Peak: {self.peak_memory_bytes / (1024 * 1024):.1f} MB), "
            f"IO: {self.io_read_bytes / 1024:.1f} KB read, {self.io_write_bytes / 1024:.1f} KB write, "
            f"Threads: {self.thread_count}, "
            f"Open Files: {self.open_files_count}, "
            f"Network: {self.network_bytes_sent / 1024:.1f} KB sent, {self.network_bytes_recv / 1024:.1f} KB recv, "
            f"Time: {self.elapsed_time:.1f}s"
        )


class ResourceMonitor:
    """
    Class for monitoring resource usage of processes.
    
    This class provides utilities for monitoring CPU, memory, I/O, and network usage
    of processes, and enforcing resource limits.
    """
    
    def __init__(
        self,
        pid: int,
        resource_limits: Optional[ResourceLimits] = None,
        include_children: bool = True,
        interval: float = 0.1,
        on_limit_exceeded: Optional[Callable[[str, Any, Any], None]] = None
    ):
        """
        Initialize a resource monitor.
        
        Args:
            pid: Process ID to monitor
            resource_limits: Resource limits to enforce
            include_children: Whether to include child processes
            interval: Monitoring interval in seconds
            on_limit_exceeded: Callback function when a limit is exceeded
        """
        self.pid = pid
        self.resource_limits = resource_limits or ResourceLimits()
        self.include_children = include_children
        self.interval = interval
        self.on_limit_exceeded = on_limit_exceeded
        
        self.process = None
        self.children = []
        self.running = False
        self.thread = None
        self.start_time = None
        
        self.usage = ResourceUsage()
        self._last_io = None
        self._last_net = None
    
    def _get_process(self) -> Optional[psutil.Process]:
        """
        Get the process to monitor.
        
        Returns:
            psutil.Process: Process object, or None if the process doesn't exist
        """
        try:
            return psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            return None
    
    def _get_children(self, process: psutil.Process) -> List[psutil.Process]:
        """
        Get child processes.
        
        Args:
            process: Parent process
            
        Returns:
            List[psutil.Process]: List of child processes
        """
        try:
            return process.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []
    
    def _check_limits(self, usage: ResourceUsage):
        """
        Check if resource usage exceeds limits.
        
        Args:
            usage: Current resource usage
        """
        if not self.on_limit_exceeded:
            return
        
        # Check CPU time limit
        if self.resource_limits.max_cpu_time > 0 and usage.elapsed_time > self.resource_limits.max_cpu_time:
            self.on_limit_exceeded("cpu_time", usage.elapsed_time, self.resource_limits.max_cpu_time)
        
        # Check memory limit
        if self.resource_limits.max_memory > 0 and usage.memory_bytes > self.resource_limits.max_memory:
            self.on_limit_exceeded("memory", usage.memory_bytes, self.resource_limits.max_memory)
    
    def _update_usage(self):
        """Update resource usage statistics."""
        if not self.process:
            return
        
        try:
            # Update process list
            if self.include_children:
                self.children = self._get_children(self.process)
            
            # Get all processes to monitor
            processes = [self.process] + self.children if self.include_children else [self.process]
            
            # Reset usage
            self.usage.cpu_percent = 0.0
            self.usage.memory_bytes = 0
            self.usage.thread_count = 0
            self.usage.open_files_count = 0
            
            # Aggregate usage from all processes
            for proc in processes:
                try:
                    # CPU usage
                    self.usage.cpu_percent += proc.cpu_percent(interval=None)
                    
                    # Memory usage
                    memory_info = proc.memory_info()
                    self.usage.memory_bytes += memory_info.rss
                    
                    # Update peak memory
                    if self.usage.memory_bytes > self.usage.peak_memory_bytes:
                        self.usage.peak_memory_bytes = self.usage.memory_bytes
                    
                    # Thread count
                    self.usage.thread_count += proc.num_threads()
                    
                    # Open files count
                    try:
                        self.usage.open_files_count += len(proc.open_files())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                    
                    # I/O counters
                    try:
                        io_counters = proc.io_counters()
                        if self._last_io is None:
                            self._last_io = io_counters
                        
                        self.usage.io_read_bytes += io_counters.read_bytes
                        self.usage.io_write_bytes += io_counters.write_bytes
                        self.usage.io_read_count += io_counters.read_count
                        self.usage.io_write_count += io_counters.write_count
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                    
                    # Network counters
                    try:
                        net_counters = proc.net_io_counters()
                        if self._last_net is None:
                            self._last_net = net_counters
                        
                        self.usage.network_bytes_sent += net_counters.bytes_sent
                        self.usage.network_bytes_recv += net_counters.bytes_recv
                        self.usage.network_connections += len(proc.connections())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process might have exited
                    continue
            
            # Update elapsed time
            self.usage.elapsed_time = time.time() - self.start_time
            
            # Check if resource limits are exceeded
            self._check_limits(self.usage)
        
        except Exception as e:
            print(f"Error updating resource usage: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        self.start_time = time.time()
        
        while self.running:
            self._update_usage()
            time.sleep(self.interval)
    
    def start(self):
        """Start monitoring."""
        if self.running:
            return
        
        self.process = self._get_process()
        if not self.process:
            raise ValueError(f"Process with PID {self.pid} not found")
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def get_usage(self) -> ResourceUsage:
        """
        Get current resource usage.
        
        Returns:
            ResourceUsage: Current resource usage
        """
        return self.usage
    
    def kill_process(self):
        """Kill the monitored process and its children."""
        if not self.process:
            return
        
        try:
            # Kill children first
            if self.include_children:
                for child in self.children:
                    try:
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
            # Kill the main process
            self.process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
