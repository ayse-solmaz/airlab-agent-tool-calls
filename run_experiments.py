"""Görevleri her konfigürasyonda koşar ve sonuçları JSONL dosyasına yazar.

Çalıştırma:  uv run python run_experiments.py
Pilot:       uv run python run_experiments.py --modes baseline --tasks 8 9 --seeds 0 --out results/pilot.jsonl

Yarıda kesilirse aynı komutla devam eder: dosyada olan koşular atlanır.
"""
import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import groq
from dotenv import load_dotenv

from agent import Config, run_agent
from evaluate import check_answer
from tasks import TASKS

MODES = ["baseline", "cache", "memory"]
SEEDS = [0, 1]  # plan 3 seed idi, nedeni DESIGN.md bölüm 11
MAX_WAIT_S = 1800  # bundan uzun bekleme istenirse koşu durur, sonra kaldığı yerden devam edilir
MAX_RETRIES = 120  # bağlantı kopukken 30 sn arayla yaklaşık 1 saat dener
CONNECTION_WAIT_S = 30


class QuotaExhausted(Exception):
    """Limit kısa sürede açılmayacak; koşu durur, sonra kaldığı yerden devam edilir."""


class RetryingClient:
    """Rate limit gelince bekleyip tekrar dener. Beklenen süreyi slept_s'de tutar:
    bu süre agent'ın süresi değildir, ölçümden çıkarılır. Başarısız denemenin kendi süresi
    de buna dahildir: bağlantı saatlerce asılı kalıp koparsa o süre agent'a yazılmaz."""

    def __init__(self, client, sleep=time.sleep, clock=time.perf_counter):
        self._client = client
        self._sleep = sleep
        self._clock = clock
        self.slept_s = 0.0

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def _pause(self, seconds: float) -> None:
        # Gerçek geçen süre tutulur: bilgisayar beklerken uyursa o süre de agent'a yazılmaz.
        start = self._clock()
        self._sleep(seconds)
        self.slept_s += self._clock() - start

    def create(self, **kwargs):
        for _ in range(MAX_RETRIES):
            start = self._clock()
            try:
                return self._client.chat.completions.create(**kwargs)
            except groq.RateLimitError as e:
                self.slept_s += self._clock() - start
                wait = float(e.response.headers.get("retry-after", 10))
                if wait > MAX_WAIT_S:
                    raise QuotaExhausted(f"{wait:.0f} sn beklemek gerekiyor") from e
                self._pause(wait)
            except groq.APIConnectionError:  # kısa ağ kopması: koşu kaybolmasın
                self.slept_s += self._clock() - start
                self._pause(CONNECTION_WAIT_S)
        raise QuotaExhausted(f"{MAX_RETRIES} denemede de cevap alınamadı")


def load_done(path: Path) -> set[tuple]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return {(r["mode"], r["task_id"], r["seed"]) for r in rows}


def run_one(task: dict, config: Config, client: RetryingClient, seed: int) -> dict:
    row = {"mode": config.mode, "task_id": task["id"], "seed": seed, "model": config.model,
           "window_turns": config.window_turns, "max_steps": config.max_steps,
           "temperature": config.temperature, "error": None}
    client.slept_s = 0.0
    try:
        result = run_agent(task["soru"], config, client, seed=seed)
    except groq.APIStatusError as e:
        if isinstance(e, groq.RateLimitError):
            raise
        # Ör. modelin bozuk tool call'u yüzünden 400. Koşu başarısız sayılır, deney durmaz.
        row.update(error=f"{e.status_code}: {e.message}"[:300], success=False)
        return row
    row.update(asdict(result))
    row["elapsed_s"] = max(0.0, result.elapsed_s - client.slept_s)
    row["success"] = check_answer(task["beklenen"], result.final_answer)
    return row


def run_all(client, path: Path, modes, task_ids, seeds, model, window_turns, temperature,
            max_steps=Config.max_steps) -> int:
    """Koşulmamış kombinasyonları koşar, koşulan sayısını döndürür."""
    path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(path)
    tasks = [t for t in TASKS if t["id"] in task_ids]
    count = 0
    # Modlar en içte: kota yarıda biterse elimizde her mod için eşit sayıda koşu olur.
    with path.open("a", encoding="utf-8") as f:
        for seed in seeds:
            for task in tasks:
                for mode in modes:
                    if (mode, task["id"], seed) in done:
                        continue
                    config = Config(mode=mode, window_turns=window_turns, max_steps=max_steps,
                                    model=model, temperature=temperature)
                    row = run_one(task, config, client, seed)
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    count += 1
                    print(f"seed={seed} görev={task['id']} mod={mode} başarı={row['success']} "
                          f"istenen={row.get('requested_calls')} çalışan={row.get('executed_calls')} "
                          f"tekrar={row.get('duplicate_calls')} hata={row['error']}")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="+", default=MODES, choices=MODES)
    parser.add_argument("--tasks", nargs="+", type=int, default=[t["id"] for t in TASKS])
    parser.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    parser.add_argument("--window", type=int, default=Config.window_turns)
    parser.add_argument("--max-steps", type=int, default=Config.max_steps)
    parser.add_argument("--temperature", type=float, default=Config.temperature)
    parser.add_argument("--out", type=Path, default=Path("results/results_v3.jsonl"))
    args = parser.parse_args()

    load_dotenv()
    model = os.getenv("GROQ_MODEL", Config.model)
    client = RetryingClient(groq.Groq(api_key=os.environ["GROQ_API_KEY"], max_retries=0))
    try:
        count = run_all(client, args.out, args.modes, args.tasks, args.seeds, model, args.window,
                        args.temperature, args.max_steps)
    except QuotaExhausted as e:
        print(f"Kota doldu ({e}). Sonuçlar kaydedildi, sonra aynı komutla devam et.")
        return
    print(f"Bitti: {count} koşu eklendi -> {args.out}")


if __name__ == "__main__":
    main()
