"""Tool kullanan agent döngüsü.

Akış: model bir tool seçer -> tool çalışır -> sonuç modele geri verilir -> model devam eder,
ta ki tool çağırmadan son cevabı verene ya da max_steps dolana kadar.

Terimler:
  turn : bir assistant mesajı + onun tool_calls'larına verilen tool mesajları (bir liste).
  step : modele yapılan bir istek (chat.completions.create çağrısı).
"""
import json
import time
from dataclasses import dataclass, field

from tools import TOOL_SCHEMAS, TOOLS, call_key

SYSTEM_PROMPT = (
    "Sen Kuzey Kitabevi çalışanlarına yardım eden, tool kullanan bir asistansın. "
    "Gereken bilgileri tool'larla bul, hesaplamaları calculator ile yap. "
    "Bilgi tool'larda yoksa uydurma, bulunamadığını söyle. "
    "İşin bitince son cevabı kısa yaz ve sayısal sonucu açıkça belirt."
)


@dataclass
class Config:
    mode: str = "baseline"          # "baseline" | "cache" | "memory"
    window_turns: int = 2           # modelin gördüğü son turn sayısı (hafıza penceresi)
    max_steps: int = 10
    model: str = "openai/gpt-oss-120b"
    temperature: float = 0.6


@dataclass
class RunResult:
    final_answer: str | None = None  # max_steps dolarsa None kalır
    steps: int = 0
    requested_calls: int = 0         # modelin istediği tool call sayısı
    executed_calls: int = 0          # gerçekten çalışan tool sayısı (cache isabetleri hariç)
    duplicate_calls: int = 0         # bu görevde daha önce görülmüş call_key ile gelen çağrılar
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_s: float = 0.0
    trace: list = field(default_factory=list)  # her tool çağrısı için bir dict


# ---------------------------------------------------------------- hazır yardımcılar

def execute_tool(name: str, args: dict) -> str:
    """Tool'u çalıştırır. Bilinmeyen tool veya yanlış argüman programı çökertmez, hata metni döner."""
    if name not in TOOLS:
        return f"Hata: '{name}' adında bir tool yok."
    try:
        return TOOLS[name](**args)
    except TypeError as e:
        return f"Hata: yanlış argüman ({e})"


def assistant_to_dict(msg) -> dict:
    """Groq'un döndürdüğü mesaj nesnesini, bir sonraki istekte geri gönderilebilecek dict'e çevirir."""
    d = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        d["tool_calls"] = [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
    return d


# ---------------------------------------------------------------- agent

def build_messages(task: str, turns: list[list[dict]], memory: dict[str, str], config: Config) -> list[dict]:
    """Modele gönderilecek mesaj listesini kurar: system, user ve son window_turns kadar turn.

    Pencere mesaj sayısına göre değil turn sayısına göre kesilir. Bir "tool" mesajı, onu üreten
    assistant mesajından ayrı düşerse API 400 hatası verir; turn'ü bütün almak bunu engeller.

    memory: {call_key: sonuç}. Sadece "memory" modunda system mesajına eklenir.
    """
    system = SYSTEM_PROMPT
    if config.mode == "memory" and memory:
        system += "\n\nBu görevde daha önce aldığın tool sonuçları:\n"
        for key, output in memory.items():
            system += f"- {key} -> {output}\n"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},  # pencere ne olursa olsun görev her zaman gider
    ]
    # turns[-0:] listenin tamamını verir, bu yüzden 0 ayrıca ele alınır.
    for turn in turns[-config.window_turns:] if config.window_turns else []:
        messages.extend(turn)
    return messages


def run_agent(task: str, config: Config, client, seed: int | None = None) -> RunResult:
    """Tek bir görevi baştan sona çalıştırır ve metrikleri döndürür.

    seen, cache ve memory burada oluşturulur: bir görevin durumu sonrakine sızmamalı.
    """
    result = RunResult()
    turns, seen, cache, memory = [], set(), {}, {}
    start = time.perf_counter()

    for _ in range(config.max_steps):
        resp = client.chat.completions.create(
            model=config.model,
            messages=build_messages(task, turns, memory, config),
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=config.temperature,
            seed=seed,
        )
        result.steps += 1
        result.prompt_tokens += resp.usage.prompt_tokens
        result.completion_tokens += resp.usage.completion_tokens

        msg = resp.choices[0].message
        if not msg.tool_calls:  # tool istemediyse son cevabı vermiştir
            result.final_answer = msg.content
            break

        turn = [assistant_to_dict(msg)]
        for tc in msg.tool_calls:
            # requested burada sayılır: model çağrıyı istedi, cache bunu geri alamaz.
            result.requested_calls += 1
            name = tc.function.name

            try:
                args = json.loads(tc.function.arguments)
                if not isinstance(args, dict):
                    raise ValueError("argümanlar bir JSON nesnesi olmalı")
            except ValueError as e:  # JSONDecodeError da ValueError'dır
                # Her tool_call_id cevap bekler, yoksa API sonraki istekte hata verir.
                turn.append({"role": "tool", "tool_call_id": tc.id, "content": f"Hata: {e}"})
                continue

            key = call_key(name, args)
            duplicate = key in seen
            seen.add(key)
            result.duplicate_calls += duplicate

            cache_hit = config.mode == "cache" and key in cache
            if cache_hit:
                output = cache[key]
            else:
                output = execute_tool(name, args)
                result.executed_calls += 1
                cache[key] = output
            memory[key] = output

            turn.append({"role": "tool", "tool_call_id": tc.id, "content": output})
            result.trace.append({"tool": name, "args": args, "duplicate": duplicate,
                                 "cache_hit": cache_hit, "output": output})
        turns.append(turn)

    result.elapsed_s = time.perf_counter() - start
    return result


# ---------------------------------------------------------------- deneme

if __name__ == "__main__":
    import os

    from dotenv import load_dotenv
    from groq import Groq

    load_dotenv()
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    cfg = Config(model=os.getenv("GROQ_MODEL", Config.model))
    r = run_agent("Kadıköy şubesi Ekim 2026'da toplam kaç kitap sattı?", cfg, client, seed=0)
    print("Cevap:", r.final_answer)
    print(f"steps={r.steps} requested={r.requested_calls} executed={r.executed_calls} "
          f"duplicate={r.duplicate_calls} tokens={r.prompt_tokens}+{r.completion_tokens} süre={r.elapsed_s:.2f}s")
    for t in r.trace:
        print(" ", t)
