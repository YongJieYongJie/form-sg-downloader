import sys
from os import path


BUNDLE_DIR = getattr(sys, '_MEIPASS', path.abspath(path.dirname(__file__)))


def get_path(relative_path):
    """Returns the correct path to resources whether the script is bundled
    using pyinstaller or not.
    """
    return path.join(BUNDLE_DIR, relative_path)
