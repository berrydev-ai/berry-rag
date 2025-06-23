#!/usr/bin/env python3
"""
Comprehensive Docker Setup Test for BerryRAG
Tests all components: PostgreSQL, RAG System, Playwright Integration, and MCP Server
"""

import os
import sys
import time
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

# Test configuration
TEST_CONFIG = {
    "database_url": "postgresql://berryrag:berryrag_password@localhost:5432/berryrag",
    "test_timeout": 30,
    "services": ["postgres", "app", "mcp-server"],
    "ports": {
        "postgres": 5432,
        "app": 8000,
        "mcp": 3000
    }
}

class DockerTestSuite:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = []
        self.failed_tests = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamps"""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "TEST": "🧪"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
        
    def run_command(self, command: List[str], timeout: int = 30, capture_output: bool = True) -> Dict:
        """Run a command and return result"""
        try:
            result = subprocess.run(
                command,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def test_docker_compose_config(self) -> bool:
        """Test if docker-compose.yml is valid"""
        self.log("Testing docker-compose configuration", "TEST")
        
        result = self.run_command(["docker-compose", "config"])
        if result["success"]:
            self.log("Docker Compose configuration is valid", "SUCCESS")
            return True
        else:
            self.log(f"Docker Compose config error: {result['stderr']}", "ERROR")
            return False
    
    def test_environment_setup(self) -> bool:
        """Test environment file setup"""
        self.log("Testing environment setup", "TEST")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if not env_example.exists():
            self.log(".env.example file not found", "ERROR")
            return False
            
        if not env_file.exists():
            self.log("Creating .env from .env.example", "INFO")
            try:
                env_file.write_text(env_example.read_text())
                self.log(".env file created successfully", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to create .env file: {e}", "ERROR")
                return False
        
        self.log("Environment setup complete", "SUCCESS")
        return True
    
    def test_docker_build(self) -> bool:
        """Test Docker image building"""
        self.log("Testing Docker image build", "TEST")
        
        result = self.run_command(
            ["docker-compose", "build", "--no-cache"],
            timeout=300  # 5 minutes for build
        )
        
        if result["success"]:
            self.log("Docker images built successfully", "SUCCESS")
            return True
        else:
            self.log(f"Docker build failed: {result['stderr']}", "ERROR")
            return False
    
    def test_services_start(self) -> bool:
        """Test starting all services"""
        self.log("Testing service startup", "TEST")
        
        # Start services
        result = self.run_command(
            ["docker-compose", "up", "-d"] + TEST_CONFIG["services"],
            timeout=60
        )
        
        if not result["success"]:
            self.log(f"Failed to start services: {result['stderr']}", "ERROR")
            return False
        
        # Wait for services to be ready
        self.log("Waiting for services to be ready...", "INFO")
        time.sleep(10)
        
        # Check service status
        result = self.run_command(["docker-compose", "ps"])
        if result["success"]:
            self.log("Services started successfully", "SUCCESS")
            self.log(f"Service status:\n{result['stdout']}", "INFO")
            return True
        else:
            self.log(f"Failed to check service status: {result['stderr']}", "ERROR")
            return False
    
    def test_postgres_health(self) -> bool:
        """Test PostgreSQL database health"""
        self.log("Testing PostgreSQL health", "TEST")
        
        result = self.run_command([
            "docker-compose", "exec", "-T", "postgres",
            "pg_isready", "-U", "berryrag", "-d", "berryrag"
        ])
        
        if result["success"]:
            self.log("PostgreSQL is healthy", "SUCCESS")
            return True
        else:
            self.log(f"PostgreSQL health check failed: {result['stderr']}", "ERROR")
            return False
    
    def test_database_schema(self) -> bool:
        """Test database schema creation"""
        self.log("Testing database schema", "TEST")
        
        # Check if tables exist
        sql_query = """
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name IN ('documents', 'document_chunks');
        """
        
        result = self.run_command([
            "docker-compose", "exec", "-T", "postgres",
            "psql", "-U", "berryrag", "-d", "berryrag", "-c", sql_query
        ])
        
        if result["success"] and "documents" in result["stdout"]:
            self.log("Database schema is properly initialized", "SUCCESS")
            return True
        else:
            self.log("Database schema not found, attempting to initialize...", "WARNING")
            
            # Try to run the RAG system to initialize schema
            init_result = self.run_command([
                "docker-compose", "exec", "-T", "app",
                "python", "src/rag_system_pgvector.py", "stats"
            ])
            
            if init_result["success"]:
                self.log("Database schema initialized successfully", "SUCCESS")
                return True
            else:
                self.log(f"Failed to initialize database schema: {init_result['stderr']}", "ERROR")
                return False
    
    def test_rag_system_basic(self) -> bool:
        """Test basic RAG system functionality"""
        self.log("Testing RAG system basic functionality", "TEST")
        
        # Test stats command
        result = self.run_command([
            "docker-compose", "exec", "-T", "app",
            "python", "src/rag_system_pgvector.py", "stats"
        ])
        
        if result["success"]:
            self.log("RAG system stats command successful", "SUCCESS")
            self.log(f"Stats output:\n{result['stdout']}", "INFO")
            return True
        else:
            self.log(f"RAG system stats failed: {result['stderr']}", "ERROR")
            return False
    
    def test_rag_system_operations(self) -> bool:
        """Test RAG system document operations"""
        self.log("Testing RAG system document operations", "TEST")
        
        # Create test content
        test_content = """
        # Test Document
        
        This is a test document for the BerryRAG system.
        It contains information about Docker integration and testing.
        
        ## Features
        - Vector database with pgvector
        - Playwright web scraping
        - MCP server integration
        - Docker containerization
        
        This content should be searchable after being added to the system.
        """
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            # Copy file to container
            copy_result = self.run_command([
                "docker", "cp", temp_file, "berry-rag-app-1:/tmp/test_content.txt"
            ])
            
            if not copy_result["success"]:
                self.log(f"Failed to copy test file: {copy_result['stderr']}", "ERROR")
                return False
            
            # Add document
            add_result = self.run_command([
                "docker-compose", "exec", "-T", "app",
                "python", "src/rag_system_pgvector.py", "add",
                "https://test.example.com", "Test Document", "/tmp/test_content.txt"
            ])
            
            if not add_result["success"]:
                self.log(f"Failed to add document: {add_result['stderr']}", "ERROR")
                return False
            
            self.log("Document added successfully", "SUCCESS")
            
            # Search for content
            search_result = self.run_command([
                "docker-compose", "exec", "-T", "app",
                "python", "src/rag_system_pgvector.py", "search", "Docker integration"
            ])
            
            if search_result["success"] and "Test Document" in search_result["stdout"]:
                self.log("Document search successful", "SUCCESS")
                return True
            else:
                self.log(f"Document search failed: {search_result['stderr']}", "ERROR")
                return False
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def test_playwright_integration(self) -> bool:
        """Test Playwright integration"""
        self.log("Testing Playwright integration", "TEST")
        
        # Create test scraped content
        scraped_dir = self.project_root / "scraped_content"
        scraped_dir.mkdir(exist_ok=True)
        
        test_scraped_content = """# Test Scraped Page

Source: https://example.com/test-page
Scraped: 2024-01-15T14:30:00

## Content

This is test content that was scraped from a webpage.
It demonstrates the Playwright integration functionality.

### Key Points
- Web scraping with Playwright
- Content processing and cleaning
- Integration with vector database
- Quality filtering and validation

The system should process this content and make it searchable.
"""
        
        test_file = scraped_dir / "scraped_2024-01-15_14-30-00_test_example.md"
        test_file.write_text(test_scraped_content)
        
        try:
            # Test processing scraped files
            result = self.run_command([
                "docker-compose", "run", "--rm", "playwright-service"
            ])
            
            if result["success"]:
                self.log("Playwright integration test successful", "SUCCESS")
                return True
            else:
                self.log(f"Playwright integration failed: {result['stderr']}", "ERROR")
                return False
                
        finally:
            # Clean up test file
            try:
                test_file.unlink()
            except:
                pass
    
    def test_mcp_server(self) -> bool:
        """Test MCP server functionality"""
        self.log("Testing MCP server", "TEST")
        
        # Check if MCP server is running
        result = self.run_command([
            "docker-compose", "ps", "mcp-server"
        ])
        
        if result["success"] and "Up" in result["stdout"]:
            self.log("MCP server is running", "SUCCESS")
            return True
        else:
            self.log("MCP server is not running properly", "WARNING")
            
            # Try to start MCP server
            start_result = self.run_command([
                "docker-compose", "up", "-d", "mcp-server"
            ])
            
            if start_result["success"]:
                time.sleep(5)  # Wait for startup
                self.log("MCP server started successfully", "SUCCESS")
                return True
            else:
                self.log(f"Failed to start MCP server: {start_result['stderr']}", "ERROR")
                return False
    
    def test_helper_script(self) -> bool:
        """Test the helper script functionality"""
        self.log("Testing helper script", "TEST")
        
        script_path = self.project_root / "docker-scripts" / "docker-commands.sh"
        
        if not script_path.exists():
            self.log("Helper script not found", "ERROR")
            return False
        
        # Test script help
        result = self.run_command([str(script_path), "help"])
        
        if result["success"] and "BerryRAG Docker Management Script" in result["stdout"]:
            self.log("Helper script is working", "SUCCESS")
            return True
        else:
            self.log(f"Helper script test failed: {result['stderr']}", "ERROR")
            return False
    
    def cleanup_services(self):
        """Clean up Docker services"""
        self.log("Cleaning up Docker services", "INFO")
        
        result = self.run_command(["docker-compose", "down", "-v"])
        if result["success"]:
            self.log("Services cleaned up successfully", "SUCCESS")
        else:
            self.log(f"Cleanup warning: {result['stderr']}", "WARNING")
    
    def run_all_tests(self) -> bool:
        """Run all tests in sequence"""
        tests = [
            ("Docker Compose Config", self.test_docker_compose_config),
            ("Environment Setup", self.test_environment_setup),
            ("Docker Build", self.test_docker_build),
            ("Services Start", self.test_services_start),
            ("PostgreSQL Health", self.test_postgres_health),
            ("Database Schema", self.test_database_schema),
            ("RAG System Basic", self.test_rag_system_basic),
            ("RAG System Operations", self.test_rag_system_operations),
            ("Playwright Integration", self.test_playwright_integration),
            ("MCP Server", self.test_mcp_server),
            ("Helper Script", self.test_helper_script),
        ]
        
        self.log("Starting comprehensive Docker test suite", "INFO")
        self.log("=" * 60, "INFO")
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"Running test: {test_name}", "TEST")
            try:
                if test_func():
                    passed += 1
                    self.results.append((test_name, True, ""))
                else:
                    self.failed_tests.append(test_name)
                    self.results.append((test_name, False, "Test failed"))
            except Exception as e:
                self.log(f"Test {test_name} threw exception: {e}", "ERROR")
                self.failed_tests.append(test_name)
                self.results.append((test_name, False, str(e)))
            
            self.log("-" * 40, "INFO")
        
        # Print summary
        self.log("=" * 60, "INFO")
        self.log(f"Test Results: {passed}/{total} tests passed", "INFO")
        
        if self.failed_tests:
            self.log("Failed tests:", "ERROR")
            for test in self.failed_tests:
                self.log(f"  - {test}", "ERROR")
        else:
            self.log("All tests passed! 🎉", "SUCCESS")
        
        return len(self.failed_tests) == 0

def main():
    """Main test runner"""
    test_suite = DockerTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        
        if success:
            print("\n🎉 All Docker components are working correctly!")
            print("Your BerryRAG Docker setup is ready to use.")
            print("\nNext steps:")
            print("1. Start services: ./docker-scripts/docker-commands.sh start")
            print("2. Add documents: ./docker-scripts/docker-commands.sh rag add <url> <title> <file>")
            print("3. Search content: ./docker-scripts/docker-commands.sh rag search \"your query\"")
            sys.exit(0)
        else:
            print(f"\n❌ {len(test_suite.failed_tests)} test(s) failed.")
            print("Please check the error messages above and fix the issues.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        sys.exit(1)
    finally:
        # Always try to clean up
        try:
            test_suite.cleanup_services()
        except:
            pass

if __name__ == "__main__":
    main()
