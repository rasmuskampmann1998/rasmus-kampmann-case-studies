"""Build the NorthStarFunnel PBIR report by driving pbi-cli (not by hand-
writing JSON). Hand-authored PBIR was structurally wrong — wrong report.json
location, missing version.json — so the report is now scaffolded and populated
through pbi-cli, which guarantees a valid project. Re-run any time:

    python powerbi/_gen_report.py

Requires pbi-cli on PATH (or set PBI below). Idempotent: wipes and rebuilds the
.Report folder from scratch.
"""
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PBI = os.environ.get("PBI", r"C:\Users\rasmu\.local\bin\pbi.exe")
REPORT = HERE / "NorthStarFunnel.Report"


def run(*args: str) -> None:
    cmd = [PBI, *args]
    # Force UTF-8 + a UTF-8 child console so the middle-dot in measure names
    # doesn't crash pbi-cli's cp1252 stdout on Windows.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    r = subprocess.run(cmd, cwd=HERE, capture_output=True,
                        encoding="utf-8", errors="replace", env=env)
    # pbi-cli prints a benign pywin32 warning to stderr when Desktop sync is
    # unavailable; only treat a non-zero exit as failure.
    if r.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    print("ok:", " ".join(args[:4]))


# Measure / column references (post-rename, [Domain] · [Metric]).
M = lambda n: f"_Measures[{n}]"
C = lambda t, c: f"{t}[{c}]"

# Pages: (id, display).
PAGES = [
    ("funnel", "Funnel Overview"),
    ("icp", "ICP & Segments"),
    ("reps", "Rep Performance"),
    ("velocity", "Velocity & Loss"),
]

# Visuals: (page, name, type, x, y, w, h, bind-kwargs).
# bind-kwargs maps a pbi visual-bind flag -> field reference.
VISUALS = [
    # --- Funnel Overview ---
    ("funnel", "f_calls", "card", 16, 16, 240, 110,
     {"field": M("Funnel · Total Calls")}),
    ("funnel", "f_conn", "card", 268, 16, 240, 110,
     {"field": M("Funnel · Connect Rate")}),
    ("funnel", "f_held", "card", 520, 16, 240, 110,
     {"field": M("Funnel · Meetings Held")}),
    ("funnel", "f_wr", "card", 772, 16, 240, 110,
     {"field": M("Funnel · Win Rate Meeting->Won")}),
    ("funnel", "f_mrr", "card", 1024, 16, 240, 110,
     {"field": M("Revenue · MRR Won USD")}),
    ("funnel", "f_stagebar", "bar", 16, 140, 620, 560,
     {"category": C("dim_stage", "stage_name"), "value": M("Funnel · Won Deals")}),
    ("funnel", "f_trend_won", "line", 648, 140, 616, 270,
     {"category": C("dim_date", "month_name"), "value": M("Funnel · Won Deals")}),
    ("funnel", "f_trend_mrr", "line", 648, 420, 616, 280,
     {"category": C("dim_date", "month_name"), "value": M("Revenue · MRR Won USD")}),
    # --- ICP & Segments ---
    ("icp", "i_emp", "column", 16, 16, 624, 340,
     {"category": C("dim_company", "employee_band"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    ("icp", "i_ind", "bar", 656, 16, 608, 340,
     {"category": C("dim_company", "industry"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    ("icp", "i_type", "bar", 16, 372, 410, 332,
     {"category": C("dim_company", "company_type"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    ("icp", "i_acct", "bar", 440, 372, 410, 332,
     {"category": C("dim_company", "accounting_system"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    # matrix bind supports --row + --value only; the employee-band x industry
    # cross-tab is added Desktop-side (see powerbi/README.md runbook).
    ("icp", "i_heat", "matrix", 864, 372, 400, 332,
     {"row": C("dim_company", "employee_band"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    # --- Rep Performance ---
    ("reps", "r_wr", "bar", 16, 16, 624, 688,
     {"category": C("dim_rep", "rep_name"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    ("reps", "r_vol", "column", 656, 16, 608, 340,
     {"category": C("dim_rep", "rep_name"), "value": M("Funnel · Total Calls")}),
    # matrix (not table) so rep_name can be a row grouping — pbi-cli's table
    # bind supports --value only; matrix supports --row + --value.
    ("reps", "r_tbl", "matrix", 656, 372, 608, 332,
     {"row": C("dim_rep", "rep_name"),
      "value": M("Funnel · Win Rate Meeting->Won")}),
    # --- Velocity & Loss ---
    ("velocity", "v_pareto", "bar", 16, 16, 624, 440,
     {"category": C("dim_lost_reason", "reason_category"),
      "value": M("Funnel · Lost Deals")}),
    ("velocity", "v_hist", "column", 656, 16, 608, 440,
     {"category": C("fact_meetings", "days_to_close"),
      "value": M("Funnel · Won Deals")}),
    ("velocity", "v_cancel", "card", 16, 472, 300, 232,
     {"field": M("Funnel · Cancellation Share of Losses")}),
    ("velocity", "v_cycle", "card", 332, 472, 300, 232,
     {"field": M("Funnel · Avg Days Meeting->Won")}),
    ("velocity", "v_mrr", "card", 656, 472, 300, 232,
     {"field": M("Revenue · Avg MRR per Won Deal")}),
]


MEASURES_TMDL = (HERE / "NorthStarFunnel.Dataset" / "definition"
                 / "tables" / "_Measures.tmdl")
EXPECTED_MEASURES = 17  # see dashboard-spec.md; the 17 [Domain] · [Metric] set


def guard_dataset() -> None:
    """Fail loudly if Power BI Desktop has stripped hand-authored measures.

    Desktop writes back only the loaded model on save, so opening the .pbip
    and saving silently drops hand-authored measures and leaves an empty
    `measure Measure` stub. Building a report on a stripped dataset ships a
    broken artefact. Refuse to build until the measure set is whole.
    """
    txt = MEASURES_TMDL.read_text(encoding="utf-8")
    real = txt.count("\n\tmeasure '")          # named, real measures
    stub = "\n\tmeasure Measure\n" in txt      # Desktop's empty stub
    if real < EXPECTED_MEASURES or stub:
        raise SystemExit(
            f"FAILED: _Measures.tmdl looks Desktop-stripped "
            f"({real} real measures, expected {EXPECTED_MEASURES}; "
            f"stub present: {stub}). Re-assert the measure set from "
            f"dashboard-spec.md before regenerating the report."
        )
    print(f"ok: dataset guard ({real} measures, no stub)")


def main() -> None:
    guard_dataset()
    if REPORT.exists():
        shutil.rmtree(REPORT)
    run("report", "create", ".", "--name", "NorthStarFunnel",
        "--dataset-path", "../NorthStarFunnel.Dataset")

    for pid, disp in PAGES:
        run("report", "--no-sync", "add-page", "-d", disp, "-n", pid)

    for page, name, vtype, x, y, w, h, bind in VISUALS:
        run("visual", "--no-sync", "add", "--page", page, "--type", vtype,
            "-n", name, "--x", str(x), "--y", str(y),
            "--width", str(w), "--height", str(h))
        bind_args: list[str] = ["visual", "--no-sync", "bind", name,
                                "--page", page]
        for flag, ref in bind.items():
            bind_args += [f"--{flag}", ref]
        run(*bind_args)

    run("report", "--path", "./NorthStarFunnel.Report", "validate")
    print("report rebuilt + validated")


if __name__ == "__main__":
    main()
