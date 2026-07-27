from __future__ import annotations

import json
import os
import shutil
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
from scripts.doctor import check_modes as doctor_check_modes, check_paths as doctor_check_paths
from scripts.evaluate_behavioral_acceptance import evaluate as evaluate_behavioral_acceptance
from scripts.finalize_cycle_outcome import finalize_cycle_outcome
from scripts.list_active_jobs import collect_jobs, parse_elapsed, parse_ps_line
from scripts.research_history import history_attention, load_recent_outcomes, render_history
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


class BootstrapLayoutTests(unittest.TestCase):
    def test_init_runtime_ledgers_creates_neutral_files_without_overwriting(self) -> None:
        import scripts.bootstrap_layout as bootstrap_layout

        with tempfile.TemporaryDirectory() as tmpdir:
            control_root = Path(tmpdir) / "control"
            (control_root / "runtime").mkdir(parents=True)
            original_root = bootstrap_layout.root
            bootstrap_layout.root = lambda: control_root
            try:
                bootstrap_layout.init_runtime_ledgers()
                self.assertIn("# Current Status", (control_root / "runtime" / "current_status.md").read_text(encoding="utf-8"))
                self.assertIn("# Research Lanes", (control_root / "runtime" / "research_lanes.md").read_text(encoding="utf-8"))
                journal = control_root / "runtime" / "agent_journal.md"
                self.assertIn("# Agent Journal", journal.read_text(encoding="utf-8"))
                journal.write_text("existing project chronology\n", encoding="utf-8")
                bootstrap_layout.init_runtime_ledgers()
            finally:
                bootstrap_layout.root = original_root

            self.assertEqual((control_root / "runtime" / "agent_journal.md").read_text(encoding="utf-8"), "existing project chronology\n")

    def test_link_map_refuses_existing_regular_file(self) -> None:
        import scripts.bootstrap_layout as bootstrap_layout

        with tempfile.TemporaryDirectory() as tmpdir:
            control_root = Path(tmpdir) / "control"
            target = Path(tmpdir) / "target"
            control_root.mkdir()
            target.mkdir()
            parent = control_root / "workspaces"
            parent.mkdir()
            existing = parent / "main"
            existing.write_text("do not delete", encoding="utf-8")

            original_root = bootstrap_layout.root
            bootstrap_layout.root = lambda: control_root
            try:
                with self.assertRaisesRegex(RuntimeError, "refusing to replace non-symlink"):
                    bootstrap_layout.link_map("workspaces", "workspaces", {"workspaces": {"main": {"path": str(target)}}})
            finally:
                bootstrap_layout.root = original_root

            self.assertEqual(existing.read_text(encoding="utf-8"), "do not delete")

    def test_link_map_replaces_existing_symlink(self) -> None:
        import scripts.bootstrap_layout as bootstrap_layout

        with tempfile.TemporaryDirectory() as tmpdir:
            control_root = Path(tmpdir) / "control"
            old_target = Path(tmpdir) / "old"
            new_target = Path(tmpdir) / "new"
            control_root.mkdir()
            old_target.mkdir()
            new_target.mkdir()
            parent = control_root / "workspaces"
            parent.mkdir()
            link = parent / "main"
            os.symlink(old_target, link)

            original_root = bootstrap_layout.root
            bootstrap_layout.root = lambda: control_root
            try:
                bootstrap_layout.link_map("workspaces", "workspaces", {"workspaces": {"main": {"path": str(new_target)}}})
            finally:
                bootstrap_layout.root = original_root

            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), str(new_target))

    def test_link_map_rejects_unsafe_link_name(self) -> None:
        import scripts.bootstrap_layout as bootstrap_layout

        with tempfile.TemporaryDirectory() as tmpdir:
            control_root = Path(tmpdir) / "control"
            target = Path(tmpdir) / "target"
            control_root.mkdir()
            target.mkdir()

            original_root = bootstrap_layout.root
            bootstrap_layout.root = lambda: control_root
            try:
                with self.assertRaisesRegex(ValueError, "unsafe workspaces link name"):
                    bootstrap_layout.link_map("workspaces", "workspaces", {"workspaces": {"../escape": {"path": str(target)}}})
            finally:
                bootstrap_layout.root = original_root


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


class ResearchHistoryTests(unittest.TestCase):
    def test_history_is_bounded_and_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_dir = Path(tmpdir)
            old = {"agent_mode": "method_exploration", "cycle_kind": "cycle", "summary": "old", "evidence_records": [], "action_records": [], "next_decision": "old decision"}
            new = {"agent_mode": "audit_validation", "cycle_kind": "cycle", "summary": "new", "evidence_records": [], "action_records": [], "next_decision": "new decision"}
            (archive_dir / "20260727_100000.json").write_text(json.dumps(old), encoding="utf-8")
            (archive_dir / "20260727_110000.json").write_text(json.dumps(new), encoding="utf-8")

            outcomes, notices = load_recent_outcomes(archive_dir, limit=1)
            rendered = render_history(outcomes, notices, "audit_validation")
            self.assertEqual([item[0] for item in outcomes], ["20260727_110000"])
            self.assertIn("new decision", rendered)
            self.assertNotIn("old decision", rendered)

    def test_history_attention_surfaces_mode_mismatch_and_missing_evidence(self) -> None:
        outcomes = [
            (
                "cycle-1",
                {
                    "agent_mode": "method_exploration",
                    "evidence_records": [{"id": "missing", "state": "observed", "path": "runtime/missing-proof.json"}],
                    "action_records": [{"id": "probe", "state": "running"}],
                },
            )
        ]
        messages = history_attention(outcomes, "audit_validation")
        self.assertTrue(any("current AGENT_MODE" in message for message in messages))
        self.assertTrue(any("unresolved historical actions" in message for message in messages))
        self.assertTrue(any("no longer present" in message for message in messages))


class BehavioralAcceptanceTests(unittest.TestCase):
    def test_acceptance_evaluator_requires_observed_decision_evidence(self) -> None:
        expectations = {
            "expected_mode": "method_exploration",
            "required_observed_paths": ["profiles/default/CYCLE_BRIEF.md"],
            "decision_requires_observed": True,
            "required_action_states": ["planned"],
        }
        outcome = {
            "agent_mode": "method_exploration",
            "evidence_records": [{"id": "brief", "state": "observed", "path": "profiles/default/CYCLE_BRIEF.md"}],
            "decision_evidence_ids": ["brief"],
            "action_records": [{"id": "probe", "state": "planned"}],
        }
        self.assertFalse([item for item in evaluate_behavioral_acceptance(expectations, outcome) if item.severity == "ERROR"])

        outcome["evidence_records"][0]["state"] = "planned"
        findings = evaluate_behavioral_acceptance(expectations, outcome)
        self.assertTrue([item for item in findings if item.severity == "ERROR" and "not supported by observed" in item.message])


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

    def test_doctor_warns_on_ambiguous_or_writable_originals(self) -> None:
        findings = []
        doctor_check_paths(
            findings,
            {
                "workspaces": {"legacy": "/tmp/workspace"},
                "originals": {
                    "implicit": {"path": "/tmp/original"},
                    "mutable": {"path": "/tmp/original-copy", "writable": True},
                },
            },
        )
        messages = [item.message for item in findings if item.severity == "WARN"]
        self.assertTrue(any("legacy string path" in message for message in messages))
        self.assertTrue(any("no writable declaration" in message for message in messages))
        self.assertTrue(any("marked writable" in message for message in messages))


class CycleOutcomeTests(unittest.TestCase):
    def lineage(self) -> dict:
        return {
            "evidence_records": [
                {
                    "id": "brief",
                    "state": "observed",
                    "path": "profiles/default/CYCLE_BRIEF.md",
                    "summary": "The project brief defines the bounded cycle shape.",
                    "impact": "It bounds the proposed probe and required state updates.",
                }
            ],
            "action_records": [
                {
                    "id": "inspect-brief",
                    "state": "completed",
                    "description": "Read the cycle brief before selecting a probe.",
                    "rationale": "The brief provides the available local context.",
                    "evidence_ids": ["brief"],
                }
            ],
            "decision_evidence_ids": ["brief"],
            "mode_transition": None,
        }

    def valid_payload(self) -> dict:
        config = load_config()
        contract = get_value(config, "modes.agent_mode_contracts.method_exploration")
        return {
            "agent_mode": "method_exploration",
            "execution_mode": "manual",
            "cycle_kind": "cycle",
            "summary": "Reduced one uncertainty with a bounded probe.",
            "reads": ["profiles/default/CYCLE_BRIEF.md"],
            "actions": ["smoke test"],
            "artifacts": ["runtime/current_status.md"],
            "evidence_paths": ["profiles/default/CYCLE_BRIEF.md"],
            **self.lineage(),
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
            **self.lineage(),
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

    def test_observed_evidence_must_exist(self) -> None:
        config = load_config()
        payload = self.valid_payload()
        payload["evidence_records"][0]["path"] = "runtime/does-not-exist.json"
        findings = []
        check_cycle_outcome_payload(findings, config, payload)
        self.assertTrue([item for item in findings if item.severity == "ERROR" and "observed evidence path" in item.message])

    def test_mode_transition_must_match_the_outcome_mode(self) -> None:
        config = load_config()
        payload = self.valid_payload()
        payload["mode_transition"] = {
            "from": "method_exploration",
            "to": "audit_validation",
            "reason": "The current uncertainty needs an audit.",
            "evidence_ids": ["brief"],
        }
        findings = []
        check_cycle_outcome_payload(findings, config, payload)
        self.assertTrue([item for item in findings if item.severity == "ERROR" and "mode_transition.to must match" in item.message])

    def test_finalize_archives_valid_outcome_without_overwriting_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "pending.json"
            archive_dir = Path(tmpdir) / "history"
            latest = Path(tmpdir) / "latest.json"
            source.write_text(json.dumps(self.valid_payload()), encoding="utf-8")

            findings = finalize_cycle_outcome(source, archive_dir, latest, "cycle-001")
            self.assertFalse([item for item in findings if item.severity == "ERROR"])
            self.assertEqual(json.loads((archive_dir / "cycle-001.json").read_text(encoding="utf-8")), self.valid_payload())
            self.assertEqual(json.loads(latest.read_text(encoding="utf-8")), self.valid_payload())

            duplicate = finalize_cycle_outcome(source, archive_dir, latest, "cycle-001")
            self.assertTrue([item for item in duplicate if item.severity == "ERROR" and "refusing to overwrite" in item.message])

    def test_finalize_rejects_missing_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            findings = finalize_cycle_outcome(
                Path(tmpdir) / "missing.json",
                Path(tmpdir) / "history",
                Path(tmpdir) / "latest.json",
                "cycle-002",
            )
            self.assertTrue([item for item in findings if item.severity == "ERROR"])

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


class RunnerOutcomeBoundaryTests(unittest.TestCase):
    def test_runner_requires_a_pending_outcome_before_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            control_root = Path(tmpdir) / "control"
            shutil.copytree(
                ROOT,
                control_root,
                ignore=shutil.ignore_patterns(".git", "runtime", "logs", "__pycache__", "*.pyc", ".codex-home"),
            )
            fake_planner = control_root / "tests" / "fixtures" / "fake_successful_planner.sh"
            fake_planner.chmod(0o755)
            env = os.environ.copy()
            env["AGENT_CONFIG"] = str(control_root / "tests" / "fixtures" / "missing_outcome_project.json")
            proc = subprocess.run(
                ["bash", str(control_root / "scripts" / "run_codex_cycle.sh")],
                cwd=control_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(proc.returncode, 65, proc.stdout + proc.stderr)
            self.assertTrue((control_root / "runtime" / "REVIEW_REQUIRED").exists())
            self.assertFalse((control_root / "runtime" / "last_cycle_outcome.json").exists())


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
