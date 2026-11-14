"""Topology rules: do pipe endpoints exist, and is each facility connected?"""
from app.core.errors import NotFoundError
from app.repositories.plant_repo import PlantRepository


def analyse_graph(node_ids: set[str], pipes: list[tuple[str, str, str]]) -> dict:
    """pipes is a list of (pipe_id, from_node, to_node). Pure function."""
    adjacency: dict[str, set[str]] = {n: set() for n in node_ids}
    bad_pipes = []
    for pipe_id, a, b in pipes:
        missing = [n for n in (a, b) if n not in node_ids]
        if missing:
            bad_pipes.append({"pipe_id": pipe_id, "missing_nodes": missing})
            continue  # a pipe with a missing end cannot join anything
        adjacency[a].add(b)
        adjacency[b].add(a)

    # Find connected groups of nodes with a simple walk (depth-first search).
    seen: set[str] = set()
    components: list[list[str]] = []
    for start in sorted(node_ids):
        if start in seen:
            continue
        seen.add(start)
        stack, group = [start], []
        while stack:
            node = stack.pop()
            group.append(node)
            for nxt in adjacency[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(sorted(group))

    isolated = sorted(g[0] for g in components if len(g) == 1)
    connected = len(components) == 1
    return {
        "node_count": len(node_ids),
        "pipe_count": len(pipes),
        "component_count": len(components),
        "connected": connected,
        "isolated_nodes": isolated,
        "invalid_pipes": bad_pipes,
        "status": "OK" if connected and not bad_pipes else "ISSUES",
    }


class TopologyService:
    def __init__(self, repo: PlantRepository):
        self.repo = repo

    def check_facility(self, facility_id: str) -> dict:
        if self.repo.get_facility(facility_id) is None:
            raise NotFoundError(f"Facility {facility_id} not found")
        nodes = (
            {p.pump_id for p in self.repo.list_pumps(facility_id)}
            | {t.tank_id for t in self.repo.list_tanks(facility_id)}
            | {v.valve_id for v in self.repo.list_valves(facility_id)}
        )
        pipes = [(p.pipe_id, p.from_node_id, p.to_node_id)
                 for p in self.repo.list_pipes(facility_id)]
        result = analyse_graph(nodes, pipes)
        result["facility_id"] = facility_id
        return result

    def check_all(self) -> list[dict]:
        return [self.check_facility(f.facility_id) for f in self.repo.list_facilities()]