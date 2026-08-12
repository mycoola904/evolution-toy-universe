import subprocess

from persistence.git_info import GitInfo, get_git_info


def test_get_git_info_returns_commit_and_dirty_state(monkeypatch, tmp_path):
    responses = iter(
        [
            subprocess.CompletedProcess([], 0, stdout="abc123\n"),
            subprocess.CompletedProcess([], 0, stdout=" M src/main.py\n"),
        ]
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: next(responses),
    )

    assert get_git_info(tmp_path) == GitInfo("abc123", True)


def test_get_git_info_distinguishes_clean_and_unavailable(
    monkeypatch,
    tmp_path,
):
    clean_responses = iter(
        [
            subprocess.CompletedProcess([], 0, stdout="abc123\n"),
            subprocess.CompletedProcess([], 0, stdout=""),
        ]
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: next(clean_responses),
    )
    assert get_git_info(tmp_path) == GitInfo("abc123", False)

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(subprocess, "run", fail)
    assert get_git_info(tmp_path) == GitInfo(None, None)
