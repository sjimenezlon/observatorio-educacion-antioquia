#!/usr/bin/env python3
"""Valida fuentes, comparabilidad e interfaz explicativa de MaterIA Gris V35."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "verificacion-v35.json"


def check(name: str, condition: bool, detail: str) -> dict:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "correcto", "detail": detail}


def main() -> None:
    sources = json.loads((PUBLIC / "fuentes-antioquia.json").read_text(encoding="utf-8"))
    audit = json.loads((PUBLIC / "auditoria-cifras.json").read_text(encoding="utf-8"))
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    indicators = {item["id"]: item for item in sources["indicators"]}
    source_ids = {item["id"] for item in sources["sources"]}
    expected_sources = {
        "medellin-transito-2024",
        "medellin-plan-indicativo-2025",
        "medellin-siguiente-nivel-2026",
        "gob-transformacion-media-2025",
        "gob-resultados-educacion-2025",
        "gob-matricula-escolar-marzo-2026",
        "spadies-cierre-2024",
    }
    expected_indicators = {
        "medellin-immediate-transition-2024",
        "district-permanence-supported-2025",
        "matricula-cero-delivered-2025",
        "media-transformation-institutions-2025",
        "school-enrolment-march-2026",
        "school-meals-2025",
        "inclusive-education-students-2025",
        "spadies-annual-dropout-2023",
        "spadies-intersemester-absence-2023",
    }
    permanence_parts = [23695, 5423, 7133]
    zero_tuition_parts = [22166, 4157, 1329, 474, 153, 89, 49, 26]
    checks = [
        check("registry_scale", sources["summary"]["sources"] == 44 and sources["summary"]["indicators"] == 147, "registro acumulado V37: 44 fuentes y 147 indicadores"),
        check("registry_version", sources["meta"]["version"] == "V37" and sources["meta"]["research_cut"] == "2026-07-17", "versión acumulada y corte sincronizados"),
        check("evidence_distribution", sources["summary"]["evidence"] == {"derivada": 7, "directa": 50, "encuesta": 80, "reportada": 10}, "tipos de evidencia conservan su clasificación"),
        check("new_sources", expected_sources <= source_ids, "siete nuevas fuentes oficiales presentes"),
        check("new_indicators", expected_indicators <= indicators.keys(), "indicadores críticos de trayectoria presentes"),
        check("transition_comparison", indicators["medellin-immediate-transition-2024"]["value"] > indicators["colombia-immediate-transition-2024"]["value"] > indicators["antioquia-immediate-transition-2024"]["value"], "comparación de tránsito 2024 conserva los tres universos"),
        check("district_permanence_sum", sum(permanence_parts) == indicators["district-permanence-supported-2025"]["value"], "ITM + Colmayor + Pascual = 36.251 apoyados"),
        check("zero_tuition_sum", sum(zero_tuition_parts) == indicators["matricula-cero-delivered-2025"]["value"], "desglose institucional = 28.443 beneficios entregados"),
        check("national_reference", all(indicators[item]["territory"] == "Colombia" for item in ("spadies-annual-dropout-2023", "spadies-intersemester-absence-2023", "spadies-cohort-dropout-university")), "SPADIES permanece rotulado como referencia nacional"),
        check("metadata_complete", all(item["universe"] and item["caveat"] and item["decision_use"] for item in indicators.values()), "cero universos, cautelas o usos decisionales vacíos"),
        check("about_section", all(token in html for token in ('id="que-es-materia"', "materia-gris-explicada.webp", "Qué es MaterIA Gris", "Explorar las 147 cifras")), "imagen y explicación integradas a la interfaz"),
        check("trajectory_layer", all(token in html for token in ("tray-system-view", "36.251", "17.000+", "8,97 %")), "nuevas señales visibles en Trayectorias"),
        check("image_assets", (PUBLIC / "materia-gris-explicada.webp").stat().st_size > 100_000 and (PUBLIC / "materia-gris-explicada.png").stat().st_size > 1_000_000, "imagen WebP optimizada y respaldo PNG disponibles"),
        check("audit_contract", audit["fuentes_v37"]["fuentes_revisadas"] == 44 and audit["diagnostico_v35"]["nuevos_indicadores"] == 22, "auditoría histórica V35 y registro acumulado V37 sincronizados"),
    ]
    payload = {
        "meta": {
            "title": "Verificación V35 · diagnóstico ampliado e imagen explicativa",
            "validated_on": date(2026, 7, 17).isoformat(),
            "method": "Controles de fuentes, indicadores, sumas publicadas, territorios, metadatos, activos visuales y contrato de interfaz.",
        },
        "summary": {"status": "correcto", "checks": len(checks), "errors": 0},
        "checks": checks,
        "caveats": [
            "Las 147 cifras no forman una única cohorte y no se suman entre sí.",
            "Metas anunciadas, beneficios entregados, estudiantes apoyados y matrícula son universos diferentes.",
            "Los datos SPADIES son referencias nacionales hasta contar con una extracción departamental reproducible.",
            "La imagen explica el propósito de MaterIA Gris; no representa una medición ni una recomendación automática.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
