"""Unit tests for FCP Doctor."""

import os
from unittest.mock import patch
from praisonai_tools.fcp_tool.doctor import FCPDoctor, CheckResult


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_passed_result(self):
        """Test passed check result."""
        result = CheckResult(name="Test", passed=True, message="OK")
        assert result.passed
        assert result.remediation is None

    def test_failed_result(self):
        """Test failed check result with remediation."""
        result = CheckResult(
            name="Test",
            passed=False,
            message="Failed",
            remediation="Fix it"
        )
        assert not result.passed
        assert result.remediation == "Fix it"


class TestFCPDoctor:
    """Tests for FCPDoctor class."""

    def test_check_macos_on_darwin(self):
        """Test macOS check on Darwin."""
        doctor = FCPDoctor()
        with patch('platform.system', return_value='Darwin'):
            with patch('platform.mac_ver', return_value=('14.0', ('', '', ''), '')):
                result = doctor.check_macos()
                assert result.passed
                assert "14.0" in result.message

    def test_check_macos_on_linux(self):
        """Test macOS check on Linux."""
        doctor = FCPDoctor()
        with patch('platform.system', return_value='Linux'):
            result = doctor.check_macos()
            assert not result.passed
            assert result.remediation is not None

    def test_check_openai_api_key_set(self):
        """Test OpenAI API key check when set."""
        doctor = FCPDoctor()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test1234'}):
            result = doctor.check_openai_api_key()
            assert result.passed
            assert "1234" in result.message  # Last 4 chars

    def test_check_openai_api_key_not_set(self):
        """Test OpenAI API key check when not set."""
        doctor = FCPDoctor()
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY if it exists
            env = os.environ.copy()
            env.pop('OPENAI_API_KEY', None)
            with patch.dict(os.environ, env, clear=True):
                result = doctor.check_openai_api_key()
                assert not result.passed
                assert result.remediation is not None

    def test_run_all_checks(self):
        """Test running all checks."""
        doctor = FCPDoctor()
        results = doctor.run_all_checks()
        assert len(results) == 7  # 7 checks total
        assert all(isinstance(r, CheckResult) for r in results)

    def test_get_summary(self):
        """Test getting summary."""
        doctor = FCPDoctor()
        results = [
            CheckResult(name="Test1", passed=True, message="OK"),
            CheckResult(name="Test2", passed=False, message="Failed"),
        ]
        summary = doctor.get_summary(results)

        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert not summary["all_passed"]
        assert len(summary["checks"]) == 2
