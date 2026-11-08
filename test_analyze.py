"""analyze.py testleri. API anahtarı ve gerçek sonuç dosyası gerektirmez.

Çalıştırma:  uv run python -m unittest -v test_analyze
"""
import unittest

from analyze import TIME, duplicates, fmt, matched, matched_note, seed_means, seed_values, success_table


def row(mode, task_id, seed, requested=1, success=True, error=None, final_answer="cevap"):
    return {"mode": mode, "task_id": task_id, "seed": seed, "requested_calls": requested,
            "duplicate_calls": requested, "success": success, "error": error, "final_answer": final_answer}


class TestAnalyze(unittest.TestCase):

    def test_matched_drops_pair_from_every_mode(self):
        rows = [row("baseline", 8, 0), row("cache", 8, 0, error="400"), row("memory", 8, 0),
                row("baseline", 8, 1), row("cache", 8, 1), row("memory", 8, 1)]
        kept = matched(rows)
        self.assertEqual(len(kept), 3)
        self.assertEqual({r["seed"] for r in kept}, {1})

    def test_matched_note_names_dropped_pairs(self):
        rows = [row("baseline", 8, 0), row("cache", 8, 0, error="400"), row("memory", 8, 0),
                row("baseline", 8, 1), row("cache", 8, 1), row("memory", 8, 1)]
        self.assertIn("görev 8 seed 0", matched_note(rows))
        self.assertIn("her modda 1 koşu kaldı", matched_note(rows))

    def test_matched_note_without_api_error(self):
        rows = [row("baseline", 8, 0), row("cache", 8, 0), row("memory", 8, 0)]
        self.assertEqual(matched_note(rows), "API hatası olmadı, hiçbir koşu çıkarılmadı: her modda 1 koşu var.")

    def test_seed_means_averages_inside_each_seed(self):
        rows = [row("cache", 1, 0, requested=2), row("cache", 2, 0, requested=4),
                row("cache", 1, 1, requested=10), row("memory", 1, 1, requested=99)]
        self.assertEqual(seed_means(rows, "cache", lambda r: r["requested_calls"]), [3, 10])

    def test_time_uses_median_so_one_stall_does_not_dominate(self):
        rows = [row("cache", t, 0) | {"elapsed_s": s} for t, s in [(1, 2), (2, 3), (3, 50000)]]
        self.assertEqual(seed_values(rows, "cache", TIME), [3])

    def test_fmt_uses_sample_std(self):
        self.assertEqual(fmt([1, 2, 3]), "2,00 ± 1,00")
        self.assertEqual(fmt([1, 2, 3], 0), "2 ± 1")

    def test_api_error_counts_as_failure(self):
        rows = [row(m, 1, s) for m in ("baseline", "memory") for s in (0, 1)]
        rows += [row("cache", 1, 0), row("cache", 1, 1, success=False, error="400", final_answer=None)]
        line = next(l for l in success_table(rows).splitlines() if l.startswith("| cache"))
        self.assertEqual(line, "| cache | 50,0 ± 70,7 | 1 / 2 | 0 | 1 |")

    def test_step_limit_is_counted_separately_from_api_error(self):
        rows = [row(m, 1, s) for m in ("cache", "memory") for s in (0, 1)]
        rows += [row("baseline", 1, 0), row("baseline", 1, 1, success=False, final_answer=None)]
        line = next(l for l in success_table(rows).splitlines() if l.startswith("| baseline"))
        self.assertTrue(line.endswith("| 1 | 0 |"), line)

    def test_duplicates_marks_missing_run(self):
        self.assertEqual(duplicates([row("cache", 8, 0, requested=3), row("cache", 8, 1)]), "4")
        self.assertEqual(duplicates([row("cache", 8, 0, requested=3), row("cache", 8, 1, error="400")]), "3*")


if __name__ == "__main__":
    unittest.main()
