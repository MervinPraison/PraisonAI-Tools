"""
CLI entry point for praisonai_tools.docs_generator.
"""

import argparse
import sys
from .generator import ReferenceDocsGenerator

def main():
    parser = argparse.ArgumentParser(description="PraisonAI SDK Documentation Generator")
    parser.add_argument("--package", choices=["praisonaiagents", "praisonai", "typescript", "all"], 
                        default="all", help="Package to generate docs for")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--docs-root", default="/Users/praison/PraisonAIDocs", 
                        help="Root directory of the documentation repository")
    
    args = parser.parse_args()
    
    generator = ReferenceDocsGenerator(docs_root=args.docs_root)
    
    if args.package == "all":
        generator.generate_all(dry_run=args.dry_run)
    else:
        generator.generate_package(args.package, dry_run=args.dry_run)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
