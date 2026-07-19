from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_core.config import get_value, load_config, resolve_path, root
from scripts.compute_signature import command_lines
from scripts.list_active_jobs import parse_elapsed, parse_ps_line
from scripts.render_prompt import render_context


class ConfigTests(unittest.TestCase):
    def test_load_example_config(self) -> None:
        config = load_config()
        self.assertIn("project", config)
        self.assertIn("modes", config)
        self.assertEqual(get_value(config, "modes.default_batch_profile"), "auto")

    def test_root_interpolation(self) -> None:
        config = load_config()
        hints = get_value(config, "job_detection.managed_hints")
        self.assertIn(str(root()), hints)

    def test_resolve_relative_path(self) -> None:
        self.assertEqual(resolve_path("runtime"), ROOT / "runtime")


class ProcessParsingTests(unittest.TestCase):
    def test_parse_elapsed_linux_seconds(self) -> None:
        self.assertEqual(parse_elapsed("3661"), 3661)

    def test_parse_elapsed_posix_etime(self) -> None:
        self.assertEqual(parse_elapsed("01:02:03"), 3723)
        self.assertEqual(parse_elapsed("02:03"), 123)
        self.assertEqual(parse_elapsed("1-00:00:01"), 86401)

    def test_parse_ps_line(self) -> None:
        parsed = parse_ps_line("123 1 S 00:00:05 python train.py --x")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed[0], 123)
        self.assertEqual(parsed[3], 5)
        self.assertIn("train.py", parsed[4])


class SignatureTests(unittest.TestCase):
    def test_missing_command_is_empty(self) -> None:
        self.assertEqual(command_lines(["definitely-not-a-real-agent-tool"]), [])


class PromptRenderTests(unittest.TestCase):
    def test_render_context_contains_project_docs(self) -> None:
        config = load_config()
        rendered = render_context(config, "cycle")
        self.assertIn("Rendered Agent Context", rendered)
        self.assertIn("agents_policy", rendered)
        self.assertIn("manifest_columns", rendered)


class ScriptSmokeTests(unittest.TestCase):
    def test_doctor_json_has_no_errors(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "doctor.py"), "--json"],
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )
        findings = json.loads(proc.stdout)
        self.assertFalse([item for item in findings if item["severity"] == "ERROR"])


if __name__ == "__main__":
    unittest.main()

