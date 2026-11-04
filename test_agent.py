"""agent.py testleri. API anahtarı gerektirmez: Groq yerine senaryolu sahte bir client kullanır.

Çalıştırma:  uv run python -m unittest -v test_agent
"""
import json
import unittest
from types import SimpleNamespace as NS

from agent import Config, run_agent


def tool_call(id_, name, args):
    raw = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
    return NS(id=id_, type="function", function=NS(name=name, arguments=raw))


class FakeClient:
    """Sırayla önceden yazılmış cevapları döndürür; aldığı mesajları kaydeder.

    script'in her elemanı ya bir string (son cevap) ya da tool_call listesidir.
    Script bitince hep tool çağırmaya devam eder (max_steps testi için).
    """

    def __init__(self, script):
        self.script = list(script)
        self.requests = []  # her isteğin messages listesi
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(list(kwargs["messages"]))
        step = self.script.pop(0) if self.script else [tool_call("loop", "calculator", {"expression": "1+1"})]
        msg = NS(content=step, tool_calls=None) if isinstance(step, str) else NS(content=None, tool_calls=step)
        return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=10, completion_tokens=5))


KUR = {"query": "dolar kuru"}
KUR_VARIANT = {"query": "DOLAR   kuru "}  # normalize edilince KUR ile aynı
HESAP = {"expression": "2*3"}


class TestAgent(unittest.TestCase):

    def test_direct_answer(self):
        r = run_agent("soru", Config(), FakeClient(["42"]))
        self.assertEqual(r.final_answer, "42")
        self.assertEqual((r.steps, r.requested_calls, r.executed_calls), (1, 0, 0))
        self.assertEqual((r.prompt_tokens, r.completion_tokens), (10, 5))

    def test_first_request_has_system_and_user(self):
        client = FakeClient(["ok"])
        run_agent("görev metni", Config(), client)
        msgs = client.requests[0]
        self.assertEqual([m["role"] for m in msgs], ["system", "user"])
        self.assertEqual(msgs[1]["content"], "görev metni")

    def test_duplicate_counted_in_baseline(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)],
                             [tool_call("b", "web_search", KUR_VARIANT)],
                             "bitti"])
        r = run_agent("soru", Config(mode="baseline"), client)
        self.assertEqual(r.final_answer, "bitti")
        self.assertEqual((r.steps, r.requested_calls, r.executed_calls, r.duplicate_calls), (3, 2, 2, 1))

    def test_cache_skips_execution_but_not_request(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)],
                             [tool_call("b", "web_search", KUR_VARIANT)],
                             "bitti"])
        r = run_agent("soru", Config(mode="cache"), client)
        self.assertEqual((r.requested_calls, r.executed_calls, r.duplicate_calls), (2, 1, 1))
        # cache'ten dönen sonuç modele yine de tool mesajı olarak gitmeli
        last_tool = [m for m in client.requests[2] if m["role"] == "tool"][-1]
        self.assertIn("42,00", last_tool["content"])

    def test_no_cache_outside_cache_mode(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)],
                             [tool_call("b", "web_search", KUR)],
                             "bitti"])
        r = run_agent("soru", Config(mode="memory"), client)
        self.assertEqual(r.executed_calls, 2)

    def test_window_keeps_whole_turns(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)],
                             [tool_call("b", "calculator", HESAP)],
                             "bitti"])
        run_agent("soru", Config(window_turns=1), client)
        msgs = client.requests[2]  # iki turn sonra; pencere sadece sonuncuyu göstermeli
        self.assertEqual([m["role"] for m in msgs], ["system", "user", "assistant", "tool"])
        self.assertEqual(msgs[2]["tool_calls"][0]["id"], "b")
        self.assertEqual(msgs[3]["tool_call_id"], "b")

    def test_memory_survives_window(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)],
                             [tool_call("b", "calculator", HESAP)],
                             "bitti"])
        run_agent("soru", Config(mode="memory", window_turns=1), client)
        self.assertIn("42,00", client.requests[2][0]["content"])  # pencereden düştü ama hafızada duruyor

    def test_no_memory_block_in_baseline(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)], "bitti"])
        run_agent("soru", Config(mode="baseline"), client)
        self.assertNotIn("42,00", client.requests[1][0]["content"])

    def test_parallel_calls_in_one_turn(self):
        client = FakeClient([[tool_call("a", "web_search", KUR), tool_call("b", "calculator", HESAP)],
                             "bitti"])
        r = run_agent("soru", Config(), client)
        self.assertEqual((r.steps, r.requested_calls, r.executed_calls), (2, 2, 2))
        tools = [m for m in client.requests[1] if m["role"] == "tool"]
        self.assertEqual([m["tool_call_id"] for m in tools], ["a", "b"])
        self.assertEqual(len(r.trace), 2)

    def test_bad_arguments_do_not_crash(self):
        for raw in ["{bozuk json", "[1, 2]"]:
            client = FakeClient([[tool_call("a", "calculator", raw)], "bitti"])
            r = run_agent("soru", Config(), client)
            self.assertEqual(r.final_answer, "bitti")
            self.assertEqual((r.requested_calls, r.executed_calls), (1, 0))
            tool_msg = [m for m in client.requests[1] if m["role"] == "tool"][0]
            self.assertIn("Hata", tool_msg["content"])

    def test_max_steps(self):
        r = run_agent("soru", Config(max_steps=4), FakeClient([]))
        self.assertIsNone(r.final_answer)
        self.assertEqual(r.steps, 4)

    def test_state_is_per_task(self):
        client = FakeClient([[tool_call("a", "web_search", KUR)], "bitti",
                             [tool_call("b", "web_search", KUR)], "bitti"])
        run_agent("soru 1", Config(mode="cache"), client)
        r = run_agent("soru 2", Config(mode="cache"), client)
        self.assertEqual((r.executed_calls, r.duplicate_calls), (1, 0))


if __name__ == "__main__":
    unittest.main()
