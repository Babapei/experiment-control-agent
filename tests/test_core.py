from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_core.config import get_value, load_config, resolve_path, root
from scripts.compute_signature import command_lines
from scripts.list_active_jobs import collect_jobs, parse_elapsed, parse_ps_line
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

    def test_collect_jobs_ignores_zombies(self) -> None:
        import scripts.list_active_jobs as list_active_jobs

        original = list_active_jobs.run_ps
        list_active_jobs.run_ps = lambda: ["123 1 Z 10 /repo/train.py --x"]
        try:
            jobs = collect_jobs(
                {
                    "job_detection": {
                        "managed_hints": ["/repo"],
                        "patterns": [{"category": "training", "regex": "train\\.py"}],
                    }
                }
            )
        finally:
            list_active_jobs.run_ps = original
        self.assertEqual(jobs, [])


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

    def test_toy_config_doctor_has_no_errors(self) -> None:
        env = os.environ.copy()
        env["AGENT_CONFIG"] = str(ROOT / "examples" / "toy-sleep-experiment" / "project.json")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "doctor.py"), "--json"],
            text=True,
            stdout=subprocess.PIPE,
            env=env,
            check=True,
        )
        findings = json.loads(proc.stdout)
        self.assertFalse([item for item in findings if item["severity"] == "ERROR"])

    def test_toy_task_writes_completed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "toy"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "examples" / "toy-sleep-experiment" / "toy_task.py"),
                    "--task-id",
                    "unit-test",
                    "--duration",
                    "0",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            payload = json.loads((output_dir / "completed.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["task_id"], "unit-test")
            self.assertEqual(payload["status"], "completed")

    def test_validate_state_passes_without_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            import scripts.validate_agent_state as validate_agent_state

            original = validate_agent_state.state_file
            validate_agent_state.state_file = lambda name: Path(tmpdir) / name
            try:
                findings = []
                validate_agent_state.check_modes(findings, load_config())
            finally:
                validate_agent_state.state_file = original
        self.assertFalse([item for item in findings if item.severity == "ERROR"])


if __name__ == "__main__":
    unittest.main()
