# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of ScholarAI seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to [security@scholarai.dev](mailto:security@scholarai.dev).

You should receive a response within 48 hours. If for some reason you do not, please follow up to ensure we received your original message.

### What to Include

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours.
- **Assessment**: We will assess the vulnerability and determine its impact.
- **Fix**: We will develop and test a fix for the vulnerability.
- **Release**: We will release the fix as soon as possible.
- **Disclosure**: We will publicly disclose the vulnerability after the fix is released.

## Security Scanning

ScholarAI uses automated security scanning in our CI/CD pipeline:

### SAST (Static Application Security Testing)

- **Semgrep**: Custom rules for Python and TypeScript security patterns
- **CodeQL**: GitHub's semantic code analysis for JavaScript/TypeScript and Python
- **Bandit**: Python security linter for common security issues

### Dependency Scanning

- **npm audit**: Node.js dependency vulnerability scanning
- **pip-audit**: Python dependency vulnerability scanning
- **Snyk**: Continuous dependency monitoring (requires API key)

### Container Security

- **Trivy**: Container image vulnerability scanning

### Secrets Detection

- **Gitleaks**: Detection of hardcoded secrets and credentials

## Running Security Scans Locally

### Prerequisites

Install the required security tools:

```bash
# Python security tools
pip install bandit pip-audit semgrep

# Node.js security tools (built-in)
npm install -g snyk  # Optional: for Snyk integration
```

### Running Scans

Use the provided security scanning script:

```bash
# Run all security checks
bash scripts/security/run-security-scan.sh

# Run only Python security checks
bash scripts/security/run-security-scan.sh --python-only

# Run only Node.js security checks
bash scripts/security/run-security-scan.sh --node-only

# Run with Semgrep SAST
bash scripts/security/run-security-scan.sh --semgrep

# Run all checks including Semgrep
bash scripts/security/run-security-scan.sh --all
```

### Manual Scanning

#### Python Security

```bash
cd apps/api

# Bandit SAST scan
bandit -r app/ -ll -ii --skip B101,B311

# Dependency vulnerability check
pip-audit -r requirements.txt

# Safety check (alternative to pip-audit)
safety check -r requirements.txt
```

#### Node.js Security

```bash
cd apps/web

# npm audit
npm audit

# Snyk test (requires API key)
snyk test
```

#### Semgrep SAST

```bash
# Run with project-specific rules
semgrep scan --config .semgrep.yml

# Run with community rules
semgrep scan --config "p/security-audit" --config "p/secrets"

# Run with all recommended rules
semgrep scan --config "p/default" --config "p/security-audit" --config "p/secrets" --config "p/python" --config "p/typescript"
```

## Security Best Practices

### For Developers

1. **Never commit secrets**: Use environment variables for API keys, passwords, and tokens.
2. **Validate all inputs**: Sanitize user input at system boundaries.
3. **Use parameterized queries**: Prevent SQL injection by using ORM or parameterized queries.
4. **Keep dependencies updated**: Regularly update dependencies to patch known vulnerabilities.
5. **Follow the principle of least privilege**: Grant minimal permissions required.
6. **Enable security headers**: Use appropriate HTTP security headers.
7. **Log security events**: Log authentication attempts, access control failures, etc.

### Code Review Checklist

When reviewing code for security:

- [ ] No hardcoded secrets or credentials
- [ ] All user inputs are validated and sanitized
- [ ] SQL queries use parameterized statements
- [ ] Authentication and authorization are properly implemented
- [ ] Sensitive data is encrypted at rest and in transit
- [ ] Error messages don't leak sensitive information
- [ ] Dependencies are up-to-date and have no known vulnerabilities

## Security Tools Configuration

### Semgrep

The project includes a `.semgrep.yml` configuration file with custom rules for:

- SQL injection prevention
- Hardcoded secrets detection
- Unsafe deserialization
- Command injection
- Path traversal
- XSS via dangerouslySetInnerHTML
- FastAPI authentication checks

### CodeQL

CodeQL is configured to analyze:

- JavaScript/TypeScript code
- Python code
- Security-extended queries

### Bandit

Bandit is configured to skip:

- B101: Use of assert (acceptable in tests)
- B311: Use of random (acceptable for non-cryptographic purposes)

## Incident Response

In case of a security incident:

1. **Contain**: Immediately contain the incident to prevent further damage.
2. **Assess**: Assess the impact and scope of the incident.
3. **Notify**: Notify affected users and stakeholders.
4. **Remediate**: Implement fixes to address the root cause.
5. **Document**: Document the incident and lessons learned.
6. **Review**: Review and update security measures.

## Contact

For security-related questions or concerns:

- Email: [security@scholarai.dev](mailto:security@scholarai.dev)
- Security Advisories: [GitHub Security Advisories](https://github.com/scholar-ai/scholar-ai/security/advisories)

## Acknowledgments

We would like to thank the following individuals for responsibly disclosing security vulnerabilities:

- (List will be updated as vulnerabilities are reported and fixed)

## References

- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
