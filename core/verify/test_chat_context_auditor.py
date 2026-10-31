#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/verify/test_chat_context_auditor.py — Детерміністичні unit-тести для ChatContextAuditor (Kernel v0.9.12).
"""

import sys
sys.dont_write_bytecode = True

import unittest
from core.verify.chat_context_auditor import ChatContextAuditor, build_git_sha_manifest


class TestChatContextAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = ChatContextAuditor(strict=False)

    def test_clean_compliant_session_pass(self):
        records = [
            {"step_index": 1, "source": "SYSTEM", "type": "INFO", "content": "Session init"},
            {"step_index": 2, "source": "MODEL", "type": "ACTION", "content": "telemetry", "tool_calls": [
                {"name": "run_command", "args": {"CommandLine": "python3 core/inspect/phase1_inspect.py --telemetry"}}
            ]},
            {"step_index": 3, "source": "MODEL", "type": "ACTION", "content": "plan", "tool_calls": [
                {"name": "write_to_file", "args": {"TargetFile": "/path/to/implementation_plan.md"}}
            ]},
            {"step_index": 4, "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "+"},
            {"step_index": 5, "source": "MODEL", "type": "ACTION", "content": "edit", "tool_calls": [
                {"name": "write_to_file", "args": {"TargetFile": "/path/to/core/engine/helper.py"}}
            ]},
            {"step_index": 6, "source": "MODEL", "type": "ACTION", "content": "commit", "tool_calls": [
                {"name": "run_command", "args": {"CommandLine": "git commit -m 'feat: helper [verified: antigravity]'"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["violations_count"], 0)
        self.assertIn("Git State Seal Gate (всі модифікації запечатано комітом)", report["passed_checks"])

    def test_git_first_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "ACTION", "content": "blind search", "tool_calls": [
                {"name": "find_by_name", "args": {"Pattern": "*.py"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("GIT_FIRST_GATE", gates)

    def test_telemetry_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "ACTION", "content": "write plan early", "tool_calls": [
                {"name": "write_to_file", "args": {"TargetFile": "/path/to/implementation_plan.md"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("TELEMETRY_GATE", gates)

    def test_approval_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "ACTION", "content": "edit code without approval", "tool_calls": [
                {"name": "replace_file_content", "args": {"TargetFile": "/path/to/core/server.py"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("APPROVAL_GATE", gates)

    def test_zero_inline_eval_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "ACTION", "content": "inline eval", "tool_calls": [
                {"name": "run_command", "args": {"CommandLine": "python3 -c 'print(1)'"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("ZERO_INLINE_EVAL_GATE", gates)

    def test_shell_state_isolation_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "ACTION", "content": "redirect shell", "tool_calls": [
                {"name": "run_command", "args": {"CommandLine": "echo 'x' > .system_generated/bad.txt"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("SHELL_STATE_ISOLATION_GATE", gates)

    def test_secret_isolation_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "ACTION", "content": "cat secret", "tool_calls": [
                {"name": "run_command", "args": {"CommandLine": "cat ~/.gemini/antigravity/.core_master_hmac.secret"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("SECRET_ISOLATION_GATE", gates)

    def test_git_attribution_gate_violation(self):
        records = [
            {"step_index": 1, "source": "MODEL", "type": "AI", "content": "model: qwen2.5-coder:1.5b"},
            {"step_index": 2, "source": "MODEL", "type": "ACTION", "content": "fake commit", "tool_calls": [
                {"name": "run_command", "args": {"CommandLine": "git commit -m 'feat: test [generated: claude-3-opus]'"}}
            ]}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("GIT_ATTRIBUTION_GATE", gates)

    def test_git_state_seal_gate_violation(self):
        """Фаза 5.2: модифікував код, але сесія завершилася без виклику git commit."""
        records = [
            {"step_index": 1, "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "+"},
            {"step_index": 2, "source": "MODEL", "type": "ACTION", "content": "edit", "tool_calls": [
                {"name": "write_to_file", "args": {"TargetFile": "/path/to/core/engine/sync.py"}}
            ]},
            {"step_index": 3, "source": "MODEL", "type": "INFO", "content": "Done without commit"}
        ]
        report = self.auditor.audit_transcript(records, check_live_git=False)
        self.assertEqual(report["status"], "FAIL")
        gates = [v["gate"] for v in report["violations"]]
        self.assertIn("GIT_STATE_SEAL_GATE", gates)

    def test_build_git_sha_manifest(self):
        manifest = build_git_sha_manifest()
        self.assertIsInstance(manifest, dict)


if __name__ == "__main__":
    unittest.main()
