"""Nuitka entry point.

Nuitka compiles a script, not a console-script entry point, so this thin
wrapper just calls the package's ``main``.
"""

from telltape import main

if __name__ == "__main__":
    main()
