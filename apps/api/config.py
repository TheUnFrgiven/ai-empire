from pathlib import Path
import os

from dotenv import dotenv_values, load_dotenv


def load_environment() -> None:
    """Load API and repo environment files in a deterministic order."""
    api_dir = Path(__file__).resolve().parent
    repo_root = api_dir.parent.parent
    original_env_keys = set(os.environ)

    # Real environment variables keep highest priority. The API-local file wins
    # over the repo-root fallback when both define the same key.
    load_dotenv(repo_root / ".env", override=False)
    for key, value in dotenv_values(api_dir / ".env").items():
        if key and value is not None and key not in original_env_keys:
            os.environ[key] = value
