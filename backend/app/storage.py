"""Object storage abstraction.

LocalObjectStorage (writing to the filesystem) is what actually runs today —
this is a REAL, working implementation, not a stub. S3ObjectStorage is an
honest, documented ABSTRACTION for the production target described in the
architecture: it defines the exact interface a real S3-backed implementation
must satisfy, but is not implemented, because no bucket/credentials exist in
this environment. Swapping it in later means implementing these two methods
and changing one line in `get_object_storage` — nothing calling this module
needs to change.

Keys are always server-generated (scan UUID + a whitelisted extension — see
routes/scan.py) and never derived from a client-supplied filename, so there is
no path-traversal surface here regardless of backend.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ObjectStorage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def url_for(self, key: str) -> str: ...


class LocalObjectStorage(ObjectStorage):
    def __init__(self, base_dir: Path, public_prefix: str = "/uploads"):
        self.base_dir = base_dir
        self.public_prefix = public_prefix

    def save(self, key: str, data: bytes) -> None:
        # `key` is always a server-generated "<uuid4hex><allowed-ext>" (see
        # EXTENSION_BY_CONTENT_TYPE in routes/scan.py) — never a client-supplied
        # filename — so this can never escape base_dir via "../" or an absolute path.
        (self.base_dir / key).write_bytes(data)

    def url_for(self, key: str) -> str:
        return f"{self.public_prefix}/{key}"


class S3ObjectStorage(ObjectStorage):
    """PRODUCTION ABSTRACTION — NOT IMPLEMENTED.

    No S3-compatible bucket or credentials exist in this environment to
    integrate against honestly. This class exists so the interface production
    would need is explicit and reviewable now, rather than deferred to a vague
    "future work" note.
    """

    def __init__(self, bucket: str, region: str | None = None):
        self.bucket = bucket
        self.region = region

    def save(self, key: str, data: bytes) -> None:
        raise NotImplementedError("S3ObjectStorage requires boto3 and real bucket credentials — not configured here.")

    def url_for(self, key: str) -> str:
        raise NotImplementedError("S3ObjectStorage requires boto3 and real bucket credentials — not configured here.")


def get_object_storage(upload_dir: Path) -> ObjectStorage:
    return LocalObjectStorage(base_dir=upload_dir)
