import time
from typing import Dict, Any

# In-memory simulator for telecom router statuses
# Maps IP address -> Current state dictionary
_SIMULATED_ROUTERS: Dict[str, Dict[str, Any]] = {}

def _initialize_router(router_ip: str):
    """Initialize a router with simulated network problems if it doesn't exist."""
    if router_ip not in _SIMULATED_ROUTERS:
        # Default starting state with network issues
        _SIMULATED_ROUTERS[router_ip] = {
            "ip": router_ip,
            "status": "unhealthy",
            "latency_ms": 185.5,
            "packet_loss_pct": 14.2,
            "cpu_usage_pct": 92.0,
            "memory_usage_pct": 85.0,
            "dns_resolution": "failed",
            "connection_state": "degraded",
            "active_connections": 1240,
            "system_errors": [
                "DNS_CACHE_CORRUPTED",
                "ROUTING_TABLE_OVERFLOW",
                "EXCESSIVE_NAT_SESSIONS"
            ],
            "firmware_version": "v12.4.2-telecom-custom",
            "uptime_seconds": 1582400,
            "fix_count": 0
        }

def run_router_diagnostics(router_ip: str) -> Dict[str, Any]:
    """
    Run diagnostic metrics collection on a specified router IP.
    
    Args:
        router_ip: The IP address of the target router.
        
    Returns:
        Dict: Router diagnostic parameters and errors.
    """
    _initialize_router(router_ip)
    # Simulate slight variance in diagnostics query time
    time.sleep(0.5)
    return _SIMULATED_ROUTERS[router_ip].copy()

def apply_router_fix(router_ip: str, action: str) -> Dict[str, Any]:
    """
    Apply a simulated troubleshooting/healing patch on a router.
    
    Args:
        router_ip: The target router's IP address.
        action: The action to apply. Valid values: 
                'flush_dns_cache', 'clear_routing_table', 'reboot_router', 'terminate_nat_sessions'
                
    Returns:
        Dict: Results of the healing action.
    """
    _initialize_router(router_ip)
    router = _SIMULATED_ROUTERS[router_ip]
    router["fix_count"] += 1
    
    time.sleep(0.8) # Simulate time to push configuration to router
    
    action = action.lower().strip()
    result = {"success": False, "details": ""}
    
    if action == "flush_dns_cache":
        if "DNS_CACHE_CORRUPTED" in router["system_errors"]:
            router["system_errors"].remove("DNS_CACHE_CORRUPTED")
            router["dns_resolution"] = "success"
            router["cpu_usage_pct"] = max(45.0, router["cpu_usage_pct"] - 30.0)
            result["success"] = True
            result["details"] = "DNS cache flushed. DNS resolution service restored."
        else:
            result["success"] = True
            result["details"] = "DNS cache was already clean. No changes made."
            
    elif action == "clear_routing_table":
        if "ROUTING_TABLE_OVERFLOW" in router["system_errors"]:
            router["system_errors"].remove("ROUTING_TABLE_OVERFLOW")
            router["latency_ms"] = min(router["latency_ms"], 45.0)
            router["packet_loss_pct"] = max(0.0, router["packet_loss_pct"] - 8.0)
            result["success"] = True
            result["details"] = "Routing tables cleared and rebuilt. Latency stabilized."
        else:
            result["success"] = True
            result["details"] = "Routing table was healthy. No changes made."
            
    elif action == "terminate_nat_sessions":
        if "EXCESSIVE_NAT_SESSIONS" in router["system_errors"]:
            router["system_errors"].remove("EXCESSIVE_NAT_SESSIONS")
            router["active_connections"] = 120
            router["memory_usage_pct"] = max(35.0, router["memory_usage_pct"] - 40.0)
            router["packet_loss_pct"] = max(0.0, router["packet_loss_pct"] - 5.0)
            result["success"] = True
            result["details"] = "Stale NAT sessions terminated. Memory usage reduced."
        else:
            result["success"] = True
            result["details"] = "NAT sessions under threshold limits. No changes made."
            
    elif action == "reboot_router":
        # Rebooting fixes all persistent software/session errors
        router["system_errors"] = []
        router["latency_ms"] = 12.5
        router["packet_loss_pct"] = 0.0
        router["cpu_usage_pct"] = 15.0
        router["memory_usage_pct"] = 28.0
        router["dns_resolution"] = "success"
        router["connection_state"] = "healthy"
        router["active_connections"] = 45
        router["uptime_seconds"] = 10
        router["status"] = "healthy"
        result["success"] = True
        result["details"] = "Router rebooted successfully. All telemetry cleared and returned to normal limits."
        
    else:
        result["success"] = False
        result["details"] = f"Unknown action: '{action}'. Choose from 'flush_dns_cache', 'clear_routing_table', 'terminate_nat_sessions', 'reboot_router'."
        
    # Check if router is now fully healthy
    if len(router["system_errors"]) == 0 and router["latency_ms"] < 50.0 and router["packet_loss_pct"] < 1.0:
        router["status"] = "healthy"
        router["connection_state"] = "healthy"
        
    result["router_state"] = router.copy()
    return result
