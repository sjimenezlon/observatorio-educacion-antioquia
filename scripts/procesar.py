#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Observatorio de Educación Superior de Antioquia — todos los niveles
(pregrado: técnica profesional, tecnológica, universitaria; posgrado:
especializaciones, maestría, doctorado), con lente de detalle TyT.
Procesa bases consolidadas SNIES (MEN), Saber TyT (ICFES), OLE y MinCiencias.
Autor: Santiago Jiménez Londoño.
"""
import json, glob, unicodedata
from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
OUT  = Path(__file__).resolve().parent.parent / "public"
OUT.mkdir(exist_ok=True)

def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()

# nivel de formación canónico (tolera variantes entre vigencias) y su nivel académico
NIVELES = {
    "formacion tecnica profesional": ("Técnica profesional", "Pregrado"),
    "tecnica profesional": ("Técnica profesional", "Pregrado"),
    "tecnologico": ("Tecnológica", "Pregrado"), "tecnologica": ("Tecnológica", "Pregrado"),
    "universitario": ("Universitaria", "Pregrado"), "universitaria": ("Universitaria", "Pregrado"),
    "especializacion tecnico profesional": ("Especialización", "Posgrado"),
    "especializacion tecnica profesional": ("Especialización", "Posgrado"),
    "especializacion tecnologica": ("Especialización", "Posgrado"),
    "especializacion universitaria": ("Especialización", "Posgrado"),
    "especializacion medico quirurgica": ("Especialización", "Posgrado"),
    "especializacion medica quirurgica": ("Especialización", "Posgrado"),
    "maestria": ("Maestría", "Posgrado"), "doctorado": ("Doctorado", "Posgrado"),
}
TYT = {"Técnica profesional", "Tecnológica"}
ORDEN_NIVEL = ["Técnica profesional", "Tecnológica", "Universitaria", "Especialización", "Maestría", "Doctorado"]

def hoja_datos(archivo, valor):
    xl = pd.ExcelFile(DATA / archivo)
    for hoja in xl.sheet_names:
        if "NDICE" in hoja.upper():
            continue
        peek = pd.read_excel(xl, sheet_name=hoja, header=None, nrows=15)
        for i, row in peek.iterrows():
            vals = [str(x).strip().upper() for x in row.tolist()]
            if "AÑO" in vals and any(v.startswith(valor) for v in vals):
                return hoja, i
    raise ValueError(f"No encontré encabezado con {valor} en {archivo}")

def leer_snies(archivo, valor, semestre_pico=False):
    hoja, hdr = hoja_datos(archivo, valor)
    df = pd.read_excel(DATA / archivo, sheet_name=hoja, header=hdr)
    df.columns = [" ".join(str(c).upper().split()) for c in df.columns]
    df = df.rename(columns={"METODOLOGÍA": "MODALIDAD", "CARACTER IES": "CARÁCTER IES",
                            "ID ÁREA DE CONOCIMIENTO": "ID ÁREA", "GÉNERO": "SEXO"})
    df = df.rename(columns={c: valor for c in df.columns if c.startswith(valor) and c != valor})
    if "SECTOR IES" in df.columns:
        df["SECTOR IES"] = df["SECTOR IES"].astype(str).str.strip().str.capitalize().replace({"Privado": "Privada"})
    if "SEXO" in df.columns:
        df["SEXO"] = df["SEXO"].astype(str).str.strip().str.capitalize()
    df[valor] = pd.to_numeric(df[valor], errors="coerce").fillna(0)
    df = df[df["DEPARTAMENTO DE OFERTA DEL PROGRAMA"].astype(str).str.strip().str.upper() == "ANTIOQUIA"]
    niv = df["NIVEL DE FORMACIÓN"].map(lambda x: NIVELES.get(norm(x)))
    df = df[niv.notna()].copy()
    df["NIVEL_G"] = niv.dropna().map(lambda t: t[0])
    df["NIVEL_ACAD"] = niv.dropna().map(lambda t: t[1])
    if semestre_pico and "SEMESTRE" in df.columns:
        # La matrícula oficial anual ≈ semestre con mayor total (sumar semestres duplica personas)
        tot = df.groupby("SEMESTRE")[valor].sum()
        df = df[df["SEMESTRE"] == tot.idxmax()]
    return df

def g(df, cols, valor):
    return df.groupby(cols, dropna=False)[valor].sum().reset_index()

def nombre_ies(nombre):
    if "servicio nacional de aprendizaje" in norm(nombre):
        return "SENA"
    return (nombre.strip().title().strip("-").replace(" De ", " de ").replace(" Y ", " y ")
            .replace(" La ", " la ").replace(" Del ", " del ").replace(" En ", " en "))

ANIOS = list(range(2018, 2025))
print("== Matrícula 2018-2024 (todos los niveles, semestre pico) ==")
mats, grads = {}, {}
for anio in ANIOS:
    mats[anio] = leer_snies(f"matriculados_{anio}.xlsx", "MATRICULADOS", semestre_pico=True)
    grads[anio] = leer_snies(f"graduados_{anio}.xlsx", "GRADUADOS")
    print(anio, "matrícula:", int(mats[anio]["MATRICULADOS"].sum()), "| graduados:", int(grads[anio]["GRADUADOS"].sum()))

# ---------- Series por nivel, sector, modalidad, sexo ----------
def moda_grupo(m):
    k = norm(m)
    if k == "presencial": return "Presencial"
    if k in ("virtual", "distancia (virtual)"): return "Virtual"
    if k in ("a distancia", "distancia (tradicional)"): return "A distancia"
    return "Híbrida/combinada"

serie, serie_grad, modalidad, sexo = [], [], [], []
for anio in ANIOS:
    df = mats[anio]
    d = {"anio": anio, "niveles": {}, "sector": {}, "tyt": int(df.loc[df["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum())}
    for niv, v in g(df, ["NIVEL_G"], "MATRICULADOS").values: d["niveles"][niv] = int(v)
    for sec, v in g(df, ["SECTOR IES"], "MATRICULADOS").values: d["sector"][sec.strip()] = int(v)
    serie.append(d)
    dg = grads[anio]
    dd = {"anio": anio, "total": int(dg["GRADUADOS"].sum()), "niveles": {}, "sector": {}}
    for niv, v in g(dg, ["NIVEL_G"], "GRADUADOS").values: dd["niveles"][niv] = int(v)
    for sec, v in g(dg, ["SECTOR IES"], "GRADUADOS").values: dd["sector"][sec.strip()] = int(v)
    serie_grad.append(dd)
    df2 = df.copy(); df2["MG"] = df2["MODALIDAD"].map(moda_grupo)
    dm = {"anio": anio}
    for k, v in g(df2, ["MG"], "MATRICULADOS").values: dm[k] = int(v)
    modalidad.append(dm)
    ds = {"anio": anio}
    for k, v in g(df, ["SEXO"], "MATRICULADOS").values: ds[str(k).strip()] = int(v)
    sexo.append(ds)

# ---------- IES 2024 ----------
m24, g24 = mats[2024], grads[2024]
m23 = mats[2023]
ies = []
for (cod, nombre), sub in m24.groupby(["CÓDIGO DE LA INSTITUCIÓN", "INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)"]):
    gsub = g24[g24["CÓDIGO DE LA INSTITUCIÓN"] == cod]
    msub23 = m23[m23["CÓDIGO DE LA INSTITUCIÓN"] == cod]
    ies.append({
        "codigo": int(cod), "nombre": nombre_ies(nombre),
        "sector": sub["SECTOR IES"].iloc[0].strip(),
        "caracter": sub["CARÁCTER IES"].iloc[0].strip(),
        "acreditada": str(sub["IES ACREDITADA"].iloc[0]).strip().upper().startswith("S"),
        "domicilio_ant": sub["DEPARTAMENTO DE DOMICILIO DE LA IES"].iloc[0].strip() == "Antioquia",
        "matricula24": int(sub["MATRICULADOS"].sum()),
        "matricula23": int(msub23["MATRICULADOS"].sum()),
        "pregrado24": int(sub.loc[sub["NIVEL_ACAD"] == "Pregrado", "MATRICULADOS"].sum()),
        "posgrado24": int(sub.loc[sub["NIVEL_ACAD"] == "Posgrado", "MATRICULADOS"].sum()),
        "tyt24": int(sub.loc[sub["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum()),
        "graduados24": int(gsub["GRADUADOS"].sum()),
        "programas": int(sub["CÓDIGO SNIES DEL PROGRAMA"].nunique()),
        "municipios": int(sub["MUNICIPIO DE OFERTA DEL PROGRAMA"].nunique()),
        "mat_acreditada": int(sub.loc[sub["PROGRAMA ACREDITADO"].astype(str).str.upper().str.startswith("S"), "MATRICULADOS"].sum()),
    })
ies.sort(key=lambda x: -x["matricula24"])

# ---------- Municipios 2024 ----------
munis = []
for mun, sub in m24.groupby("MUNICIPIO DE OFERTA DEL PROGRAMA"):
    gsub = g24[g24["MUNICIPIO DE OFERTA DEL PROGRAMA"] == mun]
    munis.append({
        "municipio": mun.strip(), "codigo": str(int(float(sub["CÓDIGO DEL MUNICIPIO (PROGRAMA)"].iloc[0]))).zfill(5),
        "matricula24": int(sub["MATRICULADOS"].sum()),
        "tyt24": int(sub.loc[sub["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum()),
        "posgrado24": int(sub.loc[sub["NIVEL_ACAD"] == "Posgrado", "MATRICULADOS"].sum()),
        "ies": int(sub["CÓDIGO DE LA INSTITUCIÓN"].nunique()),
        "programas": int(sub["CÓDIGO SNIES DEL PROGRAMA"].nunique()),
        "graduados24": int(gsub["GRADUADOS"].sum()),
        "oficial": int(sub.loc[sub["SECTOR IES"].str.strip() == "Oficial", "MATRICULADOS"].sum()),
    })
munis.sort(key=lambda x: -x["matricula24"])

# ---------- Áreas (serie) y NBC (2024) ----------
areas = {}
for anio in ANIOS:
    for a, v in g(mats[anio], ["ÁREA DE CONOCIMIENTO"], "MATRICULADOS").values:
        k = norm(a)
        areas.setdefault(k, {"area": str(a).strip(), "mat": {}, "grad": {}})
        areas[k]["area"] = str(a).strip().capitalize()
        areas[k]["mat"][anio] = areas[k]["mat"].get(anio, 0) + int(v)
    for a, v in g(grads[anio], ["ÁREA DE CONOCIMIENTO"], "GRADUADOS").values:
        k = norm(a)
        areas.setdefault(k, {"area": str(a).strip().capitalize(), "mat": {}, "grad": {}})
        areas[k]["grad"][anio] = areas[k]["grad"].get(anio, 0) + int(v)
areas_final = sorted(areas.values(), key=lambda x: -x["mat"].get(2024, 0))

nbc = g(m24, ["NÚCLEO BÁSICO DEL CONOCIMIENTO (NBC)"], "MATRICULADOS")
nbc.columns = ["nbc", "matricula24"]
gn = g(g24, ["NÚCLEO BÁSICO DEL CONOCIMIENTO (NBC)"], "GRADUADOS")
gn.columns = ["nbc", "graduados24"]
nbc = nbc.merge(gn, on="nbc", how="outer").fillna(0)
nbc_final = sorted([{"nbc": str(r.nbc).strip().title(), "matricula24": int(r.matricula24), "graduados24": int(r.graduados24)}
                    for r in nbc.itertuples()], key=lambda x: -x["matricula24"])

# ---------- Programas 2024 (explorador, todos los niveles) ----------
progs = []
for (snies, prog), sub in m24.groupby(["CÓDIGO SNIES DEL PROGRAMA", "PROGRAMA ACADÉMICO"]):
    progs.append({
        "snies": int(snies), "programa": str(prog).strip().title(),
        "ies": nombre_ies(sub["INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)"].iloc[0]),
        "sector": sub["SECTOR IES"].iloc[0].strip(),
        "nivel": sub["NIVEL_G"].iloc[0],
        "area": str(sub["ÁREA DE CONOCIMIENTO"].iloc[0]).strip(),
        "municipios": sorted(sub["MUNICIPIO DE OFERTA DEL PROGRAMA"].str.strip().unique().tolist()),
        "modalidad": moda_grupo(sub["MODALIDAD"].iloc[0]),
        "matricula24": int(sub["MATRICULADOS"].sum()),
        "acreditado": str(sub["PROGRAMA ACREDITADO"].iloc[0]).strip().upper().startswith("S"),
    })
progs.sort(key=lambda x: -x["matricula24"])

# ---------- Acreditación de alta calidad por nivel (proxy de calidad, 2024) ----------
acred = []
for niv in ORDEN_NIVEL:
    sub = m24[m24["NIVEL_G"] == niv]
    ac_mask = sub["PROGRAMA ACREDITADO"].astype(str).str.upper().str.startswith("S")
    acred.append({"nivel": niv,
                  "matricula": int(sub["MATRICULADOS"].sum()),
                  "mat_acreditada": int(sub.loc[ac_mask, "MATRICULADOS"].sum()),
                  "programas": int(sub["CÓDIGO SNIES DEL PROGRAMA"].nunique()),
                  "prog_acreditados": int(sub.loc[ac_mask, "CÓDIGO SNIES DEL PROGRAMA"].nunique())})

# ---------- Embudo 2024 (total y TyT) ----------
embudo = {"matriculados": int(m24["MATRICULADOS"].sum()), "graduados": int(g24["GRADUADOS"].sum()),
          "matriculados_tyt": int(m24.loc[m24["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum())}
for archivo, campo, clave in [("inscritos_2024.xlsx", "INSCRITOS", "inscritos"),
                              ("admitidos_2024.xlsx", "ADMITIDOS", "admitidos"),
                              ("primer_curso_2024.xlsx", "MATRICULADOS PRIMER CURSO", "primer_curso")]:
    df = leer_snies(archivo, campo)
    embudo[clave] = int(df[campo].sum())
    embudo[clave + "_tyt"] = int(df.loc[df["NIVEL_G"].isin(TYT), campo].sum())

# ---------- Docentes 2024 (IES domiciliadas en Antioquia) ----------
_h, _r = hoja_datos("docentes_2024.xlsx", "DOCENTES")
doc = pd.read_excel(DATA / "docentes_2024.xlsx", sheet_name=_h, header=_r)
doc.columns = [" ".join(str(c).upper().split()) for c in doc.columns]
doc = doc[doc["DEPARTAMENTO DE DOMICILIO DE LA IES"] == "Antioquia"].copy()
doc["DOCENTES"] = pd.to_numeric(doc["DOCENTES"], errors="coerce").fillna(0)
doc = doc[doc["SEMESTRE"] == doc["SEMESTRE"].max()]
CAR_TYT = ["Institución Técnica Profesional", "Institución Tecnológica", "Institución Universitaria/Escuela Tecnológica"]
docentes = {"total": int(doc["DOCENTES"].sum()),
            "total_tyt": int(doc.loc[doc["CARÁCTER IES"].isin(CAR_TYT), "DOCENTES"].sum()),
            "formacion": {}, "dedicacion": {}}
for k, v in doc.groupby("MÁXIMO NIVEL DE FORMACIÓN DEL DOCENTE")["DOCENTES"].sum().items():
    docentes["formacion"][str(k).strip()] = int(v)
for k, v in doc.groupby("TIEMPO DE DEDICACIÓN DEL DOCENTE")["DOCENTES"].sum().items():
    docentes["dedicacion"][str(k).strip()] = int(v)

# ---------- Saber TyT ----------
sab = pd.concat([pd.read_csv(f, low_memory=False) for f in sorted(glob.glob(str(DATA / "saber_tyt_ant_*.csv")))])
MODS = {"mod_razona_cuantitat_punt": "rc", "mod_lectura_critica_punt": "lc",
        "mod_competen_ciudada_punt": "cc", "mod_comuni_escrita_punt": "ce", "mod_ingles_punt": "ing"}
for c in MODS: sab[c] = pd.to_numeric(sab[c], errors="coerce")
sab["periodo"] = sab["periodo"].astype(str)
nal = {r["periodo"]: r for r in json.load(open(DATA / "saber_tyt_nacional_periodos.json"))}
serie_saber = []
for per, sub in sab.groupby("periodo"):
    if len(sub) < 3000 or per == "20142":
        continue
    d = {"periodo": per, "n": int(len(sub))}
    for c, k in MODS.items(): d[k] = round(float(sub[c].mean()), 1)
    if per in nal:
        d["nal"] = {k: round(float(nal[per][k]), 1) for k in ["rc", "lc", "cc", "ce", "ing"] if nal[per].get(k)}
        d["n_nal"] = int(nal[per]["n"])
    serie_saber.append(d)
serie_saber.sort(key=lambda x: x["periodo"])

s22 = sab[sab["periodo"].isin(["20221", "20224"])].copy()
_sector_map = {norm(i["nombre"]): i["sector"] for i in ies}
def _sector_snies(nom):
    ni = norm(nom)
    for x, sec in _sector_map.items():
        if len(x) > 8 and (ni == x or ni.startswith(x) or x.startswith(ni)):
            return sec
    return None
saber_ies = []
for (cod, nom), sub in s22.groupby(["inst_cod_institucion", "inst_nombre_institucion"]):
    if len(sub) < 100: continue
    d = {"ies": str(nom).strip().title(), "n": int(len(sub)),
         "origen": _sector_snies(nom) or ("Privada" if "NO OFICIAL" in str(sub["inst_origen"].iloc[0]).upper() else "Oficial")}
    for c, k in MODS.items(): d[k] = round(float(sub[c].mean()), 1)
    d["global"] = round(float(pd.concat([sub[c] for c in MODS], axis=0).mean()), 1)
    saber_ies.append(d)
saber_ies.sort(key=lambda x: -x["global"])

ETIQUETAS = {"0": "No trabaja", "F": "Femenino", "M": "Masculino", "Si": "Sí"}
def dist(col, top=None):
    s = s22[col].fillna("Sin información").astype(str).str.strip()
    s = s.map(lambda x: ETIQUETAS.get(x, x))
    c = dict(s.value_counts())
    # fusiona claves con U+FFFD en su contraparte limpia (mismo largo, resto igual)
    for k in [k for k in c if "�" in k]:
        for limpio in [x for x in c if "�" not in x]:
            if len(limpio) == len(k) and all(a == b or b == "�" for a, b in zip(limpio, k)):
                c[limpio] += c.pop(k); break
    c = dict(sorted(c.items(), key=lambda kv: -kv[1]))
    if top: c = dict(list(c.items())[:top])
    return {k: int(v) for k, v in c.items()}
social = {"n": int(len(s22)),
          "estrato": dist("fami_estratovivienda"), "edu_madre": dist("fami_educacionmadre"),
          "trabaja": dist("estu_horassemanatrabaja"), "internet": dist("fami_tieneinternet"),
          "computador": dist("fami_tienecomputador"), "genero": dist("estu_genero"),
          "beca": dist("estu_pagomatriculabeca"), "credito": dist("estu_pagomatriculacredito"),
          "propio": dist("estu_pagomatriculapropio"), "valor_matricula": dist("estu_valormatriculauniversidad")}

# ---------- Grupos de investigación — Convocatoria 957 de 2024 (resultados dic. 2025) ----------
# Listado PDF de Minciencias (sin departamento): se asigna por código GrupLAC contra la base
# histórica de convocatorias (90 % de cobertura) y, para grupos nuevos, por institución avaladora
# con domicilio en Antioquia.
g957 = [g for g in json.load(open(DATA / "grupos_957.json")) if g["reconocido"]]
cod_map = json.load(open(DATA / "grupos_cod_map.json"))
ies_norm_set = {norm(i["nombre"]) for i in ies}
ies_tyt_norm = {norm(i["nombre"]) for i in ies if i["tyt24"] > 0}
ies_ant_norm = {norm(i["nombre"]) for i in ies if i["domicilio_ant"]}
def _match(inst, nombres):
    ni = norm(inst)
    return any(ni == x or ni.startswith(x) or x.startswith(ni) for x in nombres if len(x) > 8)
grupos_ant = []
for g in g957:
    avales = [a.strip() for a in g["avales"].split(";") if a.strip()]
    info = cod_map.get(g["cod"])
    if info:
        es_ant = info.get("depto") == "Antioquia"
    else:
        es_ant = any(_match(a, ies_ant_norm) for a in avales)
    if es_ant:
        grupos_ant.append({**g, "avales_l": avales, "area": (info or {}).get("area")})
grupos_out = {"total": len(grupos_ant),
              "clasificacion": dict(Counter(g["clas"] or "Reconocido" for g in grupos_ant)),
              "por_area": dict(Counter(g["area"] or "Sin dato (grupo nuevo)" for g in grupos_ant).most_common()),
              "por_ies": []}
aval, aval_clas = Counter(), {}
for g in grupos_ant:
    for inst in g["avales_l"]:
        inst = inst.strip().title()
        aval[inst] += 1
        aval_clas.setdefault(inst, Counter())[g["clas"] or "Reconocido"] += 1
for inst, n in aval.most_common(40):
    grupos_out["por_ies"].append({"ies": inst, "grupos": n, "clas": dict(aval_clas[inst]),
                                  "oferta_ant": _match(inst, ies_norm_set), "oferta_tyt": _match(inst, ies_tyt_norm)})
print("Grupos 957 Antioquia:", grupos_out["total"], grupos_out["clasificacion"])

# ---------- OLE: vinculación y salario por nivel — IES antioqueñas ----------
ies_ant_codes = {i["codigo"] for i in ies if i["domicilio_ant"]}
ole = pd.read_excel(DATA / "ole_base_ibc_2023.xlsx", sheet_name="Base_IBC_2023", header=8)
ole.columns = [" ".join(str(c).upper().split()) for c in ole.columns]
ole["GRADUADOS"] = pd.to_numeric(ole["GRADUADOS"], errors="coerce").fillna(0)
ole["COD_IES"] = pd.to_numeric(ole["CÓDIGO DE LA INSTITUCIÓN"], errors="coerce")
ole["ANIO_GRADO"] = pd.to_numeric(ole["AÑO DE GRADO"], errors="coerce")
oniv = ole["NIVEL DE FORMACIÓN"].map(lambda x: NIVELES.get(norm(x)))
ole["NIVEL_G"] = oniv.map(lambda t: t[0] if t else None)
ole_ant = ole[ole["COD_IES"].isin(ies_ant_codes) & ole["NIVEL_G"].notna()].copy()
recientes = ole_ant[ole_ant["ANIO_GRADO"] >= 2018]
grad22 = grads[2022][pd.to_numeric(grads[2022]["CÓDIGO DE LA INSTITUCIÓN"], errors="coerce").isin(ies_ant_codes)]
salida_ole = {
    "nota": "Graduados de IES con domicilio en Antioquia que cotizaron a seguridad social en 2023 (OLE, corte 2023). Excluye SENA y UNAD (domicilio fuera del departamento).",
    "vinculados_2023_recientes": int(recientes["GRADUADOS"].sum()),
    "salario_por_nivel": {}, "vinculacion_por_nivel": {}, "top_programas_tyt": [],
}
for niv in ORDEN_NIVEL:
    sub = recientes[recientes["NIVEL_G"] == niv]
    if sub["GRADUADOS"].sum() > 0:
        salida_ole["salario_por_nivel"][niv] = {k: int(v) for k, v in sub.groupby("INGRESO")["GRADUADOS"].sum().items()}
    vin22 = int(ole_ant.loc[(ole_ant["ANIO_GRADO"] == 2022) & (ole_ant["NIVEL_G"] == niv), "GRADUADOS"].sum())
    g22 = int(grad22.loc[grad22["NIVEL_G"] == niv, "GRADUADOS"].sum())
    if g22 > 0:
        salida_ole["vinculacion_por_nivel"][niv] = {"vinculados": vin22, "graduados": g22,
                                                    "tasa": round(100 * vin22 / g22, 1)}
rec_tyt = recientes[recientes["NIVEL_G"].isin(TYT)]
tp = rec_tyt.groupby(["PROGRAMA ACADÉMICO"])["GRADUADOS"].sum().sort_values(ascending=False).head(15)
salida_ole["top_programas_tyt"] = [{"programa": str(k).strip().title(), "vinculados": int(v)} for k, v in tp.items()]
print("OLE vinculación por nivel:", {k: v["tasa"] for k, v in salida_ole["vinculacion_por_nivel"].items()})


# ---------- Subregiones de Antioquia (mapping Gobernación, datos.gov.co t2ca-uae5) ----------
sub_map_raw = json.load(open(DATA / "subregiones.json"))
sub_map = {norm(k): v.replace("Aburra", "Aburrá") for k, v in sub_map_raw.items()}
sub_map["san pedro de los milagros"] = sub_map.get("san pedro", "Norte")
m24["SUBREGION"] = m24["MUNICIPIO DE OFERTA DEL PROGRAMA"].map(lambda x: sub_map.get(norm(x)))
g24["SUBREGION"] = g24["MUNICIPIO DE OFERTA DEL PROGRAMA"].map(lambda x: sub_map.get(norm(x)))
print("municipios 2024 sin subregión:", m24.loc[m24["SUBREGION"].isna(), "MUNICIPIO DE OFERTA DEL PROGRAMA"].unique())
subregiones = []
for sr, sub in m24[m24["SUBREGION"].notna()].groupby("SUBREGION"):
    gsub = g24[g24["SUBREGION"] == sr]
    subregiones.append({
        "subregion": sr,
        "matricula24": int(sub["MATRICULADOS"].sum()),
        "tyt24": int(sub.loc[sub["NIVEL_G"].isin(TYT), "MATRICULADOS"].sum()),
        "posgrado24": int(sub.loc[sub["NIVEL_ACAD"] == "Posgrado", "MATRICULADOS"].sum()),
        "graduados24": int(gsub["GRADUADOS"].sum()),
        "ies": int(sub["CÓDIGO DE LA INSTITUCIÓN"].nunique()),
        "programas": int(sub["CÓDIGO SNIES DEL PROGRAMA"].nunique()),
        "municipios_oferta": int(sub["MUNICIPIO DE OFERTA DEL PROGRAMA"].nunique()),
    })
subregiones.sort(key=lambda x: -x["matricula24"])
for mu in munis:
    mu["subregion"] = sub_map.get(norm(mu["municipio"]))

# ---------- Bilingüismo: niveles MCER de inglés en Saber TyT (API agregada) ----------
MCER = {"pre-a1": "Bajo A1", "-a1": "Bajo A1", "a-": "Bajo A1",
        "a1": "A1", "a2": "A2", "b1": "B1", "b2": "B2 o más", "b+": "B2 o más"}
NIVELES_MCER = ["Bajo A1", "A1", "A2", "B1", "B2 o más"]
def agg_mcer(rows):
    out = {}
    for r in rows:
        per = r.get("periodo")
        lvl = MCER.get(str(r.get("mod_ingles_desem", "")).lower().strip())
        if not per or not lvl: continue
        out.setdefault(per, {n: 0 for n in NIVELES_MCER})
        out[per][lvl] += int(r["count"])
    return out
ing_ant = agg_mcer(json.load(open(DATA / "ingles_ant_periodo.json")))
ing_nal = agg_mcer(json.load(open(DATA / "ingles_nal_periodo.json")))
periodos_ok = [s_["periodo"] for s_ in serie_saber]
ingles_serie = []
for per in periodos_ok:
    a, n = ing_ant.get(per), ing_nal.get(per)
    if not a or not n: continue
    ta, tn = sum(a.values()), sum(n.values())
    ingles_serie.append({"periodo": per, "n": ta,
                         "dist": {k: round(100 * v / ta, 1) for k, v in a.items()},
                         "b1mas_ant": round(100 * (a["B1"] + a["B2 o más"]) / ta, 1),
                         "b1mas_nal": round(100 * (n["B1"] + n["B2 o más"]) / tn, 1)})
ing_ies_raw = {}
for r in json.load(open(DATA / "ingles_ies_2022.json")):
    lvl = MCER.get(str(r.get("mod_ingles_desem", "")).lower().strip())
    if not lvl: continue
    d = ing_ies_raw.setdefault(str(r["inst_nombre_institucion"]).strip().title(), {n: 0 for n in NIVELES_MCER})
    d[lvl] += int(r["count"])
ingles_ies = []
for nom, d in ing_ies_raw.items():
    t = sum(d.values())
    if t < 100: continue
    ingles_ies.append({"ies": nom, "n": t, "b1mas": round(100 * (d["B1"] + d["B2 o más"]) / t, 1),
                       "dist": {k: round(100 * v / t, 1) for k, v in d.items()},
                       "origen": _sector_snies(nom) or "Privada"})
ingles_ies.sort(key=lambda x: -x["b1mas"])
print("Inglés B1+ Antioquia último periodo:", ingles_serie[-1]["b1mas_ant"], "% | nacional:", ingles_serie[-1]["b1mas_nal"], "%")

# ---------- Empleabilidad por área de conocimiento (OLE, IES antioqueñas, todos los niveles) ----------
ole_area = ole[ole["COD_IES"].isin(ies_ant_codes) & ole["NIVEL_G"].notna()].copy()
grad22_area = grad22.copy()
RANGOS_ALTOS = ["Entre 2,5 y 4 SMMLV", "Entre 4 y 6 SMMLV", "Entre 6 y 9 SMMLV", "Más de 9 SMMLV"]
ole_areas_out = []
for ar, sub in ole_area.groupby("ÁREA DE CONOCIMIENTO"):
    ar_n = norm(ar)
    vin22 = int(sub.loc[sub["ANIO_GRADO"] == 2022, "GRADUADOS"].sum())
    g22 = int(grad22_area.loc[grad22_area["ÁREA DE CONOCIMIENTO"].map(norm) == ar_n, "GRADUADOS"].sum())
    rec = sub[sub["ANIO_GRADO"] >= 2018]
    cot = int(rec["GRADUADOS"].sum())
    altos = int(rec.loc[rec["INGRESO"].isin(RANGOS_ALTOS), "GRADUADOS"].sum())
    if g22 < 100 or cot < 200: continue
    ole_areas_out.append({"area": str(ar).strip().capitalize(), "vinculados": vin22, "graduados": g22,
                          "tasa": round(100 * vin22 / g22, 1), "cotizantes": cot,
                          "pct_25mas": round(100 * altos / cot, 1)})
ole_areas_out.sort(key=lambda x: -x["tasa"])
salida_ole["areas"] = ole_areas_out
print("Empleabilidad por área:", [(a["area"][:30], a["tasa"]) for a in ole_areas_out[:4]])


# ---------- Serie de demanda 2018-2024: inscripciones y primer curso ----------
def leer_variantes(archivo, candidatos):
    for val in candidatos:
        try:
            return leer_snies(archivo, val), val
        except ValueError:
            continue
    raise ValueError(f"Sin columna de valor en {archivo}: {candidatos}")
serie_demanda = []
for anio in ANIOS:
    di, vi = leer_variantes(f"inscritos_{anio}.xlsx", ["INSCRITOS", "INSCRIPCIONES"])
    dp, vp = leer_variantes(f"primer_curso_{anio}.xlsx", ["MATRICULADOS PRIMER CURSO", "PRIMER CURSO"])
    serie_demanda.append({"anio": anio,
                          "inscritos": int(di[vi].sum()),
                          "inscritos_tyt": int(di.loc[di["NIVEL_G"].isin(TYT), vi].sum()),
                          "primer_curso": int(dp[vp].sum()),
                          "primer_curso_tyt": int(dp.loc[dp["NIVEL_G"].isin(TYT), vp].sum())})
print("Demanda:", [(d["anio"], d["inscritos"], d["primer_curso"]) for d in serie_demanda][::3])

# ---------- Saber TyT por municipio (2022) ----------
sm_raw = json.load(open(DATA / "saber_municipio_2022.json"))
# fusiona variantes con U+FFFD (promedios ponderados por n)
sm_acc = {}
for r in sm_raw:
    mu = str(r.get("estu_prgm_municipio", "")).strip()
    key = norm(mu.replace("\ufffd", "?"))
    key2 = None
    for k in sm_acc:
        if len(k) == len(key) and all(a == b or "?" in (a, b) for a, b in zip(k, key)):
            key2 = k; break
    key = key2 or key.replace("?", "")
    n = int(r["n"])
    d = sm_acc.setdefault(key, {"n": 0, "suma": 0.0})
    mods = [float(r[k]) for k in ("rc", "lc", "cc", "ce", "ing") if r.get(k)]
    if not mods: continue
    d["n"] += n
    d["suma"] += n * (sum(mods) / len(mods))
saber_muni = []
munis_norm = {norm(m["municipio"]): m for m in munis}
for key, d in sm_acc.items():
    if d["n"] < 50 or key not in munis_norm: continue
    m = munis_norm[key]
    saber_muni.append({"municipio": m["municipio"], "codigo": m["codigo"],
                       "global": round(d["suma"] / d["n"], 1), "n": d["n"]})
saber_muni.sort(key=lambda x: -x["global"])
print("Saber por municipio (n>=50):", len(saber_muni), "| top:", [(x["municipio"], x["global"]) for x in saber_muni[:3]])

# ---------- Participación femenina por nivel (2024) ----------
mujeres_nivel = []
for niv in ORDEN_NIVEL:
    sub = m24[m24["NIVEL_G"] == niv]
    f = int(sub.loc[sub["SEXO"] == "Femenino", "MATRICULADOS"].sum())
    t = int(sub.loc[sub["SEXO"].isin(["Femenino", "Masculino"]), "MATRICULADOS"].sum())
    if t: mujeres_nivel.append({"nivel": niv, "pct": round(100 * f / t, 1), "mujeres": f, "total": t})

# ---------- Cobertura bruta (oferta) 17-21 por subregión — DANE proyecciones 2024 ----------
# Requiere data/pob_antioquia_17_21.json generado por scripts/preparar_poblacion.py
cobertura = None
pob_file = DATA / "pob_antioquia_17_21.json"
if pob_file.exists():
    pob = json.load(open(pob_file))  # {"municipios": {cod: pob}, "subregiones": {nombre: pob}}
    for mu in munis:
        mu["pob_17_21"] = pob["municipios"].get(mu["codigo"])
    cobertura = []
    for s_ in subregiones:
        pobs = pob["subregiones"].get(s_["subregion"])
        preg = int(m24.loc[(m24["SUBREGION"] == s_["subregion"]) & (m24["NIVEL_ACAD"] == "Pregrado"), "MATRICULADOS"].sum())
        if pobs:
            cobertura.append({"subregion": s_["subregion"], "pregrado": preg, "pob_17_21": pobs,
                              "cobertura": round(100 * preg / pobs, 1)})
    cobertura.sort(key=lambda x: -x["cobertura"])
    tot_p = sum(c["pregrado"] for c in cobertura); tot_pob = sum(c["pob_17_21"] for c in cobertura)
    cobertura.append({"subregion": "Antioquia (total)", "pregrado": tot_p, "pob_17_21": tot_pob,
                      "cobertura": round(100 * tot_p / tot_pob, 1)})
    print("Cobertura subregional:", [(c["subregion"], c["cobertura"]) for c in cobertura])
else:
    print("Cobertura pendiente: falta", pob_file)


# ---------- Brecha de género por área (2024) y STEM ----------
STEM = {"ingenieria, arquitectura, urbanismo y afines", "matematicas y ciencias naturales",
        "ingenieria, arquitectura, urbanismo", "matematicas y ciencias naturales y afines"}
genero_area = []
for ar, sub in m24.groupby("ÁREA DE CONOCIMIENTO"):
    f = int(sub.loc[sub["SEXO"] == "Femenino", "MATRICULADOS"].sum())
    t = int(sub.loc[sub["SEXO"].isin(["Femenino", "Masculino"]), "MATRICULADOS"].sum())
    if t < 500: continue
    genero_area.append({"area": str(ar).strip().capitalize(), "pct": round(100 * f / t, 1),
                        "mujeres": f, "total": t, "stem": norm(ar) in STEM})
genero_area.sort(key=lambda x: -x["pct"])
stem_f = sum(a["mujeres"] for a in genero_area if a["stem"])
stem_t = sum(a["total"] for a in genero_area if a["stem"])
stem_pct = round(100 * stem_f / stem_t, 1) if stem_t else None
print("Mujeres en STEM:", stem_pct, "%")

# ---------- Financiación de la matrícula (Saber TyT 2022) ----------
social["stem_mujeres_pct"] = stem_pct

# ---------- Salida ----------
salida = {
    "meta": {
        "titulo": "MaterIA Gris · Educación superior de Antioquia",
        "autor": "Santiago Jiménez Londoño",
        "corte": "2026-07-12",
        "fuentes": [
            "SNIES – Bases consolidadas del MEN: matriculados, graduados, inscritos, admitidos, primer curso y docentes, vigencias 2018-2024 (todos los niveles de formación).",
            "OLE – Observatorio Laboral para la Educación: base de ingreso base de cotización (IBC) 2023 por programa e institución, descargada del portal OLE.",
            "ICFES vía datos.gov.co (iwgf-bkfk): Resultados únicos Saber TyT 2017-2022, microdato de 161.281 evaluados de programas ofertados en Antioquia; niveles MCER de inglés por agregación API.",
            "Gobernación de Antioquia vía datos.gov.co (t2ca-uae5): correspondencia municipio-subregión.",
            "DANE — GEIH: tasa de desempleo Medellín A.M. 8,6 % (trimestre móvil mar-may 2026).",
            "DANE — Proyecciones de población municipal por área, sexo y edad (base CNPV 2018, act. 2025): población de 17 a 21 años para la cobertura bruta subregional.",
            "MinCiencias: resultados finales de la Convocatoria 957 de 2024 (Resolución 1531, dic. 2025), listado oficial PDF; departamento y gran área asignados por código GrupLAC contra la base histórica de convocatorias (datos.gov.co hrhc-c4wu).",
            "MEN vía datos.gov.co (5wck-szir): base histórica de matrícula (descartada para la serie por inconsistencias de reporte semestral 2015-2017).",
        ],
    },
    "serie": serie, "serie_graduados": serie_grad, "ies": ies, "municipios": munis,
    "areas": areas_final, "nbc": nbc_final[:30], "modalidad": modalidad, "sexo": sexo,
    "programas": progs, "embudo": embudo, "docentes": docentes, "acreditacion": acred,
    "subregiones": {"agg": subregiones, "mapa": {k: v.replace("Aburra", "Aburrá") for k, v in sub_map_raw.items()}, "cobertura": cobertura},
    "serie_demanda": serie_demanda, "saber_municipio": saber_muni, "mujeres_nivel": mujeres_nivel,
    "genero_area": genero_area,
    "ingles": {"serie": ingles_serie, "ies": ingles_ies},
    "saber": {"serie": serie_saber, "ies": saber_ies, "social": social},
    "grupos": grupos_out, "ole": salida_ole,
}
with open(OUT / "datos.json", "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False)
with open(OUT / "datos.js", "w", encoding="utf-8") as f:
    f.write("window.OBS = " + json.dumps(salida, ensure_ascii=False) + ";")
print("OK →", OUT / "datos.json", f"{(OUT/'datos.json').stat().st_size/1e6:.2f} MB")
print("IES:", len(ies), "| municipios:", len(munis), "| programas:", len(progs))
print("Serie 2024:", serie[-1]["niveles"])
print("Embudo:", {k: embudo[k] for k in ["inscritos", "admitidos", "primer_curso", "matriculados", "graduados"]})
print("Acreditación:", [(a["nivel"], a["prog_acreditados"], a["programas"]) for a in acred])
