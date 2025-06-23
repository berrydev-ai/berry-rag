#!/bin/bash

# BerryRAG Docker Management Scripts
# Helper commands for managing the Docker-based BerryRAG system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before proceeding."
        return 1
    fi
    return 0
}

# Build all services
build_all() {
    print_status "Building all Docker services..."
    docker-compose build --no-cache
    print_success "All services built successfully!"
}

# Start all services
start_all() {
    check_env_file || return 1
    print_status "Starting all services..."
    docker-compose up -d postgres app mcp-server
    print_success "All services started!"
    print_status "Services running:"
    print_status "  - PostgreSQL: localhost:${POSTGRES_PORT:-5432}"
    print_status "  - RAG App: localhost:${APP_PORT:-8000}"
    print_status "  - MCP Server: localhost:${MCP_PORT:-3000}"
}

# Stop all services
stop_all() {
    print_status "Stopping all services..."
    docker-compose down
    print_success "All services stopped!"
}

# Restart all services
restart_all() {
    print_status "Restarting all services..."
    docker-compose restart
    print_success "All services restarted!"
}

# Process scraped files
process_scraped() {
    check_env_file || return 1
    print_status "Processing scraped files..."
    docker-compose run --rm playwright-service
    print_success "Scraped files processed!"
}

# Run RAG system commands
run_rag_command() {
    local command="$1"
    shift
    check_env_file || return 1
    print_status "Running RAG command: $command"
    docker-compose exec app python src/rag_system_pgvector.py "$command" "$@"
}

# Run MCP server in interactive mode
run_mcp_interactive() {
    check_env_file || return 1
    print_status "Starting MCP server in interactive mode..."
    docker-compose run --rm --service-ports mcp-server
}

# View logs
view_logs() {
    local service="${1:-}"
    if [ -z "$service" ]; then
        print_status "Viewing logs for all services..."
        docker-compose logs -f
    else
        print_status "Viewing logs for service: $service"
        docker-compose logs -f "$service"
    fi
}

# Clean up everything
cleanup() {
    print_warning "This will remove all containers, volumes, and images. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Cleaning up Docker resources..."
        docker-compose down -v --rmi all
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Health check
health_check() {
    print_status "Checking service health..."
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Services are running"
        
        # Check PostgreSQL
        if docker-compose exec postgres pg_isready -U berryrag -d berryrag >/dev/null 2>&1; then
            print_success "PostgreSQL is healthy"
        else
            print_error "PostgreSQL is not responding"
        fi
        
        # Check app service
        if docker-compose exec app python -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
            print_success "App service is healthy"
        else
            print_error "App service is not responding"
        fi
        
        # Check MCP server
        if docker-compose ps mcp-server | grep -q "Up"; then
            print_success "MCP server is running"
        else
            print_warning "MCP server is not running"
        fi
        
    else
        print_error "No services are running"
    fi
}

# Show usage
show_usage() {
    echo "BerryRAG Docker Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  build              Build all Docker services"
    echo "  start              Start all services"
    echo "  stop               Stop all services"
    echo "  restart            Restart all services"
    echo "  process-scraped    Process scraped files with Playwright integration"
    echo "  rag <command>      Run RAG system command (search, list, stats, etc.)"
    echo "  mcp-interactive    Run MCP server in interactive mode"
    echo "  logs [service]     View logs (all services or specific service)"
    echo "  health             Check service health"
    echo "  cleanup            Remove all containers, volumes, and images"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 rag search \"React hooks\" # Search the vector database"
    echo "  $0 rag stats               # Show database statistics"
    echo "  $0 logs app                # View app service logs"
    echo "  $0 process-scraped         # Process new scraped content"
}

# Main command dispatcher
case "${1:-}" in
    build)
        build_all
        ;;
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    process-scraped)
        process_scraped
        ;;
    rag)
        shift
        run_rag_command "$@"
        ;;
    mcp-interactive)
        run_mcp_interactive
        ;;
    logs)
        view_logs "$2"
        ;;
    health)
        health_check
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_usage
        ;;
    "")
        print_error "No command specified."
        show_usage
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac
