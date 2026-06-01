# Security Scanning Guide

## Overview

ScholarAI implements a comprehensive security scanning strategy that integrates SAST (Static Application Security Testing), dependency scanning, container security, and secrets detection into the CI/CD pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Scanning Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Semgrep   │  │   CodeQL    │  │   Bandit    │            │
│  │    SAST     │  │  Analysis   │  │   Python    │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                │                │                    │
│         └────────────────┼────────────────┘                    │
│                          ▼                                     │
│                   ┌─────────────┐                              │
│                   │   Security  │                              │
│                   │   Summary   │                              │
│                   └──────┬──────┘                              │
│                          │                                     │
│  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────┐            │
│  │ npm audit   │  │   Trivy     │  │  Gitleaks   │            │
│  │  Node.js    │  │  Container  │  │   Secrets   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Tools

### 1. Semgrep

**Purpose**: Pattern-based SAST for Python and TypeScript

**Configuration**: `.semgrep.yml`

**Custom Rules**:
- SQL injection prevention
- Hardcoded secrets detection
- Unsafe deserialization
- Command injection
- Path traversal
- XSS via dangerouslySetInnerHTML
- FastAPI authentication checks

**Usage**:
```bash
# Run with project rules
semgrep scan --config .semgrep.yml

# Run with community rules
semgrep scan --config "p/security-audit" --config "p/secrets"

# Run in CI mode
semgrep ci
```

### 2. CodeQL

**Purpose**: Semantic code analysis for JavaScript/TypeScript and Python

**Configuration**: `.github/workflows/security.yml`

**Queries**: security-extended

**Usage**:
```bash
# Local analysis (requires CodeQL CLI)
codeql database create my-db --language=javascript-typescript
codeql database analyze my-db javascript-codeql.qls --format=sarif-latest --output=results.sarif
```

### 3. Bandit

**Purpose**: Python security linter

**Configuration**: Inline in workflow

**Skipped Rules**:
- B101: Use of assert (acceptable in tests)
- B311: Use of random (acceptable for non-cryptographic purposes)

**Usage**:
```bash
# Run on API code
cd apps/api
bandit -r app/ -ll -ii --skip B101,B311

# Generate JSON report
bandit -r app/ -ll -ii --skip B101,B311 --format json --output bandit-results.json
```

### 4. pip-audit

**Purpose**: Python dependency vulnerability scanning

**Usage**:
```bash
cd apps/api
pip-audit -r requirements.txt

# Strict mode (fail on any vulnerability)
pip-audit -r requirements.txt --strict
```

### 5. npm audit

**Purpose**: Node.js dependency vulnerability scanning

**Usage**:
```bash
cd apps/web
npm audit

# Fail on high severity
npm audit --audit-level=high
```

### 6. Trivy

**Purpose**: Container image vulnerability scanning

**Usage**:
```bash
# Scan Docker image
trivy image scholarai-backend:latest

# Scan with SARIF output
trivy image --format sarif --output results.sarif scholarai-backend:latest
```

### 7. Gitleaks

**Purpose**: Detection of hardcoded secrets and credentials

**Configuration**: `.gitleaks.toml`

**Usage**:
```bash
# Scan repository
gitleaks detect

# Scan with verbose output
gitleaks detect --verbose

# Scan specific path
gitleaks detect --source apps/api
```

## CI/CD Integration

### Workflow Structure

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  pull_request:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 6 * * *'  # Daily at 06:00 UTC

jobs:
  semgrep:
    # SAST scanning

  codeql:
    # Semantic analysis

  python-security:
    # Bandit + pip-audit

  node-security:
    # npm audit + Snyk

  container-security:
    # Trivy

  secrets-detection:
    # Gitleaks

  security-summary:
    # Aggregate results
```

### Integration with Existing Workflows

Security checks are integrated into:

1. **verify.yml**: Security quick scan as part of verify gate
2. **test.yml**: Security scan as build dependency
3. **governance.yml**: Security baseline check

### Failure Behavior

- **Critical findings**: Block PR merge
- **High findings**: Warning, allow merge with approval
- **Medium/Low findings**: Informational only

## Local Development

### Running Security Scans

Use the provided script:

```bash
# Run all security checks
bash scripts/security/run-security-scan.sh

# Run specific checks
bash scripts/security/run-security-scan.sh --python-only
bash scripts/security/run-security-scan.sh --node-only
bash scripts/security/run-security-scan.sh --semgrep
```

### Pre-commit Hooks

Install pre-commit hooks for automatic security checks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### IDE Integration

#### VS Code

Install extensions:
- **Semgrep**: Real-time SAST scanning
- **Python Security**: Bandit integration
- **Gitleaks**: Secrets detection

#### PyCharm

Install plugins:
- **Bandit**: Python security linting
- **Semgrep**: SAST scanning

## Security Rules

### OWASP Top 10 Coverage

| OWASP Category | Tools | Custom Rules |
|----------------|-------|--------------|
| A01: Broken Access Control | Semgrep, CodeQL | FastAPI auth checks |
| A02: Cryptographic Failures | Bandit, Semgrep | Weak crypto detection |
| A03: Injection | Semgrep, CodeQL | SQL injection, command injection |
| A04: Insecure Design | CodeQL | Pattern analysis |
| A05: Security Misconfiguration | Semgrep | Debug mode detection |
| A06: Vulnerable Components | pip-audit, npm audit | Dependency scanning |
| A07: Auth Failures | Semgrep, CodeQL | Auth dependency checks |
| A08: Data Integrity | Semgrep | Deserialization checks |
| A09: Logging Failures | Bandit | Logging analysis |
| A10: SSRF | Semgrep | URL validation |

### Custom Rule Categories

#### Python

- **SQL Injection**: Parameterized query enforcement
- **Command Injection**: Shell command prevention
- **Path Traversal**: File path validation
- **Hardcoded Secrets**: Credential detection
- **Unsafe Deserialization**: Pickle/YAML safety
- **FastAPI Auth**: Endpoint authentication

#### TypeScript/JavaScript

- **XSS**: dangerouslySetInnerHTML warnings
- **eval()**: Dynamic code execution prevention
- **Console.log**: Production logging cleanup
- **Hardcoded Tokens**: Credential detection
- **Open Redirect**: URL validation

## Best Practices

### For Developers

1. **Run scans locally** before committing
2. **Fix critical findings** immediately
3. **Review warnings** and assess risk
4. **Update dependencies** regularly
5. **Never commit secrets** to version control

### For Security Team

1. **Review SARIF results** in GitHub Security tab
2. **Monitor dependency alerts** via GitHub Dependabot
3. **Audit container images** before deployment
4. **Track security metrics** over time
5. **Update rules** based on new threats

### For CI/CD

1. **Fail fast** on critical findings
2. **Cache dependencies** for faster scans
3. **Parallelize scans** where possible
4. **Upload results** to GitHub Security
5. **Notify team** on failures

## Troubleshooting

### Common Issues

#### Semgrep Timeout

```bash
# Increase timeout
semgrep scan --timeout 300

# Scan specific directories
semgrep scan --include apps/api --include apps/web
```

#### False Positives

```bash
# Add to .semgrep.yml
rules:
  - id: my-rule
    paths:
      exclude:
        - test/
        - "*.test.ts"
```

#### Dependency Warnings

```bash
# Check specific package
pip-audit --fix -r requirements.txt

# Ignore specific vulnerability
pip-audit --ignore-vuln PYSEC-2024-XX
```

## References

- [Semgrep Documentation](https://semgrep.dev/docs/)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [pip-audit Documentation](https://pypi.org/project/pip-audit/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
