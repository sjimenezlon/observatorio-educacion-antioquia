"""Benchmark interdepartamental de matrícula (todos los niveles, semestre pico).

Reutiliza las bases consolidadas SNIES nacionales ya descargadas en data/
(matriculados_2018.xlsx … matriculados_2024.xlsx) y emite
data/benchmark_deptos.json con la serie por departamento seleccionado.
El semestre pico se toma POR departamento y año (misma metodología que
procesar.py aplica a Antioquia).
"""
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
DEPTOS = ["ANTIOQUIA", "BOGOTÁ D.C.", "VALLE DEL CAUCA", "SANTANDER", "ATLÁNTICO"]
ANIOS = range(2018, 2025)


def buscar_header(xl):
    for hoja in pd.ExcelFile(xl).sheet_names:
        peek = pd.read_excel(xl, sheet_name=hoja, header=None, nrows=15)
        for i, row in peek.iterrows():
            vals = [" ".join(str(v).upper().split()) for v in row.tolist()]
            if any("DEPARTAMENTO DE OFERTA" in v for v in vals):
                return hoja, i
    raise ValueError(f"header no encontrado en {xl}")


series = {d: {} for d in DEPTOS}
etiquetas = {}
for anio in ANIOS:
    f = DATA / f"matriculados_{anio}.xlsx"
    hoja, hdr = buscar_header(f)
    df = pd.read_excel(f, sheet_name=hoja, header=hdr)
    df.columns = [" ".join(str(c).upper().split()) for c in df.columns]
    df = df.rename(columns={c: "MATRICULADOS" for c in df.columns
                            if c.startswith("MATRICULADOS") and c != "MATRICULADOS"})
    df["MATRICULADOS"] = pd.to_numeric(df["MATRICULADOS"], errors="coerce").fillna(0)
    col_dep = "DEPARTAMENTO DE OFERTA DEL PROGRAMA"
    df[col_dep] = df[col_dep].astype(str).str.strip().str.upper()
    # normaliza tildes/variantes de Bogotá entre vigencias
    df[col_dep] = df[col_dep].replace({"BOGOTA D.C.": "BOGOTÁ D.C.", "BOGOTA, D.C.": "BOGOTÁ D.C.",
                                       "BOGOTÁ, D.C.": "BOGOTÁ D.C.", "BOGOTÁ D.C": "BOGOTÁ D.C.",
                                       "BOGOTA D.C": "BOGOTÁ D.C."})
    etiquetas[anio] = sorted(df[col_dep].unique().tolist())
    for d in DEPTOS:
        sub = df[df[col_dep] == d]
        if sub.empty or "SEMESTRE" not in df.columns:
            series[d][anio] = None
            continue
        tot = sub.groupby("SEMESTRE")["MATRICULADOS"].sum()
        series[d][anio] = int(tot.max())
    print(anio, {d: series[d][anio] for d in DEPTOS})

out = {"deptos": DEPTOS, "anios": list(ANIOS), "series": series,
       "nota": "Matrícula todos los niveles, semestre pico por departamento y vigencia (SNIES bases consolidadas nacionales)."}
(DATA / "benchmark_deptos.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("ok → data/benchmark_deptos.json")
