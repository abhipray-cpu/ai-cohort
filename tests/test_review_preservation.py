import pymupdf
from contracts.tenderlens import Claim, DraftBrief, SourceCitation
from tenderlens_api.store import Store


def brief(document_id: str):
    return DraftBrief(
        schema_version="1.0",
        title="Road tender",
        claims=[
            Claim(
                kind="deadline",
                value="1 Dec 2026",
                status="verified",
                citations=[
                    SourceCitation(document_id=document_id, page=1, quote="Deadline 1 Dec 2026")
                ],
            )
        ],
        open_questions=[],
    )


def test_identical_claim_keeps_review_after_rerun(tmp_path):
    store = Store(tmp_path)
    opportunity = store.create_opportunity("Road tender")
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Deadline 1 Dec 2026")
    document = store.add_document(opportunity["id"], "road.pdf", pdf.tobytes())
    pdf.close()

    first = store.create_run(opportunity["id"])
    store.finish_run(first["id"], brief(document["id"]))
    first_claim = store.run(first["id"])["brief"]["claims"][0]
    store.review_claim(first_claim["id"], "accepted", None, "Checked against PDF")

    second = store.create_run(opportunity["id"])
    store.finish_run(second["id"], brief(document["id"]))
    second_claim = store.run(second["id"])["brief"]["claims"][0]
    assert second_claim["review_status"] == "accepted"
    assert second_claim["review_reason"] == "Checked against PDF"

    changed = brief(document["id"])
    changed.claims[0].value = "2 Dec 2026"
    third = store.create_run(opportunity["id"])
    store.finish_run(third["id"], changed)
    assert store.run(third["id"])["brief"]["claims"][0]["review_status"] is None
