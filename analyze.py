"""results/results_v3.jsonl dosyasından tabloları ve grafiği üretir. API çağrısı yapmaz.

Çalıştırma:  uv run python analyze.py
Çıktı:       results/summary.md, results/modlar.png

Önce her seed için ortalama alınır, sonra seed ortalamalarının ortalaması ± std'si
raporlanır. Std örneklem std'sidir (n-1'e bölünür), çünkü seed'ler bir örneklemdir.
Süre için seed içinde medyan alınır, nedeni seed_values'ta.
"""
import json
from pathlib import Path
from statistics import mean, median, stdev

import matplotlib

matplotlib.use("Agg")  # ekran açmadan dosyaya çizer
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from tasks import TASKS

MODES = ["baseline", "cache", "memory"]
RESULTS = Path("results/results_v3.jsonl")  # ana sonuç; nedeni DESIGN.md'de
SUMMARY = Path("results/summary.md")
FIGURE = Path("results/modlar.png")
TIME = "Süre medyanı (sn)"

# Tablo sütunu -> koşu satırından değeri okuyan fonksiyon
METRICS = {
    "İstenen çağrı": lambda r: r["requested_calls"],
    "Çalışan çağrı": lambda r: r["executed_calls"],
    "Tekrar çağrı": lambda r: r["duplicate_calls"],
    "Adım": lambda r: r["steps"],
    "Token": lambda r: r["prompt_tokens"] + r["completion_tokens"],
    TIME: lambda r: r["elapsed_s"],
}

COLORS = {"İstenen çağrı": "#2a78d6", "Çalışan çağrı": "#eb6834", "Tekrar çağrı": "#1baf7a"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def matched(rows: list[dict]) -> list[dict]:
    """API hatası olan (görev, seed) çiftlerini bütün modlardan çıkarır.

    Hatalı koşunun çağrı sayıları kayıtlı değil. Sadece o koşuyu atmak, en uzun görevleri
    tek bir moddan silip o modu olduğundan iyi gösterirdi. Çifti her moddan çıkarınca
    modlar aynı görevler üzerinden karşılaştırılır.
    """
    bad = {(r["task_id"], r["seed"]) for r in rows if r["error"]}
    return [r for r in rows if (r["task_id"], r["seed"]) not in bad]


def seed_means(rows: list[dict], mode: str, value, agg=mean) -> list[float]:
    """Bir mod için her seed'in özetini döndürür (seed sırasıyla). Varsayılan özet ortalamadır."""
    seeds = sorted({r["seed"] for r in rows})
    return [agg([value(r) for r in rows if r["mode"] == mode and r["seed"] == s]) for s in seeds]


def seed_values(rows: list[dict], mode: str, name: str) -> list[float]:
    # Süre için medyan: ilk koşuda birkaç koşu agent dışı bir duraklamayla şişmişti (en uzunu
    # 4 adımda 56.445 sn). Ortalama böyle tek bir koşuya bağlı kalır. Ham süreler dosyada duruyor.
    return seed_means(rows, mode, METRICS[name], median if name == TIME else mean)


def fmt(values: list[float], digits: int = 2) -> str:
    text = f"{mean(values):.{digits}f} ± {stdev(values):.{digits}f}"
    return text.replace(".", ",")


def table(header: list[str], body: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in body]
    return "\n".join(lines)


def success_table(rows: list[dict]) -> str:
    """Bütün koşular. API hatası başarısız sayılır: görev tamamlanmadı."""
    body = []
    for mode in MODES:
        group = [r for r in rows if r["mode"] == mode]
        step_limit = sum(not r["error"] and not r["final_answer"] for r in group)
        body.append([mode, fmt(seed_means(rows, mode, lambda r: 100 * r["success"]), 1),
                     f"{sum(r['success'] for r in group)} / {len(group)}",
                     step_limit, sum(bool(r["error"]) for r in group)])
    return table(["Mod", "Başarı oranı (%)", "Başarılı koşu", "Adım sınırına takılan", "API hatası"], body)


def metric_table(rows: list[dict]) -> str:
    body = [[mode] + [fmt(seed_values(rows, mode, name), 0 if name == "Token" else 2)
                      for name in METRICS] for mode in MODES]
    return table(["Mod"] + list(METRICS), body)


def change_table(rows: list[dict]) -> str:
    """Baseline'a göre yüzde değişim. Eksi, azalma demektir."""
    body = []
    for mode in MODES[1:]:
        cells = []
        for name in METRICS:
            base = mean(seed_values(rows, "baseline", name))
            cells.append(f"{100 * (mean(seed_values(rows, mode, name)) - base) / base:+.1f}".replace(".", ","))
        body.append([mode] + cells)
    return table(["Mod"] + list(METRICS), body)


def duplicates(group: list[dict]) -> str:
    """Tekrar toplamı. Yıldız, hatalı koşunun toplamda olmadığını gösterir."""
    ok = [r for r in group if not r["error"]]
    total = str(sum(r["duplicate_calls"] for r in ok))
    return total if len(ok) == len(group) else total + "*"


def task_table(rows: list[dict]) -> str:
    body = []
    for task in TASKS:
        groups = [[r for r in rows if r["mode"] == m and r["task_id"] == task["id"]] for m in MODES]
        body.append([task["id"], "evet" if task["tekrar"] else "hayır"]
                    + [f"{sum(r['success'] for r in g)} / {len(g)}" for g in groups]
                    + [duplicates(g) for g in groups])
    header = ["Görev", "Tekrar tetikler"] + [f"{m} başarı" for m in MODES] + [f"{m} tekrar" for m in MODES]
    return table(header, body)


def matched_note(rows: list[dict]) -> str:
    """Eşleştirilmiş tabloların açıklaması. API hatası yoksa hiçbir koşu çıkarılmaz."""
    per_mode = len(matched(rows)) // len(MODES)
    dropped = ", ".join(f"görev {r['task_id']} seed {r['seed']}" for r in rows if r["error"])
    if not dropped:
        return f"API hatası olmadı, hiçbir koşu çıkarılmadı: her modda {per_mode} koşu var."
    return (f"API hatası olan görev-seed çiftleri ({dropped}) üç moddan da çıkarıldı, her modda {per_mode} "
            "koşu kaldı. Bu çiftlerdeki çağrılar aşağıdaki ortalamalarda yoktur, toplamlar görev tablosundadır.")


def summary(rows: list[dict]) -> str:
    same = matched(rows)
    repeat_ids = {t["id"] for t in TASKS if t["tekrar"]}
    repeat = [r for r in same if r["task_id"] in repeat_ids]
    other = [r for r in same if r["task_id"] not in repeat_ids]
    return "\n\n".join([
        "# Sonuç tabloları",
        f"`analyze.py` ile üretildi. Değerler {len({r['seed'] for r in rows})} seed üzerinden "
        "ortalama ± örneklem std'sidir.",
        "## Başarı (bütün koşular)",
        "API hatası başarısız sayılır.",
        success_table(rows),
        "## Görev başına ortalamalar (eşleştirilmiş koşular)",
        matched_note(rows) + " Süre, seed içi medyandır.",
        metric_table(same),
        "## Baseline'a göre değişim (%)",
        change_table(same),
        "## Sadece tekrar tetikleyen görevler (eşleştirilmiş)",
        metric_table(repeat),
        "## Diğer görevler (eşleştirilmiş)",
        metric_table(other),
        "## Görev bazında sonuçlar (bütün koşular)",
        "Tekrar sütunları bütün seed'lerin toplamıdır. Yıldız: API hatası veren koşu toplamda yok.",
        task_table(rows),
    ]) + "\n"


def style(ax, title: str) -> None:
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.set_facecolor(SURFACE)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0)


def plot(rows: list[dict], path: Path) -> None:
    same = matched(rows)
    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4.4), width_ratios=[1, 2], facecolor=SURFACE)
    bar_error = {"ecolor": INK, "capsize": 3, "elinewidth": 1}

    # Sol: başarı oranı, bütün koşular
    values = [seed_means(rows, m, lambda r: 100 * r["success"]) for m in MODES]
    heights = [mean(v) for v in values]
    bars = left.bar(MODES, heights, yerr=[stdev(v) for v in values], width=0.55, color=MUTED, error_kw=bar_error)
    left.bar_label(bars, labels=[f"%{h:.1f}".replace(".", ",") for h in heights], label_type="center",
                   color="white", fontsize=10)
    left.set_ylim(0, 110)
    left.set_yticks(range(0, 101, 25))
    style(left, "Başarı oranı (%)")

    # Sağ: çağrı sayıları, eşleştirilmiş koşular. Aynı ölçek olduğu için tek eksen yeter.
    width = 0.26
    for i, name in enumerate(COLORS):
        values = [seed_means(same, m, METRICS[name]) for m in MODES]
        heights = [mean(v) for v in values]
        x = [m + (i - 1) * (width + 0.01) for m in range(len(MODES))]
        bars = right.bar(x, heights, yerr=[stdev(v) for v in values], width=width, color=COLORS[name],
                         label=name, error_kw=bar_error)
        if name == "Tekrar çağrı":  # hedef metrik; memory'de çubuk görünmediği için sayı şart
            for bar, value, height in zip(bars, values, heights):
                right.text(bar.get_x() + width / 2, height + stdev(value) + 0.12,
                           f"{height:.2f}".replace(".", ","), ha="center", color=INK, fontsize=10)
    right.set_xticks(range(len(MODES)), MODES)
    right.yaxis.set_major_locator(MaxNLocator(integer=True))
    right.legend(frameon=False, ncols=3, loc="upper right", labelcolor=MUTED, fontsize=9)
    right.set_ylim(0, right.get_ylim()[1] * 1.15)  # çağrı sayısı eksi olamaz, hata çizgisi 0'da kesilir
    style(right, "Görev başına çağrı sayısı")

    total, kept = len(rows) // len(MODES), len(same) // len(MODES)
    runs = (f"{total} koşu / mod." if kept == total else
            f"Sol: {total} koşu / mod. Sağ: API hatalı görev-seed çiftleri çıkarıldı, {kept} koşu / mod.")
    fig.text(0.01, 0.015, f"Çubuk: seed ortalaması. Hata çizgisi: {len({r['seed'] for r in rows})} seed üzerinden std. "
                          f"{runs}", color=MUTED, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    rows = load_rows(RESULTS)
    SUMMARY.write_text(summary(rows), encoding="utf-8")
    plot(rows, FIGURE)
    print(f"{len(rows)} koşu okundu -> {SUMMARY}, {FIGURE}")


if __name__ == "__main__":
    main()
