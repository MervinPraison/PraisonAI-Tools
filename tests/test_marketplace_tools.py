"""Tests for marketplace tools."""

import pytest
import os
from praisonai_tools import (
    pinchwork_delegate, verify_agent_identity, check_trust_score,
    check_behavioral_trust, verify_task_delegation_safety,
    verify_handoff_safety, trust_verified_handoff,
    is_trust_verification_enabled, get_trust_config, JoyTrustTool
)


def test_marketplace_tools_import():
    """Test that marketplace tools can be imported."""
    assert pinchwork_delegate is not None
    assert verify_agent_identity is not None  
    assert check_trust_score is not None
    assert check_behavioral_trust is not None
    assert verify_task_delegation_safety is not None
    # New Joy Trust integration functions
    assert verify_handoff_safety is not None
    assert trust_verified_handoff is not None
    assert is_trust_verification_enabled is not None
    assert get_trust_config is not None
    assert JoyTrustTool is not None


def test_pinchwork_delegate_signature():
    """Test pinchwork_delegate tool signature and documentation."""
    # Check function exists and has proper signature
    assert callable(pinchwork_delegate)
    
    # Check documentation
    doc = pinchwork_delegate.__doc__
    assert "Delegate a task to the Pinchwork agent marketplace" in doc
    assert "task:" in doc
    assert "skills_required:" in doc
    assert "budget:" in doc


def test_verify_agent_identity_signature():
    """Test verify_agent_identity tool signature and documentation."""
    # Check function exists and has proper signature
    assert callable(verify_agent_identity)
    
    # Check documentation
    doc = verify_agent_identity.__doc__
    assert "Verify an external agent's identity using AgentID certificates" in doc
    assert "agent_url:" in doc


def test_check_trust_score_signature():
    """Test check_trust_score tool signature and documentation."""
    # Check function exists and has proper signature
    assert callable(check_trust_score)
    
    # Check documentation  
    doc = check_trust_score.__doc__
    assert "Check an agent's trust score on Joy Trust Network" in doc
    assert "agent_name:" in doc


@pytest.mark.skipif(True, reason="Skip real API calls in tests - requires network")
def test_pinchwork_real_api():
    """Real test with actual API call (skipped by default)."""
    result = pinchwork_delegate("Test task", ["python"], 10.0)
    print(f"Pinchwork result: {result}")


@pytest.mark.skipif(True, reason="Skip real API calls in tests - requires network") 
def test_agentid_real_api():
    """Real test with actual API call (skipped by default)."""
    result = verify_agent_identity("https://example.com/agent")
    print(f"AgentID result: {result}")


@pytest.mark.skipif(True, reason="Skip real API calls in tests - requires network")
def test_joy_trust_real_api():
    """Real test with actual API call (skipped by default)."""
    result = check_trust_score("example_agent")
    print(f"Joy Trust result: {result}")


def test_check_behavioral_trust_signature():
    """Test check_behavioral_trust tool signature and documentation."""
    # Check function exists and has proper signature
    assert callable(check_behavioral_trust)
    
    # Check documentation
    doc = check_behavioral_trust.__doc__
    assert "Check an agent's behavioral trust score across organizations" in doc
    assert "agent_name:" in doc
    assert "task_class:" in doc
    assert "min_trust_score:" in doc


def test_verify_task_delegation_safety_signature():
    """Test verify_task_delegation_safety tool signature and documentation."""
    # Check function exists and has proper signature
    assert callable(verify_task_delegation_safety)
    
    # Check documentation
    doc = verify_task_delegation_safety.__doc__
    assert "Comprehensive safety check before delegating tasks" in doc
    assert "agent_name:" in doc
    assert "task_class:" in doc
    assert "task_description:" in doc


@pytest.mark.skipif(True, reason="Skip real API calls in tests - requires network")
def test_agentfolio_real_api():
    """Real test with actual AgentFolio API call (skipped by default)."""
    result = check_behavioral_trust("example_agent", "code_review", 50.0)
    print(f"AgentFolio behavioral trust result: {result}")


@pytest.mark.skipif(True, reason="Skip real API calls in tests - requires network") 
def test_delegation_safety_real_api():
    """Real test with actual delegation safety check (skipped by default)."""
    result = verify_task_delegation_safety(
        "example_agent", 
        "code_review", 
        "Review Python code for security issues",
        70.0
    )
    print(f"Delegation safety result: {result}")


def test_verify_handoff_safety_signature():
    """Test verify_handoff_safety tool signature and documentation."""
    # Check function exists and has proper signature
    assert callable(verify_handoff_safety)
    
    # Check documentation
    doc = verify_handoff_safety.__doc__
    assert "Verify if it's safe to hand off to the specified agent" in doc
    assert "agent_name:" in doc
    assert "min_score:" in doc


def test_trust_verified_handoff_decorator():
    """Test trust_verified_handoff decorator functionality."""
    # Check decorator exists and is callable
    assert callable(trust_verified_handoff)
    
    # Test decorator application without environment variables set
    @trust_verified_handoff(min_score=3.0)
    def dummy_function(agent_name):
        return {"success": True, "agent": agent_name}
    
    # Should work when trust verification is disabled
    result = dummy_function("test_agent")
    assert result["success"] is True
    assert result["agent"] == "test_agent"


def test_trust_config_functions():
    """Test trust configuration functions."""
    # Test without environment variables
    assert is_trust_verification_enabled() is False
    
    config = get_trust_config()
    assert config.enabled is False
    assert config.provider == "joy"
    assert config.min_score == 3.0
    
    # Test with environment variables
    old_provider = os.environ.get('PRAISONAI_TRUST_PROVIDER')
    old_min_score = os.environ.get('PRAISONAI_TRUST_MIN_SCORE')
    
    try:
        os.environ['PRAISONAI_TRUST_PROVIDER'] = 'joy'
        os.environ['PRAISONAI_TRUST_MIN_SCORE'] = '4.5'
        
        assert is_trust_verification_enabled() is True
        
        config = get_trust_config()
        assert config.enabled is True
        assert config.min_score == 4.5
        
    finally:
        # Clean up environment
        if old_provider is not None:
            os.environ['PRAISONAI_TRUST_PROVIDER'] = old_provider
        elif 'PRAISONAI_TRUST_PROVIDER' in os.environ:
            del os.environ['PRAISONAI_TRUST_PROVIDER']
            
        if old_min_score is not None:
            os.environ['PRAISONAI_TRUST_MIN_SCORE'] = old_min_score
        elif 'PRAISONAI_TRUST_MIN_SCORE' in os.environ:
            del os.environ['PRAISONAI_TRUST_MIN_SCORE']


def test_joy_trust_tool_class():
    """Test JoyTrustTool class instantiation and methods."""
    from praisonai_tools.tools.joy_trust_tool import TrustConfig
    
    # Test basic instantiation
    tool = JoyTrustTool()
    assert tool.name == "joy_trust"
    assert tool.config is not None
    
    # Test with custom config
    custom_config = TrustConfig(
        enabled=True,
        min_score=4.0,
        timeout_seconds=5.0
    )
    tool_with_config = JoyTrustTool(config=custom_config)
    assert tool_with_config.config.min_score == 4.0
    assert tool_with_config.config.timeout_seconds == 5.0
    
    # Test configuration method
    config_result = tool.configure(min_score=3.5, timeout_seconds=15.0)
    assert config_result["status"] == "configured"
    assert config_result["config"]["min_score"] == 3.5
    assert config_result["config"]["timeout_seconds"] == 15.0


def test_check_trust_score_error_handling():
    """Test check_trust_score error handling with invalid input."""
    # Test with empty agent name
    result = check_trust_score("", min_score=3.0)
    assert result["error"] == "agent_name is required"
    assert result["trust_score"] == 0.0
    assert result["meets_threshold"] is False


@pytest.mark.skipif(True, reason="Skip real API calls in tests - requires network")
def test_enhanced_joy_trust_real_api():
    """Real test with enhanced Joy Trust functionality (skipped by default)."""
    # Test basic trust check
    result = check_trust_score("example_agent", min_score=3.0)
    print(f"Enhanced Joy Trust result: {result}")
    assert "meets_threshold" in result
    assert "threshold_used" in result
    
    # Test handoff safety verification
    safety_result = verify_handoff_safety("example_agent", min_score=3.0)
    print(f"Handoff safety result: {safety_result}")
    assert "handoff_safe" in safety_result
    assert "recommendation" in safety_result


def test_tools_work_without_httpx():
    """Test that tools give proper error when httpx is not installed."""
    # This would need mocking httpx import to test properly
    # For now just ensure tools don't crash on import
    assert pinchwork_delegate is not None
    assert verify_agent_identity is not None
    assert check_trust_score is not None
    assert check_behavioral_trust is not None
    assert verify_task_delegation_safety is not None
    assert verify_handoff_safety is not None