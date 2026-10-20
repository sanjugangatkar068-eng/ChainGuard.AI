import os
import sys
import tempfile

# Make `import main` / `import database` work when pytest runs from anywhere.
sys.path.insert(0, os.path.dirname(__file__))

# Point the app at a throwaway database before it is imported.
os.environ.setdefault(
    "DATABASE_PATH",
    os.path.join(tempfile.mkdtemp(prefix="chainguard-test-"), "test.db"),
)

# Keep tests deterministic regardless of the developer's environment:
# no LLM, and no live feed URLs.
os.environ["LLM_PROVIDER"] = "none"
os.environ.pop("LLM_API_KEY", None)
os.environ.pop("SIGNAL_FEEDS", None)

import pytest  # noqa: E402

import database as db  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Start every test from an empty schema."""
    db.init_db()
    with db.get_conn() as conn:
        for table in ("disruptions", "analyses", "approvals", "audit_logs"):
            conn.execute(f"DELETE FROM {table}")
    yield
