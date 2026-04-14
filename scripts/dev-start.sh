#!/bin/bash
#
# ScholarAI Dev Start Script
# Interactive menu for debugging and development
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Service groups
DB_SERVICES="postgres redis neo4j etcd minio milvus-standalone"
BACKEND_SERVICES="backend celery_worker"
ALL_SERVICES="$DB_SERVICES $BACKEND_SERVICES"

# Helper functions
print_header() {
    echo -e "${CYAN}"
    echo "========================================"
    echo "  ScholarAI 智读 - Dev Start Script"
    echo "========================================"
    echo -e "${NC}"
}

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

# Check if docker-compose is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available"
        exit 1
    fi
    print_success "Docker and Docker Compose are available"
}

# Show service status
show_status() {
    print_status "Checking service status..."
    echo ""
    cd "$PROJECT_ROOT"
    docker compose ps
    echo ""
}

# Start database services only
start_db() {
    print_status "Starting database services: $DB_SERVICES"
    cd "$PROJECT_ROOT"
    docker compose up -d $DB_SERVICES
    print_success "Database services started"
    show_status
}

# Start backend services only
start_backend() {
    print_status "Starting backend services: $BACKEND_SERVICES"
    cd "$PROJECT_ROOT"
    docker compose up -d $BACKEND_SERVICES
    print_success "Backend services started"
    show_status
}

# Start all services
start_all() {
    print_status "Starting all services..."
    cd "$PROJECT_ROOT"
    docker compose up -d
    print_success "All services started"
    show_status
}

# View backend logs
view_backend_logs() {
    print_status "Viewing backend logs (Ctrl+C to exit)..."
    cd "$PROJECT_ROOT"
    docker compose logs -f backend
}

# View celery logs
view_celery_logs() {
    print_status "Viewing celery worker logs (Ctrl+C to exit)..."
    cd "$PROJECT_ROOT"
    docker compose logs -f celery_worker
}

# View all logs
view_all_logs() {
    print_status "Viewing all logs (Ctrl+C to exit)..."
    cd "$PROJECT_ROOT"
    docker compose logs -f
}

# Stop all services
stop_all() {
    print_status "Stopping all services..."
    cd "$PROJECT_ROOT"
    docker compose down
    print_success "All services stopped"
    show_status
}

# Stop and remove volumes (clean reset)
clean_reset() {
    print_warning "This will remove all data volumes!"
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        print_status "Stopping services and removing volumes..."
        cd "$PROJECT_ROOT"
        docker compose down -v
        print_success "Clean reset completed"
    else
        print_status "Clean reset cancelled"
    fi
}

# Restart backend services
restart_backend() {
    print_status "Restarting backend services..."
    cd "$PROJECT_ROOT"
    docker compose restart $BACKEND_SERVICES
    print_success "Backend services restarted"
    show_status
}

# Show interactive menu
show_menu() {
    print_header
    echo ""
    echo "Available options:"
    echo ""
    echo "  1) Start database services only (postgres, redis, neo4j, milvus...)"
    echo "  2) Start backend services only (backend, celery_worker)"
    echo "  3) Start all services"
    echo "  4) View backend logs (follow mode)"
    echo "  5) View celery worker logs (follow mode)"
    echo "  6) View all logs (follow mode)"
    echo "  7) Show service status"
    echo "  8) Stop all services"
    echo "  9) Clean reset (stop + remove volumes)"
    echo "  r) Restart backend services"
    echo "  q) Quit"
    echo ""
}

# Main loop
main() {
    check_docker

    while true; do
        show_menu
        read -p "Select option (1-9, r, q): " choice
        echo ""

        case $choice in
            1)
                start_db
                ;;
            2)
                start_backend
                ;;
            3)
                start_all
                ;;
            4)
                view_backend_logs
                ;;
            5)
                view_celery_logs
                ;;
            6)
                view_all_logs
                ;;
            7)
                show_status
                ;;
            8)
                stop_all
                ;;
            9)
                clean_reset
                ;;
            r|R)
                restart_backend
                ;;
            q|Q)
                print_status "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid option: $choice"
                ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
        echo ""
    done
}

# Run main
main