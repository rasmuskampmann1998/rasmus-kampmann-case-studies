"""Generate the 10 table TMDL files for the NorthStarFunnel PBIP dataset
from the CSV schemas. Run once from the powerbi/ folder; not part of the
case-study deliverable surface (it builds the deliverable).

    python powerbi/_gen_tmdl.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
TBL = HERE / "NorthStarFunnel.Dataset" / "definition" / "tables"
TBL.mkdir(parents=True, exist_ok=True)

# pandas dtype -> (TMDL dataType, M transform type)
PQ = {
    "int64": ("int64", "Int64.Type"),
    "float64": ("double", "type number"),
    "bool": ("boolean", "type logical"),
    "str": ("string", "type text"),
    "object": ("string", "type text"),
}

TABLES = {
    "dim_date": "Dimensions",
    "dim_company": "Dimensions",
    "dim_rep": "Dimensions",
    "dim_stage": "Dimensions",
    "dim_source": "Dimensions",
    "dim_lost_reason": "Dimensions",
    "fact_calls": "Facts",
    "fact_meetings": "Facts",
    "fact_deals": "Facts",
}
# Columns that must stay text even though they look numeric (keys joined as text
# elsewhere) — none here, keys are already string except *_date_key ints which
# are fine as int64 and join to dim_date[date_key] int64.

LINEAGE = 0x7a1f0c00


def tmdl_type(col: str, dtype: str) -> tuple[str, str]:
    return PQ.get(dtype, PQ["str"])


for i, (tbl, group) in enumerate(TABLES.items()):
    df = pd.read_csv(DATA / f"{tbl}.csv", nrows=200, keep_default_na=False)
    lines: list[str] = [f"table {tbl}", f"\tlineageTag: {LINEAGE + i:032x}"[:20] + f"-0000-4000-8000-{LINEAGE + i:012x}"]
    # simpler stable lineage tags
    lines = [f"table {tbl}"]
    lines.append("")
    col_types: list[tuple[str, str]] = []
    for col in df.columns:
        dt = str(df[col].dtype)
        if dt.startswith("int"):
            dt = "int64"
        elif dt.startswith("float"):
            dt = "float64"
        elif dt == "bool":
            dt = "bool"
        else:
            dt = "str"
        tmdl_t, m_t = tmdl_type(col, dt)
        col_types.append((col, m_t))
        lines.append(f"\tcolumn {col}")
        lines.append(f"\t\tdataType: {tmdl_t}")
        lines.append(f"\t\tsourceColumn: {col}")
        if col.endswith("_key") and tmdl_t in ("string", "int64"):
            lines.append("\t\tsummarizeBy: none")
        elif tmdl_t in ("int64", "double"):
            lines.append("\t\tsummarizeBy: sum")
        else:
            lines.append("\t\tsummarizeBy: none")
        lines.append("")
    # Power Query M partition
    transforms = ", ".join(f'{{"{c}", {t}}}' for c, t in col_types)
    m = [
        f"\tpartition {tbl} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\tlet",
        f'\t\t\t\tSrc = Csv.Document(File.Contents(DataFolder & "\\{tbl}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "\t\t\t\tProm = Table.PromoteHeaders(Src, [PromoteAllScalars=true]),",
        f"\t\t\t\tTyped = Table.TransformColumnTypes(Prom, {{{transforms}}})",
        "\t\t\tin",
        "\t\t\t\tTyped",
        "",
        f"\tannotation PBI_NavigationStepName = Navigation",
        f"\tannotation PBI_ResultType = Table",
    ]
    body = "\n".join(lines) + "\n" + "\n".join(m) + "\n"
    (TBL / f"{tbl}.tmdl").write_text(body, encoding="utf-8")
    print(f"wrote tables/{tbl}.tmdl ({len(df.columns)} cols)")

print("done")
