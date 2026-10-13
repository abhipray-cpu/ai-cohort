from tenderlens_api.store import Store


def test_stale_running_job_can_be_reclaimed(tmp_path):
    store = Store(tmp_path)
    opportunity = store.create_opportunity("Example")
    with store.connect() as db:
        db.execute(
            "INSERT INTO runs(id,opportunity_id,status,document_hashes,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?)",
            ("r1", opportunity["id"], "running", "{}", "2020-01-01", "2020-01-01"),
        )
    assert store.claim_next_run()["id"] == "r1"
    assert store.claim_next_run() is None
