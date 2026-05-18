"""Build the ChannelPerformance PBIR report by driving pbi-cli (not by hand-
writing JSON). Re-run any time:

    python powerbi/_gen_report.py

Requires pbi-cli on PATH (or set PBI below). Idempotent: wipes and rebuilds
the .Report folder from scratch, then validates it.
"""
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PBI = os.environ.get("PBI", r"C:\Users\rasmu\.local\bin\pbi.exe")
REPORT = HERE / "ChannelPerformance.Report"


def run(*args: str) -> None:
    cmd = [PBI, *args]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    r = subprocess.run(cmd, cwd=HERE, capture_output=True,
                        encoding="utf-8", errors="replace", env=env)
    if r.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    print("ok:", " ".join(args[:4]))


DATASET_MEASURES = (HERE / "ChannelPerformance.Dataset" / "definition"
                    / "tables" / "_Measures.tmdl")
# The 5 Phase-8 churn measures. Power BI Desktop strips these from the TMDL
# every time it opens the .pbip and saves (it writes back only the loaded
# model). Binding report visuals to a measure that is not in the dataset
# produces a report that validates structurally but is broken on refresh, so
# the build refuses to run against a stripped dataset.
REQUIRED_CHURN_MEASURES = [
    "Channel · Churned Deals",
    "Channel · Retention Rate",
    "Revenue · Churned MRR",
    "Revenue · Net Revenue Retention",
    "Channel · Won & Retained",
]
MIN_MEASURE_COUNT = 20


def guard_dataset() -> None:
    """Abort loudly if Desktop has stripped the churn measures."""
    if not DATASET_MEASURES.exists():
        raise SystemExit(f"FAILED: {DATASET_MEASURES} not found")
    txt = DATASET_MEASURES.read_text(encoding="utf-8")
    n = txt.count("\tmeasure '")
    missing = [m for m in REQUIRED_CHURN_MEASURES if f"measure '{m}'" not in txt]
    if n < MIN_MEASURE_COUNT or missing:
        raise SystemExit(
            "FAILED: dataset is in the Desktop-stripped state.\n"
            f"  measures found: {n} (need >= {MIN_MEASURE_COUNT})\n"
            f"  missing churn measures: {missing or 'none'}\n"
            "  Re-assert the Phase-8 churn measure block in\n"
            f"  {DATASET_MEASURES}\n"
            "  (Power BI Desktop drops them on save — see powerbi/README.md "
            "runbook). Do NOT rebuild the report until this is fixed.")
    print(f"ok: dataset guard ({n} measures, all churn measures present)")


M = lambda n: f"_Measures[{n}]"
C = lambda t, c: f"{t}[{c}]"

# Pages: (id, display).
# Phase 8: "Efficiency & Dialer ROI" → "Channel Economics" (the dialer cut
# was non-zero for only 2 of 10 channels, so 3 of its 4 visuals were 2-bar
# charts); "Trend & Loss" → "Retention & Loss" (the monthly win-rate trend
# plotted noise — created_date is uniform-random, no designed time trend).
PAGES = [
    ("overview", "Channel Overview"),
    ("economics", "Channel Economics"),
    ("icp", "Channel x ICP"),
    ("retloss", "Retention & Loss"),
]

# Visuals: (page, name, type, x, y, w, h, bind-kwargs).
VISUALS = [
    # --- Channel Overview ---
    ("overview", "o_deals", "card", 16, 16, 240, 110,
     {"field": M("Channel · Deals")}),
    ("overview", "o_won", "card", 268, 16, 240, 110,
     {"field": M("Channel · Won Deals")}),
    ("overview", "o_wr", "card", 520, 16, 240, 110,
     {"field": M("Channel · Win Rate")}),
    ("overview", "o_mrr", "card", 772, 16, 240, 110,
     {"field": M("Revenue · Won MRR USD")}),
    ("overview", "o_avgmrr", "card", 1024, 16, 240, 110,
     {"field": M("Revenue · Avg MRR per Won Deal")}),
    ("overview", "o_wr_by_chan", "bar", 16, 140, 624, 560,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Channel · Win Rate")}),
    # Phase 9: these two were `column`. Converted to `bar` so the whole report
    # uses one comparison grammar (horizontal bars for category comparison),
    # which also gives the long channel names room to read without rotation.
    ("overview", "o_mrr_pareto", "bar", 656, 140, 608, 280,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Revenue · Won MRR USD")}),
    ("overview", "o_vol", "bar", 656, 432, 608, 268,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Channel · Deals")}),
    # --- Channel Economics (Phase 8: all 10 channels, win × retention) ---
    # Lead visual: net revenue retention by channel — the post-sale axis the
    # "best channel" verdict turns on. Then the all-channel economics matrix
    # (win, retention, NRR, net MRR). The dialer cut is kept but demoted to a
    # single corner card pair: it is a real finding (the scarce resource sits
    # on the worst channels) but it is NOT the efficiency axis for the 8
    # non-dialer channels, so it no longer leads the page.
    ("economics", "ec_nrr_by_chan", "bar", 16, 16, 624, 440,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Revenue · Net Revenue Retention")}),
    ("economics", "ec_ret_by_chan", "bar", 656, 16, 608, 440,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Channel · Retention Rate")}),
    ("economics", "ec_matrix", "matrix", 16, 472, 834, 232,
     {"row": C("dim_channel", "channel_name"),
      "value": M("Channel · Win Rate")}),
    ("economics", "ec_grp", "matrix", 864, 472, 200, 232,
     {"row": C("dim_channel", "channel_group"),
      "value": M("Revenue · Net Revenue Retention")}),
    ("economics", "ec_dialer", "card", 1076, 472, 188, 110,
     {"field": M("Channel · MRR per Dialer Hour")}),
    ("economics", "ec_t2w", "card", 1076, 594, 188, 110,
     {"field": M("Channel · Avg Days to Won")}),
    # --- Channel x ICP ---
    ("icp", "i_heat", "matrix", 16, 16, 760, 688,
     {"row": C("dim_channel", "channel_name"),
      "value": M("Channel · Win Rate")}),
    ("icp", "i_emp", "bar", 792, 16, 472, 340,
     {"category": C("dim_company", "employee_band"),
      "value": M("Channel · Win Rate")}),
    ("icp", "i_ind", "bar", 792, 372, 472, 332,
     {"category": C("dim_company", "industry"),
      "value": M("Channel · Win Rate")}),
    # --- Retention & Loss ---
    # Lead visual (Phase 9): the ONE honest line chart in the report. x-axis
    # is fact_deals[retained_months], an integer 1..12 — a real ordered
    # domain (months a won customer stayed before churning), NOT a fabricated
    # time trend. The Phase-8-removed chart was dishonest because created_date
    # is uniform-random; retained_months is a designed survival signal, so a
    # line over it carries real information. Legend = channel_group, value =
    # won customers reaching that retention depth.
    ("retloss", "r_survival", "line", 16, 16, 1248, 300,
     {"category": C("fact_deals", "retained_months"),
      "legend": C("dim_channel", "channel_group"),
      "value": M("Channel · Won & Retained")}),
    ("retloss", "r_won_ret", "bar", 16, 332, 624, 252,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Channel · Won & Retained")}),
    ("retloss", "r_churn_mrr", "bar", 656, 332, 608, 252,
     {"category": C("dim_channel", "channel_name"),
      "value": M("Revenue · Churned MRR")}),
    ("retloss", "r_pareto", "bar", 16, 596, 624, 188,
     {"category": C("dim_lost_reason", "reason_category"),
      "value": M("Channel · Lost Deals")}),
    ("retloss", "r_ret", "card", 656, 596, 296, 90,
     {"field": M("Channel · Retention Rate")}),
    ("retloss", "r_nrr", "card", 968, 596, 296, 90,
     {"field": M("Revenue · Net Revenue Retention")}),
    ("retloss", "r_cancrate", "card", 656, 694, 296, 90,
     {"field": M("Channel · Meeting Cancel Rate")}),
    ("retloss", "r_trap", "card", 968, 694, 296, 90,
     {"field": M("Channel · MRR per Dialer Hour")}),
]


def main() -> None:
    guard_dataset()
    if REPORT.exists():
        shutil.rmtree(REPORT)
    run("report", "create", ".", "--name", "ChannelPerformance",
        "--dataset-path", "../ChannelPerformance.Dataset")

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

    # Phase 9: apply the custom theme headless. set-theme copies the JSON into
    # StaticResources/RegisteredResources and points report.json at it; the
    # look takes effect when the .pbip opens in Desktop. Validated after, so a
    # malformed theme fails the build instead of shipping silently.
    run("report", "--path", "./ChannelPerformance.Report",
        "set-theme", "-f", "channel-performance-theme.json")
    run("report", "--path", "./ChannelPerformance.Report", "validate")
    run("report", "--path", "./ChannelPerformance.Report", "get-theme")
    print("report rebuilt + themed + validated")


if __name__ == "__main__":
    main()
