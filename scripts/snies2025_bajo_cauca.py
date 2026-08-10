#!/usr/bin/env python3
"""Cifras 2025 de Antioquia y del Bajo Cauca desde la base consolidada del SNIES.

El MEN publicó «Estudiantes Matriculados 2025» a finales de julio de 2026
(articles-430149_recurso.xlsx). Este script calcula, con el mismo método que
scripts/procesar.py —semestre pico de la vigencia y municipio de OFERTA del
programa, no domicilio de la IES—, las cifras que alimentan el deck
/presentacion, y las compara contra 2024 para poder narrar la variación.

Uso: python3 scripts/snies2025_bajo_cauca.py
"""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"

BAJO_CAUCA = ["Caucasia", "El Bagre", "Cáceres", "Tarazá", "Zaragoza", "Nechí"]
TYT = ["Técnica Profesional", "Tecnológica"]


def leer(archivo):
    """Lee una base consolidada del SNIES y se queda con el semestre pico.

    Sumar los dos semestres duplicaría a quien se matriculó en ambos, así que
    la vigencia se representa con el semestre de mayor matrícula, igual que en
    el resto del sitio.
    """
    xl = pd.ExcelFile(DATA / archivo)
    hoja = [h for h in xl.sheet_names if h != "ÍNDICE"][0]
    peek = pd.read_excel(xl, sheet_name=hoja, header=None, nrows=15)
    hdr = next(
        i for i in range(15)
        if peek.iloc[i].astype(str).str.contains("CÓDIGO DE LA INSTITUCIÓN").any()
    )
    df = pd.read_excel(xl, sheet_name=hoja, header=hdr)
    df.columns = [str(c).strip() for c in df.columns]
    val = "MATRICULADOS"
    if "SEMESTRE" in df.columns:
        pico = df.groupby("SEMESTRE")[val].sum().idxmax()
        df = df[df["SEMESTRE"] == pico].copy()
        df.attrs["semestre"] = int(pico)
    return df


def antioquia(df):
    col = "DEPARTAMENTO DE OFERTA DEL PROGRAMA"
    if col not in df.columns:
        col = [c for c in df.columns if c.startswith("DEPARTAMENTO DE OFERTA")][0]
    return df[df[col].astype(str).str.strip().str.upper() == "ANTIOQUIA"].copy()


def resumen(df, etiqueta):
    ant = antioquia(df)
    muni = "MUNICIPIO DE OFERTA DEL PROGRAMA"
    tyt = ant.loc[ant["NIVEL DE FORMACIÓN"].isin(TYT), "MATRICULADOS"].sum()
    print(f"\n===== {etiqueta} · semestre {df.attrs.get('semestre','?')} =====")
    print(f"Antioquia matrícula     {int(ant['MATRICULADOS'].sum()):>10,}")
    print(f"  técnica y tecnológica {int(tyt):>10,}")
    print(f"  universitaria         {int(ant.loc[ant['NIVEL DE FORMACIÓN']=='Universitario','MATRICULADOS'].sum()):>10,}")
    print(f"  posgrado              {int(ant.loc[ant['NIVEL ACADÉMICO']=='Posgrado','MATRICULADOS'].sum()):>10,}")
    print(f"  IES                   {ant['IES_PADRE_NOMBRE'].nunique() if 'IES_PADRE_NOMBRE' in ant else ant['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'].nunique():>10,}")
    print(f"  programas             {ant['CÓDIGO SNIES DEL PROGRAMA'].nunique():>10,}")
    print(f"  municipios con oferta {ant[muni].nunique():>10,}")

    bc = ant[ant[muni].isin(BAJO_CAUCA)]
    print(f"Bajo Cauca matrícula    {int(bc['MATRICULADOS'].sum()):>10,}")
    for m in BAJO_CAUCA:
        s = bc[bc[muni] == m]
        if len(s):
            print(f"   {m:<12} {int(s['MATRICULADOS'].sum()):>7,}  programas {s['CÓDIGO SNIES DEL PROGRAMA'].nunique():>3}"
                  f"  IES {s['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'].nunique():>2}")
        else:
            print(f"   {m:<12} {'0':>7}  sin oferta")
    print(f"   TyT del Bajo Cauca   {int(bc.loc[bc['NIVEL DE FORMACIÓN'].isin(TYT),'MATRICULADOS'].sum()):>7,}")
    print(f"   posgrado             {int(bc.loc[bc['NIVEL ACADÉMICO']=='Posgrado','MATRICULADOS'].sum()):>7,}")
    return ant, bc


def detalle_programas(bc):
    muni = "MUNICIPIO DE OFERTA DEL PROGRAMA"
    print("\n--- programas del Bajo Cauca 2025 ---")
    cols = ["INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)", "PROGRAMA ACADÉMICO",
            "NIVEL DE FORMACIÓN", muni, "MATRICULADOS"]
    t = bc.groupby(cols[:-1], as_index=False)["MATRICULADOS"].sum()
    t = t.sort_values("MATRICULADOS", ascending=False)
    for _, r in t.iterrows():
        print(f"{r[cols[0]][:34]:<34} | {r['NIVEL DE FORMACIÓN'][:12]:<12} | "
              f"{str(r['PROGRAMA ACADÉMICO'])[:42]:<42} | {r[muni]:<10} | {int(r['MATRICULADOS']):>5}")
    print("\nÁreas de conocimiento (matrícula):")
    for k, v in bc.groupby("ÁREA DE CONOCIMIENTO")["MATRICULADOS"].sum().sort_values(ascending=False).items():
        print(f"   {str(k)[:52]:<52} {int(v):>6,}")


def main():
    d25 = leer("snies_matriculados_2025.xlsx")
    ant25, bc25 = resumen(d25, "2025")
    detalle_programas(bc25)

    prev = DATA / "matriculados_2024.xlsx"
    if prev.exists():
        d24 = leer("matriculados_2024.xlsx")
        resumen(d24, "2024 (control)")


if __name__ == "__main__":
    main()
