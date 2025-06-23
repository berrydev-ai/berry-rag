#!/usr/bin/env python3
"""
Test script to verify Docker port configuration works correctly.
This script checks if the services are accessible on the configured ports.
"""

import os
import socket
import time
import sys
from urllib.parse import urlparse

def test_port_connectivity(host, port, service_name):
    """Test if a port is accessible."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ {service_name} is accessible on {host}:{port}")
            return True
        else:
            print(f"❌ {service_name} is NOT accessible on {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Error testing {service_name} on {host}:{port}: {e}")
        return False

def get_env_port(env_var, default_port):
    """Get port from environment variable or use default."""
    try:
        return int(os.getenv(env_var, default_port))
    except ValueError:
        print(f"⚠️  Invalid port value for {env_var}, using default {default_port}")
        return int(default_port)

def main():
    print("🔍 Testing Docker Port Configuration")
    print("=" * 50)
    
    # Get configured ports
    app_port = get_env_port('APP_PORT', 8000)
    postgres_port = get_env_port('POSTGRES_PORT', 5432)
    
    print(f"📋 Configuration:")
    print(f"   APP_PORT: {app_port}")
    print(f"   POSTGRES_PORT: {postgres_port}")
    print()
    
    # Test connectivity
    print("🔌 Testing port connectivity...")
    
    app_accessible = test_port_connectivity('localhost', app_port, 'Application')
    postgres_accessible = test_port_connectivity('localhost', postgres_port, 'PostgreSQL')
    
    print()
    
    # Summary
    if app_accessible and postgres_accessible:
        print("🎉 All services are accessible on configured ports!")
        print(f"   • Application: http://localhost:{app_port}")
        print(f"   • PostgreSQL: localhost:{postgres_port}")
        return 0
    else:
        print("⚠️  Some services are not accessible.")
        print("   Make sure Docker Compose is running with:")
        print("   docker-compose up")
        return 1

if __name__ == "__main__":
    sys.exit(main())
