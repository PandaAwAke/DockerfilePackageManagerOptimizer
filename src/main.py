"""
    [Dockerfile package manager optimizer]

    This tool will recognize all supported package managers (both system-specific
    and Language-specific), and then modify the Dockerfile1.read to a --mount=type=cache version.
    This operation will leverage the caches of the package managers, and these caches will not
    remain in the final image. The rebuild process of the Dockerfile1.read (for whose build cache
    got invalidated) will be surely accelerated too.

"""
import sys

from engine import Engine

if __name__ == '__main__':
    engine = Engine(sys.argv[1:])
    engine.run()
