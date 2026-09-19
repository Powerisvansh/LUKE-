import os


def root():
    """Resolve the Luke runtime root: ~/.luke when deployed, else the source
    tree (dev on the build host). Overridable with $LUKE_ROOT."""
    env = os.environ.get("LUKE_ROOT")
    if env:
        return env
    home = os.path.expanduser("~/.luke")
    if os.path.isdir(home):
        return home
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = root()


def p(*parts):
    return os.path.join(ROOT, *parts)