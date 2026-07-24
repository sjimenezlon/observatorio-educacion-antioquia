#!/usr/bin/env python3
"""Verificación V35: antesala, financiación, OLE por programa y coherencia del registro.

Comprueba que las cifras publicadas por la V35 sean internamente consistentes
(las sumas cuadran, los umbrales se cumplen, ninguna ruta viva tiene fecha
vencida) y deja el resultado en public/verificacion-v35.json.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOY = date(2026, 7, 24)


def check(name: str, ok: bool, detail: str) -> dict:
    if not ok:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "ok", "detail": detail}


def main() -> None:
    bm = json.loads((ROOT / "data" / "basica_media.json").read_text())
    fx = json.loads((ROOT / "data" / "financiacion.json").read_text())
    sena = json.loads((ROOT / "data" / "sena_fpi.json").read_text())
    olep = json.loads((ROOT / "public" / "ole_programas.js").read_text().removeprefix("window.OLEP=").removesuffix(";"))
    fuentes = json.loads((ROOT / "public" / "fuentes-antioquia.json").read_text())
    rutas = json.loads((ROOT / "public" / "oportunidades-antioquia.json").read_text())
    index = (ROOT / "public" / "index.html").read_text()

    checks = []

    # --- antesala: básica y media ---
    u2024 = next(r for r in bm["serie_nivel"] if r["anio"] == 2024)
    suma = u2024["preescolar"] + u2024["primaria"] + u2024["secundaria"] + u2024["media"] + u2024["otros"]
    checks.append(check("bm_total_2024", suma == u2024["total"] == 1148645, f"niveles suman el total 2024 ({u2024['total']:,})"))
    sub_total = sum(s["total"] for s in bm["subregion"])
    checks.append(check("bm_subregiones", sub_total == u2024["total"], "9 subregiones suman exactamente el total departamental"))
    checks.append(check("bm_sin_2018", all(r["anio"] != 2018 for r in bm["serie_nivel"]), "la serie declara el hueco 2018 del dataset origen"))
    cob24 = next(c for c in bm["cobertura"] if c["anio"] == 2024)
    checks.append(check("bm_cobertura_media", cob24["neta_media"] == 52.81, "cobertura neta de media 2024 = 52,81 %"))
    bach24 = dict(bm["bachilleres"]["total"])[2024]
    checks.append(check("bm_bachilleres", bach24 == 86837, "bachilleres 2024 = 86.837"))

    # --- financiación ---
    o2025 = next(o for o in fx["icetex"]["otorgados"] if o["anio"] == 2025)
    o2024 = next(o for o in fx["icetex"]["otorgados"] if o["anio"] == 2024)
    var = round(100 * (o2025["n"] - o2024["n"]) / o2024["n"], 1)
    checks.append(check("icetex_desplome", o2025["n"] == 484 and var == -84.7, f"créditos nuevos 2025 = 484 ({var} %)"))
    cart = fx["icetex"]["cartera"]["epocas"]["AMORTIZACION"]
    mora = cart["mora_1_90d"] + cart["mora_mas_90d"]
    checks.append(check("icetex_mora", cart["al_dia"] + mora == cart["creditos"] and round(100 * mora / cart["creditos"], 1) == 28.9,
                        "cartera en amortización cuadra y la mora es 28,9 % de los créditos"))
    checks.append(check("becas_subregion", sum(n for _, n in fx["becas_gob"]["subregion"]) == fx["becas_gob"]["total"] == 14566,
                        "las 9 subregiones suman los 14.566 beneficiarios"))
    g = fx["becas_gob"]["graduacion"]
    checks.append(check("becas_graduacion", round(100 * g["graduados"] / g["universo"], 1) == 59.4, "graduación 59,4 % en cohortes 2013-2018"))

    # --- SENA ---
    checks.append(check("sena_universo", sena["aprendices"]["titulada"] + sena["aprendices"]["complementaria"] == sena["aprendices"]["total"] == 168420,
                        "titulada + complementaria = 168.420 aprendices"))
    checks.append(check("sena_niveles", sum(n for _, n in sena["aprendices"]["nivel"]) == sena["aprendices"]["total"],
                        "los 6 niveles suman el total de aprendices"))

    # --- OLE por programa ---
    checks.append(check("ole_umbral", all(p["n"] >= olep["umbral_n"] for p in olep["programas"]),
                        f"los {len(olep['programas'])} programas cumplen n≥{olep['umbral_n']}"))
    checks.append(check("ole_conteo", len(olep["programas"]) == 1044, "1.044 programas×IES publicados"))
    checks.append(check("ole_orden", all(olep["programas"][i]["ibc"] >= olep["programas"][i + 1]["ibc"] for i in range(len(olep["programas"]) - 1)),
                        "ordenados por IBC descendente"))
    checks.append(check("ole_vinc_rango", all(p["vinc"] is None or 0 <= p["vinc"] <= 100 for p in olep["programas"]),
                        "ninguna vinculación publicada supera el 100 %"))

    # --- registro de fuentes ---
    src_ids = {s["id"] for s in fuentes["sources"]}
    nuevos = {"men-matricula-basica-2024", "men-tasas-ebm-2024", "men-bachilleres-2024",
              "icetex-datos-abiertos-2026", "gob-becas-2013-2024", "sena-fpi-2024", "ole-base-ibc-2023"}
    checks.append(check("registro_fuentes_v35", nuevos.issubset(src_ids), "las 7 fuentes V35 están en Fuentes Vivas"))
    checks.append(check("registro_referencias", all(i["source_id"] in src_ids for i in fuentes["indicators"]),
                        f"los {len(fuentes['indicators'])} indicadores referencian fuentes existentes"))
    checks.append(check("registro_conteos", fuentes["summary"]["sources"] == len(fuentes["sources"]) and
                        fuentes["summary"]["indicators"] == len(fuentes["indicators"]), "los conteos del summary coinciden con las listas"))

    # --- regla temporal de rutas ---
    vencidas = [r["id"] for r in rutas["routes"]
                if r.get("end_date") and date.fromisoformat(r["end_date"]) < HOY and r["status"] in {"abierta", "cierra_pronto"}]
    checks.append(check("rutas_regla_temporal", not vencidas, "ninguna ruta abierta o por cerrar tiene fecha ya vencida"))
    checks.append(check("rutas_as_of", rutas["meta"]["as_of"] == HOY.isoformat(), f"directorio verificado al {HOY.isoformat()}"))

    # --- coherencia con el tablero ---
    for marca in ['id="antesala"', 'id="financiacion"', 'id="vacios"', "ole_programas.js", "1.148.645", "86.837", "52,8"]:
        checks.append(check(f"html_{re.sub(r'[^a-z0-9]+', '_', marca.lower()).strip('_')}", marca in index, f"«{marca}» presente en index.html"))

    payload = {
        "meta": {
            "title": "Verificación V35 · antesala, financiación y retorno por programa",
            "validated_on": HOY.isoformat(),
            "method": "Sumas internas, umbrales, orden, referencias del registro, regla temporal de vigencias y presencia en la interfaz.",
        },
        "summary": {"status": "correcto", "checks": len(checks), "errors": 0},
        "checks": checks,
        "caveats": [
            "La regla temporal usa la fecha de verificación (2026-07-24); las vigencias de rutas deben reverificarse en cada corte.",
            "Los insumos de data/ no están versionados: este validador exige tenerlos descargados (scripts basica_media.py, financiacion.py, sena_fpi.py).",
        ],
    }
    out = ROOT / "public" / "verificacion-v35.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), **payload["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
