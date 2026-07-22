#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MaterIA Gris — Retorno salarial por PROGRAMA (OLE, corte 2023).

Construye data/ole_programas.json: IBC estimado promedio por programa×IES
de las IES con domicilio en Antioquia (mismo universo que procesar.py:
excluye SENA y UNAD por domicilio fuera del departamento).

Fuentes locales:
  - data/ole_base_ibc_2023.xlsx (Base_IBC_2023): microdato agregado
    programa × IES × sexo × año de grado × rango de ingreso. Es la ÚNICA
    fuente OLE local con nivel programa. Cotizantes a seguridad social
    en 2023 en su máximo nivel de formación; años de grado 2001-2022.
  - data/ole_anexo_ibc_2020_2023.xlsx: SOLO agregados nacionales por
    nivel de formación / CINE / sexo / periodo — no trae programa ni IES,
    por eso la tendencia por programa (delta) queda en null. Se usa aquí
    únicamente para verificar esa limitación y documentar la cohorte.
  - data/matriculados_2024.xlsx: define las IES con domicilio en Antioquia
    (misma regla que procesar.py).
  - data/graduados_2022.xlsx: denominador de la tasa de vinculación
    (vinculados 2023 con grado 2022 / graduados SNIES 2022), la misma
    definición que usa el sitio a nivel de nivel de formación y área.

Metodología del IBC promedio: el OLE reporta el ingreso en 7 bandas de
SMMLV; se toma el punto medio de cada banda (banda abierta «Más de 9
SMMLV» → 10,5) y se pondera por graduados cotizantes. Con esos puntos
medios este script REPRODUCE EXACTAMENTE las cifras por área que ya
publica el sitio (Salud 3,61 · Ingeniería 3,10 · Economía 2,46 …).

Cohorte «de enganche»: graduados 2018-2022 que cotizaron en 2023
(la misma ventana `recientes` de procesar.py).

Autor: Santiago Jiménez Londoño.
"""
import json, re, unicodedata
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
SMMLV_2023 = 1_160_000   # salario mínimo mensual legal vigente 2023
ANIO_COHORTE_MIN = 2018  # «recientes»: grado 2018-2022, cotizantes 2023
# Mínimo de cotizantes recientes por programa. Se mantiene en 20 porque las
# residencias médicas (los IBC más altos del departamento) tienen cohortes de
# 20-40 cotizantes: subir el umbral las sacaría del tablero. Tamaños medidos
# del JSON: n≥20 → ~177 KB · n≥30 → ~148 KB · n≥40 → ~125 KB.
UMBRAL_N = 20
UMBRAL_G22 = 20          # mínimo de graduados 2022 para publicar vinculación

# Punto medio de cada banda de ingreso (en SMMLV). La banda abierta se fija
# en 10,5 porque con ese valor el promedio ponderado por área coincide con
# lo que el sitio ya publica (Salud 3,61 SMMLV, etc.).
PUNTO_MEDIO = {
    "1 SMMLV": 1.0,
    "Entre 1 y 1,5 SMMLV": 1.25,
    "Entre 1,5 y 2,5 SMMLV": 2.0,
    "Entre 2,5 y 4 SMMLV": 3.25,
    "Entre 4 y 6 SMMLV": 5.0,
    "Entre 6 y 9 SMMLV": 7.5,
    "Más de 9 SMMLV": 10.5,
}

def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()

def clave(s):
    """Llave de programa robusta: sin tildes, sin puntuación, espacios colapsados.
    Une variantes del mismo programa («… - MBA» vs «…  MBA »)."""
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", norm(s)).split())

def titulo(s):
    """Título legible para nombres de programa (la base OLE viene en mayúsculas)."""
    t = " ".join(str(s).split()).title()
    for a, b in ((" De ", " de "), (" Del ", " del "), (" La ", " la "), (" Las ", " las "),
                 (" Los ", " los "), (" El ", " el "), (" Y ", " y "), (" En ", " en "),
                 (" E ", " e "), (" A ", " a "), (" Para ", " para "), (" Con ", " con ")):
        t = t.replace(a, b)
    return t

# Nivel de formación canónico — mismo diccionario de procesar.py, más la
# etiqueta llana «Especialización» que trae la base OLE (incluye la
# médico-quirúrgica como nivel propio del sitio: Especialización).
NIVELES = {
    "formacion tecnica profesional": "Técnica profesional",
    "tecnica profesional": "Técnica profesional",
    "tecnologico": "Tecnológica", "tecnologica": "Tecnológica",
    "universitario": "Universitaria", "universitaria": "Universitaria",
    "especializacion": "Especialización",
    "especializacion tecnico profesional": "Especialización",
    "especializacion tecnica profesional": "Especialización",
    "especializacion tecnologica": "Especialización",
    "especializacion universitaria": "Especialización",
    "especializacion medico quirurgica": "Especialización",
    "especializacion medica quirurgica": "Especialización",
    "maestria": "Maestría", "doctorado": "Doctorado",
}

def nombre_ies(nombre):
    return (str(nombre).strip().title().strip("-").replace(" De ", " de ")
            .replace(" Y ", " y ").replace(" La ", " la ")
            .replace(" Del ", " del ").replace(" En ", " en "))

# ---------- 0. Verificación: el anexo 2020-2023 no trae nivel programa ----------
anexo = pd.ExcelFile(DATA / "ole_anexo_ibc_2020_2023.xlsx")
hojas_datos = [h for h in anexo.sheet_names if h.startswith("IBC")]
assert not any("programa" in norm(h) or "ies" in norm(h) for h in anexo.sheet_names), \
    "El anexo ahora trae nivel programa: revisar si permite calcular delta."
print("Anexo OLE 2020-2023: hojas", hojas_datos)
print("→ solo agregados nacionales (nivel formación / CINE / sexo / periodo);")
print("  sin programa ni IES: la tendencia por programa (delta) queda en null.")

# ---------- 1. IES con domicilio en Antioquia (misma regla que procesar.py) ----------
xl = pd.ExcelFile(DATA / "matriculados_2024.xlsx")
hoja = hdr = None
for h in xl.sheet_names:
    if "NDICE" in h.upper():
        continue
    peek = pd.read_excel(xl, sheet_name=h, header=None, nrows=15)
    for i, row in peek.iterrows():
        vals = [str(x).strip().upper() for x in row.tolist()]
        if "AÑO" in vals and any(v.startswith("MATRICULADOS") for v in vals):
            hoja, hdr = h, i
            break
    if hoja:
        break
m24 = pd.read_excel(xl, sheet_name=hoja, header=hdr)
m24.columns = [" ".join(str(c).upper().split()) for c in m24.columns]
m24 = m24[m24["DEPARTAMENTO DE OFERTA DEL PROGRAMA"].astype(str).str.strip().str.upper() == "ANTIOQUIA"]
ant = m24[m24["DEPARTAMENTO DE DOMICILIO DE LA IES"].astype(str).str.strip() == "Antioquia"]
ies_ant_codes = set(pd.to_numeric(ant["CÓDIGO DE LA INSTITUCIÓN"], errors="coerce").dropna().astype(int))
print("IES con domicilio en Antioquia:", len(ies_ant_codes), "(excluye SENA y UNAD)")

# ---------- 2. Base OLE por programa: cotizantes 2023, IES antioqueñas ----------
ole = pd.read_excel(DATA / "ole_base_ibc_2023.xlsx", sheet_name="Base_IBC_2023", header=8)
ole.columns = [" ".join(str(c).upper().split()) for c in ole.columns]
ole["GRADUADOS"] = pd.to_numeric(ole["GRADUADOS"], errors="coerce").fillna(0)
ole["COD_IES"] = pd.to_numeric(ole["CÓDIGO DE LA INSTITUCIÓN"], errors="coerce")
ole["ANIO_GRADO"] = pd.to_numeric(ole["AÑO DE GRADO"], errors="coerce")
ole["NIVEL_G"] = ole["NIVEL DE FORMACIÓN"].map(lambda x: NIVELES.get(norm(x)))
assert ole["NIVEL_G"].notna().all(), "Nivel de formación sin mapear en la base OLE"
ole["MID"] = ole["INGRESO"].map(PUNTO_MEDIO)
assert ole["MID"].notna().all(), "Banda de ingreso sin punto medio: " + str(ole.loc[ole["MID"].isna(), "INGRESO"].unique())
ole_ant = ole[ole["COD_IES"].isin(ies_ant_codes)].copy()
rec = ole_ant[ole_ant["ANIO_GRADO"] >= ANIO_COHORTE_MIN].copy()
print("Cotizantes 2023 (grado 2001-2022, IES ant.):", int(ole_ant["GRADUADOS"].sum()))
print(f"Cohorte de enganche (grado {ANIO_COHORTE_MIN}-2022):", int(rec["GRADUADOS"].sum()))

# Verificación de coherencia con el sitio: punto medio ponderado por área,
# pregrado reciente — debe dar Salud ≈ 3,61 SMMLV (lo que publica index.html).
chk = rec[rec["NIVEL ACADÉMICO"] == "Pregrado"]
area_chk = chk.groupby("ÁREA DE CONOCIMIENTO").apply(
    lambda s: (s["MID"] * s["GRADUADOS"]).sum() / s["GRADUADOS"].sum(), include_groups=False).round(2)
print("Verificación por área (pregrado, debe coincidir con el sitio):")
for a, v in area_chk.items():
    print(f"  {a[:45]:45s} {v:.2f} SMMLV")
assert abs(area_chk.get("Ciencias de la salud", 0) - 3.61) < 0.03, "Salud no da ≈3,61 SMMLV: revisar universo/puntos medios"

# ---------- 3. Graduados SNIES 2022 por programa (denominador de vinculación) ----------
xg = pd.ExcelFile(DATA / "graduados_2022.xlsx")
hoja = hdr = None
for h in xg.sheet_names:
    if "NDICE" in h.upper():
        continue
    peek = pd.read_excel(xg, sheet_name=h, header=None, nrows=15)
    for i, row in peek.iterrows():
        vals = [str(x).strip().upper() for x in row.tolist()]
        if "AÑO" in vals and any(v.startswith("GRADUADOS") for v in vals):
            hoja, hdr = h, i
            break
    if hoja:
        break
g22 = pd.read_excel(xg, sheet_name=hoja, header=hdr)
g22.columns = [" ".join(str(c).upper().split()) for c in g22.columns]
g22["GRADUADOS"] = pd.to_numeric(g22["GRADUADOS"], errors="coerce").fillna(0)
g22["COD_IES"] = pd.to_numeric(g22["CÓDIGO DE LA INSTITUCIÓN"], errors="coerce")
g22 = g22[g22["COD_IES"].isin(ies_ant_codes)].copy()
g22["NIVEL_G"] = g22["NIVEL DE FORMACIÓN"].map(lambda x: NIVELES.get(norm(x)))
g22 = g22[g22["NIVEL_G"].notna()]
# Llave programa×IES×nivel por nombre normalizado (los códigos SNIES pueden
# variar entre jornadas/renovaciones del mismo programa).
g22["KEY"] = list(zip(g22["COD_IES"].astype(int), g22["PROGRAMA ACADÉMICO"].map(clave), g22["NIVEL_G"]))
grad22_prog = g22.groupby("KEY")["GRADUADOS"].sum()
print("Programas con graduados SNIES 2022 (IES ant.):", len(grad22_prog))

# ---------- 4. Agregación por programa × IES × nivel ----------
rec["KEY"] = list(zip(rec["COD_IES"].astype(int), rec["PROGRAMA ACADÉMICO"].map(clave), rec["NIVEL_G"]))
vin22 = ole_ant[ole_ant["ANIO_GRADO"] == 2022].copy()
vin22["KEY"] = list(zip(vin22["COD_IES"].astype(int), vin22["PROGRAMA ACADÉMICO"].map(clave), vin22["NIVEL_G"]))
vin22_prog = vin22.groupby("KEY")["GRADUADOS"].sum()

programas = []
for key, sub in rec.groupby("KEY"):
    n = int(sub["GRADUADOS"].sum())
    if n < UMBRAL_N:
        continue
    smmlv_prom = (sub["MID"] * sub["GRADUADOS"]).sum() / n
    # Tasa de vinculación: cotizantes 2023 con grado 2022 / graduados SNIES 2022.
    vinc = None
    v22, gr22 = float(vin22_prog.get(key, 0)), float(grad22_prog.get(key, 0))
    if gr22 >= UMBRAL_G22:
        t = 100 * v22 / gr22
        # >110 % delata cambio de nombre/código del programa: no se publica.
        vinc = round(min(t, 100.0), 1) if t <= 110 else None
    programas.append({
        "programa": titulo(sub["PROGRAMA ACADÉMICO"].iloc[0]),
        "ies": nombre_ies(sub["INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)"].iloc[0]),
        "nivel": key[2],
        "ibc": int(round(smmlv_prom * SMMLV_2023)),
        "smmlv": round(smmlv_prom, 2),
        "n": n,
        "vinc": vinc,
        # El anexo 2020-2023 solo trae agregados nacionales (sin programa):
        # no hay serie longitudinal por programa para calcular tendencia.
        "delta": None,
    })
programas.sort(key=lambda p: -p["ibc"])
print(f"Programas×IES con n≥{UMBRAL_N} cotizantes recientes:", len(programas))
print("  con tasa de vinculación publicable:", sum(1 for p in programas if p["vinc"] is not None))

# ---------- 5. Salida ----------
salida = {
    "corte": "IBC estimado 2023 (OLE base por programa, corte 2023; anexo 2020-2023 solo agrega nacional)",
    "nota": ("Graduados 2018-2022 de IES con domicilio en Antioquia (excluye SENA y UNAD) que cotizaron a "
             "seguridad social en 2023 en su máximo nivel de formación. IBC = punto medio ponderado de las "
             "7 bandas de ingreso del OLE (banda abierta «Más de 9 SMMLV» → 10,5); misma metodología del "
             "gráfico por área del sitio. vinc = cotizantes 2023 con grado 2022 / graduados SNIES 2022 del "
             "mismo programa (solo si ≥20 graduados). delta = null: el anexo OLE 2020-2023 no trae nivel "
             "programa, no hay serie longitudinal para tendencia."),
    "smmlv": SMMLV_2023,
    "umbral_n": UMBRAL_N,
    "programas": programas,
}
out = DATA / "ole_programas.json"
out.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("Escrito", out, f"({out.stat().st_size/1024:.1f} KB)")

print("\nTop 10 por IBC:")
for p in programas[:10]:
    print(f"  {p['smmlv']:5.2f} SMMLV  n={p['n']:4d}  {p['programa'][:48]} — {p['ies'][:42]} ({p['nivel']})")
print("Bottom 5 por IBC:")
for p in programas[-5:]:
    print(f"  {p['smmlv']:5.2f} SMMLV  n={p['n']:4d}  {p['programa'][:48]} — {p['ies'][:42]} ({p['nivel']})")
