#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae población 17-21 (2024, área Total) por municipio de Antioquia y por
subregión desde las proyecciones municipales DANE (CNPV 2018)
→ data/pob_antioquia_17_21.json"""
import json, re, unicodedata
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
HOJA = "PobMunicipalxÁreaSexoEdad"

def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()

# fila 8 = subencabezados de edad ("Hombres 17 años", "Mujeres 21 años", …)
labels = pd.read_excel(DATA / "dane_pob_mun.xlsx", sheet_name=HOJA, header=None,
                       skiprows=8, nrows=1).iloc[0].tolist()
edad_idx = [i for i, lb in enumerate(labels)
            if re.match(r"^(Hombres|Mujeres) (17|18|19|20|21) años$", str(lb).strip())]
print("columnas de edad 17-21:", len(edad_idx))
usecols = [0, 2, 3, 4, 5] + edad_idx  # DP, MPIO, DPMP(nombre), AÑO, ÁREA + edades
df = pd.read_excel(DATA / "dane_pob_mun.xlsx", sheet_name=HOJA, header=None,
                   skiprows=9, usecols=usecols)
df.columns = ["DP", "MPIO", "NOM", "ANIO", "AREA"] + [f"e{i}" for i in range(len(edad_idx))]
df = df[(df["DP"].astype(str).str.zfill(2) == "05")
        & (pd.to_numeric(df["ANIO"], errors="coerce") == 2024)
        & (df["AREA"].astype(str).str.strip() == "Total")].copy()
ecols = [c for c in df.columns if c.startswith("e")]
df["P1721"] = df[ecols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
print("municipios Antioquia 2024:", len(df), "| población 17-21 total:", int(df["P1721"].sum()))

sub_raw = json.load(open(DATA / "subregiones.json"))
sub_map = {norm(k): v.replace("Aburra", "Aburrá") for k, v in sub_raw.items()}
sub_map["san pedro de los milagros"] = sub_map.get("san pedro", "Norte")
sub_map["santafe de antioquia"] = sub_map.get("santa fe de antioquia", "Occidente")
sub_map["donmatias"] = sub_map.get("don matias", "Norte")
sub_map["penol"] = sub_map.get("el penol", "Oriente")
sub_map["retiro"] = sub_map.get("el retiro", "Oriente")
sub_map["san andres de cuerquia"] = sub_map.get("san andres", "Norte")
mun_out, sub_out, sin = {}, {}, []
for r in df.itertuples():
    code = str(r.MPIO).strip().zfill(5)
    mun_out[code] = int(r.P1721)
    sr = sub_map.get(norm(r.NOM))
    if sr: sub_out[sr] = sub_out.get(sr, 0) + int(r.P1721)
    else: sin.append(str(r.NOM))
print("sin subregión:", sin)
print("subregiones:", sub_out)
json.dump({"municipios": mun_out, "subregiones": sub_out},
          open(DATA / "pob_antioquia_17_21.json", "w"))
print("OK → pob_antioquia_17_21.json")
