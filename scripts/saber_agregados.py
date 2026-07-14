"""Agregados ICFES 2023-2025 (Saber Pro y TyT) → data/saber_agregados.json

Fuente: XLSX oficiales de icfes.gov.co (descarga directa, sin login), promedios
por nivel de agregación. Extrae: (a) puntaje global Antioquia vs Colombia por
año y examen; (b) ranking de IES antioqueñas (PUNTAJE_GLOBAL, n>=100).
"""
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
out = {"serie": [], "ies": {"pro": {}, "tyt": {}}}

for examen, pref in [("pro", "saberpro"), ("tyt", "sabertyt")]:
    for anio in (2023, 2024, 2025):
        f = DATA / f"{pref}_agg_{anio}.xlsx"
        df = pd.read_excel(f, sheet_name=0)
        df.columns = [str(c).strip().upper() for c in df.columns]
        pg = df[df["MEDIDA_AGREGACION"].str.strip() == "PUNTAJE_GLOBAL"].copy()
        pg["AGG"] = pg["AGREGACION"].str.strip()
        pg["DEP"] = pg["NOMBRE_DEPARTAMENTO"].astype(str).str.strip().str.upper()

        nal = pg[pg["AGG"] == "PAIS"]["PROMEDIO_GLOBAL"].mean()
        ant = pg[(pg["AGG"] == "DEPARTAMENTO") & (pg["DEP"] == "ANTIOQUIA")]["PROMEDIO_GLOBAL"].mean()
        n_ant = pg[(pg["AGG"] == "DEPARTAMENTO") & (pg["DEP"] == "ANTIOQUIA")]["CANTIDADEVALUADOS"].max()
        out["serie"].append({"examen": examen, "anio": anio,
                             "antioquia": round(float(ant), 1) if pd.notna(ant) else None,
                             "nacional": round(float(nal), 1) if pd.notna(nal) else None,
                             "evaluados_ant": int(n_ant) if pd.notna(n_ant) else None})

        ies = pg[(pg["AGG"] == "INSTITUCIÓN") & (pg["DEP"] == "ANTIOQUIA")
                 & (pg["CANTIDADEVALUADOS"] >= 100)]
        rk = (ies.groupby("NOMBRE_INSTITUCION")
              .agg(prom=("PROMEDIO_GLOBAL", "mean"), n=("CANTIDADEVALUADOS", "max"))
              .sort_values("prom", ascending=False))
        out["ies"][examen][anio] = [
            {"ies": str(k).strip().title(), "prom": round(float(v.prom), 1), "n": int(v.n)}
            for k, v in rk.iterrows()]
        print(examen, anio, "| Ant:", out["serie"][-1]["antioquia"], "Nal:", out["serie"][-1]["nacional"],
              "| IES(n>=100):", len(out["ies"][examen][anio]),
              "| top:", out["ies"][examen][anio][0] if out["ies"][examen][anio] else "—")

(DATA / "saber_agregados.json").write_text(json.dumps(out, ensure_ascii=False))
print("ok → data/saber_agregados.json")
