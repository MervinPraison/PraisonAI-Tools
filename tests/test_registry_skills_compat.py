"""Tier 0: pin that registry-installed skills (./.claude/skills/) are discoverable.

Registries that expose ``skill install <name>`` install into ``./.claude/skills/``.
PraisonAI's skill discovery already scans that directory, so registry-installed
skills are discoverable with zero connector code. This test pins that contract.
"""

import os
import pytest


def test_claude_skills_dir_is_scanned(tmp_path, monkeypatch):
    discovery = pytest.importorskip("praisonaiagents.skills.discovery")

    skills_dir = tmp_path / ".claude" / "skills" / "my-registry-skill"
    skills_dir.mkdir(parents=True)

    monkeypatch.chdir(tmp_path)
    dirs = discovery.get_default_skill_dirs()

    claude_skills = tmp_path / ".claude" / "skills"
    assert any(os.path.samefile(str(d), str(claude_skills)) for d in dirs), (
        "PraisonAI must scan ./.claude/skills/ so registry-installed skills are "
        "discoverable with zero connector code."
    )
