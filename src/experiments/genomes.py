from hashlib import sha256
import json
from typing import Any


def persisted_genome_key(genome: Any) -> str:
    """Return a stable key for equality of a persisted JSONB genome value."""
    return json.dumps(genome, sort_keys=True, separators=(",", ":"))


def genome_display_digest(genome: Any) -> str:
    """Return a compact label; callers must not use it as genome identity."""
    key = persisted_genome_key(genome)
    return sha256(key.encode("utf-8")).hexdigest()[:12]
