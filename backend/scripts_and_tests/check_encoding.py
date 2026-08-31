import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# The issue is that on Windows, if cmd is passed as a list of strings with special characters,
# subprocess.list2cmdline or CreateProcessW handles it, but if any environment encoding is set to ascii, it throws.
# To make subprocess 100% safe on Windows with any Unicode / Chinese / Vietnamese filename:
print("Current system encoding:", sys.getdefaultencoding())
print("File system encoding:", sys.getfilesystemencoding())
