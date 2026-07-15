#!/usr/bin/env python3
"""Audita el atlas territorial contra los XLSX oficiales de SNIES y DANE.

Uso:
  python3 scripts/auditar_atlas.py
  python3 scripts/auditar_atlas.py --snies /ruta/matriculados_2024.xlsx \
      --dane /ruta/dane_pob_mun.xlsx

No modifica archivos: imprime un informe JSON y termina con código 1 si encuentra
diferencias entre las fuentes crudas, public/datos.json y public/mapa.js.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def norm(value):
    value = unicodedata.normalize("NFD", str(value))
    return "".join(c for c in value if unicodedata.category(c) != "Mn").lower().strip()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snies_header(path):
    excel = pd.ExcelFile(path)
    for sheet in excel.sheet_names:
        if "NDICE" in sheet.upper():
            continue
        preview = pd.read_excel(excel, sheet_name=sheet, header=None, nrows=15)
        for row_index, row in preview.iterrows():
            values = [str(x).strip().upper() for x in row.tolist()]
            if "AÑO" in values and "MATRICULADOS" in values:
                return sheet, row_index
    raise ValueError("No se encontró el encabezado de matriculados en el archivo SNIES")


LEVELS = {
    "formacion tecnica profesional": ("Técnica profesional", "Pregrado"),
    "tecnica profesional": ("Técnica profesional", "Pregrado"),
    "tecnologico": ("Tecnológica", "Pregrado"),
    "tecnologica": ("Tecnológica", "Pregrado"),
    "universitario": ("Universitaria", "Pregrado"),
    "universitaria": ("Universitaria", "Pregrado"),
    "especializacion tecnico profesional": ("Especialización", "Posgrado"),
    "especializacion tecnica profesional": ("Especialización", "Posgrado"),
    "especializacion tecnologica": ("Especialización", "Posgrado"),
    "especializacion universitaria": ("Especialización", "Posgrado"),
    "especializacion medico quirurgica": ("Especialización", "Posgrado"),
    "especializacion medica quirurgica": ("Especialización", "Posgrado"),
    "maestria": ("Maestría", "Posgrado"),
    "doctorado": ("Doctorado", "Posgrado"),
}
TYT = {"Técnica profesional", "Tecnológica"}


def load_snies(path):
    sheet, header = snies_header(path)
    frame = pd.read_excel(path, sheet_name=sheet, header=header)
    frame.columns = [" ".join(str(c).upper().split()) for c in frame.columns]
    frame["MATRICULADOS"] = pd.to_numeric(frame["MATRICULADOS"], errors="coerce").fillna(0)
    frame = frame[
        frame["DEPARTAMENTO DE OFERTA DEL PROGRAMA"].astype(str).str.strip().str.upper() == "ANTIOQUIA"
    ].copy()
    mapped = frame["NIVEL DE FORMACIÓN"].map(lambda value: LEVELS.get(norm(value)))
    unknown = sorted(frame.loc[mapped.isna(), "NIVEL DE FORMACIÓN"].dropna().astype(str).unique())
    frame = frame[mapped.notna()].copy()
    frame["NIVEL_G"] = mapped.dropna().map(lambda value: value[0])
    frame["NIVEL_ACAD"] = mapped.dropna().map(lambda value: value[1])
    semesters = frame.groupby("SEMESTRE")["MATRICULADOS"].sum().astype(int).to_dict()
    peak = max(semesters, key=semesters.get)
    frame = frame[frame["SEMESTRE"] == peak].copy()
    frame["CODE"] = frame["CÓDIGO DEL MUNICIPIO (PROGRAMA)"].map(
        lambda value: str(int(float(value))).zfill(5)
    )
    return frame, semesters, peak, unknown


def load_dane(path):
    sheet = "PobMunicipalxÁreaSexoEdad"
    labels = pd.read_excel(path, sheet_name=sheet, header=None, skiprows=8, nrows=1).iloc[0].tolist()
    ages = [
        index for index, label in enumerate(labels)
        if re.match(r"^(Hombres|Mujeres) (17|18|19|20|21) años$", str(label).strip())
    ]
    frame = pd.read_excel(path, sheet_name=sheet, header=None, skiprows=9, usecols=[0, 2, 3, 4, 5] + ages)
    frame.columns = ["DP", "MPIO", "NOM", "ANIO", "AREA"] + [f"e{i}" for i in range(len(ages))]
    frame = frame[
        (frame["DP"].astype(str).str.zfill(2) == "05")
        & (pd.to_numeric(frame["ANIO"], errors="coerce") == 2024)
        & (frame["AREA"].astype(str).str.strip() == "Total")
    ].copy()
    frame["CODE"] = frame["MPIO"].map(lambda value: str(int(float(value))).zfill(5))
    frame["P1721"] = frame[[c for c in frame if c.startswith("e")]].apply(
        pd.to_numeric, errors="coerce"
    ).sum(axis=1).astype(int)
    return frame, len(ages)


def subregion_map(data):
    result = {norm(key): value for key, value in data["subregiones"]["mapa"].items()}
    aliases = {
        "san pedro de los milagros": ("san pedro", "Norte"),
        "santafe de antioquia": ("santa fe de antioquia", "Occidente"),
        "donmatias": ("don matias", "Norte"),
        "penol": ("el penol", "Oriente"),
        "retiro": ("el retiro", "Oriente"),
        "san andres de cuerquia": ("san andres", "Norte"),
    }
    for alias, (source, fallback) in aliases.items():
        result[alias] = result.get(source, fallback)
    return result


def municipal_rows(frame):
    rows = {}
    for code, group in frame.groupby("CODE"):
        rows[code] = {
            "municipio": str(group["MUNICIPIO DE OFERTA DEL PROGRAMA"].iloc[0]).strip(),
            "matricula24": int(group["MATRICULADOS"].sum()),
            "tyt24": int(group.loc[group["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum()),
            "posgrado24": int(group.loc[group["NIVEL_ACAD"] == "Posgrado", "MATRICULADOS"].sum()),
            "ies": int(group["CÓDIGO DE LA INSTITUCIÓN"].nunique()),
            "programas": int(group["CÓDIGO SNIES DEL PROGRAMA"].nunique()),
        }
    return rows


def audit(args):
    data = json.loads(args.datos.read_text())
    snies, semesters, peak, unknown = load_snies(args.snies)
    dane, age_columns = load_dane(args.dane)
    regions = subregion_map(data)
    snies["SUB"] = snies["MUNICIPIO DE OFERTA DEL PROGRAMA"].map(lambda value: regions.get(norm(value)))
    dane["SUB"] = dane["NOM"].map(lambda value: regions.get(norm(value)))
    errors = []

    if unknown:
        errors.append({"niveles_sin_clasificar": unknown})
    for name, frame in (("SNIES", snies), ("DANE", dane)):
        missing = frame.loc[frame["SUB"].isna(), "CODE"].drop_duplicates().tolist()
        if missing:
            errors.append({f"municipios_sin_subregion_{name.lower()}": missing})

    raw_munis = municipal_rows(snies)
    public_munis = {str(row["codigo"]).zfill(5): row for row in data["municipios"]}
    if set(raw_munis) != set(public_munis):
        errors.append({"codigos_municipales": {
            "solo_fuente": sorted(set(raw_munis) - set(public_munis)),
            "solo_publicado": sorted(set(public_munis) - set(raw_munis)),
        }})
    for code in sorted(set(raw_munis) & set(public_munis)):
        source, published = raw_munis[code], public_munis[code]
        fields = ("matricula24", "tyt24", "posgrado24", "ies", "programas")
        diff = {field: [source[field], published[field]] for field in fields if source[field] != published[field]}
        if norm(source["municipio"]) != norm(published["municipio"]):
            diff["municipio"] = [source["municipio"], published["municipio"]]
        if diff:
            errors.append({"municipio": code, "diferencias": diff})

    public_levels = next(row for row in data["serie"] if row["anio"] == 2024)["niveles"]
    raw_levels = snies.groupby("NIVEL_G")["MATRICULADOS"].sum().astype(int).to_dict()
    if raw_levels != public_levels:
        errors.append({"niveles": {"fuente": raw_levels, "publicado": public_levels}})

    population = dane.groupby("SUB")["P1721"].sum().astype(int).to_dict()
    pregrad = snies.loc[snies["NIVEL_ACAD"] == "Pregrado"].groupby("SUB")["MATRICULADOS"].sum().astype(int).to_dict()
    for row in data["subregiones"]["cobertura"]:
        if "total" in row["subregion"].lower():
            numerator, denominator = sum(pregrad.values()), int(dane["P1721"].sum())
        else:
            numerator, denominator = pregrad.get(row["subregion"]), population.get(row["subregion"])
        expected = round(100 * numerator / denominator, 1)
        actual = (row["pregrado"], row["pob_17_21"], row["cobertura"])
        if actual != (numerator, denominator, expected):
            errors.append({"cobertura": row["subregion"], "fuente": [numerator, denominator, expected], "publicado": actual})

    for row in data["subregiones"]["agg"]:
        group = snies[snies["SUB"] == row["subregion"]]
        source = {
            "matricula24": int(group["MATRICULADOS"].sum()),
            "tyt24": int(group.loc[group["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum()),
            "posgrado24": int(group.loc[group["NIVEL_ACAD"] == "Posgrado", "MATRICULADOS"].sum()),
            "ies": int(group["CÓDIGO DE LA INSTITUCIÓN"].nunique()),
            "programas": int(group["CÓDIGO SNIES DEL PROGRAMA"].nunique()),
            "municipios_oferta": int(group["CODE"].nunique()),
        }
        diff = {field: [source[field], row[field]] for field in source if source[field] != row[field]}
        if diff:
            errors.append({"subregion": row["subregion"], "diferencias": diff})

    geometry = set(re.findall(r'"c":"(05\d{3})"', args.mapa.read_text()))
    dane_codes = set(dane["CODE"])
    if geometry != dane_codes:
        errors.append({"geometria": {
            "faltantes": sorted(dane_codes - geometry),
            "sobrantes": sorted(geometry - dane_codes),
        }})

    eligible = [
        (100 * row["tyt24"] / row["matricula24"], row["municipio"])
        for row in raw_munis.values() if row["matricula24"] >= 100
    ]
    eligible.sort(reverse=True)
    return {
        "estado": "correcto" if not errors else "diferencias_encontradas",
        "fecha_auditoria": date.today().isoformat(),
        "fuentes": {
            "snies_sha256": sha256(args.snies),
            "dane_sha256": sha256(args.dane),
        },
        "metodo": {
            "semestres_snies": {str(key): value for key, value in semesters.items()},
            "semestre_pico": int(peak),
            "columnas_edad_dane": age_columns,
        },
        "resultados": {
            "matricula": int(snies["MATRICULADOS"].sum()),
            "pregrado": int(snies.loc[snies["NIVEL_ACAD"] == "Pregrado", "MATRICULADOS"].sum()),
            "poblacion_17_21": int(dane["P1721"].sum()),
            "municipios_con_oferta": len(raw_munis),
            "municipios_sin_oferta": len(dane_codes - set(raw_munis)),
            "geometrias": len(geometry),
            "diferencias_municipales": sum(1 for error in errors if "municipio" in error),
            "diferencias_subregionales": sum(1 for error in errors if "subregion" in error),
            "diferencias_cobertura": sum(1 for error in errors if "cobertura" in error),
            "mayor_tyt_100_matriculados": {
                "municipio": eligible[0][1], "porcentaje": round(eligible[0][0], 1)
            },
        },
        "errores": errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snies", type=Path, default=ROOT / "data/matriculados_2024.xlsx")
    parser.add_argument("--dane", type=Path, default=ROOT / "data/dane_pob_mun.xlsx")
    parser.add_argument("--datos", type=Path, default=ROOT / "public/datos.json")
    parser.add_argument("--mapa", type=Path, default=ROOT / "public/mapa.js")
    args = parser.parse_args()
    report = audit(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["estado"] == "correcto" else 1


if __name__ == "__main__":
    sys.exit(main())
