#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga TODOS los insumos del observatorio a data/ (≈500 MB, no versionados).
Reproduce el estado exacto con el que se construyó el tablero.

    python3 scripts/descargar_datos.py            # descarga lo que falte
    python3 scripts/descargar_datos.py --forzar   # vuelve a bajar todo

Luego:
    python3 scripts/preparar_poblacion.py   # población 17-21 (requiere dane_pob_mun.xlsx)
    python3 scripts/procesar.py             # genera public/datos.json y public/datos.js
"""
import argparse, json, subprocess, sys, urllib.parse, zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
FORZAR = "--forzar" in sys.argv

# ---------------------------------------------------------------- SNIES (MEN)
SNIES = "https://snies.mineducacion.gov.co/1778/articles-{}_recurso.xlsx"
# Bases consolidadas. Si el MEN publica una vigencia nueva, agregar aquí el
# número de artículo (está en snies.mineducacion.gov.co/portal/ESTADISTICAS/Bases-consolidadas/)
ARTICULOS = {
    "matriculados_2018.xlsx": 391575, "matriculados_2019.xlsx": 401908,
    "matriculados_2020.xlsx": 406671, "matriculados_2021.xlsx": 411252,
    "matriculados_2022.xlsx": 416244, "matriculados_2023.xlsx": 421539,
    "matriculados_2024.xlsx": 425151,
    "graduados_2018.xlsx": 391581, "graduados_2019.xlsx": 401906,
    "graduados_2020.xlsx": 408968, "graduados_2021.xlsx": 411250,
    "graduados_2022.xlsx": 416247, "graduados_2023.xlsx": 421535,
    "graduados_2024.xlsx": 425146,
    "inscritos_2018.xlsx": 391557, "inscritos_2019.xlsx": 401907,
    "inscritos_2020.xlsx": 406670, "inscritos_2021.xlsx": 411251,
    "inscritos_2022.xlsx": 416246, "inscritos_2023.xlsx": 421538,
    "inscritos_2024.xlsx": 425148,
    "primer_curso_2018.xlsx": 391569, "primer_curso_2019.xlsx": 401909,
    "primer_curso_2020.xlsx": 406672, "primer_curso_2021.xlsx": 411254,
    "primer_curso_2022.xlsx": 416245, "primer_curso_2023.xlsx": 421541,
    "primer_curso_2024.xlsx": 425155,
    "admitidos_2024.xlsx": 425154, "docentes_2024.xlsx": 425156,
}

# ---------------------------------------------------- Otras fuentes directas
DIRECTAS = {
    # OLE — Observatorio Laboral para la Educación (base IBC 2023, corte más reciente)
    "ole_base_ibc_2023.xlsx": "https://ole.mineducacion.gov.co/1769/articles-425926_recurso_1.xlsx",
    # MinCiencias — resultados finales Convocatoria 957 de 2024 (Res. 1531 de dic-2025), PDF 508 pp.
    "grupos_957_2025.pdf": "https://minciencias.gov.co/sites/default/files/resultados_finales_de_grupos_de_investigacion_957_0.pdf",
    # DANE — proyecciones municipales por área, sexo y edad (CNPV 2018). 126 MB: descarga lenta.
    "dane_pob_mun.xlsx": "https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/Municipal/PPED-AreaSexoEdadMun-2018-2042_VP.xlsx",
}

# ------------------------------------------------- datos.gov.co (API Socrata)
SOC = "https://www.datos.gov.co/resource/{}.{}?{}"
SABER, GRUPOS_HIST, AGRO = "iwgf-bkfk", "hrhc-c4wu", "t2ca-uae5"
ANT = "estu_prgm_departamento='ANTIOQUIA'"
ANT22 = f"{ANT} AND periodo in('20221','20224')"
MODS = ("mod_razona_cuantitat_punt,mod_lectura_critica_punt,mod_competen_ciudada_punt,"
        "mod_comuni_escrita_punt,mod_ingles_punt")

def soql(dataset, fmt="json", **params):
    q = urllib.parse.urlencode({f"${k}": v for k, v in params.items()}, quote_via=urllib.parse.quote)
    return SOC.format(dataset, fmt, q)

API = {
    # Saber TyT — microdato de Antioquia (161.281 filas, 4 páginas de 50 mil)
    **{f"saber_tyt_ant_{off}.csv": soql(
        SABER, "csv",
        select=("periodo,inst_cod_institucion,inst_nombre_institucion,inst_origen,"
                "estu_nivel_prgm_academico,estu_prgm_academico,estu_prgm_municipio,estu_genero,"
                "fami_estratovivienda,fami_educacionmadre,fami_tieneinternet,fami_tienecomputador,"
                "estu_horassemanatrabaja,estu_valormatriculauniversidad,estu_pagomatriculabeca,"
                "estu_pagomatriculacredito,estu_pagomatriculapropio," + MODS),
        where=ANT, order="estu_consecutivo", limit=50000, offset=off)
       for off in (0, 50000, 100000, 150000)},
    # Saber TyT — promedios nacionales por periodo (para el comparativo)
    "saber_tyt_nacional_periodos.json": soql(
        SABER,
        select=("periodo,avg(mod_razona_cuantitat_punt::number) as rc,"
                "avg(mod_lectura_critica_punt::number) as lc,avg(mod_competen_ciudada_punt::number) as cc,"
                "avg(mod_comuni_escrita_punt::number) as ce,avg(mod_ingles_punt::number) as ing,count(*) as n"),
        group="periodo", order="periodo"),
    # Saber TyT — puntaje por municipio de oferta (Antioquia, 2022)
    "saber_municipio_2022.json": soql(
        SABER,
        select=("estu_prgm_municipio,avg(mod_razona_cuantitat_punt::number) as rc,"
                "avg(mod_lectura_critica_punt::number) as lc,avg(mod_competen_ciudada_punt::number) as cc,"
                "avg(mod_comuni_escrita_punt::number) as ce,avg(mod_ingles_punt::number) as ing,count(*) as n"),
        where=ANT22, group="estu_prgm_municipio", limit=200),
    # Bilingüismo — niveles MCER de inglés
    "ingles_ant_periodo.json": soql(SABER, select="periodo,mod_ingles_desem,count(*)",
                                    where=ANT, group="periodo,mod_ingles_desem", limit=200),
    "ingles_nal_periodo.json": soql(SABER, select="periodo,mod_ingles_desem,count(*)",
                                    group="periodo,mod_ingles_desem", limit=200),
    "ingles_ies_2022.json": soql(SABER, select="inst_nombre_institucion,mod_ingles_desem,count(*)",
                                 where=ANT22, group="inst_nombre_institucion,mod_ingles_desem", limit=2000),
    # MinCiencias — base histórica de convocatorias (da departamento y gran área por código GrupLAC)
    **{f"grupos_map_{off}.json": soql(
        GRUPOS_HIST, select="cod_grupo_gr,nme_departamento_gr,nme_gran_area_gr,ano_convo",
        order="ano_convo,cod_grupo_gr", limit=25000, offset=off) for off in (0, 25000)},
    # Gobernación de Antioquia — correspondencia municipio ↔ subregión
    "subregiones_raw.json": soql(AGRO, select="municipio,subregion,count(*)",
                                 group="municipio,subregion", limit=300),
    # MEN — matrícula histórica (solo para trazabilidad; descartada en la serie por reporte inconsistente)
    "api_matricula_nivel_sector.json": soql(
        "5wck-szir", select="a_o,semestre,id_nivel_formacion,id_sector,sum(matriculados_2015)",
        where="departamento_de_oferta_del_programa='ANTIOQUIA' AND id_nivel_formacion in('4','5','7','8')",
        group="a_o,semestre,id_nivel_formacion,id_sector", order="a_o", limit=2000),
}

def bajar(nombre, url, timeout=1800):
    destino = DATA / nombre
    if destino.exists() and not FORZAR:
        print(f"  ✓ {nombre} (ya existe)")
        return True
    print(f"  ↓ {nombre} …", flush=True)
    r = subprocess.run(["curl", "-sL", "--max-time", str(timeout), "-o", str(destino), url])
    ok = r.returncode == 0 and destino.exists() and destino.stat().st_size > 1000
    if ok and nombre.endswith(".xlsx"):
        try:
            zipfile.ZipFile(destino)  # los .xlsx son zips: detecta descargas truncadas
        except zipfile.BadZipFile:
            print(f"  ✗ {nombre} llegó truncado — reintente (el archivo del DANE es grande)")
            destino.unlink(missing_ok=True)
            return False
    print(f"  {'✓' if ok else '✗'} {nombre}")
    return ok

def main():
    fallos = []
    print("== SNIES — bases consolidadas del MEN ==")
    for nombre, art in ARTICULOS.items():
        if not bajar(nombre, SNIES.format(art), 600): fallos.append(nombre)
    print("== OLE · MinCiencias · DANE ==")
    for nombre, url in DIRECTAS.items():
        if not bajar(nombre, url, 1800): fallos.append(nombre)
    print("== datos.gov.co (ICFES, MinCiencias, Gobernación) ==")
    for nombre, url in API.items():
        if not bajar(nombre, url, 300): fallos.append(nombre)

    # Derivados que necesita procesar.py
    print("== Derivados ==")
    sr = DATA / "subregiones.json"
    if FORZAR or not sr.exists():
        raw = json.load(open(DATA / "subregiones_raw.json"))
        mapa = {r["municipio"].strip(): r.get("subregion", "").strip()
                for r in raw if r.get("municipio")}
        json.dump(mapa, open(sr, "w"), ensure_ascii=False)
        print(f"  ✓ subregiones.json ({len(mapa)} municipios)")
    cm = DATA / "grupos_cod_map.json"
    if FORZAR or not cm.exists():
        m = {}
        for f in ("grupos_map_0.json", "grupos_map_25000.json"):
            for r in json.load(open(DATA / f)):  # ordenado por año: gana la convocatoria más reciente
                m[r["cod_grupo_gr"]] = {"depto": r.get("nme_departamento_gr"),
                                        "area": r.get("nme_gran_area_gr")}
        json.dump(m, open(cm, "w"), ensure_ascii=False)
        print(f"  ✓ grupos_cod_map.json ({len(m)} códigos GrupLAC)")
    g957 = DATA / "grupos_957.json"
    if FORZAR or not g957.exists():
        try:
            import pdfplumber, re
        except ImportError:
            print("  ! falta pdfplumber (pip install pdfplumber) → grupos_957.json pendiente")
            fallos.append("grupos_957.json")
        else:
            filas = []
            with pdfplumber.open(DATA / "grupos_957_2025.pdf") as pdf:
                for p in pdf.pages:
                    for r in (p.extract_table() or []):
                        c = [(str(x).replace("\n", " ").strip() if x else "") for x in r]
                        if len(c) < 9: continue
                        cod = c[0].replace(" ", "")
                        if not re.fullmatch(r"COL\d+", cod): continue
                        filas.append({"cod": cod, "nombre": c[1], "avales": c[3],
                                      "reconocido": "✓" in c[4], "clas": c[8].strip()})
            json.dump(filas, open(g957, "w"), ensure_ascii=False)
            print(f"  ✓ grupos_957.json ({len(filas)} grupos)")

    print()
    if fallos:
        print("FALLARON:", ", ".join(fallos))
        print("Reintente; el archivo del DANE (126 MB) a veces se corta a mitad.")
    else:
        print("Todo listo. Siga con:")
        print("  python3 scripts/preparar_poblacion.py")
        print("  python3 scripts/procesar.py")

if __name__ == "__main__":
    main()
