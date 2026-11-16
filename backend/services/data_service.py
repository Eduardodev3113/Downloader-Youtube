import json
import sqlite3
from pathlib import Path

import pandas as pd
import yaml

FORMATS = {"csv", "xlsx", "json", "xml", "yaml", "sql"}


def convert(source: Path, target: str, output: Path) -> None:
    ext = source.suffix.lower().lstrip(".")
    if ext == "csv":
        frame = pd.read_csv(source)
    elif ext == "xlsx":
        frame = pd.read_excel(source)
    elif ext == "json":
        frame = pd.read_json(source)
    elif ext == "xml":
        frame = pd.read_xml(source)
    elif ext in ("yaml", "yml"):
        content = yaml.safe_load(source.read_text(encoding="utf-8"))
        frame = pd.DataFrame(content if isinstance(content, list) else [content])
    else:
        raise ValueError("Formato de origem de dados não suportado.")
    if target == "csv":
        frame.to_csv(output, index=False)
    elif target == "xlsx":
        frame.to_excel(output, index=False)
    elif target == "json":
        frame.to_json(output, orient="records", force_ascii=False, indent=2)
    elif target == "xml":
        frame.to_xml(output, index=False)
    elif target == "yaml":
        output.write_text(yaml.safe_dump(frame.to_dict(orient="records"), allow_unicode=True), encoding="utf-8")
    elif target == "sql":
        output.write_text(_to_sql(frame, source.stem), encoding="utf-8")
    else:
        raise ValueError("Formato de destino não suportado.")


def _to_sql(frame: pd.DataFrame, table_name: str) -> str:
    safe_table = "".join(c for c in table_name if c.isalnum() or c == "_") or "data"
    conn = sqlite3.connect(":memory:")
    frame.to_sql(safe_table, conn, index=False, if_exists="replace")
    rows = conn.execute(f'SELECT * FROM "{safe_table}"').fetchall()
    columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{safe_table}")')]
    conn.close()
    statements = []
    for row in rows:
        values = ", ".join("NULL" if value is None else "'" + str(value).replace("'", "''") + "'" for value in row)
        statements.append(f'INSERT INTO "{safe_table}" ({", ".join(chr(34) + c.replace(chr(34), chr(34) * 2) + chr(34) for c in columns)}) VALUES ({values});')
    return "\n".join(statements) + ("\n" if statements else "")
