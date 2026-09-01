#!/usr/bin/env python3
"""Antioquia dentro del ranking nacional de matrícula 2025.

Fuente 2025: «Las 50 IES más grandes del país, por número de estudiantes, en 2025»
(El Observatorio de la Universidad Colombiana, 29-jul-2026), que publica la tabla
completa de las 275 IES con matrícula reportada al MEN, a corte 2025-2 y con los
totales de cada IES incluyendo sus seccionales.

Fuente 2024: base consolidada SNIES 2024 local (`data/matriculados_2024.xlsx`),
agregada por IES PADRE y semestre 2. Ese método reproduce exactamente el ranking
2024 publicado por la misma fuente (SENA 421.621, UNAD 179.955, UdeA 40.619…),
así que las variaciones 2024→2025 se calculan aquí en vez de tomarse del texto:
así hay Δ para las 39 antioqueñas y no sólo para las que caben en el top 50.

Salida: public/ranking_nacional.json
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
PUBLIC = RAIZ / "public"

# --- constantes de corte (cambiar aquí para un corte nuevo, no en el JSON) ---
AS_OF = "2026-07-30"
VIGENCIA = 2025
SEMESTRE_RANKING = 2
URL_2025 = ("https://www.universidad.edu.co/"
            "las-50-ies-mas-grandes-del-pais-por-numero-de-estudiantes-en-2025/")
FUENTE = "El Observatorio de la Universidad Colombiana"
FECHA_PUB = "29 de julio de 2026"
CACHE = DATA / "ranking_nacional_2025.html"

# Totales del sector que publica la propia fuente (para el contexto nacional)
NACIONAL = {"total": 2_723_364, "oficial": 1_545_484, "privada": 1_177_880,
            "ies_con_matricula": 275, "ies_registradas": 305}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s).rstrip("-")


# Un nombre contenido en otro sólo se acepta como la misma IES si cubre buena
# parte del nombre largo. Sin este umbral, «Universidad CES» (Antioquia) casaría
# con «María Goreti - Universidad CESMAG» (Nariño), que la contiene literalmente.
COBERTURA_MIN = 0.62
LARGO_MIN = 12


def contiene(a: str, b: str) -> bool:
    corto, largo = (a, b) if len(a) <= len(b) else (b, a)
    return (corto in largo and len(corto) > LARGO_MIN
            and len(corto) / len(largo) >= COBERTURA_MIN)


def descargar_2025() -> str:
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(URL_2025, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        h = r.read().decode("utf-8", errors="replace")
    CACHE.write_text(h, encoding="utf-8")
    return h


def parsear_ranking_2025(h: str) -> list[dict]:
    """Extrae las 275 filas. La tabla larga trae (posición, IES, matrícula);
    la del top 50 trae además la ubicación del año anterior."""
    filas, vistos = [], set()
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        celdas = [html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip()
                  for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        celdas = [c for c in celdas if c]

        def num(x):
            x = x.replace(".", "").replace(",", "").replace(" ", "").strip()
            return int(x) if x.isdigit() else None

        if len(celdas) >= 4 and num(celdas[0]) and num(celdas[1]):
            pos, nom, mat = num(celdas[0]), celdas[2], num(celdas[-1])
        elif len(celdas) == 3 and num(celdas[0]):
            pos, nom, mat = num(celdas[0]), celdas[1], num(celdas[-1])
        else:
            continue
        if pos is None or mat is None or pos in vistos:
            continue
        vistos.add(pos)
        filas.append({"pos": pos, "ies": nom, "mat": mat})
    if len(filas) != NACIONAL["ies_con_matricula"]:
        raise SystemExit(f"Esperaba 275 IES en el ranking 2025, extraje {len(filas)}")
    return sorted(filas, key=lambda r: r["pos"])


def ranking_2024_desde_snies() -> tuple[list[dict], dict]:
    """Reconstruye el ranking nacional 2024 (todas las IES) desde el SNIES local."""
    xl = pd.ExcelFile(DATA / "matriculados_2024.xlsx")
    hoja = next(s for s in xl.sheet_names if "NDICE" not in s.upper())
    peek = pd.read_excel(xl, sheet_name=hoja, header=None, nrows=15)
    hdr = next(i for i, row in peek.iterrows()
               if "AÑO" in [str(x).strip().upper() for x in row.tolist()]
               and any(str(x).strip().upper().startswith("MATRICULADOS") for x in row.tolist()))
    df = pd.read_excel(xl, sheet_name=hoja, header=hdr)
    df.columns = [" ".join(str(c).upper().split()) for c in df.columns]
    df["MATRICULADOS"] = pd.to_numeric(df["MATRICULADOS"], errors="coerce").fillna(0)
    df = df[df["SEMESTRE"] == SEMESTRE_RANKING].copy()

    ficha = df.drop_duplicates("CÓDIGO DE LA INSTITUCIÓN").set_index("CÓDIGO DE LA INSTITUCIÓN")
    tot = df.groupby("IES PADRE")["MATRICULADOS"].sum().sort_values(ascending=False)

    salida = []
    for pos, (cod, val) in enumerate(tot.items(), 1):
        r = ficha.loc[cod] if cod in ficha.index else None
        salida.append({
            "pos": pos,
            "codigo": int(cod),
            "ies": str(r["INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)"]).strip() if r is not None else str(cod),
            "sector": ("Oficial" if str(r["SECTOR IES"]).strip().lower().startswith("ofic")
                       else "Privada") if r is not None else "?",
            "caracter": str(r["CARÁCTER IES"]).strip() if r is not None else "?",
            "depto": str(r["DEPARTAMENTO DE DOMICILIO DE LA IES"]).strip().upper() if r is not None else "?",
            "mat": int(val),
        })
    meta = {"total_2024_sem2": int(df["MATRICULADOS"].sum()), "ies": len(salida)}
    return salida, meta


# Alias para casar los nombres del ranking 2025 con los del SNIES 2024.
# Clave = normalización del nombre SNIES; valor = fragmento a buscar en el ranking.
# Un valor con «=» delante exige igualdad exacta de la normalización (para nombres
# cortos que son prefijo de otros: «Universidad CES» vs «Universidad CESMAG»).
ALIAS = {
    "universidadeafit": "eafit",
    "universidadces": "=universidadces",
    "fundacionuniversitariaceipa": "ceipa",
    "universidadeia": "=universidadeia",
    "institutotecnologicometropolitano": "metropolitano",
    "tecnologicodeantioquia": "=tecnologicodeantioquia",
    # el ranking 2025 escribe «Universtaria» (sic) en el nombre de la IU Digital
    "institucionuniversitariadigitaldeantioquiaiudigital": "digitaldeantioquia",
    "corporacionacademiatecnologicadecolombiaatec": "academiatecnologicadecolombia",
    "corporacionacademiasuperiordeartes": "academiasuperiordeartes",
    "escueladetecnologiasdeantioquiaeta": "tecnologiasdeantioquia",
    "tecnologicodeartesdeboraarangoinstitucionredefinida": "deboraarango",
    "fundacionuniversitariabellasartes": "bellasartesmedellin",
    "corporaciontecnologicacatolicadeoccidentetecoc": "tecoc",
    "fundaciondeestudiossuperioresuniversitariosdeurabaantonioroldanbetancur": "uraba",
    "institucionuniversitariasalazaryherrera": "salazaryherrera",
}


# Erratas tipográficas de la fuente que no deben propagarse al sitio
ERRATAS = {
    "Institución Universtaria Digital de Antioquia -IU. DIGITAL":
        "Institución Universitaria Digital de Antioquia — IU Digital",
    "Coporación Academia Superior de Artes": "Corporación Academia Superior de Artes",
    "Tecnologico de Artes Débora Arango": "Tecnológico de Artes Débora Arango",
}


def casar(nom_snies: str, rank25: list[dict]) -> dict | None:
    a = norm(nom_snies).rstrip("-")
    clave = ALIAS.get(a)
    if clave:
        if clave.startswith("="):
            hits = [r for r in rank25 if norm(r["ies"]) == clave[1:]]
        else:
            hits = [r for r in rank25 if clave in norm(r["ies"])]
        return hits[0] if len(hits) == 1 else None
    exactos = [r for r in rank25 if norm(r["ies"]) == a]
    if len(exactos) == 1:
        return exactos[0]
    # Si tras la contención queda más de un candidato se descarta: es preferible
    # un hueco a un cruce equivocado.
    hits = [r for r in rank25 if contiene(a, norm(r["ies"]))]
    return hits[0] if len(hits) == 1 else None


def main() -> None:
    rank25 = parsear_ranking_2025(descargar_2025())
    rank24, meta24 = ranking_2024_desde_snies()

    idx25_por_pos = {r["pos"]: r for r in rank25}
    ant = [r for r in rank24 if r["depto"] == "ANTIOQUIA"]

    registros, sin_match = [], []
    for r in sorted(ant, key=lambda x: x["pos"]):
        m = casar(r["ies"], rank25)
        if not m:
            sin_match.append(r["ies"])
            continue
        delta = m["mat"] - r["mat"]
        registros.append({
            # se muestra el nombre tal como lo escribe la fuente (el SNIES viene en
            # mayúscula sostenida), conservando el del SNIES para trazabilidad
            "ies": ERRATAS.get(m["ies"].strip(), m["ies"].strip()),
            "ies_snies": r["ies"].strip().rstrip("-").strip(),
            "codigo": r["codigo"],
            "sector": r["sector"],
            "caracter": r["caracter"],
            "pos25": m["pos"],
            "pos24": r["pos"],
            "dpos": r["pos"] - m["pos"],          # positivo = sube en el ranking
            "mat25": m["mat"],
            "mat24": r["mat"],
            "delta": delta,
            "pct": round(delta / r["mat"] * 100, 1) if r["mat"] else None,
            # cifra idéntica a la del año anterior: puede ser estabilidad real o
            # arrastre del dato 2024 cuando la IES no reportó
            "sin_variacion": delta == 0,
        })

    if sin_match:
        print("⚠ sin correspondencia en el ranking 2025:", sin_match)

    registros.sort(key=lambda x: x["pos25"])

    # --- contexto nacional: quién más creció / más cayó en todo el país ---
    # mismo criterio conservador: exacto primero, contención sólo si es inequívoca
    movimientos = []
    for r25 in rank25:
        n25 = norm(r25["ies"])
        cand = [r for r in rank24 if norm(r["ies"]) == n25]
        if len(cand) != 1:
            cand = [r for r in rank24 if contiene(n25, norm(r["ies"]))]
        if len(cand) != 1:
            continue
        movimientos.append({"ies": r25["ies"], "delta": r25["mat"] - cand[0]["mat"],
                            "depto": cand[0]["depto"]})
    movimientos.sort(key=lambda x: -x["delta"])
    cobertura = round(len(movimientos) / len(rank25) * 100)

    ant_top50 = [r for r in registros if r["pos25"] <= 50]
    ant_top100 = [r for r in registros if r["pos25"] <= 100]
    suma25 = sum(r["mat25"] for r in registros)
    suma24 = sum(r["mat24"] for r in registros)

    doc = {
        "meta": {
            "as_of": AS_OF,
            "vigencia": VIGENCIA,
            "corte": f"{VIGENCIA}-{SEMESTRE_RANKING}",
            "fuente_2025": FUENTE,
            "fuente_2025_url": URL_2025,
            "fuente_2025_fecha": FECHA_PUB,
            "fuente_2024": "SNIES, base consolidada 2024 (agregado por IES padre, semestre 2)",
            "alcance": ("Totales por institución incluyendo seccionales y sedes en todo el país; "
                        "no es la matrícula ofertada en Antioquia."),
            "nacional": NACIONAL,
            "total_2024_sem2": meta24["total_2024_sem2"],
        },
        "resumen": {
            "ies_antioquia": len(registros),
            "en_top50": len(ant_top50),
            "en_top100": len(ant_top100),
            "matricula25": suma25,
            "matricula24": suma24,
            "delta": suma25 - suma24,
            "pct": round((suma25 - suma24) / suma24 * 100, 1),
            "peso_nacional": round(suma25 / NACIONAL["total"] * 100, 1),
            "crecen": sum(1 for r in registros if r["delta"] > 0),
            "caen": sum(1 for r in registros if r["delta"] < 0),
        },
        "ies": registros,
        "mayor_alza_pais": movimientos[:10],
        "mayor_caida_pais": movimientos[-10:][::-1],
        "cobertura_cruce_pct": cobertura,
    }

    destino = PUBLIC / "ranking_nacional.json"
    destino.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {destino.relative_to(RAIZ)} — {len(registros)} IES de Antioquia")
    print(f"  top 50: {len(ant_top50)} · top 100: {len(ant_top100)}")
    print(f"  matrícula 2025-2: {suma25:,} ({doc['resumen']['pct']:+}% vs 2024-2)")
    print(f"  peso en el país: {doc['resumen']['peso_nacional']} %")


if __name__ == "__main__":
    main()
