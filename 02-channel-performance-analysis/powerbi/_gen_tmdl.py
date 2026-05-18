"""Generate the 10 table TMDL files for the ChannelPerformance PBIP dataset
from the CSV schemas. Run once from the powerbi/ folder; not part of the
case-study deliverable surface (it builds the deliverable).

    python powerbi/_gen_tmdl.py

dim_date is emitted with `date` typed as dateTime and `month_name` sorted by
`month` so the trend axis orders correctly. The auto-date internal markers are
deliberately NOT hand-authored — dim_date is marked as the date table via the
Desktop runbook (`pbi table mark-date`), see powerbi/README.md.
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
TBL = HERE / "ChannelPerformance.Dataset" / "definition" / "tables"
TBL.mkdir(parents=True, exist_ok=True)

# pandas dtype -> (TMDL dataType, M transform type)
PQ = {
    "int64": ("int64", "Int64.Type"),
    "float64": ("double", "type number"),
    "bool": ("boolean", "type logical"),
    "str": ("string", "type text"),
}

TABLES = {
    "dim_date": "Dimensions",
    "dim_channel": "Dimensions",
    "dim_campaign": "Dimensions",
    "dim_company": "Dimensions",
    "dim_rep": "Dimensions",
    "dim_stage": "Dimensions",
    "dim_lost_reason": "Dimensions",
    "fact_touches": "Facts",
    "fact_deals": "Facts",
    "fact_meetings": "Facts",
}

DATE_HEADER = (
    "/// dim_date is the report's date dimension. It is marked as the official\n"
    "/// date table statically via the table-level annotation\n"
    "/// `__PBI_MarkAsDateTable = {\"dt\":\"date\"}` (emitted below) so time\n"
    "/// intelligence works on first refresh with no Desktop step. The\n"
    "/// auto-date-table internal markers (dataCategory: Time / padded date\n"
    "/// columns) are deliberately NOT hand-authored.\n"
)


def col_dtype(series: pd.Series) -> str:
    dt = str(series.dtype)
    if dt.startswith("int"):
        return "int64"
    if dt.startswith("float"):
        return "float64"
    if dt == "bool":
        return "bool"
    return "str"


for tbl, group in TABLES.items():
    # NOTE: type inference must let pandas coerce blanks to NaN, otherwise a
    # numeric column with empty cells (e.g. fact_meetings[days_to_close], blank
    # for cancelled meetings) is read as object and mistyped as text. The data
    # LOAD in Power Query is unaffected — this read is only for schema sniffing.
    df = pd.read_csv(DATA / f"{tbl}.csv")
    lines: list[str] = []
    if tbl == "dim_date":
        lines.append(DATE_HEADER.rstrip("\n"))
    lines.append(f"table {tbl}")
    lines.append("")

    col_types: list[tuple[str, str]] = []
    for col in df.columns:
        dt = col_dtype(df[col])
        tmdl_t, m_t = PQ[dt]

        # dim_date.date is a real date. Keep the TMDL dataType and the M cast
        # consistent (dateTime <-> type datetime) so the static
        # __PBI_MarkAsDateTable annotation binds unambiguously.
        if tbl == "dim_date" and col == "date":
            tmdl_t, m_t = "dateTime", "type datetime"

        col_types.append((col, m_t))
        lines.append(f"\tcolumn {col}")
        lines.append(f"\t\tdataType: {tmdl_t}")
        if tbl == "dim_date" and col == "date":
            lines.append("\t\tformatString: Long Date")
        lines.append(f"\t\tsourceColumn: {col}")
        if tbl == "dim_date" and col == "month_name":
            lines.append("\t\tsortByColumn: month")
        if col.endswith("_key") and tmdl_t in ("string", "int64"):
            lines.append("\t\tsummarizeBy: none")
        elif tmdl_t in ("int64", "double"):
            lines.append("\t\tsummarizeBy: sum")
        else:
            lines.append("\t\tsummarizeBy: none")
        lines.append("")

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
        "\tannotation PBI_NavigationStepName = Navigation",
        "\tannotation PBI_ResultType = Table",
    ]
    # Mark dim_date as the date table statically so no Desktop mark-date step
    # is needed and time intelligence works on first refresh.
    if tbl == "dim_date":
        m.append('\tannotation __PBI_MarkAsDateTable = {"dt":"date"}')
    body = "\n".join(lines) + "\n" + "\n".join(m) + "\n"
    (TBL / f"{tbl}.tmdl").write_text(body, encoding="utf-8")
    print(f"wrote tables/{tbl}.tmdl ({len(df.columns)} cols)")

print("done")
