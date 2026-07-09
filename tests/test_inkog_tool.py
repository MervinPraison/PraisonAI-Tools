"""Tests for Inkog Security Analysis Tool."""

from unittest.mock import patch, MagicMock
from praisonai_tools.tools.inkog_tool import InkogTool, _check_inkog_available, scan_agent_code


class TestInkogTool:
    """Test suite for InkogTool."""
    
    def test_init(self):
        """Test InkogTool initialization."""
        # Test default initialization
        tool = InkogTool()
        assert tool.name == "inkog_security"
        assert "security" in tool.description.lower()
        
        # Test with custom parameters
        tool = InkogTool(api_key="test_key", server_url="http://test.com")
        assert tool._api_key == "test_key"
        assert tool._server_url == "http://test.com"
    
    @patch.dict("os.environ", {"INKOG_API_KEY": "test_env_key"})
    def test_get_api_key(self):
        """Test API key retrieval."""
        tool = InkogTool()
        assert tool._get_api_key() == "test_env_key"
        
        # Instance key takes precedence
        tool = InkogTool(api_key="instance_key")
        assert tool._get_api_key() == "instance_key"
    
    @patch.dict("os.environ", {"INKOG_SERVER_URL": "http://env.com"})
    def test_get_server_url(self):
        """Test server URL retrieval."""
        tool = InkogTool()
        assert tool._get_server_url() == "http://env.com"
        
        # Instance URL takes precedence
        tool = InkogTool(server_url="http://instance.com")
        assert tool._get_server_url() == "http://instance.com"
    
    def test_analyze_findings_empty(self):
        """Test analyze_findings with empty results."""
        tool = InkogTool()
        
        # Test with error
        error_results = {"error": "test error"}
        analysis = tool.analyze_findings(error_results)
        assert "Scan failed" in analysis
        assert "test error" in analysis
        
        # Test with no findings
        empty_results = {"summary": {"total_findings": 0}}
        analysis = tool.analyze_findings(empty_results)
        assert "No security vulnerabilities found" in analysis
    
    def test_analyze_findings_with_data(self):
        """Test analyze_findings with security findings."""
        tool = InkogTool()
        
        results = {
            "summary": {
                "total_findings": 5,
                "critical": 2,
                "high": 2,
                "medium": 1,
                "low": 0
            },
            "server_findings": [
                {"pattern": "Token Bombing"},
                {"pattern": "Prompt Injection"},
                {"pattern": "Recursive Tool Calling"}
            ]
        }
        
        analysis = tool.analyze_findings(results)
        assert "Total Findings: 5" in analysis
        assert "CRITICAL: 2 findings" in analysis
        assert "HIGH: 2 findings" in analysis
        assert "MEDIUM: 1 findings" in analysis
        assert "Token Bombing" in analysis
        assert "Immediate attention required" in analysis
    
    def test_analyze_findings_string_input(self):
        """String (text/HTML) scan output is returned as-is, even when it
        contains the word 'error' (regression: no TypeError)."""
        tool = InkogTool()
        
        text_output = "Finding: potential error in tool loop termination."
        analysis = tool.analyze_findings(text_output)
        assert analysis == text_output


class TestInkogAvailability:
    """Test inkog availability checking."""
    
    @patch("subprocess.run")
    def test_check_inkog_available_success(self, mock_run):
        """Test successful inkog availability check."""
        # Mock successful version check
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict("os.environ", {"INKOG_API_KEY": "test_key"}):
            is_available, error = _check_inkog_available()
            assert is_available is True
            assert error is None
    
    @patch("subprocess.run")
    def test_check_inkog_not_installed(self, mock_run):
        """Test inkog not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        is_available, error = _check_inkog_available()
        assert is_available is False
        assert "not installed" in error.lower()
    
    @patch("subprocess.run")
    def test_check_inkog_no_api_key(self, mock_run):
        """Test inkog available but no API key."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict("os.environ", {}, clear=True):
            is_available, error = _check_inkog_available()
            assert is_available is False
            assert "INKOG_API_KEY" in error
    
    @patch("subprocess.run")
    def test_check_inkog_available_with_instance_api_key(self, mock_run):
        """Instance-provided api_key satisfies the availability check."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict("os.environ", {}, clear=True):
            is_available, error = _check_inkog_available(api_key="instance_key")
            assert is_available is True
            assert error is None


class TestInkogScanOperations:
    """Test inkog scan operations."""
    
    @patch("praisonai_tools.tools.inkog_tool._check_inkog_available")
    @patch("subprocess.run")
    @patch.dict("os.environ", {"INKOG_API_KEY": "test_key"})
    def test_scan_directory_json_success(self, mock_run, mock_check):
        """Test successful directory scan with JSON output."""
        mock_check.return_value = (True, None)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"summary": {"total_findings": 0}}'
        )
        
        tool = InkogTool()
        result = tool.scan_directory(path="./test", output_format="json")
        
        assert isinstance(result, dict)
        assert "summary" in result
        assert result["summary"]["total_findings"] == 0
    
    @patch("praisonai_tools.tools.inkog_tool._check_inkog_available")
    @patch("subprocess.run")
    @patch.dict("os.environ", {"INKOG_API_KEY": "test_key"})
    def test_scan_directory_text_success(self, mock_run, mock_check):
        """Test successful directory scan with text output."""
        mock_check.return_value = (True, None)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No vulnerabilities found."
        )
        
        tool = InkogTool()
        result = tool.scan_directory(path="./test", output_format="text")
        
        assert isinstance(result, str)
        assert "vulnerabilities" in result.lower()
    
    @patch("praisonai_tools.tools.inkog_tool._check_inkog_available")
    def test_scan_directory_not_available(self, mock_check):
        """Test scan when inkog is not available."""
        mock_check.return_value = (False, "inkog not installed")
        
        tool = InkogTool()
        result = tool.scan_directory()
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "not installed" in result["error"]
    
    @patch("praisonai_tools.tools.inkog_tool._check_inkog_available")
    @patch("subprocess.run")
    def test_scan_directory_command_failure(self, mock_run, mock_check):
        """Test scan when inkog command fails."""
        mock_check.return_value = (True, None)
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Command failed",
            stdout=""
        )
        
        tool = InkogTool()
        result = tool.scan_directory()
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "failed" in result["error"].lower()
    
    @patch("praisonai_tools.tools.inkog_tool._check_inkog_available") 
    @patch("subprocess.run")
    @patch.dict("os.environ", {"INKOG_API_KEY": "test_key"})
    def test_skill_scan_success(self, mock_run, mock_check):
        """Test successful skill package scan."""
        mock_check.return_value = (True, None)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"scan_type": "skill", "findings": []}'
        )
        
        tool = InkogTool()
        result = tool.skill_scan(path="./skill", deep=True)
        
        assert isinstance(result, dict)
        assert "scan_type" in result or "findings" in result
    
    @patch("praisonai_tools.tools.inkog_tool._check_inkog_available")
    @patch("subprocess.run") 
    @patch.dict("os.environ", {"INKOG_API_KEY": "test_key"})
    def test_mcp_scan_success(self, mock_run, mock_check):
        """Test successful MCP server scan."""
        mock_check.return_value = (True, None)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"mcp_server": "github", "vulnerabilities": []}'
        )
        
        tool = InkogTool()
        result = tool.mcp_scan("github", deep=True)
        
        assert isinstance(result, dict)
        # Should have some scan results structure
        
    def test_run_method_routing(self):
        """Test the run method routes to correct functions."""
        tool = InkogTool()
        
        with patch.object(tool, 'scan_directory') as mock_scan:
            mock_scan.return_value = {"test": "result"}
            tool.run(action="scan", path="./test")
            mock_scan.assert_called_once_with(
                path="./test",
                output_format="json", 
                policy="balanced",
                severity="low",
                deep=False
            )
        
        with patch.object(tool, 'skill_scan') as mock_skill:
            mock_skill.return_value = {"test": "result"}
            tool.run(action="skill-scan", path="./test")
            mock_skill.assert_called_once_with(
                path="./test",
                output_format="json",
                deep=False,
                repo=None
            )


class TestStandaloneFunctions:
    """Test standalone function interfaces."""
    
    @patch("praisonai_tools.tools.inkog_tool.InkogTool")
    def test_scan_agent_code(self, mock_tool_class):
        """Test scan_agent_code standalone function."""
        mock_tool = MagicMock()
        mock_tool.scan_directory.return_value = {"result": "test"}
        mock_tool_class.return_value = mock_tool
        
        scan_agent_code("./test", deep=True)
        
        mock_tool_class.assert_called_once()
        mock_tool.scan_directory.assert_called_once_with(
            path="./test",
            output_format="json",
            policy="balanced",
            severity="low",
            deep=True
        )


if __name__ == "__main__":
    # Run basic smoke test
    print("Running Inkog Tool smoke tests...")
    
    # Test basic initialization
    tool = InkogTool()
    print(f"✓ Tool name: {tool.name}")
    print(f"✓ Tool description contains 'security': {'security' in tool.description.lower()}")
    
    # Test availability check (will likely fail without actual installation)
    is_available, error = _check_inkog_available()
    if is_available:
        print("✓ Inkog is available and configured")
    else:
        print(f"⚠ Inkog not available: {error}")
        print("This is expected if inkog CLI is not installed")
    
    print("Smoke tests completed!")