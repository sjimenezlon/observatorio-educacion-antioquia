"""SENA — Formación Profesional Integral, Regional Antioquia → data/sena_fpi.json

Fuente: API Socrata de datos.gov.co (SENA), tres datasets con corte feb-2024
(periodo 202402; filas actualizadas 2024-03-14 — verificado contra el catálogo,
no existe corte más reciente a jul-2026):
  vv8g-8u9u  PROGRAMACIÓN ESPECÍFICA DE CURSOS LARGOS, ESPECIALES Y EVENTOS
  u4ze-bi7k  DESERCIÓN DE LA FORMACIÓN PROFESIONAL INTEGRAL
  28vu-5tx7  CERTIFICACIÓN DE LA FORMACIÓN PROFESIONAL INTEGRAL

Peculiaridades del origen (verificadas):
  · Los valores de texto traen comillas dobles EMBEBIDAS: el filtro correcto es
    nombre_regional = '"REGIONAL ANTIOQUIA"' (comillas incluidas en el valor).
  · Las fechas son texto dd/mm/yyyy (también entre comillas): el año se extrae
    de los últimos 4 caracteres; min()/max() del servidor ordenan mal (lexicográfico).
  · numero_cursos es texto → sum(numero_cursos::number).
  · Los tres datasets son una FOTO al corte (una sola vigencia), no series
    históricas: la "serie" de aprendices es por año de inicio de la ficha vigente
    y la de certificación por año de terminación de la ficha.

Agrega en el servidor ($group) y termina de cocinar con pandas.
"""
import json
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
SOC = "https://www.datos.gov.co/resource/{}.json"
# Comillas embebidas en el valor (así viene en el dataset, no es un error de tipeo)
ANT = "nombre_regional='\"REGIONAL ANTIOQUIA\"'"

# Titulada vs complementaria: la distinción clave para comparar con educación superior
TITULADA = {"TECNICO", "TECNOLOGO", "OPERARIO", "AUXILIAR",
            "PROFUNDIZACION TECNICA", "ESPECIALIZACION TECNOLOGICA"}
COMPLEMENTARIA = {"CURSO ESPECIAL", "EVENTO"}
ACENTOS = {"TECNICO": "TÉCNICO", "TECNOLOGO": "TECNÓLOGO",
           "PROFUNDIZACION TECNICA": "PROFUNDIZACIÓN TÉCNICA",
           "ESPECIALIZACION TECNOLOGICA": "ESPECIALIZACIÓN TECNOLÓGICA"}


def soql(ds, **params):
    """Consulta SoQL agregada en el servidor; devuelve DataFrame."""
    r = requests.get(SOC.format(ds), timeout=120,
                     params={f"${k}": v for k, v in params.items()})
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    assert len(df) < 9000, f"{ds}: se alcanzó el límite de página, pagine la consulta"
    return df


def limpiar(s):
    return str(s).strip().strip('"').strip()


def anio_de(fecha):
    return int(limpiar(fecha)[-4:])  # texto dd/mm/yyyy → año


def por_nivel(df, col):
    """[[nivel, n], ...] ordenado desc, con tildes, y subtotales tit/comp."""
    g = df.groupby("nivel")[col].sum().sort_values(ascending=False)
    tit = int(g[g.index.isin(TITULADA)].sum())
    comp = int(g[g.index.isin(COMPLEMENTARIA)].sum())
    filas = [[ACENTOS.get(k, k), int(v)] for k, v in g.items()]
    return filas, tit, comp


out = {"corte": "feb-2024 (periodo 202402; filas actualizadas 2024-03-14)",
       "fuente": {"aprendices": "vv8g-8u9u", "desercion": "u4ze-bi7k",
                  "certificacion": "28vu-5tx7"}}

# ------------------------------------------- 1. Aprendices en formación (vv8g-8u9u)
ap = soql("vv8g-8u9u",
          select=("fecha_inicio_ficha, nivel_formacion, sum(numero_cursos::number) as cursos,"
                  "sum(total_aprendices) as aprendices, sum(total_aprendices_activos) as activos"),
          where=ANT, group="fecha_inicio_ficha,nivel_formacion")
ap["nivel"] = ap["nivel_formacion"].map(limpiar)
ap["anio"] = ap["fecha_inicio_ficha"].map(anio_de)
for c in ("cursos", "aprendices", "activos"):
    ap[c] = ap[c].astype(int)

nivel, tit, comp = por_nivel(ap, "aprendices")
serie = ap.groupby("anio")["aprendices"].sum()
out["aprendices"] = {
    "total": int(ap["aprendices"].sum()), "titulada": tit, "complementaria": comp,
    "activos": int(ap["activos"].sum()), "cursos": int(ap["cursos"].sum()),
    "serie": [[int(a), int(n)] for a, n in serie.items()],  # por año de inicio de la ficha vigente
    "nivel": nivel}

# ------------------------------------------------------- 2. Deserción (u4ze-bi7k)
de = soql("u4ze-bi7k",
          select=("nivel_formacion, sum(total_aprendices_matriculados) as matric,"
                  "sum(desertores_a_o_actual) as desertores"),
          where=ANT, group="nivel_formacion")
de["nivel"] = de["nivel_formacion"].map(limpiar)
for c in ("matric", "desertores"):
    de[c] = de[c].astype(int)

m_tit = int(de[de["nivel"].isin(TITULADA)]["matric"].sum())
m_comp = int(de[de["nivel"].isin(COMPLEMENTARIA)]["matric"].sum())
d_tit = int(de[de["nivel"].isin(TITULADA)]["desertores"].sum())
d_comp = int(de[de["nivel"].isin(COMPLEMENTARIA)]["desertores"].sum())
out["desercion"] = {
    "matriculados": int(de["matric"].sum()), "desertores": int(de["desertores"].sum()),
    "tasa": round(100 * de["desertores"].sum() / de["matric"].sum(), 1),
    "titulada": {"desertores": d_tit, "tasa": round(100 * d_tit / m_tit, 1)},
    "complementaria": {"desertores": d_comp, "tasa": round(100 * d_comp / m_comp, 1)},
    # [nivel, matriculados, desertores, tasa %]
    "nivel": [[ACENTOS.get(r.nivel, r.nivel), r.matric, r.desertores,
               round(100 * r.desertores / r.matric, 1)]
              for r in de.sort_values("matric", ascending=False).itertuples()]}

# -------------------------------------------------- 3. Certificación (28vu-5tx7)
ce = soql("28vu-5tx7",
          select="fecha_terminacion_ficha, nivel_formacion, sum(gran_total_total_aprendices) as certificados",
          where=ANT, group="fecha_terminacion_ficha,nivel_formacion")
ce["nivel"] = ce["nivel_formacion"].map(limpiar)
ce["anio"] = ce["fecha_terminacion_ficha"].map(anio_de)
ce["certificados"] = ce["certificados"].astype(int)

nivel_c, tit_c, comp_c = por_nivel(ce, "certificados")
serie_c = ce.groupby("anio")["certificados"].sum()
out["certificacion"] = {
    "total": int(ce["certificados"].sum()), "titulada": tit_c, "complementaria": comp_c,
    "serie": [[int(a), int(n)] for a, n in serie_c.items()],  # por año de terminación de la ficha
    "nivel": nivel_c}

out["notas"] = [
    "Foto al corte feb-2024 (los tres datasets tienen una sola vigencia, periodo 202402): "
    "la serie de aprendices es por año de INICIO de la ficha vigente (cohortes en ejecución) "
    "y la de certificación por año de TERMINACIÓN de la ficha, no son series anuales de flujo.",
    "vv8g-8u9u cubre cursos LARGOS, especiales y eventos: la formación complementaria corta "
    "regular (la mayor masa del SENA, cientos de miles de cupos/año en Antioquia) NO está aquí; "
    "'complementaria' en este insumo = curso especial + evento.",
    "Titulada = técnico + tecnólogo + operario + auxiliar + profundización técnica + "
    "especialización tecnológica; es la porción comparable con educación superior (tecnólogo).",
    "desertores_a_o_actual = desertores del año en curso al corte, sobre los matriculados de las "
    "fichas vigentes; no es una tasa anual histórica.",
    "La certificación solo recoge los certificados registrados al corte (61.420 en todo el país), "
    "útil como distribución por nivel, no como total anual de certificados SENA.",
    "La Regional Antioquia dicta algunos cursos fuera del departamento "
    "(Córdoba 218, Caldas 32, Chocó 29 aprendices).",
]

# ------------------------------------------------------------- Verificaciones
a, d, c = out["aprendices"], out["desercion"], out["certificacion"]
assert a["total"] == a["titulada"] + a["complementaria"], "niveles no suman el total"
assert a["total"] == d["matriculados"], "vv8g y u4ze deben compartir el mismo universo de fichas"
assert a["total"] > 100_000, "magnitud implausible para la Regional Antioquia"
assert c["total"] == c["titulada"] + c["complementaria"]
print(f"Aprendices en formación : {a['total']:>7,} (titulada {a['titulada']:,} · "
      f"complementaria {a['complementaria']:,} · activos {a['activos']:,})")
print(f"  serie por año inicio  : {a['serie']}")
print(f"  por nivel             : {a['nivel']}")
print(f"Deserción año en curso  : {d['desertores']:>7,} ({d['tasa']} %) — "
      f"titulada {d['titulada']['tasa']} % · complementaria {d['complementaria']['tasa']} %")
print(f"Certificados al corte   : {c['total']:>7,} (titulada {c['titulada']:,} · "
      f"complementaria {c['complementaria']:,})")
print(f"  serie por año term.   : {c['serie']}")

destino = DATA / "sena_fpi.json"
destino.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(f"ok → data/sena_fpi.json ({destino.stat().st_size / 1024:.1f} KB)")
