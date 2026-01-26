import pytest
import sys
import os
from pathlib import Path

# Add scripts to path so we can import the generator
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import dummy versions first to avoid import error during TDD setup
try:
    from generate_reference_docs import sanitize_type_for_mdx, escape_mdx
except ImportError:
    def sanitize_type_for_mdx(t): return t
    def escape_mdx(t): return t

def test_sanitize_simple_type():
    assert sanitize_type_for_mdx("str") == "str"
    assert sanitize_type_for_mdx("int") == "int"

def test_sanitize_nested_brackets():
    # Complex type from Agent class
    type_str = "Callable[[TaskOutput], Tuple[bool, Any]]"
    sanitized = sanitize_type_for_mdx(type_str)
    # Goal: Simplify complex types for MDX safety
    assert "Callable" in sanitized
    assert "[[" not in sanitized

def test_sanitize_union_optional():
    assert sanitize_type_for_mdx("Optional[Union[str, int]]") == "Optional"
    assert sanitize_type_for_mdx("Union[str, Any]") == "Union"

def test_escape_angle_brackets():
    doc = "Show <available_skills> for details."
    escaped = escape_mdx(doc)
    # Check if escaped or backticked
    assert "<available_skills>" not in escaped
    assert "&lt;available_skills&gt;" in escaped or "`<available_skills>`" in escaped

def test_escape_curly_braces():
    doc = "Prompt with {input} variable."
    escaped = escape_mdx(doc)
    assert "{input}" not in escaped
    assert "&#123;input&#125;" in escaped or "`{input}`" in escaped

def test_preserve_mintlify_tags():
    doc = "Use <Badge color=\"blue\">Core</Badge>."
    escaped = escape_mdx(doc)
    assert "<Badge color=\"blue\">Core</Badge>" in escaped

def test_preserve_code_blocks():
    # Code blocks handle their own escaping in MDX usually, 
    # but we need to ensure the generator doesn't mess them up
    doc = "```python\nprint('<tag>')\n```"
    escaped = escape_mdx(doc)
    assert "<tag>" in escaped or "&lt;tag&gt;" in escaped
