#!/bin/bash
# Local security scanning script for ScholarAI
# Run this before committing to catch security issues early

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default scan types
RUN_BANDIT=true
RUN_PIP_AUDIT=true
RUN_NPM_AUDIT=true
RUN_SEMGREP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --python-only)
      RUN_NPM_AUDIT=false
      shift
      ;;
    --node-only)
      RUN_BANDIT=false
      RUN_PIP_AUDIT=false
      shift
      ;;
    --semgrep)
      RUN_SEMGREP=true
      shift
      ;;
    --all)
      RUN_SEMGREP=true
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --python-only    Run only Python security checks"
      echo "  --node-only      Run only Node.js security checks"
      echo "  --semgrep        Include Semgrep SAST scan"
      echo "  --all            Run all security checks including Semgrep"
      echo "  --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}=== ScholarAI Security Scan ===${NC}"
echo ""

# Track overall status
OVERALL_STATUS=0

# ─── Python Security Checks ────────────────────────────────────────────
if [ "$RUN_BANDIT" = true ] || [ "$RUN_PIP_AUDIT" = true ]; then
  echo -e "${YELLOW}Running Python security checks...${NC}"

  cd "$ROOT_DIR/apps/api"

  # Check if virtual environment exists
  if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo -e "${YELLOW}Warning: No virtual environment found. Using system Python.${NC}"
  fi

  # Run Bandit
  if [ "$RUN_BANDIT" = true ]; then
    echo ""
    echo -e "${YELLOW}Running Bandit SAST scan...${NC}"
    if command -v bandit &> /dev/null; then
      bandit -r app/ -ll -ii --skip B101,B311 || OVERALL_STATUS=1
    else
      echo -e "${RED}Bandit not installed. Install with: pip install bandit${NC}"
    fi
  fi

  # Run pip-audit
  if [ "$RUN_PIP_AUDIT" = true ]; then
    echo ""
    echo -e "${YELLOW}Running pip-audit dependency check...${NC}"
    if command -v pip-audit &> /dev/null; then
      pip-audit -r requirements.txt || OVERALL_STATUS=1
    else
      echo -e "${RED}pip-audit not installed. Install with: pip install pip-audit${NC}"
    fi
  fi

  cd "$ROOT_DIR"
fi

# ─── Node.js Security Checks ──────────────────────────────────────────
if [ "$RUN_NPM_AUDIT" = true ]; then
  echo ""
  echo -e "${YELLOW}Running Node.js security checks...${NC}"

  # Check web app
  if [ -f "apps/web/package.json" ]; then
    echo ""
    echo -e "${YELLOW}Auditing apps/web dependencies...${NC}"
    cd "$ROOT_DIR/apps/web"
    npm audit --audit-level=high || OVERALL_STATUS=1
    cd "$ROOT_DIR"
  fi

  # Check root package
  if [ -f "package.json" ]; then
    echo ""
    echo -e "${YELLOW}Auditing root dependencies...${NC}"
    cd "$ROOT_DIR"
    npm audit --audit-level=high || OVERALL_STATUS=1
  fi
fi

# ─── Semgrep SAST ──────────────────────────────────────────────────────
if [ "$RUN_SEMGREP" = true ]; then
  echo ""
  echo -e "${YELLOW}Running Semgrep SAST scan...${NC}"

  if command -v semgrep &> /dev/null; then
    cd "$ROOT_DIR"
    semgrep scan \
      --config .semgrep.yml \
      --config "p/security-audit" \
      --config "p/secrets" \
      --error \
      --verbose \
      || OVERALL_STATUS=1
  else
    echo -e "${RED}Semgrep not installed.${NC}"
    echo "Install with: pip install semgrep"
    echo "Or use Docker: docker run --rm -v \"\$PWD:/src\" semgrep/semgrep semgrep scan --config auto"
  fi
fi

# ─── Summary ───────────────────────────────────────────────────────────
echo ""
echo "========================================="
if [ $OVERALL_STATUS -eq 0 ]; then
  echo -e "${GREEN}✅ Security scan completed successfully${NC}"
else
  echo -e "${RED}❌ Security scan found issues${NC}"
  echo "Please review and fix the findings above."
fi
echo "========================================="

exit $OVERALL_STATUS
