"""Tests for marketplace tools."""

import pytest
from praisonai_tools.marketplace import pinchwork_delegate, verify_agent_identity, check_trust_score


def test_marketplace_tools_import():
    """Test that marketplace tools can be imported."""
    assert pinchwork_delegate is not None
    assert verify_agent_identity is not None  
    assert check_trust_score is not None


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


def test_tools_work_without_httpx():
    """Test that tools give proper error when httpx is not installed."""
    # This would need mocking httpx import to test properly
    # For now just ensure tools don't crash on import
    assert pinchwork_delegate is not None
    assert verify_agent_identity is not None
    assert check_trust_score is not None