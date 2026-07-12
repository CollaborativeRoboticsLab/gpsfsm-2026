from __future__ import annotations

import re
import csv
from pathlib import Path
from typing import Dict, List, Tuple

# -----------------------------
# Inputs & model mapping
# -----------------------------

LOG_FILES = [
    "codellama-rawlog.log",
    "llamachat-rawlog.log",
    "openai-4.1-rawlog.log",
    "openai-4o-rawlog.log",
    "openai-5-rawlog.log",
]

MODEL_NAME_MAP = {
    "codellama-rawlog.log": "codellama",
    "llamachat-rawlog.log": "llamachat",
    "openai-4.1-rawlog.log": "gpt-4.1",
    "openai-4o-rawlog.log": "gpt-4o",
    "openai-5-rawlog.log": "gpt-5",
}

IS_GPT = {
    "codellama-rawlog.log": False,
    "llamachat-rawlog.log": False,
    "openai-4.1-rawlog.log": True,
    "openai-4o-rawlog.log": True,
    "openai-5-rawlog.log": True,
}

# Labels present in logs
MODEL_LABELS: Tuple[str, ...] = (
    "Zero-shot base model result",
    "One-shot base model result",
    "Zero-shot finetuned model result",
    "One-shot finetuned model result",
    "Zero-shot OpenAI result",
    "One-shot OpenAI result",
)

# Map labels to (version, prompt)
LABEL_TO_VERSION_PROMPT = {
    "Zero-shot base model result": ("base", "zero"),
    "One-shot base model result": ("base", "one"),
    "Zero-shot finetuned model result": ("finetuned", "zero"),
    "One-shot finetuned model result": ("finetuned", "one"),
    "Zero-shot OpenAI result": ("n/a", "zero"),
    "One-shot OpenAI result": ("n/a", "one"),
}


# -----------------------------
# Regex
# -----------------------------

ITERATION_RE = re.compile(r"^\s*Iteration\s+(\d+)(?:\s+on\s+[\w\-\.]+)?:\s*$")

# Matches all result lines
RESULT_LINE_RE = re.compile(
    r"^\s*("
    + "|".join(map(re.escape, MODEL_LABELS))
    + r")\s*\(time:\s*([\d.]+)\s*seconds\):\s*$"
)

TASK_LINE_RE = re.compile(r"^Running inference on task file:\s*(generative_\d+\.txt)")


# -----------------------------
# File IO helpers
# -----------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

def write_csv(path: Path, rows: List[List[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

# -----------------------------
# Parsing / extraction
# -----------------------------

def extract_blocks(log_text: str) -> Dict[str, Dict[int, List[str]]]:
    task_blocks: Dict[str, Dict[int, List[str]]] = {}
    current_task: str | None = None
    current_it: int | None = None

    for raw in log_text.splitlines():
        line = raw.rstrip()

        # Detect new task
        m_task = TASK_LINE_RE.match(line)
        if m_task:
            current_task = m_task.group(1).replace(".txt", "")  # e.g., generative_1
            task_blocks[current_task] = {}
            current_it = None
            continue

        m_it = ITERATION_RE.match(line)
        if m_it:
            if current_task is None:
                continue  # ignore iterations outside tasks
            current_it = int(m_it.group(1))
            task_blocks[current_task][current_it] = [line]
            continue

        if current_task and current_it is not None and any(line.startswith(lbl) for lbl in MODEL_LABELS):
            task_blocks[current_task][current_it].append(line)

    return task_blocks
def parse_times(blocks: Dict[int, List[str]]) -> Dict[str, Dict[int, float]]:
    results: Dict[str, Dict[int, float]] = {}
    for it, lines in blocks.items():
        for line in lines:
            m = RESULT_LINE_RE.match(line)
            if m:
                label = m.group(1)
                if label not in results:
                    results[label] = {}
                results[label][it] = float(m.group(2))
    return results

# -----------------------------
# Formatting for outputs
# -----------------------------

def format_task_blocks_as_text(task_blocks: Dict[str, Dict[int, List[str]]]) -> str:
    parts: List[str] = []
    for task, blocks in task_blocks.items():
        parts.append(f"Running inference on task file: {task}.txt")
        for it in sorted(blocks):
            filtered = [
                line for line in blocks[it]
                if line.startswith("Iteration") or RESULT_LINE_RE.match(line)
            ]
            parts.append("\n".join(filtered))
        parts.append("")  # add spacing between tasks
    return "\n\n".join(parts)


def make_iteration_headers(all_iterations: List[int]) -> List[str]:
    return [f"Itr{it}" for it in all_iterations]

# -----------------------------
# Row building (combined CSV)
# -----------------------------

def rows_for_file(task_name: str, file_name: str, times_by_label: Dict[str, Dict[int, float]], all_iterations: List[int]) -> List[List[str]]:
    model = MODEL_NAME_MAP[file_name]
    is_gpt = IS_GPT[file_name]
    rows: List[List[str]] = []

    for label in MODEL_LABELS:
        if not times_by_label.get(label):
            continue
        version, prompt = LABEL_TO_VERSION_PROMPT[label]
        version_out = "n/a" if is_gpt else version

        row = [task_name, model, version_out, prompt]
        for it in all_iterations:
            val = times_by_label.get(label, {}).get(it, "")
            row.append(f"{val}" if val != "" else "")
        rows.append(row)

    return rows

# -----------------------------
# Orchestration
# -----------------------------

def process_one_log(file_name: str) -> Tuple[Dict[str, Dict[str, Dict[int, float]]], Dict[str, Dict[int, List[str]]]]:
    p = Path("logs/" + file_name)
    if not p.exists():
        return ({}, {})

    text = read_text(p)
    task_blocks = extract_blocks(text)
    task_times: Dict[str, Dict[str, Dict[int, float]]] = {}

    for task, blocks in task_blocks.items():
        task_times[task] = parse_times(blocks)

    return (task_times, task_blocks)


def main() -> None:
    out_dir = Path("timing_data")
    out_dir.mkdir(exist_ok=True)

    all_iterations_set = set()
    all_rows: List[List[str]] = []

    per_file_task_blocks: Dict[str, Dict[str, Dict[int, List[str]]]] = {}

    for fname in LOG_FILES:
        task_times_dict, task_blocks_dict = process_one_log(fname)
        per_file_task_blocks[fname] = task_blocks_dict

        # Save extracted.txt
        out_txt = out_dir / (Path(fname).stem + ".extracted.txt")
        write_text(out_txt, format_task_blocks_as_text(task_blocks_dict))

        for task, blocks in task_blocks_dict.items():
            all_iterations_set.update(blocks.keys())

    all_iterations_sorted = sorted(all_iterations_set)
    header = ["Task", "Model", "Version", "Prompt"] + make_iteration_headers(all_iterations_sorted)
    all_rows.append(header)

    for fname in LOG_FILES:
        task_times_dict, _ = process_one_log(fname)
        for task_name, times in task_times_dict.items():
            all_rows.extend(rows_for_file(task_name, fname, times, all_iterations_sorted))

    write_csv(out_dir / "iteration_times_all.csv", all_rows)


if __name__ == "__main__":
    main()
