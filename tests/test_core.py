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
from agent_core.provider import codex_exec_args, planning_provider
from scripts.compute_signature import command_lines
from scripts.batch_status import append_event, status_path, status_summary, validate_status_file
from scripts.doctor import check_modes as doctor_check_modes
from scripts.list_active_jobs import collect_jobs, parse_elapsed, parse_ps_line
from scripts.render_prompt import render_context
from scripts.validate_cycle_outcome import check_outcome as check_cycle_outcome_payload


class ConfigTests(unittest.TestCase):
    def test_load_example_config(self) -> None:
        config = load_config()
        self.assertIn("project", config)
        self.assertIn("modes", config)
        self.assertEqual(get_value(config, "modes.default_batch_profile"), "auto")
        self.assertIn("method_exploration", get_value(config, "modes.agent_mode_contracts"))
        self.assertIn("audit_validation", get_value(config, "modes.agent_mode_contracts"))

    def test_root_interpolation(self) -> None:
        config = load_config()
        hints = get_value(config, "job_detection.managed_hints")
        self.assertIn(str(root()), hints)

    def test_resolve_relative_path(self) -> None:
        self.assertEqual(resolve_path("runtime"), ROOT / "runtime")


class ProviderTests(unittest.TestCase):
    def test_default_provider_is_codex(self) -> None:
        provider = planning_provider(load_config())
        self.assertTrue(provider["supported"])
        self.assertEqual(provider["type"], "codex")
        self.assertEqual(provider["command"], "codex")
        self.assertEqual(provider["home"], str(ROOT / ".codex-home"))

    def test_codex_exec_args_apply_defaults(self) -> None:
        config = load_config()
        config["codex"] = dict(config.get("codex", {}))
        config["codex"]["default_model"] = "test-model"
        config["codex"]["default_reasoning_effort"] = "medium"
        config["codex"]["disable_response_storage"] = True
        args = codex_exec_args(planning_provider(config), cwd=ROOT, last_message_path=ROOT / "last.txt")
        self.assertEqual(args[:4], ["codex", "exec", "--model", "test-model"])
        self.assertIn('model_reasoning_effort="medium"', args)
        self.assertIn("disable_response_storage=true", args)
        self.assertEqual(args[-1], "-")

    def test_provider_codex_overrides_legacy_codex(self) -> None:
        config = load_config()
        config["codex"] = dict(config.get("codex", {}))
        config["codex"]["default_model"] = "legacy-model"
        config["provider"] = {"type": "codex", "command": "custom-codex", "codex": {"default_model": "provider-model"}}
        provider = planning_provider(config)
        args = codex_exec_args(provider, cwd=ROOT, last_message_path=ROOT / "last.txt")
        self.assertEqual(provider["command"], "custom-codex")
        self.assertEqual(args[:4], ["custom-codex", "exec", "--model", "provider-model"])

    def test_exec_args_overrides_config_defaults(self) -> None:
        config = load_config()
        config["codex"] = dict(config.get("codex", {}))
        config["codex"]["default_model"] = "config-model"
        config["codex"]["default_reasoning_effort"] = "low"
        args = codex_exec_args(
            planning_provider(config),
            cwd=ROOT,
            last_message_path=ROOT / "last.txt",
            model_override="override-model",
            reasoning_effort_override="high",
        )
        self.assertEqual(args[:4], ["codex", "exec", "--model", "override-model"])
        self.assertIn('model_reasoning_effort="high"', args)


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


class BatchStatusTests(unittest.TestCase):
    def test_append_and_validate_status_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            append_event(batch_dir, "pkg-a", "running", pid="123", output_root="out", log_path="run.log", command="python train.py")
            append_event(batch_dir, "pkg-a", "completed", pid="123", exit_code="0", output_root="out", log_path="run.log", command="python train.py")
            findings = validate_status_file(status_path(batch_dir))
            self.assertFalse([item for item in findings if item.severity == "ERROR"])

    def test_completed_status_requires_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                append_event(Path(tmpdir), "pkg-a", "completed")

    def test_status_summary_tracks_incomplete_and_complete_batches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            append_event(batch_dir, "pkg-a", "running", pid="123")
            append_event(batch_dir, "pkg-b", "running", pid="124")
            append_event(batch_dir, "pkg-a", "completed", pid="123", exit_code="0")
            partial = status_summary(status_path(batch_dir))
            self.assertFalse(partial["complete"])
            self.assertEqual(partial["total"], 2)
            self.assertEqual(partial["completed"], 1)
            self.assertEqual(partial["incomplete_ids"], ["pkg-b"])
            append_event(batch_dir, "pkg-b", "failed", pid="124", exit_code="1")
            final = status_summary(status_path(batch_dir))
            self.assertTrue(final["complete"])
            self.assertEqual(final["failed"], 1)
            self.assertEqual(final["failed_ids"], ["pkg-b"])

    def test_launch_wrapper_records_terminal_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            output_dir = Path(tmpdir) / "out"
            log_path = Path(tmpdir) / "job.log"
            subprocess.run(
                [
                    str(ROOT / "scripts" / "launch_batch_job.sh"),
                    str(batch_dir),
                    "pkg-a",
                    str(output_dir),
                    str(log_path),
                    "--",
                    sys.executable,
                    "-c",
                    "from pathlib import Path; import sys; p=Path(sys.argv[1]); p.mkdir(parents=True, exist_ok=True); (p / 'done.txt').write_text('ok')",
                    str(output_dir),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(50):
                rows = (status_path(batch_dir)).read_text(encoding="utf-8") if status_path(batch_dir).exists() else ""
                if "\tcompleted\t" in rows:
                    break
                import time

                time.sleep(0.1)
            findings = validate_status_file(status_path(batch_dir))
            self.assertFalse([item for item in findings if item.severity == "ERROR"])
            self.assertIn("\tcompleted\t", status_path(batch_dir).read_text(encoding="utf-8"))


class PromptRenderTests(unittest.TestCase):
    def test_render_context_contains_project_docs(self) -> None:
        config = load_config()
        rendered = render_context(config, "cycle")
        self.assertIn("Rendered Agent Context", rendered)
        self.assertIn("agents_policy", rendered)
        self.assertIn("active_agent_mode_contract", rendered)
        self.assertIn("manifest_columns", rendered)

    def test_doctor_rejects_agent_mode_without_contract(self) -> None:
        config = load_config()
        config["modes"] = dict(config["modes"])
        config["modes"]["agent_modes"] = ["missing_contract"]
        config["modes"]["default_agent_mode"] = "missing_contract"
        config["modes"]["agent_mode_contracts"] = {}
        findings = []
        doctor_check_modes(findings, config)
        self.assertTrue([item for item in findings if item.severity == "ERROR" and "missing a contract" in item.message])


class CycleOutcomeTests(unittest.TestCase):
    def test_valid_cycle_outcome(self) -> None:
        config = load_config()
        contract = get_value(config, "modes.agent_mode_contracts.method_exploration")
        payload = {
            "agent_mode": "method_exploration",
            "execution_mode": "manual",
            "cycle_kind": "cycle",
            "summary": "Reduced one uncertainty with a bounded probe.",
            "reads": ["profiles/default/CYCLE_BRIEF.md"],
            "actions": ["smoke test"],
            "artifacts": ["runtime/current_status.md"],
            "evidence_paths": ["profiles/default/CYCLE_BRIEF.md"],
            "mode_details": {
                "research_question": "Can a tiny candidate route provide useful signal?",
                "hypothesis": "A bounded probe will expose whether the route is viable.",
                "candidate_method": "Minimal prototype with one smoke-scale evaluation.",
                "validation_design": "Run one small probe and inspect its completion artifact.",
                "evaluation_signal": "Probe completes and produces interpretable evidence.",
                "decision": "Continue with a narrower follow-up.",
            },
            "success_criterion_met": contract["success_criteria"][0],
            "escalation_criterion_used": "",
            "next_decision": "continue audit with a narrower follow-up",
        }
        findings = []
        check_cycle_outcome_payload(findings, config, payload)
        self.assertFalse([item for item in findings if item.severity == "ERROR"])

    def test_cycle_outcome_requires_success_or_escalation(self) -> None:
        config = load_config()
        payload = {
            "agent_mode": "method_exploration",
            "execution_mode": "manual",
            "cycle_kind": "cycle",
            "summary": "No decision recorded.",
            "reads": ["profiles/default/CYCLE_BRIEF.md"],
            "actions": ["inspect"],
            "artifacts": ["runtime/current_status.md"],
            "evidence_paths": ["profiles/default/CYCLE_BRIEF.md"],
            "mode_details": {
                "research_question": "Can this route work?",
                "hypothesis": "Maybe.",
                "candidate_method": "Probe.",
                "validation_design": "Run it.",
                "evaluation_signal": "Artifact exists.",
                "decision": "Unknown.",
            },
            "success_criterion_met": "",
            "escalation_criterion_used": "",
            "next_decision": "unknown",
        }
        findings = []
        check_cycle_outcome_payload(findings, config, payload)
        self.assertTrue([item for item in findings if item.severity == "ERROR" and "success_criterion_met" in item.message])

    def test_method_exploration_requires_mode_details(self) -> None:
        config = load_config()
        contract = get_value(config, "modes.agent_mode_contracts.method_exploration")
        payload = {
            "agent_mode": "method_exploration",
            "execution_mode": "manual",
            "cycle_kind": "cycle",
            "summary": "Missing method-specific details.",
            "reads": ["profiles/default/CYCLE_BRIEF.md"],
            "actions": ["inspect"],
            "artifacts": ["runtime/current_status.md"],
            "evidence_paths": ["profiles/default/CYCLE_BRIEF.md"],
            "mode_details": {
                "research_question": "Can this route work?"
            },
            "success_criterion_met": contract["success_criteria"][0],
            "escalation_criterion_used": "",
            "next_decision": "continue",
        }
        findings = []
        check_cycle_outcome_payload(findings, config, payload)
        self.assertTrue([item for item in findings if item.severity == "ERROR" and "mode_details.hypothesis" in item.message])


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

    def test_sanitized_profile_config_doctor_has_no_errors(self) -> None:
        env = os.environ.copy()
        env["AGENT_CONFIG"] = str(ROOT / "profiles" / "example-ea-sbm" / "project.example.json")
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
