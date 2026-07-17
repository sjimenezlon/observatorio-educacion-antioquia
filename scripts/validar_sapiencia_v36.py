#!/usr/bin/env python3
"""Valida el scraping, la curaduría y la interfaz Sapiencia ODES de MaterIA Gris V36."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "verificacion-v36.json"


def check(name: str, condition: bool, detail: str) -> dict:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "correcto", "detail": detail}


def main() -> None:
    sapiencia = json.loads((PUBLIC / "sapiencia-observatorio.json").read_text(encoding="utf-8"))
    sources = json.loads((PUBLIC / "fuentes-antioquia.json").read_text(encoding="utf-8"))
    audit = json.loads((PUBLIC / "auditoria-cifras.json").read_text(encoding="utf-8"))
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    summary = sapiencia["summary"]
    studies = sapiencia["studies"]
    indicators = sapiencia["indicators"]
    publications = sapiencia["publications"]
    collections = Counter(item["collection"] for item in publications)
    registry_ids = {item["id"] for item in sources["indicators"]}
    source_ids = {item["id"] for item in sources["sources"]}
    key_values = {item["id"]: item["value"] for item in indicators}
    expected_source_ids = {study["id"] for study in studies}

    checks = [
        check("catalog_scale", summary["publications"] >= 64 and summary["curated_studies"] >= 8 and summary["survey_indicators"] >= 47 and summary["downloaded_pages"] >= 312, "la línea base V36 permanece dentro del catálogo acumulado"),
        check("catalog_distribution", collections == {"informe": 32, "boletín": 32}, "32 informes y 32 boletines"),
        check("unique_publications", len({item["url"] for item in publications}) == 64, "cero URL duplicadas"),
        check("pdf_fingerprints", all(study["pages"] > 0 and len(study["sha256"]) == 64 for study in studies), "ocho PDF con páginas y SHA-256"),
        check("survey_contract", all(item["evidence"] == "encuesta" and item["universe"] and item["caveat"] and item["decision_use"] for item in indicators), "47 encuestas con universo, uso y cautela"),
        check("registry_scale", sources["summary"]["sources"] >= 41 and sources["summary"]["indicators"] >= 114, "la línea base V36 permanece dentro del registro acumulado"),
        check("registry_distribution", sources["summary"]["evidence"]["encuesta"] >= 47, "las 47 encuestas V36 permanecen clasificadas"),
        check("registry_sources", expected_source_ids <= source_ids, "ocho estudios ODES incorporados como fuentes"),
        check("registry_indicators", {item["id"] for item in indicators} <= registry_ids, "47 indicadores ODES incorporados al registro"),
        check("key_values", key_values["odes-expect-apply-2024"] == 78.8 and key_values["odes-followup-money-barrier-2024"] == 40.91 and key_values["odes-zero-full-dedication-2023"] == 88 and key_values["odes-talent-low-relation-2022"] == 52, "cuatro cifras destacadas coinciden con la curaduría"),
        check("scrape_validation", sapiencia["validation"]["status"] == "correcto" and sum(value for key, value in sapiencia["validation"].items() if key != "status") == 0, "scraping sin duplicados ni verificaciones faltantes"),
        check("ui_contract", all(token in html for token in ('id="sapiencia"', "sapiencia-observatorio.json", 'id="sap-study"', 'id="sap-doc-q"', "Encuesta o sondeo")), "explorador, biblioteca y rótulo metodológico visibles"),
        check("audit_contract", audit["sapiencia_odes_v36"]["publicaciones_catalogadas"] == 64 and audit["fuentes_v36"]["indicadores_sistematizados"] == 114, "línea base histórica V36 conservada en la auditoría"),
    ]
    payload = {
        "meta": {
            "title": "Verificación V36 · Sapiencia ODES y Fuentes vivas",
            "validated_on": date(2026, 7, 17).isoformat(),
            "method": "Controles de catálogo, PDF, huellas, esquema, cifras destacadas, registro acumulado, interfaz y auditoría.",
        },
        "summary": {"status": "correcto", "checks": len(checks), "errors": 0},
        "checks": checks,
        "caveats": sapiencia["reading_rules"],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
