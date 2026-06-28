# Inkog Security Analysis Integration

This document describes the integration of [Inkog](https://github.com/inkog-io/inkog) security analysis capabilities into PraisonAI-Tools.

## Overview

Inkog is a specialized security analysis tool for AI agent code that detects vulnerabilities unique to agentic systems. It performs static analysis to catch bugs that only break in agent code, such as:

- **Token bombing** - loops where the LLM controls termination, draining API budgets
- **Recursive tool calling** - one user request fans out into thousands of LLM invocations  
- **Prompt injection sinks** - RAG output flowing into system prompts without review
- **Missing oversight** - destructive tools firing without human approval
- **Cross-tenant leakage** - global state shared between agent invocations
- **MCP tool poisoning** - malicious tool descriptions hijacking agents

## Features

### Framework Support
- **21+ frameworks**: LangChain, CrewAI, AutoGen, OpenAI Agents, LangGraph, DSPy, Phidata, and more
- **Multiple languages**: Python, TypeScript, JavaScript, and no-code platforms
- **MCP servers**: Audit Model Context Protocol servers for security issues

### Compliance Mapping
- **EU AI Act** Articles 14/15 (human oversight requirements)
- **NIST AI RMF** (risk management framework)
- **ISO 42001** (AI management systems)
- **OWASP LLM Top 10** (security vulnerabilities)

### Scan Types
- **Core scan**: Fast static analysis with vulnerability detection
- **Deep scan**: AI orchestrator-driven analysis with enhanced context
- **Skill scan**: Security analysis of SKILL.md packages and agent tools
- **MCP scan**: Audit MCP servers for tool poisoning and privilege escalation

## Installation

### Prerequisites

1. **Install Inkog CLI**:
   ```bash
   # macOS (Homebrew)
   brew tap inkog-io/inkog && brew install inkog
   
   # Or install via Go
   go install github.com/inkog-io/inkog/cmd/inkog@latest
   
   # Or download binary from releases
   # https://github.com/inkog-io/inkog/releases
   ```

2. **Get API Key**:
   - Visit [app.inkog.io](https://app.inkog.io) to get a free API key
   - Set environment variable: `export INKOG_API_KEY=your_key_here`

3. **Verify Installation**:
   ```bash
   inkog -version
   ```

## Usage

### Basic Usage

```python
from praisonai_tools import InkogTool

# Initialize the tool
inkog = InkogTool()

# Scan current directory for vulnerabilities
result = inkog.scan_directory(
    path=".",
    output_format="json", 
    policy="balanced"
)

# Analyze results
analysis = inkog.analyze_findings(result)
print(analysis)
```

### Standalone Functions

```python
from praisonai_tools.tools.inkog_tool import scan_agent_code, scan_skill_package

# Quick scan using standalone function
result = scan_agent_code("./my-agent", policy="low-noise")

# Scan a skill package
skill_result = scan_skill_package("./my-skill", deep=True)
```

### Advanced Scanning

```python
# Deep scan with AI orchestrator (requires Inkog Deep role)
deep_result = inkog.scan_directory(
    path="./agent-code",
    output_format="json",
    policy="comprehensive", 
    deep=True,
    severity="high"
)

# Generate HTML report
html_report = inkog.scan_directory(
    path="./agent-code",
    output_format="html",
    policy="balanced"
)

# Save report to file
with open("security_report.html", "w") as f:
    f.write(html_report)
```

### MCP Server Auditing

```python
# Scan MCP server by name
mcp_result = inkog.mcp_scan("github")

# Scan MCP server with custom repository
mcp_result = inkog.mcp_scan(
    "my-server", 
    repo="https://github.com/org/my-mcp-server",
    deep=True
)
```

## Configuration

### Environment Variables

- **`INKOG_API_KEY`** (required): API key from app.inkog.io
- **`INKOG_SERVER_URL`** (optional): Custom server URL for enterprise deployments

### Security Policies

Choose the appropriate policy based on your use case:

- **`low-noise`**: Only exploitable vulnerabilities (good for CI/CD)
- **`balanced`**: Vulnerabilities + risk patterns (default, good for code review)  
- **`comprehensive`**: All findings including hardening recommendations (good for security audits)

### Output Formats

- **`json`**: Structured data for programmatic processing
- **`text`**: Human-readable terminal output  
- **`html`**: Interactive report with visualizations
- **`sarif`**: SARIF format for GitHub Security tab integration

### Severity Levels

- **`critical`**: Immediate security threats
- **`high`**: Serious vulnerabilities that should be addressed soon
- **`medium`**: Moderate issues worth reviewing
- **`low`**: Minor issues and best practice recommendations

## Integration Examples

### PraisonAI Agent Security Audit

```python
from praisonaiagents import Agent
from praisonai_tools import InkogTool

# Create an agent with security analysis capability
security_agent = Agent(
    name="security_auditor",
    instructions="You analyze AI agent code for security vulnerabilities",
    tools=[InkogTool()]
)

# Audit agent code
audit_result = security_agent.start("""
Scan the ./my-agent directory for security vulnerabilities.
Focus on critical and high severity issues.
Provide a summary of findings and remediation recommendations.
""")

print(audit_result)
```

### CI/CD Pipeline Integration

```python
import sys
from praisonai_tools.tools.inkog_tool import scan_agent_code

def security_check():
    """Security check for CI/CD pipeline."""
    result = scan_agent_code(
        path=".",
        policy="low-noise",  # Only critical vulnerabilities
        severity="critical"
    )
    
    if "error" in result:
        print(f"Security scan failed: {result['error']}")
        return 1
    
    critical_count = result.get("summary", {}).get("critical", 0)
    if critical_count > 0:
        print(f"❌ Found {critical_count} critical security issues")
        return 1
    
    print("✅ No critical security vulnerabilities found")
    return 0

if __name__ == "__main__":
    sys.exit(security_check())
```

### Multi-Agent Security Review

```python
from praisonaiagents import Agent, AgentTeam
from praisonai_tools import InkogTool

# Security analysis agent
security_analyzer = Agent(
    name="security_analyzer",
    instructions="Analyze code for security vulnerabilities using Inkog",
    tools=[InkogTool()]
)

# Code reviewer agent  
code_reviewer = Agent(
    name="code_reviewer",
    instructions="Review security findings and provide remediation advice"
)

# Create security review team
security_team = AgentTeam(
    name="security_review_team",
    agents=[security_analyzer, code_reviewer],
    tasks=[
        {"agent": "security_analyzer", "task": "Scan the codebase for vulnerabilities"},
        {"agent": "code_reviewer", "task": "Review findings and create remediation plan"}
    ]
)

# Run security review
review_result = security_team.start("Perform comprehensive security review of ./agent-code")
```

## Error Handling

The tool provides detailed error messages for common issues:

```python
result = inkog.scan_directory("./nonexistent")

if "error" in result:
    error_msg = result["error"]
    
    if "not installed" in error_msg:
        print("Install inkog CLI first")
    elif "API_KEY" in error_msg:
        print("Set INKOG_API_KEY environment variable")
    elif "timeout" in error_msg:
        print("Scan timed out - try smaller directory or increase timeout")
    else:
        print(f"Scan error: {error_msg}")
```

## Best Practices

### 1. Development Workflow
```bash
# Add to your development script
inkog . --policy balanced --output json > security_report.json
```

### 2. Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: inkog-security-scan
        name: Inkog Security Scan
        entry: inkog
        args: [".", "--policy", "low-noise", "--severity", "critical"]
        language: system
        always_run: true
```

### 3. GitHub Actions
```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Inkog
        run: |
          curl -fsSL https://inkog.io/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Run Security Scan
        env:
          INKOG_API_KEY: ${{ secrets.INKOG_API_KEY }}
        run: inkog . --output sarif > results.sarif
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results.sarif
```

## Privacy & Security

Inkog uses "surgical redaction" to protect sensitive data:

### What Gets Redacted
- AWS access keys, GitHub tokens, Stripe keys
- Database connection strings with passwords
- Private keys and JWT tokens  
- High-entropy strings (API keys)

### What is NOT Redacted
- Prompts and templates (needed for injection detection)
- Business logic (needed for flow analysis)
- Configuration values (model names, etc.)
- Normal strings that don't match credential patterns

## Troubleshooting

### Common Issues

1. **"inkog CLI not installed"**
   - Install via Homebrew: `brew tap inkog-io/inkog && brew install inkog`
   - Or download from releases: https://github.com/inkog-io/inkog/releases

2. **"INKOG_API_KEY required"**
   - Get free key at https://app.inkog.io
   - Set environment variable: `export INKOG_API_KEY=your_key`

3. **"Deep scan requires Inkog Deep role"**
   - Deep scans need special account permissions
   - Use standard scan instead: `deep=False`

4. **"Scan timed out"**
   - Large codebases may timeout
   - Scan specific directories instead of entire project
   - Use policy="low-noise" for faster scans

### Debug Mode

Enable verbose output for troubleshooting:

```python
result = inkog.scan_directory(
    path=".",
    verbose=True  # Shows detailed analysis steps
)
```

## Support

- **Documentation**: https://docs.inkog.io
- **GitHub Issues**: https://github.com/inkog-io/inkog/issues  
- **Community**: https://discord.gg/NuG4SSGRH
- **Security**: security@inkog.io

## References

- [Inkog Repository](https://github.com/inkog-io/inkog)
- [State of AI Agent Security 2026 Report](https://inkog.io/report)
- [EU AI Act Compliance Guide](https://docs.inkog.io/compliance/eu-ai-act)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)