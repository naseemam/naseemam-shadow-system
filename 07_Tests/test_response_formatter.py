import importlib.util
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "response_formatter.py")
SPEC = importlib.util.spec_from_file_location("response_formatter", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["response_formatter"] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
ResponseFormatter = MODULE.ResponseFormatter


class ResponseFormatterTests(unittest.TestCase):
    def test_format_text_blocks_internal_labels(self):
        formatter = ResponseFormatter()
        raw = (
            "User request: اشرح الفكرة\n"
            "Context: internal instructions\n"
            "The answer is: عبر وكيل research_agent في /home/runner/work/file.py\n"
            "أكيد، هذه خلاصة واضحة للمستخدم."
        )
        result = formatter.format_text(raw)

        self.assertIn("خلاصة واضحة", result)
        self.assertNotIn("User request", result)
        self.assertNotIn("Context", result)
        self.assertNotIn("The answer is", result)
        self.assertNotIn("research_agent", result)
        self.assertNotIn("/home/runner/work/file.py", result)

    def test_format_payload_sanitizes_reply_and_removes_debug_trace(self):
        formatter = ResponseFormatter()
        payload = {
            "reply": "The answer is: تم التنفيذ.",
            "execution_engine": {"summary": "Debug: updated /tmp/example.py"},
            "executive_brain": {"executive_message": "Context: test"},
            "debug_trace": {"step": "internal"},
        }

        result = formatter.format_payload(payload)

        self.assertEqual(result["reply"], "تم التنفيذ.")
        self.assertEqual(result["message"], "تم التنفيذ.")
        self.assertEqual(result["assistant"], "أمير")
        self.assertNotIn("execution_engine", result)
        self.assertNotIn("executive_brain", result)
        self.assertNotIn("debug_trace", result)

    def test_format_payload_prefers_structured_agent_data(self):
        formatter = ResponseFormatter()
        payload = {
            "reply": "سأجيب باستخدام identity_agent من المصدر الداخلي",
            "agent_brain_payload": {
                "response_data": {
                    "intent": "identity",
                    "facts": {
                        "subject": "ameer",
                    },
                },
            },
        }

        result = formatter.format_payload(payload)

        self.assertEqual(
            result["reply"],
            "أنا أمير، شريكك التنفيذي. أفكر معك، أخطط، أتابع، وأقدم الرد النهائي باسمي.",
        )

    def test_format_payload_fails_closed_when_governed_reply_is_unsanitizable(self):
        formatter = ResponseFormatter()
        payload = {
            "reply": '{"debug_trace":{"tool_calls":["file.create"]}}',
            "agent_brain_payload": {
                "response_data": {
                    "intent": "identity",
                    "facts": {"subject": "ameer"},
                },
            },
        }
        result = formatter.format_payload(payload)
        self.assertEqual(result["reply"], "أنا معك.")
        self.assertEqual(result["message"], "أنا معك.")

    def test_format_text_blocks_json_like_internal_payload(self):
        formatter = ResponseFormatter()
        raw = '{"selected_agent":"identity_agent","execution_engine":{"tool_calls":["file.create"]}}'
        result = formatter.format_text(raw)
        self.assertEqual(result, "أنا معك.")

    def test_format_text_drops_source_file_and_prompt_labels(self):
        formatter = ResponseFormatter()
        raw = (
            "Source: 04_Memory/Founder.md\n"
            "File: /home/runner/work/app.py\n"
            "Prompt: internal template\n"
            "الرد للمستخدم: نسيم هي المؤسسة."
        )
        result = formatter.format_text(raw)
        self.assertEqual(result, "الرد للمستخدم: نسيم هي المؤسسة.")

    def test_format_text_blocks_repeated_provider_instruction_echo(self):
        formatter = ResponseFormatter()
        raw = " ".join(["The user is asked to provide a single answer in Arabic."] * 10)
        result = formatter.format_text(raw)
        self.assertEqual(result, "أنا معك.")

    def test_format_payload_always_returns_public_contract_only(self):
        formatter = ResponseFormatter()
        payload = {
            "reply": "مرحبا",
            "routing": {"agent": "identity_agent"},
            "execution_engine": {"tool_calls": ["file.create"]},
            "debug_trace": {"step": "router"},
            "selected_agent": "identity_agent",
        }
        result = formatter.format_payload(payload)
        self.assertEqual(set(result.keys()), {"reply", "message", "assistant"})

    def test_format_payload_non_dict_keeps_public_contract(self):
        formatter = ResponseFormatter()
        result = formatter.format_payload(None)
        self.assertEqual(set(result.keys()), {"reply", "message", "assistant"})
        self.assertEqual(result["assistant"], "أمير")


if __name__ == "__main__":
    unittest.main()
