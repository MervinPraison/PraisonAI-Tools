"""
Langextract Tool Example

This example demonstrates how to use the langextract tools for 
interactive text visualization and analysis with PraisonAI agents.

Prerequisites:
    pip install praisonai-tools[langextract]
    # or 
    pip install praisonai-tools langextract

Features demonstrated:
- Text analysis with highlighted extractions
- File-based document analysis  
- Integration with PraisonAI agents
- Interactive HTML generation
"""

import os
import tempfile
from pathlib import Path

from praisonai_tools import langextract_extract, langextract_render_file


def basic_text_analysis():
    """Demonstrate basic text analysis with highlighted extractions."""
    print("🔍 Basic Text Analysis with Langextract")
    print("=" * 50)
    
    # Sample contract text
    contract_text = """
    CONSULTING AGREEMENT
    
    This Agreement is entered into on March 15, 2024, between TechCorp Inc. 
    (the "Client") and Jane Smith (the "Consultant"). The Consultant will 
    provide AI development services for a period of 6 months starting 
    April 1, 2024. 
    
    Payment terms: $5,000 per month, payable within 15 days of invoice date.
    Confidentiality obligations remain in effect for 2 years after termination.
    """
    
    # Key terms to highlight
    key_terms = [
        "TechCorp Inc.",
        "Jane Smith", 
        "March 15, 2024",
        "April 1, 2024",
        "$5,000 per month",
        "15 days",
        "2 years",
        "AI development services"
    ]
    
    # Extract and visualize
    result = langextract_extract(
        text=contract_text,
        extractions=key_terms,
        document_id="consulting-agreement",
        output_path="contract_analysis.html",
        auto_open=False  # Set to True to open in browser automatically
    )
    
    if result.get("success"):
        print(f"✅ Analysis complete!")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Output file: {result['output_path']}")
        print(f"   Extractions: {result['extractions_count']} terms highlighted")
        print(f"   Text length: {result['text_length']} characters")
        print()
        print(f"💡 Open {result['output_path']} in your browser to view the interactive visualization!")
    else:
        print(f"❌ Error: {result.get('error')}")
        if "langextract not installed" in result.get("error", ""):
            print("💡 Install with: pip install langextract")


def file_analysis_example():
    """Demonstrate file-based document analysis."""
    print("📄 File-based Document Analysis")
    print("=" * 50)
    
    # Create a sample document
    document_content = """
    TECHNICAL SPECIFICATION DOCUMENT
    
    Project: AI-Powered Analytics Dashboard
    Version: 2.1.0
    Date: April 17, 2026
    
    REQUIREMENTS:
    - Python 3.10+ runtime environment
    - PostgreSQL 14+ database
    - Redis for caching layer
    - Docker for containerization
    - Kubernetes for orchestration
    
    SECURITY CONSIDERATIONS:
    - JWT authentication with 24-hour expiry
    - Rate limiting: 1000 requests per hour per API key
    - HTTPS-only communication
    - Data encryption at rest using AES-256
    
    PERFORMANCE TARGETS:
    - API response time: < 200ms for 95th percentile
    - Database query optimization required
    - Concurrent user support: 10,000+ users
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(document_content)
        temp_file_path = f.name
    
    try:
        # Technical terms to highlight
        tech_terms = [
            "Python 3.10+",
            "PostgreSQL 14+", 
            "Redis",
            "Docker",
            "Kubernetes",
            "JWT authentication",
            "24-hour expiry",
            "1000 requests per hour",
            "AES-256",
            "< 200ms",
            "10,000+ users"
        ]
        
        # Analyze the file
        result = langextract_render_file(
            file_path=temp_file_path,
            extractions=tech_terms,
            output_path="tech_spec_analysis.html",
            auto_open=False
        )
        
        if result.get("success"):
            print(f"✅ File analysis complete!")
            print(f"   Source file: {temp_file_path}")
            print(f"   Document ID: {result['document_id']}")
            print(f"   Output file: {result['output_path']}")
            print(f"   Extractions: {result['extractions_count']} terms highlighted")
            print(f"   Text length: {result['text_length']} characters")
            print()
            print(f"💡 Open {result['output_path']} in your browser to view the interactive visualization!")
        else:
            print(f"❌ Error: {result.get('error')}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass


def agent_integration_example():
    """Demonstrate integration with PraisonAI agents."""
    print("🤖 PraisonAI Agent Integration")
    print("=" * 50)
    
    # This is how you would integrate with agents
    agent_code = '''
from praisonaiagents import Agent
from praisonai_tools import langextract_extract, langextract_render_file

# Create an agent that analyzes documents
document_analyzer = Agent(
    name="DocumentAnalyzer",
    instructions="""
    You are a document analysis expert. When given text or documents,
    identify key entities, dates, financial figures, and important terms.
    Use langextract tools to create interactive visualizations highlighting
    your findings.
    """,
    tools=[langextract_extract, langextract_render_file]
)

# Agent workflow example
def analyze_document(text_or_file_path):
    """Agent analyzes document and creates visualization."""
    
    if text_or_file_path.endswith('.txt'):
        # File-based analysis
        response = document_analyzer.start(
            f"Analyze this document file and highlight key terms: {text_or_file_path}"
        )
    else:
        # Text-based analysis
        response = document_analyzer.start(
            f"Analyze this text and highlight important information: {text_or_file_path}"
        )
    
    return response

# Example usage:
# result = analyze_document("contract.txt")
# result = analyze_document("The quarterly report shows revenue of $1.2M...")
'''
    
    print("💻 Example agent integration code:")
    print(agent_code)
    print()
    print("🔧 Key integration points:")
    print("   - Import tools: langextract_extract, langextract_render_file")
    print("   - Add to agent tools list")
    print("   - Agent can automatically use tools based on instructions")
    print("   - Interactive HTML files created for human review")


def error_handling_example():
    """Demonstrate graceful error handling."""
    print("⚠️  Error Handling and Graceful Degradation")
    print("=" * 50)
    
    # Test without langextract installed (simulated)
    print("Testing graceful degradation when langextract is not installed:")
    
    result = langextract_extract(
        text="Sample text for analysis",
        extractions=["Sample"],
        document_id="test"
    )
    
    if "error" in result:
        print(f"✅ Graceful error handling: {result['error']}")
        print("💡 Users get clear installation instructions")
    else:
        print("✅ Langextract is available and working!")
    
    print()
    print("Common error scenarios handled:")
    print("   - ❌ langextract not installed → Clear installation message")
    print("   - ❌ Invalid file path → File not found error") 
    print("   - ❌ Empty text input → Parameter validation")
    print("   - ❌ Browser auto-open fails → Graceful fallback")


def main():
    """Run all examples."""
    print("🚀 Langextract Tool Examples for PraisonAI")
    print("=" * 70)
    print()
    
    try:
        basic_text_analysis()
        print()
        
        file_analysis_example()  
        print()
        
        agent_integration_example()
        print()
        
        error_handling_example()
        print()
        
        print("🎉 All examples completed!")
        print()
        print("📚 Next Steps:")
        print("   1. Install langextract: pip install langextract")
        print("   2. Run your own text analysis")
        print("   3. Integrate with your PraisonAI agents")
        print("   4. Open generated HTML files to see interactive visualizations")
        
    except Exception as e:
        print(f"❌ Example error: {e}")
        print("💡 This is expected if langextract is not installed")


if __name__ == "__main__":
    main()