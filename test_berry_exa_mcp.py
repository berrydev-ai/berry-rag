#!/usr/bin/env python3

"""
Test script for BerryExa MCP Server
Tests the MCP server functionality without requiring Claude Desktop
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

def test_mcp_server():
    """Test the BerryExa MCP server by sending JSON-RPC requests"""
    
    print("🍓 Testing BerryExa MCP Server...")
    
    # Test 1: List available tools
    print("\n1. Testing tools/list...")
    tools_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    process = None
    try:
        # Start the MCP server process
        process = subprocess.Popen(
            [sys.executable, "mcp_servers/berry_exa_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent
        )
        
        # Send the request
        request_json = json.dumps(tools_request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=10)
        
        if stderr:
            print(f"Server stderr: {stderr}")
        
        if stdout:
            try:
                response = json.loads(stdout.strip())
                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    print(f"✅ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"   - {tool['name']}: {tool['description']}")
                else:
                    print(f"❌ Unexpected response format: {response}")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw output: {stdout}")
        else:
            print("❌ No output received from server")
            
    except subprocess.TimeoutExpired:
        print("❌ Server timed out")
        if process:
            process.kill()
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        if process:
            process.kill()
    
    print("\n🍓 BerryExa MCP Server test complete!")

def test_docker_build():
    """Test that the Docker image builds successfully"""
    print("\n🐳 Testing Docker build...")
    
    try:
        result = subprocess.run(
            ["docker-compose", "build", "berry-exa-server"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print("✅ Docker build successful!")
        else:
            print(f"❌ Docker build failed:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Docker build timed out")
    except Exception as e:
        print(f"❌ Error building Docker image: {e}")

def main():
    """Run all tests"""
    print("🧪 BerryExa MCP Server Test Suite")
    print("=" * 50)
    
    # Test 1: MCP Server functionality
    test_mcp_server()
    
    # Test 2: Docker build
    test_docker_build()
    
    print("\n" + "=" * 50)
    print("🎉 Test suite complete!")

if __name__ == "__main__":
    main()
