"""In-memory source identity, without creating locks or changing recovery."""
import hashlib
from aka.contracts.workspace import SourceSnapshot


def snapshot(workspace, paths):
    digest = hashlib.sha256()
    for name in paths:
        content = (workspace / name).read_bytes()
        digest.update(name.encode() + b"\0" + len(content).to_bytes(8, "big") + content)
    return SourceSnapshot(tuple(paths), digest.hexdigest())

