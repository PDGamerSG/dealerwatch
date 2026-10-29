"""Link graph: shortest path orientation, missing paths and network phone numbers."""
from __future__ import annotations

import networkx as nx
import pytest

from dealerwatch.detect.links import build_graph, link_path, network_numbers, normalize_phone
from dealerwatch.models import Account, Dealer, Link, Person


def _account(aid: str, mobile: str) -> Account:
    return Account(account_id=aid, holder_name=f"Holder {aid}", pan_masked="ABCPX****K", mobile=mobile,
                   email=f"{aid.lower()}@example.in", address="Pune", bank_account="XX01", device_id=f"dev-{aid}")


@pytest.fixture
def graph() -> nx.Graph:
    dealers = [Dealer(dealer_id="D1", name="Rohan Mehta", desk_phone="+912200000001", mobile="+919000000001",
                      email="rohan@sahyadri.example"),
               Dealer(dealer_id="D2", name="Kavya Iyer", desk_phone="+912200000002", mobile="+919000000002",
                      email="kavya@sahyadri.example")]
    persons = [Person(person_id="P-001", name="Vikram Shah", relation="brother-in-law of D1",
                      mobile="98000 00001", email="v@example.in"),
               Person(person_id="P-009", name="Neha Rao", relation="friend", mobile="+919800000009",
                      email="n@example.in")]
    accounts = [_account("A-011", "+919800000011"), _account("A-012", "+919800000012"),
                _account("A-099", "+919800000099")]
    links = [
        Link(src="D1", dst="P-001", kind="declared_relative", value="brother-in-law", source="employee declaration"),
        Link(src="A-011", dst="P-001", kind="shared_mobile", value="+919800000001", source="KYC"),  # reversed
        Link(src="A-011", dst="A-012", kind="shared_device", value="dev-x", source="KYC"),
        Link(src="A-012", dst="phone:+919811111111", kind="shared_mobile", value="+919811111111", source="KYC"),
        Link(src="D2", dst="P-009", kind="declared_relative", value="friend", source="employee declaration"),
    ]
    return build_graph(dealers, persons, accounts, links)


def test_path_is_oriented_dealer_to_account(graph: nx.Graph) -> None:
    path = link_path(graph, "D1", "A-012")
    assert [(lk.src, lk.dst, lk.kind) for lk in path] == [
        ("D1", "P-001", "declared_relative"),
        ("P-001", "A-011", "shared_mobile"),
        ("A-011", "A-012", "shared_device"),
    ]
    assert path[1].value == "+919800000001" and path[1].source == "KYC"


def test_no_path(graph: nx.Graph) -> None:
    assert link_path(graph, "D1", "A-099") == []
    assert link_path(graph, "D2", "A-011") == []
    assert link_path(graph, "D1", "A-404") == []
    assert network_numbers(graph, "D1", "A-099") == set()


def test_attribute_nodes(graph: nx.Graph) -> None:
    assert graph.nodes["phone:+919811111111"]["kind"] == "phone"
    assert graph.nodes["A-011"]["kind"] == "account"


def test_network_numbers(graph: nx.Graph) -> None:
    nums = network_numbers(graph, "D1", "A-011")
    # path D1-P-001-A-011, plus 1-hop neighbours of P-001 and A-011 (A-012); dealer numbers excluded
    assert nums == {"+919800000001", "+919800000011", "+919800000012"}
    wider = network_numbers(graph, "D1", "A-012")
    assert "+919811111111" in wider and "+919000000001" not in wider


def test_normalize_phone() -> None:
    assert normalize_phone("98000 00001") == "+919800000001"
    assert normalize_phone("+91-98000-00001") == "+919800000001"
    assert normalize_phone("") == ""
