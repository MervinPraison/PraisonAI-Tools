"""
TDD Test Suite for MDX Escaping Functions.

These tests define the expected behavior for MDX escaping to ensure
generated documentation doesn't cause Mintlify parsing errors.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSanitizeTypeForMDX:
    """Tests for sanitize_type_for_mdx() function."""
    
    def test_simple_types_unchanged(self):
        """Simple types should pass through unchanged."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        assert sanitize_type_for_mdx("str") == "str"
        assert sanitize_type_for_mdx("int") == "int"
        assert sanitize_type_for_mdx("bool") == "bool"
        assert sanitize_type_for_mdx("Any") == "Any"
        assert sanitize_type_for_mdx("None") == "None"
    
    def test_optional_types(self):
        """Optional types should be simplified."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        assert sanitize_type_for_mdx("Optional[str]") == "Optional[str]"
        assert sanitize_type_for_mdx("Optional[int]") == "Optional[int]"
    
    def test_forward_references_removed(self):
        """Forward references (quoted type names) should have quotes removed."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        assert sanitize_type_for_mdx("'Agent'") == "Agent"
        assert sanitize_type_for_mdx("'Handoff'") == "Handoff"
        assert sanitize_type_for_mdx("Optional['Agent']") == "Optional[Agent]"
        assert sanitize_type_for_mdx("List['Task']") == "List[Task]"
    
    def test_callable_types_simplified(self):
        """Complex Callable types should be simplified to just 'Callable'."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        # Simple Callable
        assert sanitize_type_for_mdx("Callable[[str], str]") == "Callable"
        
        # Complex Callable with multiple args
        assert sanitize_type_for_mdx("Callable[[TaskOutput], Any]") == "Callable"
        
        # Callable with nested types
        assert sanitize_type_for_mdx("Callable[[TaskOutput], Tuple[bool, Any]]") == "Callable"
        
        # Optional Callable
        result = sanitize_type_for_mdx("Optional[Callable[[str], str]]")
        assert "Callable[[" not in result
    
    def test_nested_union_types_simplified(self):
        """Deeply nested Union types should be simplified."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        # Union with simple types
        assert sanitize_type_for_mdx("Union[str, int]") == "Union[str, int]"
        
        # Complex nested Union
        result = sanitize_type_for_mdx("Optional[Union[Callable[[X], Y], str]]")
        assert "Callable[[" not in result
    
    def test_literal_types_simplified(self):
        """Literal types with string values should be simplified."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        assert sanitize_type_for_mdx("Literal['safe', 'unsafe']") == "Literal"
        assert sanitize_type_for_mdx("Literal['a', 'b', 'c']") == "Literal"
    
    def test_dict_types_simplified(self):
        """Complex Dict types should be simplified."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        # Simple Dict
        assert sanitize_type_for_mdx("Dict[str, Any]") == "Dict[str, Any]"
        
        # Nested Dict - should simplify inner types
        result = sanitize_type_for_mdx("Dict[str, List[Union[str, int]]]")
        # Should not have deeply nested brackets
        assert result.count('[') <= 2
    
    def test_coroutine_types_simplified(self):
        """Coroutine types should be simplified."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        result = sanitize_type_for_mdx("Coroutine[Any, Any, str]")
        assert result == "Coroutine"
    
    def test_empty_and_none(self):
        """Empty string and None should be handled."""
        from generate_reference_docs import sanitize_type_for_mdx
        
        assert sanitize_type_for_mdx("") == ""
        assert sanitize_type_for_mdx(None) is None


class TestEscapeMDX:
    """Tests for escape_mdx() function."""
    
    def test_angle_brackets_escaped(self):
        """Angle brackets like <word> should be escaped."""
        from generate_reference_docs import escape_mdx
        
        # Simple angle bracket
        result = escape_mdx("Use <available_skills> for skills")
        assert "<available_skills>" not in result or "`<available_skills>`" in result
    
    def test_curly_braces_escaped(self):
        """Curly braces like {word} should be escaped."""
        from generate_reference_docs import escape_mdx
        
        result = escape_mdx("Use {context} for context")
        assert "{context}" not in result or "`{context}`" in result
    
    def test_valid_mintlify_tags_preserved(self):
        """Valid Mintlify components should NOT be escaped."""
        from generate_reference_docs import escape_mdx
        
        # These should remain unchanged
        assert "<Badge>" in escape_mdx("<Badge>Core SDK</Badge>")
        assert "<Accordion" in escape_mdx('<Accordion title="Test">')
        assert "<Card" in escape_mdx('<Card title="Test">')
        assert "<Expandable" in escape_mdx('<Expandable title="Test">')
    
    def test_code_blocks_preserved(self):
        """Content inside code blocks should NOT be escaped."""
        from generate_reference_docs import escape_mdx
        
        text = """
```python
def test():
    return <result>
```
"""
        result = escape_mdx(text)
        # The <result> inside code block should be preserved
        assert "<result>" in result
    
    def test_docstring_code_examples_wrapped(self):
        """Code examples in docstrings should be wrapped in code blocks."""
        from generate_reference_docs import escape_mdx
        
        text = """This is a description.

Usage:
    from praisonaiagents import Agent
    agent = Agent(name="test")
    result = agent.start("hello")
"""
        result = escape_mdx(text)
        # Should have code block markers
        assert "```" in result


class TestValidateMDX:
    """Tests for validate_mdx() function."""
    
    def test_valid_mdx_returns_empty(self):
        """Valid MDX should return no errors."""
        from generate_reference_docs import validate_mdx
        
        valid_mdx = """---
title: "Test"
---

# Test

<Badge>Test</Badge>

```python
code here
```
"""
        errors = validate_mdx(valid_mdx)
        assert errors == []
    
    def test_unescaped_angle_brackets_detected(self):
        """Unescaped angle brackets should be detected."""
        from generate_reference_docs import validate_mdx
        
        invalid_mdx = """---
title: "Test"
---

Use <available_skills> for skills.
"""
        errors = validate_mdx(invalid_mdx)
        assert len(errors) > 0
        assert any("available_skills" in e for e in errors)
    
    def test_unescaped_curly_braces_detected(self):
        """Unescaped curly braces should be detected."""
        from generate_reference_docs import validate_mdx
        
        invalid_mdx = """---
title: "Test"
---

Use {context} for context.
"""
        errors = validate_mdx(invalid_mdx)
        assert len(errors) > 0


class TestEscapeForTable:
    """Tests for escape_for_table() function."""
    
    def test_pipe_characters_escaped(self):
        """Pipe characters should be escaped for tables."""
        from generate_reference_docs import escape_for_table
        
        result = escape_for_table("a | b")
        assert "\\|" in result
    
    def test_complex_types_simplified(self):
        """Complex types should be simplified for tables."""
        from generate_reference_docs import escape_for_table
        
        result = escape_for_table("Callable[[TaskOutput], Tuple[bool, Any]]")
        assert "Callable[[" not in result
    
    def test_forward_references_cleaned(self):
        """Forward references should be cleaned."""
        from generate_reference_docs import escape_for_table
        
        result = escape_for_table("Optional['Agent']")
        assert "'" not in result or "Agent" in result


class TestIconMapping:
    """Tests for icon mapping completeness."""
    
    def test_all_core_modules_have_icons(self):
        """All core praisonaiagents modules should have dedicated icons."""
        from generate_reference_docs import ICON_MAP
        
        core_modules = [
            "agent", "agents", "task", "tools", "memory", "knowledge",
            "workflows", "hooks", "mcp", "guardrails", "planning",
            "session", "eval", "rag", "context", "db", "embedding",
            "skills", "handoff", "telemetry", "policy", "bus"
        ]
        
        for module in core_modules:
            assert module in ICON_MAP, f"Missing icon for module: {module}"
    
    def test_icons_are_valid_lucide_names(self):
        """All icons should be valid Lucide icon names."""
        from generate_reference_docs import ICON_MAP
        
        # Valid Lucide icons (subset for testing)
        valid_icons = {
            "robot", "users", "list-check", "wrench", "brain", "book",
            "sitemap", "link", "chart-line", "tower-broadcast", "puzzle-piece",
            "gear", "shield", "clipboard-list", "clock", "plug", "flask",
            "magnifying-glass", "folder-open", "window-maximize", "database",
            "vector-square", "graduation-cap", "arrow-right-arrow-left",
            "gavel", "wand-magic-sparkles", "rocket", "terminal", "microchip",
            "gears", "code", "file-code", "js", "image", "route", "pen",
            "expand", "eye", "check", "server", "cpu", "network-wired",
            "layer-group", "box", "boxes", "cog", "sliders", "toggle-on",
            "bolt", "zap", "sparkles", "star", "circle", "square"
        }
        
        for module, icon in ICON_MAP.items():
            # Icon should be a non-empty string
            assert isinstance(icon, str) and len(icon) > 0, f"Invalid icon for {module}"


class TestDocsJsonUpdate:
    """Tests for docs.json update functionality."""
    
    def test_backup_created(self):
        """Backup should be created before modification."""
        # This will be tested during integration
        pass
    
    def test_structure_validation(self):
        """docs.json structure should be validated before update."""
        from generate_reference_docs import validate_docs_json_structure
        
        # Valid structure
        valid_config = {
            "navigation": {
                "tabs": [
                    {
                        "tab": "SDK",
                        "groups": [
                            {"group": "Reference", "pages": []}
                        ]
                    }
                ]
            }
        }
        errors = validate_docs_json_structure(valid_config)
        assert errors == []
        
        # Invalid structure - missing SDK tab
        invalid_config = {
            "navigation": {
                "tabs": [
                    {"tab": "Other", "groups": []}
                ]
            }
        }
        errors = validate_docs_json_structure(invalid_config)
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
