import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_reference_docs import sanitize_type_for_mdx, escape_mdx

def run_test(name, func):
    try:
        func()
        print(f"PASS: {name}")
        return True
    except Exception as e:
        print(f"FAIL: {name} - {e}")
        return False

def test_sanitize_simple_type():
    assert sanitize_type_for_mdx("str") == "str"
    assert sanitize_type_for_mdx("int") == "int"

def test_sanitize_nested_brackets():
    type_str = "Callable[[TaskOutput], Tuple[bool, Any]]"
    sanitized = sanitize_type_for_mdx(type_str)
    assert "Callable" in sanitized
    assert "[[" not in sanitized

def test_sanitize_union_optional():
    assert sanitize_type_for_mdx("Optional[Union[str, int]]") == "Optional"
    assert sanitize_type_for_mdx("Union[str, Any]") == "Union"

def test_escape_angle_brackets():
    doc = "Show <available_skills> for details."
    escaped = escape_mdx(doc)
    assert "<available_skills>" not in escaped
    assert "&lt;available_skills&gt;" in escaped

def test_escape_curly_braces():
    doc = "Prompt with {input} variable."
    escaped = escape_mdx(doc)
    assert "{input}" not in escaped
    assert "&#123;input&#125;" in escaped

def test_preserve_mintlify_tags():
    doc = "Use <Badge color=\"blue\">Core</Badge>."
    escaped = escape_mdx(doc)
    assert "<Badge color=\"blue\">Core</Badge>" in escaped

def test_preserve_code_blocks():
    doc = "```python\nprint('<tag>')\n```"
    escaped = escape_mdx(doc)
    assert "<tag>" in escaped

if __name__ == "__main__":
    tests = [
        ("Simple Type", test_sanitize_simple_type),
        ("Nested Brackets", test_sanitize_nested_brackets),
        ("Union/Optional", test_sanitize_union_optional),
        ("Angle Brackets", test_escape_angle_brackets),
        ("Curly Braces", test_escape_curly_braces),
        ("Mintlify Tags", test_preserve_mintlify_tags),
        ("Code Blocks", test_preserve_code_blocks),
    ]
    
    passed = 0
    for name, test in tests:
        if run_test(name, test):
            passed += 1
            
    print(f"\nResult: {passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
