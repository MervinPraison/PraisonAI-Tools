#!/usr/bin/env python3
"""
SwarmScore Integration Example for PraisonAI

This example demonstrates how to integrate SwarmScore trust ratings 
with PraisonAI agents for portable reputation management.

SwarmScore provides cryptographically signed trust ratings based on
verified execution history, success rates, and consistency.

Requirements:
    pip install requests praisonai-tools

Usage:
    python swarmscore_example.py
"""

import json
from praisonai_tools.tools import SwarmScoreTool, load_swarmscore_by_slug


def main():
    """Demonstrate SwarmScore integration with PraisonAI."""
    print("🔍 SwarmScore Integration Example")
    print("=" * 50)
    
    # Initialize SwarmScore tool
    swarmscore = SwarmScoreTool()
    
    # Example agent slug (replace with actual agent identifier)
    agent_slug = "example-agent-123"
    
    print(f"\n📊 Loading SwarmScore for agent: {agent_slug}")
    
    # Load SwarmScore data
    result = swarmscore.load_swarmscore(agent_slug)
    
    if result.success:
        print("✅ SwarmScore loaded successfully!")
        
        # Display basic score information
        score_data = result.data
        if 'score' in score_data:
            print(f"   Trust Score: {score_data['score']}")
        if 'tier' in score_data:
            print(f"   Trust Tier: {score_data['tier']}")
        if 'jobs_completed' in score_data:
            print(f"   Jobs Completed: {score_data['jobs_completed']}")
        if 'success_rate' in score_data:
            print(f"   Success Rate: {score_data['success_rate']}%")
        
        print(f"\n🔍 Full SwarmScore data:")
        print(json.dumps(score_data, indent=2))
        
        # Verify score freshness
        if 'verify_payload' in score_data:
            print(f"\n🔐 Verifying score freshness...")
            verify_result = swarmscore.verify_swarmscore(score_data['verify_payload'])
            
            if verify_result.success:
                print("✅ Score verification successful!")
                print(f"   Verification data: {verify_result.data}")
            else:
                print(f"❌ Score verification failed: {verify_result.error}")
    else:
        print(f"❌ Failed to load SwarmScore: {result.error}")
        print("\n💡 This might happen if:")
        print("   • The agent slug doesn't exist in SwarmScore")
        print("   • The SwarmScore API is temporarily unavailable")
        print("   • Network connectivity issues")
    
    # Get discovery manifest
    print(f"\n🌐 Loading agent discovery manifest...")
    manifest_result = swarmscore.get_discovery_manifest()
    
    if manifest_result.success:
        print("✅ Discovery manifest loaded!")
        print("   This contains machine-readable data for agent-to-agent discovery")
        print(f"   Manifest keys: {list(manifest_result.data.keys())}")
    else:
        print(f"❌ Failed to load manifest: {manifest_result.error}")
    
    # Demonstrate standalone function usage
    print(f"\n🛠️  Using standalone functions:")
    try:
        # This will likely fail with the example slug, but shows the API
        score_data = load_swarmscore_by_slug(agent_slug)
        print(f"✅ Standalone function succeeded: {score_data}")
    except Exception as e:
        print(f"❌ Standalone function failed (expected): {e}")
    
    print(f"\n📚 Next Steps:")
    print("   1. Register your agent at https://swarmsync.ai")
    print("   2. Get your agent slug from the SwarmSync dashboard")
    print("   3. Replace 'example-agent-123' with your actual slug")
    print("   4. Integrate SwarmScore checks into your agent workflows")
    print(f"\n   📖 Documentation: https://swarmsync.ai/docs/protocol-specs/swarmscore")


def agent_workflow_example():
    """Example of how to integrate SwarmScore into an agent workflow."""
    print(f"\n🤖 Agent Workflow Integration Example")
    print("=" * 45)
    
    # Simulated agent execution flow
    agent_id = "my-trading-agent"
    
    # 1. Load current trust score before executing task
    swarmscore = SwarmScoreTool()
    score_result = swarmscore.load_swarmscore(agent_id)
    
    if score_result.success:
        trust_score = score_result.data.get('score', 0)
        print(f"🔍 Agent {agent_id} current trust score: {trust_score}")
        
        # 2. Make decisions based on trust level
        if trust_score >= 80:
            print("✅ High trust - proceeding with full autonomy")
            task_approach = "autonomous"
        elif trust_score >= 60:
            print("⚠️  Medium trust - requesting human approval for critical actions")
            task_approach = "supervised"
        else:
            print("❌ Low trust - operating in restricted mode")
            task_approach = "restricted"
        
        # 3. Execute task based on trust level
        print(f"🚀 Executing task with {task_approach} approach...")
        
        # 4. After task completion, the score would be updated by SwarmSync
        # (This happens externally based on verified execution results)
        print("📝 Task completed - SwarmScore will be updated based on results")
        
    else:
        print(f"⚠️  Could not load trust score: {score_result.error}")
        print("🔄 Falling back to default security settings")


if __name__ == "__main__":
    main()
    agent_workflow_example()