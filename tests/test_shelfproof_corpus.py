"""Authored archive/schema fixtures for acquisition tooling; NOT real-data evidence."""

import io
import json
import zipfile

import pytest
from shelfproof_api.corpus import USDA_URL, acquire, iter_foods, normalize_food, validate_archive


def food(**changes):
    return {
        "fdcId": 123,
        "gtinUpc": "0001234567890",
        "brandName": "Example",
        "brandOwner": "Not the brand",
        "description": "Oat flakes",
        "ingredients": "Whole grain oats",
        "packageWeight": "500 g",
        "servingSize": 30,
        "servingSizeUnit": "g",
        "marketCountry": "United States",
        "brandedFoodCategory": "Breakfast Cereals",
        **changes,
    }


def test_obvious_brand_aliases_group_by_source_owner_not_brand_spelling():
    from shelfproof_api.corpus import source_group

    assert source_group(
        food(brandName="MY MOTHER'S DELICIOUS", brandOwner="General Handle Company")
    ) == source_group(
        food(
            brandName="MY MOTHER DELICIOUS",
            brandOwner="General Handle Company",
            brandedFoodCategory="Different category",
        )
    )


def test_streamed_records_survive_chunk_boundaries_and_unicode():
    rows = [food(description="🥣 Oat flakes"), food(fdcId=124)]
    raw = json.dumps({"BrandedFoods": rows}, ensure_ascii=False).encode()
    assert list(iter_foods(io.BytesIO(raw), chunk_size=7)) == rows


def test_package_quantity_never_comes_from_serving_size_or_owner():
    assert normalize_food(food(), "release").net_quantity == 500
    assert normalize_food(food(), "release").brand == "Example"
    with pytest.raises(ValueError, match="package"):
        normalize_food(food(packageWeight=""), "release")
    with pytest.raises(ValueError, match="brand"):
        normalize_food(food(brandName=""), "release")
    with pytest.raises(ValueError):
        normalize_food(food(packageWeight="2 oz / 56 g"), "release")


def test_wrong_country_discontinued_and_restricted_identity_are_excluded():
    for changes in (
        {"marketCountry": "Canada"},
        {"discontinuedDate": "2024-01-01"},
        {"description": "Organic Oat flakes"},
        {"brandedFoodCategory": "Dietary Supplements"},
    ):
        with pytest.raises(ValueError):
            normalize_food(food(**changes), "release")


def test_archive_rejects_traversal_and_unbounded_expansion():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as file:
        file.writestr("../escape.json", "{}")
    with zipfile.ZipFile(raw) as file, pytest.raises(ValueError):
        validate_archive(file)


def test_single_overlarge_or_malformed_record_is_not_silently_skipped():
    with pytest.raises(ValueError):
        list(
            iter_foods(
                io.BytesIO(b'{"BrandedFoods":[{"x":"' + b"a" * 2000 + b'"}]}'), max_record_bytes=100
            )
        )
    with pytest.raises(ValueError):
        list(iter_foods(io.BytesIO(b'{"BrandedFoods":[{"bad":}]}')))


@pytest.mark.parametrize("payload", [b'{"BrandedFoods":[{} {}]}', b'{"BrandedFoods":[{},]}'])
def test_array_separator_errors_are_not_accepted(payload):
    with pytest.raises(ValueError):
        list(iter_foods(io.BytesIO(payload), chunk_size=3))


def test_acquisition_requires_dictionary_review_before_mapping(tmp_path, monkeypatch):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as file:
        file.writestr("foods.json", json.dumps({"BrandedFoods": [food()]}))
        file.writestr(
            "field-descriptions.txt",
            "Owned schema fixture: packageWeight is net package, servingSize is not.",
        )

    class Response(io.BytesIO):
        url = USDA_URL

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: Response(raw.getvalue()))
    root = tmp_path / "inventory"
    pending = acquire(root, target=1)
    assert pending["mapping_pending"] is True
    assert not (root / "records.jsonl").exists()
    result = acquire(
        root, target=1, reviewed_dictionary_hash=pending["dictionary_files"][0]["sha256"]
    )
    assert result["eligible_selected"] == 1


def test_official_external_dictionary_is_pinned_when_archive_omits_it(tmp_path, monkeypatch):
    from shelfproof_api.corpus import DICTIONARY_URL

    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as file:
        file.writestr("foods.json", json.dumps({"BrandedFoods": [food()]}))

    class Response(io.BytesIO):
        def __init__(self, data, url):
            super().__init__(data)
            self.url = url

    def fetch(url, **kwargs):
        if url == USDA_URL:
            return Response(raw.getvalue(), url)
        assert url == DICTIONARY_URL
        return Response(b"%PDF-1.4\nOwned dictionary fixture only", url)

    monkeypatch.setattr("urllib.request.urlopen", fetch)
    pending = acquire(tmp_path / "external-guide", target=1)
    assert pending["dictionary_files"][0]["url"] == DICTIONARY_URL
    assert pending["mapping_pending"] is True
