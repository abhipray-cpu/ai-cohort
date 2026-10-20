import pytest
from casecouncil_api.fspo import parse_listing, party_packet
from casecouncil_api.store import Store
from test_casecouncil_store import CONTEXT, PASSWORD


def test_official_listing_preserves_labels_separately_and_rejects_foreign_links():
    html = """<div class="decision col-12"><h3><a href="https://fspo.ie/complaint-outcomes/investigation-services/legally-binding-decisions/documents/2023-0200.pdf">Car Decision Reference 2023-0200</a></h3>
    <p><span>Sector:</span> Insurance</p><p><span>Product/Service:</span> Motor</p>
    <p><span>Primary Conduct Complained Of:</span> Customer Service</p>
    <p><span>Outcome:</span> Upheld</p><p><span>Year:</span> 2023</p></div>"""
    rows = parse_listing(html)
    assert rows[0]["reference"] == "2023-0200" and rows[0]["outcome"] == "Upheld"
    with pytest.raises(ValueError):
        parse_listing(html.replace("https://fspo.ie/", "https://untrusted.example/"))


def test_party_packet_removes_cover_outcome_reference_and_all_decision_reasoning():
    text = """Decision Ref: 2023-0200
Outcome: Upheld
LEGALLY BINDING DECISION OF THE FINANCIAL SERVICES AND PENSIONS OMBUDSMAN
The Complainant held a motor policy.
The Complainant’s Case
The customer says the renewal notices conflicted.
The Provider’s Case
The provider accepts a system error but disputes redress.
The Complaint for Adjudication
Whether conflicting notices were adequate.
Decision
SECRET_OUTCOME_REASONING: This complaint is upheld.
"""
    packet = party_packet(text, "2023-0200")
    assert "conflicting notices" in packet["text"]
    assert all(s not in packet["text"] for s in ["Upheld", "2023-0200", "SECRET_OUTCOME_REASONING"])
    assert text[packet["start"] : packet["end"]].strip() == packet["text"]
    wrapped = text.replace("DECISION OF", "DECISION\nOF").replace(
        "Complainant’s Case", "Complainants’ Case"
    )
    assert "conflicting notices" in party_packet(wrapped, "2023-0200")["text"]
    with pytest.raises(ValueError):
        party_packet(text.replace("\nDecision\n", "\nUnknown heading\n"), "2023-0200")


def test_irish_replay_requires_explicit_isolated_evaluation_store(tmp_path):
    for flag in (False, True):
        store = Store(tmp_path / str(flag), evaluation_only=flag)
        store.bootstrap("owner", PASSWORD)
        w = store.create_workspace("owner", "Scope test", "workspace")
        value = {**CONTEXT, "jurisdiction": "IE"}
        if flag:
            c = store.create_case("owner", w, value, "case")
            assert store.case("owner", c["id"])["context"]["jurisdiction"] == "IE"
        else:
            with pytest.raises(ValueError):
                store.create_case("owner", w, value, "case")


def test_default_http_intake_does_not_expand_product_jurisdiction(tmp_path):
    from casecouncil_api.api import create_app
    from fastapi.testclient import TestClient
    from test_casecouncil_api import login, post

    app = create_app(tmp_path, username="owner", password=PASSWORD)
    client = TestClient(app)
    login(client)
    w = post(client, "/api/workspaces", json={"name": "Default UK product"}).json()["id"]
    result = post(
        client, "/api/cases", json={"workspace": w, "context": {**CONTEXT, "jurisdiction": "IE"}}
    )
    assert result.status_code == 409
