from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class GitInfo:
    commit_hash: str | None
    dirty: bool | None


def get_git_info(repository_path: str | Path) -> GitInfo:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return GitInfo(commit_hash=None, dirty=None)

    return GitInfo(commit_hash=commit or None, dirty=bool(status.strip()))
