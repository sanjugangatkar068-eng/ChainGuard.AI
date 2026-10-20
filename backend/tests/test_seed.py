import database as db
import seed


def test_seed_populates_all_tables():
    summary = seed.seed(reset=True)

    assert summary["disruptions"] == len(seed.DEMO_DISRUPTIONS)
    assert summary["analyses"] == len(seed.DEMO_DISRUPTIONS)
    assert summary["suppliers"] == len(seed.DEMO_SUPPLIERS)

    assert db.count_records("disruptions") == len(seed.DEMO_DISRUPTIONS)
    assert db.count_records("analyses") == len(seed.DEMO_DISRUPTIONS)
    # at least the critical/high disruptions should have requested approval
    assert db.count_records("approvals") >= 1
    assert db.count_records("audit_logs") >= len(seed.DEMO_DISRUPTIONS)


def test_seed_reset_does_not_duplicate():
    seed.seed(reset=True)
    first = db.count_records("disruptions")

    seed.seed(reset=True)
    second = db.count_records("disruptions")

    assert first == second == len(seed.DEMO_DISRUPTIONS)
