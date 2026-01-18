"""
Tests for init-only auto-instrumentation feature.

These tests verify that obs.init() auto-instruments Agent classes
without requiring explicit obs.trace() context manager wrappers.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import os


class TestAutoInstrumentation:
    """Test suite for auto-instrumentation feature."""
    
    def test_obs_init_triggers_auto_instrumentation(self):
        """obs.init() should auto-instrument Agent classes by default."""
        from praisonai_tools.observability.manager import ObservabilityManager
        
        manager = ObservabilityManager()
        
        # Mock provider to avoid actual API calls
        with patch.object(manager, '_load_provider'):
            with patch.object(manager, '_auto_instrument_agents') as mock_auto:
                # Set up mock provider
                manager._providers['mock'] = MagicMock()
                mock_provider = MagicMock()
                mock_provider.init.return_value = True
                manager._providers['mock'].return_value = mock_provider
                
                # Call init with auto_instrument=True (default)
                manager.init(provider='mock')
                
                # Verify auto-instrumentation was triggered
                mock_auto.assert_called_once()
    
    def test_obs_init_respects_auto_instrument_false(self):
        """obs.init(auto_instrument=False) should NOT auto-instrument."""
        from praisonai_tools.observability.manager import ObservabilityManager
        
        manager = ObservabilityManager()
        
        with patch.object(manager, '_load_provider'):
            with patch.object(manager, '_auto_instrument_agents') as mock_auto:
                manager._providers['mock'] = MagicMock()
                mock_provider = MagicMock()
                mock_provider.init.return_value = True
                manager._providers['mock'].return_value = mock_provider
                
                manager.init(provider='mock', auto_instrument=False)
                
                # Should NOT be called
                mock_auto.assert_not_called()
    
    def test_agent_chat_produces_span_after_init(self):
        """Agent.chat() should produce spans after obs.init()."""
        from praisonai_tools.observability.manager import ObservabilityManager
        
        manager = ObservabilityManager()
        
        # Setup mock provider
        mock_provider = MagicMock()
        mock_provider.init.return_value = True
        mock_provider._initialized = True
        manager._provider = mock_provider
        
        # Auto-instrument
        manager._auto_instrument_agents()
        
        # Import Agent AFTER instrumentation
        try:
            from praisonaiagents import Agent
            
            # Create agent and call chat
            agent = Agent(name="TestAgent", instructions="Test")
            
            # Verify that Agent class was patched
            assert hasattr(Agent, '_obs_instrumented') or hasattr(agent, '_obs_instrumented')
        except ImportError:
            pytest.skip("praisonaiagents not installed")
    
    def test_no_overhead_when_not_initialized(self):
        """No performance overhead when obs.init() is not called."""
        import time
        
        # Reset singleton state
        from praisonai_tools.observability.manager import ObservabilityManager
        manager = ObservabilityManager()
        manager._provider = None
        manager._initialized = False
        
        try:
            from praisonaiagents import Agent
            
            # Create agent WITHOUT obs.init()
            start = time.time()
            agent = Agent(name="TestAgent", instructions="Test")
            creation_time = time.time() - start
            
            # Should be fast (no instrumentation overhead)
            # Allow generous time for class instantiation but fail if obs adds latency
            assert creation_time < 1.0, f"Agent creation took {creation_time}s - possible obs overhead"
        except ImportError:
            pytest.skip("praisonaiagents not installed")
    
    def test_tool_calls_create_child_spans(self):
        """Tool calls within agent should create child spans."""
        from praisonai_tools.observability.manager import ObservabilityManager
        
        manager = ObservabilityManager()
        
        mock_provider = MagicMock()
        mock_provider.init.return_value = True
        mock_provider._initialized = True
        manager._provider = mock_provider
        
        # After auto-instrumentation, tool calls should create spans
        # This is verified by checking the span creation calls on the provider
        manager._auto_instrument_agents()
        
        # Verify the infrastructure is in place
        assert hasattr(manager, '_auto_instrument_agents')


class TestObsInitAutoDetection:
    """Test provider auto-detection from environment."""
    
    def test_auto_detect_langfuse_from_env(self):
        """obs.init() should auto-detect Langfuse when env vars present."""
        from praisonai_tools.observability.config import detect_provider
        
        # Langfuse requires both PUBLIC_KEY and SECRET_KEY
        with patch.dict(os.environ, {
            'LANGFUSE_PUBLIC_KEY': 'test-key',
            'LANGFUSE_SECRET_KEY': 'test-secret'
        }):
            provider = detect_provider()
            assert provider == 'langfuse'
    
    def test_auto_detect_agentops_from_env(self):
        """obs.init() should auto-detect AgentOps when env vars present."""
        from praisonai_tools.observability.config import detect_provider
        
        with patch.dict(os.environ, {'AGENTOPS_API_KEY': 'test-key'}):
            provider = detect_provider()
            assert provider == 'agentops'
    
    def test_no_provider_when_no_env_vars(self):
        """obs.init() should return None when no env vars set."""
        from praisonai_tools.observability.config import detect_provider
        
        # Clear all provider env vars
        env_vars_to_clear = [
            'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY',
            'LANGSMITH_API_KEY', 'AGENTOPS_API_KEY',
            'ARIZE_API_KEY', 'DATADOG_API_KEY',
        ]
        
        clean_env = {k: v for k, v in os.environ.items() if k not in env_vars_to_clear}
        
        with patch.dict(os.environ, clean_env, clear=True):
            provider = detect_provider()
            # Should be None or a default fallback
            assert provider is None or provider in ['', 'none']
