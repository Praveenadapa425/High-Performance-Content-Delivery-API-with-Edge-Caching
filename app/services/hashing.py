import hashlib


def sha256_etag(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
