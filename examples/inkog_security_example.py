"""
Inkog Security Analysis Tool Example

This example demonstrates how to use the Inkog tool to analyze AI agent code
for security vulnerabilities like token bombing, prompt injection, and more.

Prerequisites:
1. Install inkog CLI: brew tap inkog-io/inkog && brew install inkog
2. Get free API key from https://app.inkog.io  
3. Set environment variable: export INKOG_API_KEY=your_key_here

The Inkog tool can detect:
- Token bombing attacks (loops where LLM controls termination)
- Prompt injection vulnerabilities
- Recursive tool calling without cycle detection  
- Missing human oversight for destructive operations
- Cross-tenant data leakage
- MCP tool poisoning
- EU AI Act / NIST / OWASP compliance issues
"""

import os
from praisonai_tools import InkogTool, scan_agent_code


def basic_security_scan():
    """Perform a basic security scan of the current directory."""
    print("🔍 Basic Security Scan Example")
    print("=" * 50)
    
    # Method 1: Using the class
    inkog = InkogTool()
    result = inkog.scan_directory(
        path=".",
        output_format="json",
        policy="balanced"  # balanced, low-noise, comprehensive
    )
    
    if "error" in result:
        print(f"❌ Scan failed: {result['error']}")
        return
    
    # Analyze the results
    analysis = inkog.analyze_findings(result)
    print(analysis)
    
    print("\n" + "=" * 50)


def advanced_security_scan():
    """Perform an advanced security scan with deep analysis."""
    print("🔬 Advanced Security Scan Example (Deep Analysis)")
    print("=" * 60)
    
    inkog = InkogTool()
    
    # Deep scan provides enhanced analysis with AI orchestrator
    result = inkog.scan_directory(
        path=".",
        output_format="json",
        policy="comprehensive",  # Show all findings including best practices
        deep=True,  # Enable AI orchestrator analysis (requires Inkog Deep role)
        verbose=True
    )
    
    if "error" in result:
        print(f"❌ Deep scan failed: {result['error']}")
        print("Note: Deep scans require the Inkog Deep role on your account")
        return
        
    # Show detailed analysis
    analysis = inkog.analyze_findings(result)
    print(analysis)
    
    # Show raw findings for debugging
    if "server_findings" in result:
        print(f"\n📊 Raw Findings ({len(result['server_findings'])} total):")
        for i, finding in enumerate(result["server_findings"][:3]):  # Show first 3
            print(f"{i+1}. {finding.get('pattern', 'Unknown')} - {finding.get('severity', 'N/A')}")
            print(f"   File: {finding.get('file', 'N/A')}:{finding.get('line', 'N/A')}")
            print(f"   Message: {finding.get('message', 'N/A')}")
            print()
    
    print("=" * 60)


def skill_package_scan():
    """Scan a SKILL.md package or MCP server."""
    print("📦 Skill Package Security Scan Example")
    print("=" * 50)
    
    inkog = InkogTool()
    
    # Scan current directory as a skill package
    result = inkog.skill_scan(
        path=".",
        output_format="json",
        deep=False
    )
    
    if "error" in result:
        print(f"❌ Skill scan failed: {result['error']}")
        return
        
    analysis = inkog.analyze_findings(result)
    print(analysis)
    
    print("\n" + "=" * 50)


def mcp_server_scan():
    """Scan an MCP server from the registry."""
    print("🔌 MCP Server Security Scan Example")
    print("=" * 50)
    
    inkog = InkogTool()
    
    # Scan a popular MCP server (GitHub)
    result = inkog.mcp_scan(
        server_name="github",
        output_format="json"
    )
    
    if "error" in result:
        print(f"❌ MCP scan failed: {result['error']}")
        return
        
    analysis = inkog.analyze_findings(result)
    print(analysis)
    
    print("\n" + "=" * 50)


def standalone_function_example():
    """Example using standalone functions for quick scans."""
    print("⚡ Standalone Function Examples")
    print("=" * 40)
    
    # Quick scan using standalone function
    print("Running quick security scan...")
    result = scan_agent_code(
        path=".", 
        output_format="json",
        policy="low-noise",  # Only critical vulnerabilities
        deep=False
    )
    
    if isinstance(result, dict) and "error" not in result:
        tool = InkogTool()
        analysis = tool.analyze_findings(result)
        print(analysis)
    else:
        print(f"Scan result: {result}")
    
    print("\n" + "=" * 40)


def html_report_example():
    """Generate an HTML security report."""
    print("📄 HTML Report Generation Example")
    print("=" * 45)
    
    inkog = InkogTool()
    
    # Generate HTML report
    html_report = inkog.scan_directory(
        path=".",
        output_format="html",
        policy="comprehensive",
        deep=False
    )
    
    if isinstance(html_report, str) and not html_report.startswith("Error"):
        # Save report to file
        report_path = "inkog_security_report.html"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"✅ HTML report generated: {report_path}")
        print(f"📄 Report size: {len(html_report)} characters")
    else:
        print(f"❌ HTML report failed: {html_report}")
    
    print("=" * 45)


def compliance_scan_example():
    """Example focused on compliance mapping."""
    print("🏛️ Compliance Mapping Example")
    print("=" * 40)
    
    # Use comprehensive policy to see compliance mappings
    inkog = InkogTool()
    result = inkog.scan_directory(
        path=".",
        output_format="json", 
        policy="comprehensive",  # Shows compliance mappings
        deep=False
    )
    
    if "error" in result:
        print(f"❌ Compliance scan failed: {result['error']}")
        return
        
    # Look for compliance information
    findings = result.get("server_findings", [])
    compliance_findings = []
    
    for finding in findings:
        if any(term in finding.get("message", "").lower() 
               for term in ["eu ai act", "nist", "owasp", "iso", "article"]):
            compliance_findings.append(finding)
    
    if compliance_findings:
        print(f"📋 Found {len(compliance_findings)} compliance-related findings:")
        for finding in compliance_findings[:3]:  # Show first 3
            print(f"• {finding.get('pattern', 'Unknown')}")
            print(f"  {finding.get('message', 'N/A')[:100]}...")
    else:
        print("✅ No specific compliance violations found")
        
    print("=" * 40)


def main():
    """Run all examples."""
    print("Inkog Security Analysis Tool Examples")
    print("=" * 60)
    
    # Check if inkog is available
    api_key = os.environ.get("INKOG_API_KEY")
    if not api_key:
        print("⚠️  WARNING: INKOG_API_KEY environment variable not set")
        print("   Get your free API key at https://app.inkog.io")
        print("   Set it with: export INKOG_API_KEY=your_key_here")
        print()
    
    try:
        # Run examples in order of complexity
        basic_security_scan()
        standalone_function_example()
        skill_package_scan()
        html_report_example()
        compliance_scan_example()
        
        # Advanced features (may require special access)
        print("\n🎓 Advanced Examples (may require Inkog Deep role):")
        print("-" * 50)
        advanced_security_scan()
        mcp_server_scan()
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        print("This may be due to:")
        print("1. Inkog CLI not installed")
        print("2. Missing INKOG_API_KEY environment variable")
        print("3. Network connectivity issues")
        print("4. Insufficient permissions for deep scans")


if __name__ == "__main__":
    main()