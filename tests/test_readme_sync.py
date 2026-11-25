"""README.md and README.ko.md must carry the same fenced shell commands."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"```(?:bash|sh|shell)\n(.*?)```", re.S)


def _commands(name: str) -> list[str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    cmds = []
    for block in FENCE.findall(text):
        for line in block.splitlines():
            line = re.sub(r"\s+#.*$", "", line).strip()
            if line and not line.startswith("#"):
                cmds.append(line)
    return cmds


def test_readme_shell_commands_match():
    assert _commands("README.md") == _commands("README.ko.md")
