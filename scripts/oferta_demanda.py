"""Métricas de oferta y demanda por área de conocimiento (Antioquia).

- Demanda revelada: inscritos 2018 vs 2024 por área (SNIES, oferta en Antioquia).
- Presión: inscritos por estudiante de primer curso 2024 ("aspirantes por silla").
- Señal de precio: salario típico de enganche (punto medio ponderado de las
  bandas de INGRESO del OLE 2023, SMMLV), pregrado de IES antioqueñas,
  graduados 2018+ que cotizaron en 2023.
→ data/oferta_demanda.json
"""
import json
import unicodedata
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"


def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def leer(archivo, valor, alias=()):
    xl = DATA / archivo
    for hoja in pd.ExcelFile(xl).sheet_names:
        peek = pd.read_excel(xl, sheet_name=hoja, header=None, nrows=15)
        hdr = None
        for i, row in peek.iterrows():
            vals = [" ".join(str(v).upper().split()) for v in row.tolist()]
            if any("DEPARTAMENTO DE OFERTA" in v for v in vals):
                hdr = i
                break
        if hdr is not None:
            break
    df = pd.read_excel(xl, sheet_name=hoja, header=hdr)
    df.columns = [" ".join(str(c).upper().split()) for c in df.columns]
    prefijos = (valor,) + tuple(alias)
    df = df.rename(columns={c: valor for c in df.columns
                            if any(c.startswith(p) for p in prefijos) and c != valor})
    df[valor] = pd.to_numeric(df[valor], errors="coerce").fillna(0)
    df = df[df["DEPARTAMENTO DE OFERTA DEL PROGRAMA"].astype(str).str.strip().str.upper() == "ANTIOQUIA"]
    return df


AREA = "ÁREA DE CONOCIMIENTO"
i18 = leer("inscritos_2018.xlsx", "INSCRITOS", alias=("INSCRIPCIONES",))
i24 = leer("inscritos_2024.xlsx", "INSCRITOS", alias=("INSCRIPCIONES",))
pc24 = leer("primer_curso_2024.xlsx", "PRIMER CURSO", alias=("MATRICULADOS PRIMER CURSO",))
m24 = leer("matriculados_2024.xlsx", "MATRICULADOS")

def por_area(df, val):
    g = df.groupby(df[AREA].map(lambda a: " ".join(str(a).strip().split())))[val].sum()
    return {norm(k): (k, int(v)) for k, v in g.items() if str(k).strip() and str(k).lower() != "nan"}

a18, a24, apc = por_area(i18, "INSCRITOS"), por_area(i24, "INSCRITOS"), por_area(pc24, "PRIMER CURSO")

# OLE: salario típico de enganche por área (pregrado, IES antioqueñas)
cod_col = "CÓDIGO DE LA INSTITUCIÓN"
ies_ant = set(pd.to_numeric(
    m24.loc[m24["DEPARTAMENTO DE DOMICILIO DE LA IES"].astype(str).str.strip() == "Antioquia", cod_col],
    errors="coerce").dropna().astype(int))
ole = pd.read_excel(DATA / "ole_base_ibc_2023.xlsx", sheet_name="Base_IBC_2023", header=8)
ole.columns = [" ".join(str(c).upper().split()) for c in ole.columns]
ole["GRADUADOS"] = pd.to_numeric(ole["GRADUADOS"], errors="coerce").fillna(0)
ole = ole[pd.to_numeric(ole[cod_col], errors="coerce").isin(ies_ant)
          & (pd.to_numeric(ole["AÑO DE GRADO"], errors="coerce") >= 2018)
          & (ole["NIVEL ACADÉMICO"].astype(str).str.strip().str.upper() == "PREGRADO")]
MID = {"1 SMMLV": 1.0, "ENTRE 1 Y 1,5 SMMLV": 1.25, "ENTRE 1,5 Y 2,5 SMMLV": 2.0,
       "ENTRE 2,5 Y 4 SMMLV": 3.25, "ENTRE 4 Y 6 SMMLV": 5.0,
       "ENTRE 6 Y 9 SMMLV": 7.5, "MÁS DE 9 SMMLV": 10.5}
ole["MID"] = ole["INGRESO"].astype(str).str.strip().str.upper().map(MID)
sal = {}
for a, sub in ole[ole["MID"].notna()].groupby(ole[AREA].map(lambda x: " ".join(str(x).strip().split()))):
    n = sub["GRADUADOS"].sum()
    if n >= 200:
        sal[norm(a)] = (round(float((sub["MID"] * sub["GRADUADOS"]).sum() / n), 2), int(n))

out = []
for k in sorted(set(a24) | set(a18)):
    nombre = a24.get(k, a18.get(k))[0]
    v18, v24 = a18.get(k, (None, None))[1], a24.get(k, (None, None))[1]
    pc = apc.get(k, (None, None))[1]
    fila = {"area": nombre, "insc18": v18, "insc24": v24, "pc24": pc,
            "ratio24": round(v24 / pc, 1) if v24 and pc else None,
            "delta_pct": round(100 * (v24 - v18) / v18, 1) if v18 and v24 else None,
            "sal_smmlv": sal.get(k, (None, None))[0], "vinculados_ole": sal.get(k, (None, None))[1]}
    out.append(fila)

(DATA / "oferta_demanda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for f in sorted(out, key=lambda x: -(x["insc24"] or 0)):
    print(f"{f['area'][:44]:46} insc18 {f['insc18']!s:>8} insc24 {f['insc24']!s:>8} Δ {f['delta_pct']!s:>7}%  asp/silla {f['ratio24']!s:>5}  sal {f['sal_smmlv']} SMMLV")
