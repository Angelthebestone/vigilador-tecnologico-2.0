# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""DependencyResolver: validates DAG and produces ordered execution plan."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    ExecutionPlan,
    GoalDAG,
)


class CyclicDependencyError(Exception):
    """Raised when the DAG contains a cycle."""

    def __init__(self, cycle_nodes: list[str]) -> None:
        self.cycle_nodes = cycle_nodes
        super().__init__(f"Cyclic dependency detected involving: {cycle_nodes}")


class EmptyDAGError(Exception):
    """Raised when the DAG has no sub-goals."""

    def __init__(self) -> None:
        super().__init__("DAG contains no sub-goals")


class DepthExceededError(Exception):
    """Raised when the DAG depth exceeds the configured maximum."""

    def __init__(self, depth: int, max_depth: int) -> None:
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(f"DAG depth {depth} exceeds max_depth {max_depth}")


class DependencyResolver:
    """Resolves sub-goal dependencies into a staged execution plan."""

    def __init__(self, max_depth: int = 10) -> None:
        self._max_depth = max_depth

    def resolve(self, dag: GoalDAG) -> ExecutionPlan:
        """Produce an ExecutionPlan with parallelizable stages. Raises on cycles/empty."""
        if not dag.sub_goals:
            raise EmptyDAGError()

        adj: dict[str, set[str]] = {}
        in_degree: dict[str, int] = {}
        all_ids: set[str] = set()

        for sg in dag.sub_goals:
            all_ids.add(sg.id)
            if sg.id not in adj:
                adj[sg.id] = set()
            if sg.id not in in_degree:
                in_degree[sg.id] = 0

        for sg in dag.sub_goals:
            for dep in sg.dependencies:
                if dep not in all_ids:
                    continue  # ignore external deps
                adj.setdefault(dep, set()).add(sg.id)
                in_degree[sg.id] = in_degree.get(sg.id, 0) + 1

        # Kahn's algorithm for topological sort with stage detection
        queue: list[str] = [n for n in all_ids if in_degree.get(n, 0) == 0]
        stages: list[tuple[str, ...]] = []
        processed = 0

        while queue:
            stages.append(tuple(sorted(queue)))
            next_queue: list[str] = []
            for node in queue:
                processed += 1
                for neighbor in adj.get(node, set()):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue

        if processed < len(all_ids):
            # Cycle detected — find involved nodes
            remaining = [n for n in all_ids if in_degree.get(n, 0) > 0]
            raise CyclicDependencyError(cycle_nodes=sorted(remaining))

        if len(stages) > self._max_depth:
            raise DepthExceededError(depth=len(stages), max_depth=self._max_depth)

        return ExecutionPlan(stages=tuple(stages))
