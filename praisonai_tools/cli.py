"""
Unified CLI for PraisonAI Tools.
"""

import argparse
import sys
from importlib import import_module

def main():
    if len(sys.argv) < 2:
        print("PraisonAI Developer Tools CLI")
        print("\nUsage: praisonai-tools [tool] [args]")
        print("\nAvailable tools:")
        print("  docs-generate    Generate SDK reference documentation")
        print("  video            AI-powered video editing tools")
        print("  fcp              Final Cut Pro automation tools")
        return 1
    
    tool = sys.argv[1]
    tool_args = sys.argv[2:]
    
    if tool == "docs-generate":
        # Handle docs-generate with its own parser for better help
        parser = argparse.ArgumentParser(prog="praisonai-tools docs-generate")
        parser.add_argument("--package", choices=["praisonaiagents", "praisonai", "typescript", "all"], 
                            default="all", help="Package to generate docs for")
        parser.add_argument("--dry-run", action="store_true", help="Don't write files")
        parser.add_argument("--docs-root", default="/Users/praison/PraisonAIDocs", 
                            help="Root directory of the documentation repository")
        parser.add_argument("--source-root", help="Root directory of the source code")
        
        args = parser.parse_args(tool_args)
        from .docs_generator.generator import ReferenceDocsGenerator
        generator = ReferenceDocsGenerator(docs_root=args.docs_root, source_root=args.source_root)
        
        if args.package == "all":
            generator.generate_all(dry_run=args.dry_run)
        else:
            generator.generate_package(args.package, dry_run=args.dry_run)
        return 0
        
    elif tool == "video":
        try:
            video_main = import_module(".video.__main__", package="praisonai_tools").main
            sys.argv = [f"{sys.argv[0]} video"] + tool_args
            return video_main()
        except ImportError as e:
            print(f"Error: Video tool not available. {e}")
            return 1
            
    elif tool == "fcp":
        try:
            fcp_main = import_module(".fcp_tool.cli", package="praisonai_tools").main
            return fcp_main(tool_args)
        except ImportError as e:
            print(f"Error: FCP tool not available. {e}")
            return 1
    else:
        print(f"Unknown tool: {tool}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
