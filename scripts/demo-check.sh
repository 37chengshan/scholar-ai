#!/bin/bash
# ScholarAI Demo Environment Check Script
# Checks container status and API endpoints for demo readiness

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0

# Working directory (where docker-compose.yml is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  ScholarAI Demo Environment Check"
echo "=========================================="
echo ""

# Helper function: check service status
check_service() {
    local service="$1"
    local expected_state="${2:-running}"

    # Use docker-compose ps to get service status
    # Output format: name, command, state, ports
    local state
    state=$(docker-compose ps --services --filter "status=$expected_state" "$service" 2>/dev/null || echo "")

    if [ "$state" = "$service" ]; then
        echo -e "${GREEN}✅${NC} $service: $expected_state"
        ((PASS++))
        return 0
    else
        # Get actual state for debugging
        local actual
        actual=$(docker-compose ps "$service" 2>/dev/null | tail -1 | awk '{print $4}' || echo "unknown")
        echo -e "${RED}❌${NC} $service: expected $expected_state, actual: $actual"
        ((FAIL++))
        return 1
    fi
}

# Helper function: check HTTP endpoint
check_endpoint() {
    local url="$1"
    local expected_status="${2:-200}"
    local description="${3:-$url}"

    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")

    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✅${NC} $description: HTTP $status"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌${NC} $description: expected HTTP $expected_status, got HTTP $status"
        ((FAIL++))
        return 1
    fi
}

# ==========================================
# Container Status Checks
# ==========================================
echo "📦 Checking Container Status..."
echo ""

# Core databases
check_service "postgres" "running"
check_service "redis" "running"
check_service "neo4j" "running"

# Milvus dependencies
check_service "etcd" "running"
check_service "minio" "running"
check_service "milvus-standalone" "running"

# Application services
check_service "backend" "running"
check_service "celery_worker" "running"

echo ""

# ==========================================
# API Endpoint Checks (localhost from host)
# ==========================================
echo "🔌 Checking API Endpoints..."
echo ""

# Backend health endpoint
check_endpoint "http://localhost:8000/health" "200" "Backend Health"

# Backend API docs
check_endpoint "http://localhost:8000/docs" "200" "Backend API Docs"

# Database ports (basic connectivity)
check_endpoint "http://localhost:5432" "000" "PostgreSQL Port" || true  # PostgreSQL doesn't respond to HTTP
check_endpoint "http://localhost:6379" "000" "Redis Port" || true       # Redis doesn't respond to HTTP

# Neo4j HTTP interface
check_endpoint "http://localhost:7474" "200" "Neo4j Browser"

# Milvus health
check_endpoint "http://localhost:9091/healthz" "200" "Milvus Health"

# MinIO health
check_endpoint "http://localhost:9000/minio/health/live" "200" "MinIO Health"

echo ""

# ==========================================
# Summary
# ==========================================
echo "=========================================="
echo "  Summary"
echo "=========================================="
echo ""
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Demo environment is ready.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please review the issues above.${NC}"
    echo ""
    echo "💡 Troubleshooting tips:"
    echo "   - Start containers: docker-compose up -d"
    echo "   - Check logs: docker-compose logs <service>"
    echo "   - Restart service: docker-compose restart <service>"
    exit 1
fi