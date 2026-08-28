"""Confirms the environment can run Python correctly, before installing anything else."""

import sys
import platform


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "participant"
    print(f"Hello, {name}")
    print(f"Python version : {platform.python_version()}")
    print(f"Executable     : {sys.executable}")


if __name__ == "__main__":
    main()
