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

# Alerts: deterministic threshold, never call a real webhook in tests.
os.environ["ALERT_MIN_LEVEL"] = "high"
os.environ.pop("ALERT_WEBHOOK_URL", None)

# Never start the autonomous background loop during tests.
os.environ["ORCHESTRATOR_INTERVAL_SECONDS"] = "0"

# Auth is opt-in; tests assume it is off unless a test enables it.
os.environ.pop("API_KEY", None)

import pytest  # noqa: E402

import database as db  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Start every test from an empty schema."""
    db.init_db()
    with db.get_conn() as conn:
        for table in ("disruptions", "analyses", "approvals", "audit_logs", "alerts"):
            conn.execute(f"DELETE FROM {table}")
        # Reset AUTOINCREMENT so ids are deterministic across tests.
        conn.execute("DELETE FROM sqlite_sequence")
    yield
