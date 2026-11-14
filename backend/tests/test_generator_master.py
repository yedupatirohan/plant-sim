import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.master_data import FULL_SCALE, generate_master

SEED = 20261022


def test_full_scale_counts():
    d = generate_master(SEED)
    assert len(d["facilities"]) == 3
    assert len(d["pumps"]) == 20
    assert len(d["tanks"]) == 30
    assert len(d["valves"]) == 60


def test_same_seed_is_identical():
    assert generate_master(SEED) == generate_master(SEED)


def test_different_seed_differs():
    assert generate_master(SEED) != generate_master(SEED + 1)


def test_ids_are_unique_and_zero_padded():
    d = generate_master(SEED)
    assert d["pumps"][0]["pump_id"] == "PUMP-001"
    assert d["pumps"][-1]["pump_id"] == "PUMP-020"
    for key, idk in [("pumps", "pump_id"), ("tanks", "tank_id"),
                     ("valves", "valve_id"), ("pipes", "pipe_id")]:
        ids = [r[idk] for r in d[key]]
        assert len(ids) == len(set(ids))


def test_every_component_has_a_valid_facility():
    d = generate_master(SEED)
    fids = {f["facility_id"] for f in d["facilities"]}
    for key in ("pumps", "tanks", "valves", "pipes"):
        assert all(r["facility_id"] in fids for r in d[key])


def test_every_pipe_connects_two_valid_nodes_in_same_facility():
    d = generate_master(SEED)
    node_fac = {}
    for key, idk in [("pumps", "pump_id"), ("tanks", "tank_id"), ("valves", "valve_id")]:
        for r in d[key]:
            node_fac[r[idk]] = r["facility_id"]
    for p in d["pipes"]:
        assert p["from_node_id"] in node_fac and p["to_node_id"] in node_fac
        assert node_fac[p["from_node_id"]] == p["facility_id"] == node_fac[p["to_node_id"]]
        assert p["from_node_id"] != p["to_node_id"]


def test_each_facility_topology_is_connected():
    d = generate_master(SEED)
    for fac in d["facilities"]:
        fid = fac["facility_id"]
        nodes = {r[k] for key, k in [("pumps", "pump_id"), ("tanks", "tank_id"), ("valves", "valve_id")]
                 for r in d[key] if r["facility_id"] == fid}
        adj = {n: set() for n in nodes}
        for p in d["pipes"]:
            if p["facility_id"] == fid:
                adj[p["from_node_id"]].add(p["to_node_id"])
                adj[p["to_node_id"]].add(p["from_node_id"])
        start = next(iter(nodes))
        seen, stack = {start}, [start]
        while stack:
            for nb in adj[stack.pop()]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        assert seen == nodes


def test_small_scale_uses_same_generator():
    d = generate_master(SEED, {"facilities": 1, "pumps": 2, "tanks": 2, "valves": 3})
    assert len(d["pumps"]) == 2 and len(d["valves"]) == 3