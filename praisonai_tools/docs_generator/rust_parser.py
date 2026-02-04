"""
Rust Documentation Parser for PraisonAI.

Parses Rust source code to extract documentation for MDX generation.
Uses tree-sitter for robust Rust syntax parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import shared data classes from generator
try:
    from .generator import (
        ParamInfo,
        MethodInfo,
        ClassInfo,
        FunctionInfo,
        ModuleInfo,
        SKIP_MODULES,
        SKIP_METHODS,
    )
except ImportError:
    # Define minimal fallback classes when run standalone
    from dataclasses import dataclass, field
    from typing import List, Optional, Tuple
    
    @dataclass
    class ParamInfo:
        name: str
        type: str = ""
        default: Optional[str] = None
        description: str = ""
        required: bool = True
    
    @dataclass
    class MethodInfo:
        name: str
        signature: str = ""
        return_type: str = ""
        docstring: str = ""
        params: List[ParamInfo] = field(default_factory=list)
        is_async: bool = False
        is_static: bool = False
        examples: List[str] = field(default_factory=list)
    
    @dataclass
    class ClassInfo:
        name: str
        docstring: str = ""
        bases: List[str] = field(default_factory=list)
        methods: List[MethodInfo] = field(default_factory=list)
        static_methods: List[MethodInfo] = field(default_factory=list)
        properties: List[ParamInfo] = field(default_factory=list)
        init_params: List[ParamInfo] = field(default_factory=list)
        examples: List[str] = field(default_factory=list)
    
    @dataclass
    class FunctionInfo:
        name: str
        signature: str = ""
        return_type: str = ""
        docstring: str = ""
        params: List[ParamInfo] = field(default_factory=list)
        is_async: bool = False
        examples: List[str] = field(default_factory=list)
    
    @dataclass 
    class ModuleInfo:
        name: str
        short_name: str = ""
        display_name: str = ""
        docstring: str = ""
        is_init: bool = False
        package: str = ""
        classes: List[ClassInfo] = field(default_factory=list)
        functions: List[FunctionInfo] = field(default_factory=list)
        constants: List[Tuple[str, str]] = field(default_factory=list)
    
    SKIP_MODULES = {"tests", "__pycache__", "conftest"}
    SKIP_METHODS = {"__init__", "__repr__", "__str__"}

# Try to import tree-sitter, provide fallback
try:
    import tree_sitter_rust as ts_rust
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


# =============================================================================
# RUST-SPECIFIC DATA CLASSES
# =============================================================================

@dataclass
class TraitInfo:
    """Information about a Rust trait."""
    name: str
    docstring: str = ""
    methods: List[MethodInfo] = field(default_factory=list)
    supertraits: List[str] = field(default_factory=list)


@dataclass
class EnumInfo:
    """Information about a Rust enum."""
    name: str
    docstring: str = ""
    variants: List[Tuple[str, str]] = field(default_factory=list)  # (name, docstring)


@dataclass
class MacroInfo:
    """Information about a Rust macro."""
    name: str
    docstring: str = ""
    attributes: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


# =============================================================================
# RUST DOC PARSER (REGEX-BASED FALLBACK)
# =============================================================================

class RustDocParser:
    """Parse Rust source code for documentation.
    
    This parser extracts documentation from Rust source files using regex patterns.
    It handles:
    - Module doc comments (//!)
    - Item doc comments (///)
    - Structs, traits, enums, and functions
    - Impl blocks and methods
    - Proc-macro definitions
    """
    
    # Skip these module names
    SKIP_MODULES = {"target", "tests", "examples", "benches", ".git"}
    
    def __init__(self, crate_path: Path, crate_name: str = "praisonai"):
        """Initialize the parser.
        
        Args:
            crate_path: Path to the crate root (containing Cargo.toml)
            crate_name: Name of the crate for module prefixes
        """
        self.crate_path = crate_path
        self.crate_name = crate_name
        self.src_path = crate_path / "src"
        
        # Cache for parsed files
        self._file_cache: Dict[Path, str] = {}
    
    def get_modules(self) -> List[str]:
        """Get list of modules to document.
        
        Returns:
            List of module paths (e.g., ['praisonai.agent', 'praisonai.tools'])
        """
        modules = set()
        
        if not self.src_path.exists():
            return []
        
        # Find all .rs files
        for rs_file in self.src_path.rglob("*.rs"):
            # Skip test files
            if "tests" in rs_file.parts or "test_" in rs_file.name:
                continue
            
            # Convert file path to module path
            rel_path = rs_file.relative_to(self.src_path)
            parts = list(rel_path.parts)
            
            # Handle mod.rs and lib.rs
            if parts[-1] == "mod.rs":
                parts = parts[:-1]
            elif parts[-1] == "lib.rs":
                parts = []  # lib.rs is the crate root
            else:
                parts[-1] = parts[-1].replace(".rs", "")
            
            if parts:
                module_name = f"{self.crate_name}.{'.'.join(parts)}"
            else:
                module_name = self.crate_name
            
            modules.add(module_name)
        
        return sorted(modules)
    
    def parse_module(self, module_path: str) -> Optional[ModuleInfo]:
        """Parse a module and extract documentation.
        
        Args:
            module_path: Fully qualified module path (e.g., 'praisonai.agent')
            
        Returns:
            ModuleInfo or None if module not found
        """
        # Convert module path to file path
        file_path = self._module_to_file(module_path)
        if not file_path or not file_path.exists():
            return None
        
        try:
            content = self._read_file(file_path)
            
            # Extract module-level doc comments
            module_doc = self._extract_module_docs(content)
            
            # Get module short name
            parts = module_path.split(".")
            short_name = parts[-1] if len(parts) > 1 else module_path
            
            info = ModuleInfo(
                name=module_path,
                short_name=short_name,
                docstring=module_doc,
                is_init=file_path.name in ("lib.rs", "mod.rs"),
                package="rust",
            )
            
            # Parse structs as classes
            info.classes = self._parse_structs(content)
            
            # Parse traits (also as classes with special handling)
            traits = self._parse_traits(content)
            for trait in traits:
                info.classes.append(ClassInfo(
                    name=trait.name,
                    docstring=trait.docstring,
                    bases=trait.supertraits,
                    methods=trait.methods,
                ))
            
            # Parse enums
            enums = self._parse_enums(content)
            for enum in enums:
                info.classes.append(ClassInfo(
                    name=enum.name,
                    docstring=enum.docstring,
                    properties=[
                        ParamInfo(name=v[0], description=v[1], type="variant")
                        for v in enum.variants
                    ],
                ))
            
            # Parse standalone functions
            info.functions = self._parse_functions(content)
            
            # Parse impl blocks and attach methods to structs
            self._parse_impl_blocks(content, info)
            
            return info
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _module_to_file(self, module_path: str) -> Optional[Path]:
        """Convert module path to file path."""
        parts = module_path.split(".")
        
        # Remove crate name prefix
        if parts[0] == self.crate_name:
            parts = parts[1:]
        
        if not parts:
            # Crate root - try lib.rs
            lib_rs = self.src_path / "lib.rs"
            if lib_rs.exists():
                return lib_rs
            return None
        
        # Try mod.rs first
        mod_path = self.src_path / "/".join(parts) / "mod.rs"
        if mod_path.exists():
            return mod_path
        
        # Try direct file
        file_path = self.src_path / "/".join(parts[:-1]) / f"{parts[-1]}.rs"
        if file_path.exists():
            return file_path
        
        # Try as single file in src/
        single_file = self.src_path / f"{parts[-1]}.rs"
        if single_file.exists():
            return single_file
        
        return None
    
    def _read_file(self, path: Path) -> str:
        """Read file with caching."""
        if path not in self._file_cache:
            self._file_cache[path] = path.read_text(encoding="utf-8")
        return self._file_cache[path]
    
    def _extract_module_docs(self, content: str) -> str:
        """Extract module-level doc comments (//!)."""
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//!"):
                # Remove //! prefix
                doc_line = stripped[3:].strip()
                lines.append(doc_line)
            elif stripped.startswith("//") or stripped.startswith("#"):
                continue  # Skip other comments and attributes
            elif stripped:
                break  # Stop at first non-comment/non-attribute line
        
        return "\n".join(lines)
    
    def _extract_doc_comments(self, content: str, start_pos: int) -> str:
        """Extract doc comments (///) before an item.
        
        Args:
            content: Full file content
            start_pos: Position where the item definition starts
            
        Returns:
            Extracted documentation string
        """
        # Find the start of line containing start_pos
        line_start = content.rfind("\n", 0, start_pos) + 1
        
        # Work backwards to find doc comments
        lines = []
        pos = line_start - 1
        
        while pos > 0:
            # Find previous line
            prev_line_end = pos
            prev_line_start = content.rfind("\n", 0, prev_line_end) + 1
            line = content[prev_line_start:prev_line_end].strip()
            
            if line.startswith("///"):
                lines.insert(0, line[3:].strip())
                pos = prev_line_start - 1
            elif line.startswith("#["):
                # Skip attributes
                pos = prev_line_start - 1
            elif not line:
                # Skip empty lines
                pos = prev_line_start - 1
            else:
                break
        
        return "\n".join(lines)
    
    def _parse_structs(self, content: str) -> List[ClassInfo]:
        """Parse struct definitions."""
        structs = []
        
        # Match: pub struct Name { ... } or pub struct Name;
        pattern = r'pub\s+struct\s+(\w+)(?:<[^>]*>)?\s*(?:\{([^}]*)\}|;)'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            name = match.group(1)
            fields_str = match.group(2) or ""
            
            # Extract doc comments
            doc = self._extract_doc_comments(content, match.start())
            
            # Parse fields
            properties = []
            if fields_str:
                field_pattern = r'(?:pub\s+)?(\w+):\s*([^,\n]+)'
                for field_match in re.finditer(field_pattern, fields_str):
                    field_name = field_match.group(1)
                    field_type = field_match.group(2).strip().rstrip(",")
                    
                    # Extract field doc comment
                    field_doc = self._extract_doc_comments(fields_str, field_match.start())
                    
                    properties.append(ParamInfo(
                        name=field_name,
                        type=field_type,
                        description=field_doc,
                    ))
            
            # Parse examples from docstring
            examples = self._extract_examples(doc)
            
            structs.append(ClassInfo(
                name=name,
                docstring=self._clean_docstring(doc),
                properties=properties,
                examples=examples,
            ))
        
        return structs
    
    def _parse_traits(self, content: str) -> List[TraitInfo]:
        """Parse trait definitions."""
        traits = []
        
        # Match: pub trait Name { ... }
        pattern = r'pub\s+trait\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+))?\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            name = match.group(1)
            supertraits_str = match.group(2) or ""
            body = match.group(3)
            
            # Extract doc comments
            doc = self._extract_doc_comments(content, match.start())
            
            # Parse supertraits
            supertraits = []
            if supertraits_str:
                supertraits = [s.strip() for s in supertraits_str.split("+")]
            
            # Parse required methods
            methods = self._parse_trait_methods(body)
            
            traits.append(TraitInfo(
                name=name,
                docstring=self._clean_docstring(doc),
                methods=methods,
                supertraits=supertraits,
            ))
        
        return traits
    
    def _parse_trait_methods(self, body: str) -> List[MethodInfo]:
        """Parse methods from a trait body."""
        methods = []
        
        # Match method signatures: fn name(...) -> Type;
        pattern = r'fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^;{]+))?[;{]'
        
        for match in re.finditer(pattern, body):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3) or "()".strip() if match.group(3) else "()"
            
            # Extract doc comment
            doc = self._extract_doc_comments(body, match.start())
            
            # Parse parameters
            params = self._parse_params(params_str)
            
            methods.append(MethodInfo(
                name=name,
                signature=params_str,
                return_type=return_type.strip(),
                docstring=self._clean_docstring(doc),
                params=params,
                is_async="async" in body[max(0, match.start()-10):match.start()],
            ))
        
        return methods
    
    def _parse_enums(self, content: str) -> List[EnumInfo]:
        """Parse enum definitions."""
        enums = []
        
        # Match: pub enum Name { ... }
        pattern = r'pub\s+enum\s+(\w+)(?:<[^>]*>)?\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            name = match.group(1)
            body = match.group(2)
            
            # Extract doc comments
            doc = self._extract_doc_comments(content, match.start())
            
            # Parse variants
            variants = []
            variant_pattern = r'(\w+)(?:\s*\{[^}]*\}|\s*\([^)]*\))?'
            for var_match in re.finditer(variant_pattern, body):
                var_name = var_match.group(1)
                if var_name in ("pub", "struct", "fn"):
                    continue
                var_doc = self._extract_doc_comments(body, var_match.start())
                variants.append((var_name, var_doc))
            
            enums.append(EnumInfo(
                name=name,
                docstring=self._clean_docstring(doc),
                variants=variants,
            ))
        
        return enums
    
    def _parse_functions(self, content: str) -> List[FunctionInfo]:
        """Parse standalone public functions."""
        functions = []
        
        # Match: pub fn name(...) -> Type { ... }
        # Exclude functions inside impl blocks by checking context
        pattern = r'^pub\s+(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)(?:\s*->\s*([^{]+))?\s*\{'
        
        for match in re.finditer(pattern, content, re.MULTILINE):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3).strip() if match.group(3) else "()"
            
            # Skip if this looks like it's inside an impl block
            # (simple heuristic: check if there's an unmatched `impl` before this)
            before = content[:match.start()]
            impl_count = before.count("impl ")
            close_brace_count = before.count("}")
            if impl_count > close_brace_count:
                continue
            
            # Extract doc comments
            doc = self._extract_doc_comments(content, match.start())
            
            # Parse parameters
            params = self._parse_params(params_str)
            
            # Check if async
            is_async = "async" in match.group(0)
            
            functions.append(FunctionInfo(
                name=name,
                signature=params_str,
                return_type=return_type,
                docstring=self._clean_docstring(doc),
                params=params,
                is_async=is_async,
                examples=self._extract_examples(doc),
            ))
        
        return functions
    
    def _parse_impl_blocks(self, content: str, module_info: ModuleInfo) -> None:
        """Parse impl blocks and attach methods to corresponding structs."""
        
        # Find all impl block starts
        impl_pattern = r'impl(?:<[^>]*>)?\s+(?:(\w+)\s+for\s+)?(\w+)(?:<[^>]*>)?\s*\{'
        
        for match in re.finditer(impl_pattern, content):
            trait_name = match.group(1)  # For trait impls
            struct_name = match.group(2)
            
            # Find the matching closing brace using brace counting
            start_pos = match.end() - 1  # Position of opening brace
            body = self._extract_brace_content(content, start_pos)
            
            if body:
                # Parse methods from impl body
                methods = self._parse_impl_methods(body)
                
                # Find the corresponding struct and add methods
                for cls in module_info.classes:
                    if cls.name == struct_name:
                        cls.methods.extend(methods)
                        break
    
    def _extract_brace_content(self, content: str, start_pos: int) -> str:
        """Extract content within braces, handling nested braces correctly."""
        if content[start_pos] != '{':
            return ""
        
        depth = 0
        i = start_pos
        
        while i < len(content):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    return content[start_pos + 1:i]
            i += 1
        
        return content[start_pos + 1:]  # No closing brace found
    
    def _parse_impl_methods(self, body: str) -> List[MethodInfo]:
        """Parse methods from an impl block body."""
        methods = []
        
        # Match: pub fn name(...) -> Type { ... }
        pattern = r'pub\s+(?:async\s+)?fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^{]+))?\s*\{'
        
        for match in re.finditer(pattern, body):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3).strip() if match.group(3) else "()"
            
            # Skip internal methods
            if name.startswith("_") or name in SKIP_METHODS:
                continue
            
            # Extract doc comments
            doc = self._extract_doc_comments(body, match.start())
            
            # Parse parameters
            params = self._parse_params(params_str)
            
            # Detect method type
            is_static = "&self" not in params_str and "self" not in params_str
            is_async = "async" in match.group(0)
            
            methods.append(MethodInfo(
                name=name,
                signature=params_str,
                return_type=return_type,
                docstring=self._clean_docstring(doc),
                params=params,
                is_async=is_async,
                is_static=is_static,
                examples=self._extract_examples(doc),
            ))
        
        return methods
    
    def _parse_params(self, params_str: str) -> List[ParamInfo]:
        """Parse function/method parameters."""
        params = []
        
        if not params_str.strip():
            return params
        
        # Simple parameter parsing
        # Handle: name: Type, &self, &mut self, self
        for part in params_str.split(","):
            part = part.strip()
            if not part:
                continue
            
            # Skip self parameters
            if part in ("self", "&self", "&mut self"):
                continue
            
            # Match: name: Type
            param_match = re.match(r'(\w+)\s*:\s*(.+)', part)
            if param_match:
                name = param_match.group(1)
                type_str = param_match.group(2).strip()
                
                # Check for default (= value)
                default = None
                if "=" in type_str:
                    type_str, default = type_str.split("=", 1)
                    type_str = type_str.strip()
                    default = default.strip()
                
                params.append(ParamInfo(
                    name=name,
                    type=type_str,
                    default=default,
                    required=default is None,
                ))
        
        return params
    
    def _extract_examples(self, doc: str) -> List[str]:
        """Extract code examples from documentation."""
        examples = []
        
        # Find ```rust or ``` blocks
        pattern = r'```(?:rust(?:,ignore)?)?\n(.*?)```'
        for match in re.finditer(pattern, doc, re.DOTALL):
            examples.append(match.group(1).strip())
        
        return examples
    
    def _clean_docstring(self, doc: str) -> str:
        """Clean up a docstring for display."""
        # Remove example blocks for the main description
        doc = re.sub(r'# Example.*', '', doc, flags=re.DOTALL | re.IGNORECASE)
        doc = re.sub(r'```.*?```', '', doc, flags=re.DOTALL)
        
        # Clean up whitespace
        lines = [line.strip() for line in doc.split("\n")]
        lines = [line for line in lines if line]
        
        return " ".join(lines)


# =============================================================================
# PROC-MACRO PARSER
# =============================================================================

class ProcMacroParser(RustDocParser):
    """Parser specialized for proc-macro crates (like praisonai-derive)."""
    
    def parse_macros(self) -> List[MacroInfo]:
        """Parse proc-macro definitions."""
        macros = []
        
        lib_rs = self.src_path / "lib.rs"
        if not lib_rs.exists():
            return macros
        
        content = self._read_file(lib_rs)
        
        # Match: #[proc_macro_attribute] pub fn name(...) { ... }
        pattern = r'#\[proc_macro(?:_attribute|_derive)?\]\s*pub\s+fn\s+(\w+)'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            
            # Extract doc comments
            doc = self._extract_doc_comments(content, match.start())
            
            macros.append(MacroInfo(
                name=name,
                docstring=self._clean_docstring(doc),
                examples=self._extract_examples(doc),
            ))
        
        return macros


# =============================================================================
# WORKSPACE PARSER
# =============================================================================

class RustWorkspaceParser:
    """Parse an entire Rust workspace with multiple crates."""
    
    def __init__(self, workspace_path: Path):
        """Initialize the workspace parser.
        
        Args:
            workspace_path: Path to workspace root (containing Cargo.toml with [workspace])
        """
        self.workspace_path = workspace_path
        self.crates: Dict[str, RustDocParser] = {}
        self._discover_crates()
    
    def _discover_crates(self) -> None:
        """Discover crates in the workspace."""
        # Parse workspace Cargo.toml
        cargo_toml = self.workspace_path / "Cargo.toml"
        if not cargo_toml.exists():
            return
        
        content = cargo_toml.read_text()
        
        # Find workspace members
        members_match = re.search(r'members\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if members_match:
            members_str = members_match.group(1)
            members = re.findall(r'"([^"]+)"', members_str)
            
            for member in members:
                member_path = self.workspace_path / member
                if member_path.exists():
                    crate_name = member.replace("-", "_")
                    
                    # Use ProcMacroParser for derive crate
                    if "derive" in member:
                        self.crates[crate_name] = ProcMacroParser(member_path, crate_name)
                    else:
                        self.crates[crate_name] = RustDocParser(member_path, crate_name)
    
    def get_all_modules(self) -> Dict[str, List[str]]:
        """Get all modules from all crates.
        
        Returns:
            Dict mapping crate name to list of module paths
        """
        result = {}
        for crate_name, parser in self.crates.items():
            result[crate_name] = parser.get_modules()
        return result
    
    def parse_all(self) -> Dict[str, List[ModuleInfo]]:
        """Parse all modules from all crates.
        
        Returns:
            Dict mapping crate name to list of ModuleInfo
        """
        result = {}
        for crate_name, parser in self.crates.items():
            modules = []
            for module_path in parser.get_modules():
                module_info = parser.parse_module(module_path)
                if module_info:
                    modules.append(module_info)
            result[crate_name] = modules
        return result
