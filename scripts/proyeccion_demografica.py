"""Proyección de población 17-21 por subregión de Antioquia, 2018-2042.

Extiende la lógica de preparar_poblacion.py (que solo saca 2024) a toda la
serie de proyecciones municipales DANE (CNPV 2018, área Total) y agrega por
subregión → data/proyeccion_17_21.json
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
HOJA = "PobMunicipalxÁreaSexoEdad"


def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


labels = pd.read_excel(DATA / "dane_pob_mun.xlsx", sheet_name=HOJA, header=None,
                       skiprows=8, nrows=1).iloc[0].tolist()
edad_idx = [i for i, lb in enumerate(labels)
            if re.match(r"^(Hombres|Mujeres) (17|18|19|20|21) años$", str(lb).strip())]
usecols = [0, 2, 3, 4, 5] + edad_idx
df = pd.read_excel(DATA / "dane_pob_mun.xlsx", sheet_name=HOJA, header=None,
                   skiprows=9, usecols=usecols)
df.columns = ["DP", "MPIO", "NOM", "ANIO", "AREA"] + [f"e{i}" for i in range(len(edad_idx))]
df["ANIO"] = pd.to_numeric(df["ANIO"], errors="coerce")
df = df[(df["DP"].astype(str).str.zfill(2) == "05")
        & df["ANIO"].between(2018, 2042)
        & (df["AREA"].astype(str).str.strip() == "Total")].copy()
ecols = [c for c in df.columns if c.startswith("e")]
df["P1721"] = df[ecols].apply(pd.to_numeric, errors="coerce").sum(axis=1)

sub_raw = json.load(open(DATA / "subregiones.json"))
sub_map = {norm(k): v.replace("Aburra", "Aburrá") for k, v in sub_raw.items()}
for alias, canon in [("san pedro de los milagros", "san pedro"),
                     ("santafe de antioquia", "santa fe de antioquia"),
                     ("donmatias", "don matias"), ("penol", "el penol"),
                     ("retiro", "el retiro")]:
    if canon in sub_map:
        sub_map[alias] = sub_map[canon]
# los dos nombres largos del DANE que no aparecen así en subregiones.json (ambos del Norte)
sub_map.setdefault("san pedro de los milagros", "Norte")
sub_map.setdefault("san andres de cuerquia", "Norte")

df["SUB"] = df["NOM"].map(lambda n: sub_map.get(norm(n)))
sin = df[df["SUB"].isna()]["NOM"].unique().tolist()
if sin:
    print("municipios sin subregión:", sin)

agg = df.groupby(["ANIO", "SUB"])["P1721"].sum().unstack().astype(int)
total = df.groupby("ANIO")["P1721"].sum().astype(int)

out = {
    "anios": [int(a) for a in total.index],
    "total": {int(a): int(v) for a, v in total.items()},
    "subregiones": {s: {int(a): int(v) for a, v in agg[s].items()} for s in agg.columns},
    "nota": "Población proyectada de 17 a 21 años, área Total, proyecciones municipales DANE CNPV-2018 (2018-2042).",
}
(DATA / "proyeccion_17_21.json").write_text(json.dumps(out, ensure_ascii=False))
p24, p35, p42 = total.get(2024), total.get(2035), total.get(2042)
print(f"Antioquia 17-21 · 2018: {total.get(2018):,} · 2024: {p24:,} · 2030: {total.get(2030):,} · 2035: {p35:,} · 2042: {p42:,}")
print(f"Δ 2024→2035: {100*(p35-p24)/p24:.1f} % · Δ 2024→2042: {100*(p42-p24)/p24:.1f} %")
for s in agg.columns:
    print(f"  {s}: 2024 {agg[s][2024]:,} → 2035 {agg[s][2035]:,} ({100*(agg[s][2035]-agg[s][2024])/agg[s][2024]:+.1f} %)")
