"""T048: Verify adapters read only frontmatter during scan."""

import tempfile
from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import KDenseAdapter


def test_frontmatter_only_read():
    """KDenseAdapter only reads frontmatter, body is empty."""
    with tempfile.TemporaryDirectory() as tmp:
        vendor = Path(tmp) / "k_dense" / "skills"
        skill_dir = vendor / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nid: test-skill\ndescription: Test\n---\nThis is the body content that should not be read during boot.\n"
        )

        adapter = KDenseAdapter(Path(tmp) / "k_dense")
        results = adapter.scan()
        assert len(results) == 1
        _, _, body = results[0]
        assert body == ""  # Body should be empty because we read frontmatter-only
