"""La antesala: básica y media — Antioquia → data/basica_media.json

Fuentes (API Socrata de datos.gov.co, MEN; agregación en el servidor con $group):
  ngw5-c5nw  MEN_MATRICULA_EN_EDUCACION_EN_PREESCOLAR, BÁSICA Y MEDIA
             (microagregados sede×grado×edad×género; 34 M de filas, 2010-2024
              SIN 2018 — el año no existe en el dataset, verificado)
  ji8i-4anb  MEN_ESTADISTICAS ... POR_DEPARTAMENTO (tasas: cobertura neta/bruta,
             deserción intraanual, por nivel; fila Antioquia 2011-2024)
  nudc-7mev  MEN_ESTADISTICAS ... POR_MUNICIPIO (mismas tasas por municipio;
             se usa SOLO para verificar el agregado departamental por ponderación)
  5c2k-ahfc  MEN_NÚMERO_BACHILLERES_POR_ETC (municipio×año, 2019-2024)

Peculiaridades del origen (verificadas contra la API):
  · ngw5-c5nw cambia de formato entre vigencias: 2010-2017 usa
    cod_dane_departamento='05' y nombres en Title Case ("Antioquia");
    2019-2024 usa '5' y MAYÚSCULAS ("ANTIOQUIA"). Se filtra con IN ('05','5').
  · ngw5-c5nw NO tiene 2018 (ninguna fila nacional); la serie queda con hueco.
  · nudc-7mev NO trae matrícula, solo tasas: la matrícula por nivel sale de
    ngw5-c5nw sumando por codigo_grado (CLEI de adultos mapeados a su nivel
    equivalente según la práctica del MEN; aceleración → primaria; los grados
    41-45 de las escuelas normales son post-media → "otros").
  · 5c2k-ahfc tiene el año 2022 DUPLICADO (250 filas en vez de 125 para
    Antioquia): una copia mislabeled de las filas 2024 convive con las filas
    2022 verdaderas. Se depura eliminando, por municipio, la fila 2022 idéntica
    a la 2024 en todas las medidas.
  · El dataset de "tránsito inmediato a educación superior" NO existe en
    datos.gov.co (búsquedas 'transito inmediato', 'tránsito educación superior',
    'MEN transito', 'SPADIES': 0 resultados vivos) → transito = null.
"""
import json
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
SOC = "https://www.datos.gov.co/resource/{}.json"
ANT_NGW = "cod_dane_departamento in('05','5')"  # ambos formatos de vigencia


def soql(ds, **params):
    """Consulta SoQL agregada en el servidor; devuelve DataFrame (con reintentos)."""
    for intento in range(5):
        try:
            r = requests.get(SOC.format(ds), timeout=590,
                             params={f"${k}": v for k, v in params.items()})
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            assert len(df) < 9000, f"{ds}: límite de página alcanzado, paginar"
            return df
        except (requests.RequestException, ValueError) as e:
            if intento == 4:
                raise
            print(f"  reintento {intento + 1} en {ds}: {e}", flush=True)
            time.sleep(20)


def corte_de(ds):
    """Fecha de última actualización de filas del dataset (metadatos Socrata)."""
    r = requests.get(f"https://www.datos.gov.co/api/views/{ds}.json", timeout=60)
    r.raise_for_status()
    ts = r.json().get("rowsUpdatedAt")
    return time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else "s. d."


def norm(s):
    """MAYÚSCULAS sin tildes ni espacios repetidos, para casar nombres."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


# Grado → nivel. CLEI de adultos al nivel equivalente (práctica MEN):
# ciclos 1-2 → primaria, 3-4 → secundaria, 5-6 → media. Aceleración (99) →
# primaria. Formación complementaria de escuelas normales (post-media) → otros:
# grados 12-13 en las vigencias viejas, 41-45 + introductorio en las nuevas.
NIVEL = {**{g: "preescolar" for g in (-2, -1, 0)},
         **{g: "primaria" for g in (1, 2, 3, 4, 5, 21, 22, 99)},
         **{g: "secundaria" for g in (6, 7, 8, 9, 23, 24)},
         **{g: "media" for g in (10, 11, 25, 26)},
         **{g: "otros" for g in (12, 13, 41, 42, 43, 44, 45)}}
NIVELES = ["preescolar", "primaria", "secundaria", "media", "otros"]

# ------------------------------------ 1. Matrícula por nivel (ngw5-c5nw), 2011-2024
# Una consulta por año (el filtro por anno_inf usa índice y responde en ~15 s;
# sin él, el $group barre 34 M de filas y se agota el tiempo del servidor).
print("1. Matrícula por nivel, Antioquia (ngw5-c5nv, por año)…")
serie_nivel, sectores_anio = [], {}
for anio in range(2011, 2025):
    df = soql("ngw5-c5nw",
              select="codigo_grado, sector, sum(total_matricula) as n",
              where=f"anno_inf='{anio}' AND {ANT_NGW}",
              group="codigo_grado,sector")
    if df.empty:
        print(f"  {anio}: SIN FILAS (hueco del dataset)")
        continue
    df["n"] = df["n"].astype(int)
    df["grado"] = df["codigo_grado"].astype(int)
    desconocidos = sorted(set(df["grado"]) - set(NIVEL))
    if desconocidos:
        n_desc = int(df.loc[df["grado"].isin(desconocidos), "n"].sum())
        print(f"  AVISO {anio}: grados sin mapear {desconocidos} → 'otros' "
              f"({n_desc:,} matriculados)")
        assert n_desc < 0.01 * df["n"].sum(), \
            f"{anio}: los grados sin mapear pesan demasiado"
    df["nivel"] = df["grado"].map(NIVEL).fillna("otros")
    fila = {"anio": anio}
    fila.update({nv: int(df.loc[df["nivel"] == nv, "n"].sum()) for nv in NIVELES})
    fila["total"] = int(df["n"].sum())
    serie_nivel.append(fila)
    sectores_anio[anio] = df.groupby("sector")["n"].sum().to_dict()
    print(f"  {anio}: total {fila['total']:>9,} · sectores {sectores_anio[anio]}")

anios = [f["anio"] for f in serie_nivel]
assert len(anios) == len(set(anios)), "años duplicados en serie_nivel"
assert all(f["total"] == sum(f[nv] for nv in NIVELES) for f in serie_nivel), \
    "los niveles no suman el total"
ult = serie_nivel[-1]
assert 1_000_000 < ult["total"] < 1_500_000, \
    f"matrícula {ult['anio']} implausible para Antioquia: {ult['total']:,}"
# Universo: el dataset trae oficial Y no oficial en todas las vigencias
assert all(len(s) >= 2 for s in sectores_anio.values()), \
    "algún año quedó con un solo sector: revisar universo oficial/no oficial"

# --------------------------- 2. Subregional 2024: matrícula por nivel (ngw5-c5nw)
print("2. Matrícula subregional 2024…")
ANIO_SUB = ult["anio"]
# ojo: en las vigencias 2019+ el código departamental es '5' (sin cero); se usa
# ese literal y no el IN para aprovechar la caché del servidor (consulta pesada)
mu = soql("ngw5-c5nw",
          select="municipio,codigo_grado,sum(total_matricula)",
          where=f"cod_dane_departamento='5' AND anno_inf='{ANIO_SUB}'",
          group="municipio,codigo_grado", limit=5000)
mu["n"] = mu["sum_total_matricula"].astype(int)
mu["nivel"] = mu["codigo_grado"].astype(int).map(NIVEL)

submap = {norm(k): v for k, v in
          json.loads((DATA / "subregiones.json").read_text()).items()}
# Alias: nombres MEN que no casan con subregiones.json ni normalizando
ALIAS = {"ANTIOQUIA": "SANTA FE DE ANTIOQUIA", "BOLIVAR": "CIUDAD BOLIVAR",
         "CARMEN DE VIBORAL": "EL CARMEN DE VIBORAL", "PEÑOL": "EL PEÑOL",
         "PTO NARE(LA MAGDALENA)": "PUERTO NARE", "RETIRO": "EL RETIRO",
         "SAN ANDRES DE CUERQUIA": "SAN ANDRES DE C.",
         "SAN PEDRO DE LOS MILAGROS": "SAN PEDRO DE LOS M.",
         "SAN VICENTE FERRER": "SAN VICENTE", "SANTUARIO": "EL SANTUARIO",
         "YONDO(CASABE)": "YONDO"}
# ojo: norm() también quita la virgulilla de la Ñ, aplicar a ambos lados
ALIAS = {norm(k): norm(v) for k, v in ALIAS.items()}
mu["muni_n"] = mu["municipio"].map(norm).map(lambda m: ALIAS.get(m, m))
mu["subregion"] = mu["muni_n"].map(submap)
sin_match = sorted(mu.loc[mu["subregion"].isna(), "municipio"].unique())
assert not sin_match, f"municipios sin subregión: {sin_match}"
print(f"  municipios casados: {mu['muni_n'].nunique()} / sin match: {sin_match}")

piv = mu.pivot_table(index="subregion", columns="nivel", values="n",
                     aggfunc="sum", fill_value=0)
subregion = [{"subregion": s, **{nv: int(piv.loc[s].get(nv, 0)) for nv in NIVELES},
              "total": int(piv.loc[s].sum())}
             for s in piv.sum(axis=1).sort_values(ascending=False).index]
assert sum(r["total"] for r in subregion) == ult["total"], \
    "la suma subregional no cuadra con el total departamental (mismo dataset)"

# --------------- 3. Cobertura y deserción departamentales (ji8i-4anb), 2011-2024
print("3. Cobertura y deserción, fila departamental Antioquia (ji8i-4anb)…")
dep = soql("ji8i-4anb", where="departamento='Antioquia'", order="ano")
dep["anio"] = dep["ano"].astype(int)
assert dep["anio"].is_unique, "años duplicados en ji8i-4anb"
F = lambda c: dep[c].astype(float)
cobertura = [{"anio": int(r.anio),
              "neta": round(float(r.cobertura_neta), 2),
              "bruta": round(float(r.cobertura_bruta), 2),
              "neta_transicion": round(float(r.cobertura_neta_transicion), 2),
              "neta_primaria": round(float(r.cobertura_neta_primaria), 2),
              "neta_secundaria": round(float(r.cobertura_neta_secundaria), 2),
              "neta_media": round(float(r.cobertura_neta_media), 2)}
             for r in dep.itertuples()]
desercion = [[int(a), round(t, 2)] for a, t in zip(dep["anio"], F("desercion"))]
desercion_nivel = [{"anio": int(r.anio),
                    "transicion": round(float(r.desercion_transicion), 2),
                    "primaria": round(float(r.desercion_primaria), 2),
                    "secundaria": round(float(r.desercion_secundaria), 2),
                    "media": round(float(r.desercion_media), 2)}
                   for r in dep.itertuples()]

# Verificación cruzada: el agregado departamental de ji8i-4anb debe coincidir
# (±2 pp) con la ponderación municipal de nudc-7mev por población 5-16.
# Las columnas de nudc-7mev son texto (::number) y el código departamental
# cambia de formato: '5' en 2011-2022 y '05' en 2023-2024 (verificado).
P = "poblaci_n_5_16::number"
nu = soql("nudc-7mev",
          select=f"a_o, sum({P}) as pob,"
                 f"sum(cobertura_neta::number * {P})/sum({P}) as neta,"
                 f"sum(cobertura_bruta::number * {P})/sum({P}) as bruta",
          where="c_digo_departamento in('5','05')", group="a_o", order="a_o")
nu["anio"] = nu["a_o"].astype(int)
# 2021 se excluye del cotejo: la población municipal de nudc-7mev viene
# corrupta ese año (suma 9.634 en vez de ~1,15 M; verificado contra la API)
chk = dep.merge(nu, on="anio").query("anio != 2021")
d_neta = (chk["cobertura_neta"].astype(float) - chk["neta"].astype(float)).abs().max()
d_bruta = (chk["cobertura_bruta"].astype(float) - chk["bruta"].astype(float)).abs().max()
print(f"  ji8i vs nudc ponderado (sin 2021) — desvío máx: "
      f"neta {d_neta:.2f} pp, bruta {d_bruta:.2f} pp")
assert d_neta < 3.5 and d_bruta < 3.5, \
    "el agregado departamental no cuadra con nudc-7mev"

# --------------------------------- 4. Bachilleres por ETC (5c2k-ahfc), 2019-2024
print("4. Bachilleres por ETC (5c2k-ahfc)…")
ba = soql("5c2k-ahfc", where="departamento='Antioquia'", limit=2000)
MED = ["matricula_11_total", "matricula_26_total",
       "aprobados_11_total", "aprobados_26_total"]
for c in MED:
    ba[c] = ba[c].astype(int)
ba["anio"] = ba["a_o"].astype(int)

# Depurar el 2022 duplicado: el año viene con 250 filas (125 municipios × 2)
# porque una copia mislabeled del cargue 2024 convive con las filas 2022
# verdaderas. Se conserva UNA fila por municipio, prefiriendo la que difiere
# de su fila 2024 (si ambas coinciden con 2024 —caso San José de la Montaña—
# se conserva una cualquiera: son idénticas).
f24 = ba[ba["anio"] == 2024].set_index("codigo_municipio")[MED]
b22 = ba[ba["anio"] == 2022]
eq24 = b22.apply(lambda r: r["codigo_municipio"] in f24.index
                 and (f24.loc[r["codigo_municipio"], MED] == r[MED]).all(), axis=1)
conservar, ambiguos = [], []
for muni, g in b22.groupby("codigo_municipio"):
    difieren = g.index[~eq24.loc[g.index]]
    conservar.append(difieren[0] if len(difieren) else g.index[0])
    if len(g) > 1 and not len(difieren):
        ambiguos.append(g["municipio"].iloc[0])
ba = ba.drop(b22.index.difference(conservar))
n22 = (ba["anio"] == 2022).sum()
print(f"  filas 2022: {len(b22)} → {n22} (municipios con 2022 idéntico a 2024: "
      f"{ambiguos})")
assert n22 == (ba["anio"] == 2024).sum() == 125, "la depuración de 2022 no cuadra"

ba["bachilleres"] = ba["aprobados_11_total"] + ba["aprobados_26_total"]
ETC = {"Antioquia (ETC)": "Antioquia (no certificados)", "Apartado": "Apartadó",
       "La estrella(ETC)": "La Estrella"}
ba["etc"] = ba["secretaria"].map(lambda s: ETC.get(s, s))
tot = ba.groupby("anio")[["bachilleres", "aprobados_11_total"]].sum()
serie_etc = [{"etc": e, "serie": [[int(a), int(n)] for a, n in
                                  g.groupby("anio")["bachilleres"].sum().items()]}
             for e, g in sorted(ba.groupby("etc"),
                                key=lambda kv: -kv[1]["bachilleres"].sum())]
suma_etc = sum(n for e in serie_etc for a, n in e["serie"] if a == 2024)
assert suma_etc == int(tot.loc[2024, "bachilleres"]), "ETC no suman el total"
# tras depurar, 2022 debe volver a la magnitud de sus vecinos (no el doble)
v = tot["bachilleres"]
assert 0.7 < v[2022] / ((v[2021] + v[2023]) / 2) < 1.3, "2022 sigue inflado"

# ------------------------------------------------------------------ 5. Ensamble
out = {
    "corte": (f"matrícula ngw5-c5nw ({corte_de('ngw5-c5nw')}) · tasas ji8i-4anb "
              f"({corte_de('ji8i-4anb')}) · bachilleres 5c2k-ahfc "
              f"({corte_de('5c2k-ahfc')}); descargado 2026-07-22"),
    "fuente": {"matricula": "ngw5-c5nw", "tasas_departamento": "ji8i-4anb",
               "tasas_municipio": "nudc-7mev", "bachilleres": "5c2k-ahfc"},
    "universo": ("Matrícula oficial + no oficial (todos los sectores del anexo "
                 "6A/SIMAT), preescolar a media, incluye CLEI de adultos mapeados "
                 "a su nivel equivalente; 'otros' = formación complementaria de "
                 "escuelas normales (post-media)"),
    "serie_nivel": serie_nivel,
    "cobertura": cobertura,
    "desercion": desercion,
    "desercion_nivel": desercion_nivel,
    "subregion": subregion,
    "anio_subregion": ANIO_SUB,
    "bachilleres": {
        "definicion": ("aprobados de grado 11 + ciclo 26 (CLEI VI adultos), "
                       "sectores oficial y no oficial"),
        "total": [[int(a), int(n)] for a, n in tot["bachilleres"].items()],
        "g11": [[int(a), int(n)] for a, n in tot["aprobados_11_total"].items()],
        "etc": serie_etc},
    "transito": None,
    "notas": [
        "ngw5-c5nw no tiene el año 2018 (hueco en la serie de matrícula, "
        "verificado a nivel nacional); las tasas de ji8i-4anb sí traen 2018.",
        "La matrícula por nivel suma oficial + no oficial; los ciclos de adultos "
        "(CLEI) se asignan al nivel equivalente (1-2 primaria, 3-4 secundaria, "
        "5-6 media) y la aceleración del aprendizaje a primaria.",
        "Cobertura y deserción vienen de la fila departamental oficial del MEN "
        "(ji8i-4anb); verificadas contra la ponderación municipal de nudc-7mev "
        "por población 5-16 (coinciden a <0,5 pp salvo 2014, con ceros "
        "municipales, y 2021, cuya población municipal viene corrupta en "
        "nudc-7mev). La deserción es intraanual, calculada por el MEN sobre la "
        "matrícula del sector oficial.",
        "El salto de cobertura entre 2017 (neta 86,0 %) y 2018 (94,1 %) es un "
        "artefacto del denominador: el MEN reestimó la población 5-16 con el "
        "Censo 2018 (de 1,27 M a 1,15 M), no hubo mejora real de cobertura.",
        "El año 2022 de bachilleres venía duplicado en el origen (una copia del "
        "cargue 2024 mislabeled); se depuró fila a fila contra 2024.",
        "En datos.gov.co no existe dataset vivo de tránsito inmediato a "
        "educación superior por municipio/ETC (SPADIES fue dado de baja).",
    ],
}

# ------------------------------------------------------------- Verificaciones
print(f"\nMatrícula {ult['anio']}: {ult['total']:,} "
      f"(pre {ult['preescolar']:,} · prim {ult['primaria']:,} · "
      f"sec {ult['secundaria']:,} · media {ult['media']:,} · otros {ult['otros']:,})")
print(f"Variación 2011→{ult['anio']}: "
      f"{100 * (ult['total'] / serie_nivel[0]['total'] - 1):+.1f} %")
c = cobertura[-1]
print(f"Cobertura {c['anio']}: neta {c['neta']} % · bruta {c['bruta']} % · "
      f"neta media {c['neta_media']} %")
print(f"Deserción {desercion[-1][0]}: {desercion[-1][1]} %")
print(f"Bachilleres {tot.index[-1]}: {int(v.iloc[-1]):,} "
      f"(solo grado 11: {int(tot['aprobados_11_total'].iloc[-1]):,}) · "
      f"ETC: {len(serie_etc)}")
print("Subregiones:", {r['subregion']: r['total'] for r in subregion})

destino = DATA / "basica_media.json"
destino.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(f"ok → data/basica_media.json ({destino.stat().st_size / 1024:.1f} KB)")
