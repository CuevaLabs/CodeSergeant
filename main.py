#!/usr/bin/env python3
"""Main entry point for Code Sergeant."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check if running in venv (recommended)
venv_python = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")
if os.path.exists(venv_python) and sys.executable != venv_python:
    print("⚠️  WARNING: Not running from virtual environment!")
    print(f"   Current Python: {sys.executable}")
    print(f"   Recommended: {venv_python}")
    print("   Run: source .venv/bin/activate && python3 main.py")
    print()

from code_sergeant.logging_utils import setup_logging
from code_sergeant.menu_bar import CodeSergeantApp

def main():
    """Launch Code Sergeant menu bar app."""
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Code Sergeant")
    
    try:
        # Create and run app
        app = CodeSergeantApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

