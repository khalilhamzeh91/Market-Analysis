"""
Publishes the HTML report to GitHub Pages after each run.
The report is saved as index.html in the repo root.
"""

import subprocess
import shutil
import os
from datetime import datetime
import config

REPO_URL   = "https://github.com/khalilhamzeh91/Market-Analysis.git"
REPO_DIR   = "C:/Users/khali/Documents/Market-Analysis"
INDEX_FILE = f"{REPO_DIR}/index.html"


def _run(cmd: list, cwd: str = REPO_DIR) -> bool:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  git error: {result.stderr.strip()}")
        return False
    return True


def _get_branch() -> str:
    """Detect the default remote branch (main or master)."""
    result = subprocess.run(
        ["git", "remote", "show", "origin"],
        cwd=REPO_DIR, capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if "HEAD branch" in line:
            return line.split(":")[-1].strip()
    return "main"


def setup():
    """Clone the repo if not already cloned locally."""
    if os.path.exists(REPO_DIR):
        return True

    print(f"  Cloning repo to {REPO_DIR}...")
    result = subprocess.run(
        ["git", "clone", REPO_URL, REPO_DIR],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Clone failed: {result.stderr.strip()}")
        return False

    print("  Repo cloned.")
    return True


def publish():
    """Copy report → index.html, commit, push."""
    if not setup():
        return False

    if not os.path.exists(config.REPORT_FILE):
        print("  No report file found, skipping publish.")
        return False

    branch = _get_branch()

    # Pull latest first to avoid conflicts
    _run(["git", "pull", "--rebase", "origin", branch])

    # Copy report as index.html
    shutil.copy2(config.REPORT_FILE, INDEX_FILE)

    # Copy all Python source files
    bot_dir = "C:/Users/khali/Documents/market_analysis_bot"
    for fname in os.listdir(bot_dir):
        if fname.endswith(".py"):
            shutil.copy2(os.path.join(bot_dir, fname), os.path.join(REPO_DIR, fname))

    # Stage, commit, push
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not _run(["git", "add", "index.html", "*.py"]):
        return False
    if not _run(["git", "commit", "-m", f"Update report + source {now}"]):
        print("  Nothing to commit.")
        return True
    if not _run(["git", "push", "origin", branch]):
        return False

    print(f"  Published → https://khalilhamzeh91.github.io/Market-Analysis")
    return True
