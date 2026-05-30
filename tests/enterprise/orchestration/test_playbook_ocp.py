"""Test OCP: adding a new playbook YAML is recognized without modifying Python."""

from __future__ import annotations

from pathlib import Path

from vigilancia_multiagente.enterprise.orchestration.playbook_registry import PlaybookRegistry


class TestPlaybookOCP:
    def test_new_yaml_recognized_without_code_change(self, tmp_path: Path) -> None:
        """A new playbook YAML dropped into the dir is loaded automatically."""
        # Create a minimal valid playbook YAML
        pb_yaml = tmp_path / "new-playbook.yaml"
        pb_yaml.write_text(
            "id: new-playbook\n"
            "name: New Playbook\n"
            "executor_type: single_agent\n"
            "parallel: false\n"
            "agents:\n"
            "  - id: agent1\n"
            "    role: helper\n"
            "    skills_allowed:\n"
            "      - web_search\n",
            encoding="utf-8",
        )

        reg = PlaybookRegistry()
        reg.load_all(tmp_path)

        pb = reg.get("new-playbook")
        assert pb.name == "New Playbook"
        assert pb.executor_type == "single_agent"
