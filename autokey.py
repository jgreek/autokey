"""AutoKey - backward-compatible wrapper.

This module provides backward compatibility for existing scripts.
The actual implementation is in the autokey package.
"""

from autokey import AutoKey
from autokey.main import main

if __name__ == "__main__":
    main()