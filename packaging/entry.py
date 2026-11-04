"""PyInstaller entry point for the CRA Studio executable."""
import multiprocessing
import sys

from cra_studio.main import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
