"""Tests for base tool classes."""

import pytest
from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError, validate_tool
from praisonai_tools.tools.decorator import tool, FunctionTool, is_tool, get_tool_schema


class TestToolResult:
    """Tests for ToolResult class."""
    
    def test_successful_result(self):
        """Test creating a successful result."""
        result = ToolResult(output="test output", success=True)
        assert result.success is True
        assert result.output == "test output"
        assert result.error is None
        assert str(result) == "test output"
    
    def test_failed_result(self):
        """Test creating a failed result."""
        result = ToolResult(output=None, success=False, error="Something went wrong")
        assert result.success is False
        assert result.output is None
        assert result.error == "Something went wrong"
        assert "Error:" in str(result)
    
    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = ToolResult(
            output="data",
            success=True,
            metadata={"duration": 1.5, "source": "test"}
        )
        assert result.metadata["duration"] == 1.5
        assert result.metadata["source"] == "test"
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = ToolResult(output="test", success=True, metadata={"key": "value"})
        d = result.to_dict()
        assert d["output"] == "test"
        assert d["success"] is True
        assert d["metadata"]["key"] == "value"


class TestBaseTool:
    """Tests for BaseTool class."""
    
    def test_concrete_tool_creation(self):
        """Test creating a concrete tool."""
        class MyTool(BaseTool):
            name = "my_tool"
            description = "A test tool"
            
            def run(self, query: str) -> str:
                return f"Result: {query}"
        
        tool = MyTool()
        assert tool.name == "my_tool"
        assert tool.description == "A test tool"
        assert tool.version == "1.0.0"
    
    def test_tool_execution(self):
        """Test executing a tool."""
        class EchoTool(BaseTool):
            name = "echo"
            description = "Echoes input"
            
            def run(self, message: str) -> str:
                return message
        
        tool = EchoTool()
        result = tool.run(message="Hello")
        assert result == "Hello"
        
        # Test callable
        result = tool(message="World")
        assert result == "World"
    
    def test_safe_run_success(self):
        """Test safe_run with successful execution."""
        class SafeTool(BaseTool):
            name = "safe"
            description = "Safe tool"
            
            def run(self, x: int) -> int:
                return x * 2
        
        tool = SafeTool()
        result = tool.safe_run(x=5)
        assert result.success is True
        assert result.output == 10
    
    def test_safe_run_failure(self):
        """Test safe_run with failed execution."""
        class FailingTool(BaseTool):
            name = "failing"
            description = "Failing tool"
            
            def run(self, x: int) -> int:
                raise ValueError("Intentional error")
        
        tool = FailingTool()
        result = tool.safe_run(x=5)
        assert result.success is False
        assert "Intentional error" in result.error
    
    def test_get_schema(self):
        """Test getting OpenAI-compatible schema."""
        class SchemaTool(BaseTool):
            name = "schema_tool"
            description = "Tool with schema"
            
            def run(self, query: str, limit: int = 10) -> dict:
                return {}
        
        tool = SchemaTool()
        schema = tool.get_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "schema_tool"
        assert schema["function"]["description"] == "Tool with schema"
        assert "query" in schema["function"]["parameters"]["properties"]
    
    def test_auto_name_from_class(self):
        """Test automatic name generation from class name."""
        class AutoNameTool(BaseTool):
            description = "Auto named"
            
            def run(self) -> str:
                return "ok"
        
        tool = AutoNameTool()
        assert tool.name == "autoname"
    
    def test_validation(self):
        """Test tool validation."""
        class ValidTool(BaseTool):
            name = "valid"
            description = "Valid tool"
            
            def run(self) -> str:
                return "ok"
        
        tool = ValidTool()
        assert tool.validate() is True


class TestToolDecorator:
    """Tests for @tool decorator."""
    
    def test_simple_decorator(self):
        """Test simple @tool decorator."""
        @tool
        def greet(name: str) -> str:
            """Greet someone."""
            return f"Hello, {name}!"
        
        assert isinstance(greet, FunctionTool)
        assert greet.name == "greet"
        assert "Greet someone" in greet.description
        
        result = greet(name="World")
        assert result == "Hello, World!"
    
    def test_decorator_with_args(self):
        """Test @tool decorator with arguments."""
        @tool(name="custom_greet", description="Custom greeting")
        def greet(name: str) -> str:
            return f"Hi, {name}!"
        
        assert greet.name == "custom_greet"
        assert greet.description == "Custom greeting"
    
    def test_decorator_preserves_signature(self):
        """Test that decorator preserves function signature."""
        @tool
        def add(a: int, b: int = 0) -> int:
            """Add two numbers."""
            return a + b
        
        schema = add.get_schema()
        params = schema["function"]["parameters"]
        
        assert "a" in params["properties"]
        assert "b" in params["properties"]
        assert "a" in params["required"]
        assert "b" not in params["required"]  # Has default value
    
    def test_is_tool(self):
        """Test is_tool function."""
        @tool
        def my_tool() -> str:
            """A tool."""
            return "ok"
        
        assert is_tool(my_tool) is True
        assert is_tool(lambda: None) is False
    
    def test_get_tool_schema(self):
        """Test get_tool_schema function."""
        @tool
        def search(query: str) -> list:
            """Search for something."""
            return []
        
        schema = get_tool_schema(search)
        assert schema is not None
        assert schema["function"]["name"] == "search"


class TestValidateTool:
    """Tests for validate_tool function."""
    
    def test_validate_base_tool(self):
        """Test validating a BaseTool instance."""
        class ValidTool(BaseTool):
            name = "valid"
            description = "Valid"
            
            def run(self) -> str:
                return "ok"
        
        tool = ValidTool()
        assert validate_tool(tool) is True
    
    def test_validate_callable(self):
        """Test validating a callable."""
        def my_func():
            pass
        
        assert validate_tool(my_func) is True
    
    def test_validate_invalid(self):
        """Test validating an invalid object."""
        with pytest.raises(ToolValidationError):
            validate_tool("not a tool")
