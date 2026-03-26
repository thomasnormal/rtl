from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_xrun_skill_prefers_xcelium_for_package_heavy_tasks() -> None:
    skill = (ROOT / ".opencode" / "skills" / "xrun" / "SKILL.md").read_text()
    assert "package-heavy" in skill
    assert "compile/elaboration" in skill
    assert "Prefer `xrun`" in skill
    assert "required compile check" in skill


def test_yosys_skill_mentions_fallback_role() -> None:
    skill = (ROOT / ".opencode" / "skills" / "yosys" / "SKILL.md").read_text()
    assert "fallback" in skill
    assert "small standalone RTL" in skill
    assert "do not use Yosys as the required compile check" in skill
