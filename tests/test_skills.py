from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_xrun_skill_prefers_xcelium_for_package_heavy_tasks() -> None:
    skill = (ROOT / ".opencode" / "skills" / "xrun" / "SKILL.md").read_text()
    assert "package-heavy" in skill
    assert "compile/elaboration" in skill
    assert "Prefer `xrun`" in skill
    assert "required compile check" in skill
    assert "explicitly select the DUT top" in skill
    assert "helper interface or package alone does not count" in skill
    assert "`vcdcat`" in skill
    assert "waveform" in skill


def test_yosys_skill_marks_repo_flow_as_xrun_only() -> None:
    skill = (ROOT / ".opencode" / "skills" / "yosys" / "SKILL.md").read_text()
    assert "Do not use `yosys` in this repo" in skill
    assert "Use `xrun`/Xcelium" in skill
