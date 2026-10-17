import numpy as np
import pytest
from contracts.relaydesk import Recall
from relaydesk_api.embeddings import Encoder, validate_vector
from relaydesk_api.recall import RecallEngine, index_case
from test_relaydesk_core import batch, setup


@pytest.mark.parametrize(
    "value", [np.zeros(384), np.ones(2), np.full(384, np.nan), np.full(384, np.inf)]
)
def test_invalid_vectors_are_rejected(value):
    with pytest.raises(ValueError):
        validate_vector(value)


def test_real_vectors_recall_after_restart_and_account_isolation(tmp_path):
    from pathlib import Path

    from relaydesk_api.store import Store

    model = Path("var/models/relaydesk-minilm/manifest.json")
    if not model.exists():
        pytest.skip("Provision genuine encoder; no fabricated semantic substitute")
    encoder = Encoder(model.parent)
    store, case = setup(tmp_path)
    store.import_messages(
        "alice",
        case["id"],
        batch("The database cannot establish a connection because the password is incorrect."),
    )
    index_case(store, "alice", case["id"], encoder)
    reopened = Store(store.root, ledger_dir=tmp_path / "ledger")
    result = RecallEngine(reopened, encoder).search(
        "alice", case["id"], Recall(question="Why is authentication to the data server failing?")
    )
    assert result["mode"] == "semantic_hybrid" and result["hits"]
    assert "password" in result["hits"][0]["body"]
    # Paraphrase evidence is semantic, not just a substring/keyword lookup.
    probe = Recall(question="Credentials rejected during login")
    semantic = RecallEngine(reopened, encoder).search("alice", case["id"], probe)
    lexical = RecallEngine(reopened).search("alice", case["id"], probe)
    assert semantic["hits"] and not lexical["hits"]
    with pytest.raises(PermissionError):
        RecallEngine(reopened, encoder).search("bob", case["id"], Recall(question="database"))
