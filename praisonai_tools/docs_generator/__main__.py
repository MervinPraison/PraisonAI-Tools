"""
CLI entry point for praisonai_tools.docs_generator.

This can be run in two ways:
1. Directly: cd praisonai_tools/docs_generator && python __main__.py --package rust
2. As module (requires praisonaiagents): python -m praisonai_tools.docs_generator --package rust
"""

import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="PraisonAI SDK Documentation Generator")
    parser.add_argument("--package", choices=["praisonaiagents", "praisonai", "typescript", "rust", "all"], 
                        default="all", help="Package to generate docs for")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--docs-root", default="/Users/praison/PraisonAIDocs", 
                        help="Root directory of the documentation repository")
    parser.add_argument("--layout", choices=["legacy", "granular"], default="granular",
                        help="Documentation layout type")
    parser.add_argument("--rust-path", default="/Users/praison/praisonai-package/src/praisonai-rust",
                        help="Path to Rust SDK workspace")
    
    args = parser.parse_args()
    
    # For Rust-only generation, use the standalone script to avoid praisonaiagents dependency
    if args.package == "rust":
        # Use the standalone Rust generator
        from pathlib import Path
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir))
        
        from generate_rust_docs import main as rust_main
        # Patch sys.argv for the rust script
        sys.argv = [
            'generate_rust_docs.py',
            '--rust-path', args.rust_path,
            '--docs-root', args.docs_root,
        ]
        if args.dry_run:
            sys.argv.append('--dry-run')
        rust_main()
        return 0
    
    # For other packages, use the full generator (requires praisonaiagents)
    try:
        from .generator import ReferenceDocsGenerator, LayoutType
    except ImportError as e:
        print(f"Error: {e}")
        print("\nFor generating Python/TypeScript docs, install praisonaiagents:")
        print("  pip install praisonaiagents")
        print("\nFor Rust docs only, use: --package rust")
        return 1
    
    layout = LayoutType.LEGACY if args.layout == "legacy" else LayoutType.GRANULAR
    generator = ReferenceDocsGenerator(docs_root=args.docs_root, layout=layout)
    
    if args.package == "all":
        generator.generate_all(dry_run=args.dry_run)
    else:
        generator.generate_package(args.package, dry_run=args.dry_run)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
