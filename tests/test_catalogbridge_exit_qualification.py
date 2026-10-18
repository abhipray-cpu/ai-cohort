from contracts.catalogbridge import Product

from scripts.evaluate_catalogbridge_confidence_exit import capacity_conflict, lower_bound


def test_conflict_rule_abstains_on_multi_attribute_titles_and_unit_conversion():
    a = Product(id="a", title="8GB RAM 128GB drive")
    b = Product(id="b", title="16GB RAM 128GB drive")
    assert not capacity_conflict(a, b)
    assert not capacity_conflict(
        Product(id="a", title="1TB disk"), Product(id="b", title="1000GB disk")
    )
    assert capacity_conflict(Product(id="a", title="8GB RAM"), Product(id="b", title="16GB RAM"))


def test_qualification_uses_uncertainty_not_point_precision():
    assert lower_bound(0, 0) == 0
    assert lower_bound(10, 10) < 0.99
    assert lower_bound(500, 500) >= 0.99
    assert lower_bound(720, 724) < 0.99
