"""Link graph between dealers, known persons and retail accounts, built with networkx.

Node ids: dealer_id ("D1"), person_id ("P-001"), account_id ("A-011"), or attribute nodes
"phone:+91...", "email:...", "bank:...", "device:...", "address:..." as they appear in links.json.
Each edge carries `links`: every Link between the two nodes, in input order.
"""
from __future__ import annotations

import re

import networkx as nx

from dealerwatch.models import Account, Dealer, Link, Person

ATTRIBUTE_KINDS = ("phone", "email", "bank", "device", "address")


def normalize_phone(number: str | None) -> str:
    """Canonical "+<digits>" form; bare 10-digit Indian numbers get the +91 prefix."""
    digits = re.sub(r"\D", "", number or "")
    if not digits:
        return ""
    if len(digits) == 10:
        digits = "91" + digits
    return "+" + digits


def _attribute_node(node_id: str) -> dict[str, str | None]:
    prefix, _, value = node_id.partition(":")
    kind = prefix if value and prefix in ATTRIBUTE_KINDS else "other"
    return {"kind": kind, "label": value or node_id, "phone": value if kind == "phone" else None}


def build_graph(dealers: list[Dealer], persons: list[Person], accounts: list[Account],
                links: list[Link]) -> nx.Graph:
    """Undirected graph of entities; unknown link endpoints become attribute nodes."""
    graph = nx.Graph()
    for d in dealers:
        graph.add_node(d.dealer_id, kind="dealer", label=d.name, phone=None)
    for p in persons:
        graph.add_node(p.person_id, kind="person", label=p.name, phone=p.mobile)
    for a in accounts:
        graph.add_node(a.account_id, kind="account", label=a.holder_name, phone=a.mobile)
    for link in links:
        if link.src == link.dst:
            continue
        for node in (link.src, link.dst):
            if node not in graph:
                graph.add_node(node, **_attribute_node(node))
        if graph.has_edge(link.src, link.dst):
            graph[link.src][link.dst]["links"].append(link)
        else:
            graph.add_edge(link.src, link.dst, links=[link])
    return graph


def path_nodes(graph: nx.Graph, dealer_id: str, account_id: str) -> list[str]:
    """Node ids on the shortest dealer -> account path, or [] if there is none."""
    if dealer_id not in graph or account_id not in graph:
        return []
    try:
        return list(nx.shortest_path(graph, dealer_id, account_id))
    except nx.NetworkXNoPath:
        return []


def link_path(graph: nx.Graph, dealer_id: str, account_id: str) -> list[Link]:
    """Link edges along the shortest path, each oriented so src -> dst follows dealer -> account."""
    nodes = path_nodes(graph, dealer_id, account_id)
    out: list[Link] = []
    for a, b in zip(nodes, nodes[1:]):
        link = graph[a][b]["links"][0]
        if link.src != a:
            link = link.model_copy(update={"src": a, "dst": b})
        out.append(link)
    return out


def network_numbers(graph: nx.Graph, dealer_id: str, account_id: str) -> set[str]:
    """Normalised phone numbers of non-dealer nodes on the path and their 1-hop neighbours."""
    seeds = [n for n in path_nodes(graph, dealer_id, account_id) if graph.nodes[n]["kind"] != "dealer"]
    near = set(seeds)
    for node in seeds:
        near.update(graph.neighbors(node))
    numbers: set[str] = set()
    for node in near:
        data = graph.nodes[node]
        if data.get("kind") != "dealer" and data.get("phone"):
            numbers.add(normalize_phone(data["phone"]))
    numbers.discard("")
    return numbers
