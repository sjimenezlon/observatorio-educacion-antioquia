#!/usr/bin/env python3
"""Valida recursos, estudios, indicadores e interfaz Sapiencia ODES V37."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "verificacion-v37.json"


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
    dashboards = sapiencia["dashboards"]
    values = {item["id"]: item["value"] for item in indicators}
    study_ids = {item["id"] for item in studies}
    source_ids = {item["id"] for item in sources["sources"]}
    indicator_ids = {item["id"] for item in sources["indicators"]}
    dashboard_types = Counter(item["collection"] for item in dashboards)
    new_studies = {
        "odes-expectativas-clei-2023",
        "odes-financiacion-etdh-2022",
        "odes-fondos-pregrado-laboral-2022",
    }
    new_indicators = {
        "odes-clei-does-not-know-sapiencia-2023",
        "odes-etdh-own-resources-2022",
        "odes-funds-no-ies-job-support-2022",
        "odes-funds-salary-below-expected-2022",
    }

    checks = [
        check("catalog_scale", summary["catalog_resources"] == 113 and summary["publications"] == 64 and summary["dashboards"] == 49, "113 recursos: 64 PDF y 49 tableros"),
        check("dashboard_distribution", dashboard_types == {"tablero_estudio": 18, "tablero_cifras": 31}, "18 tableros de estudios y 31 de cifras"),
        check("dashboard_security", all(item["url"].startswith("https://app.powerbi.com/view?") for item in dashboards), "49 tableros enlazados por HTTPS a Power BI"),
        check("study_scale", summary["curated_studies"] == 11 and summary["downloaded_pages"] == 411, "11 estudios y 411 páginas verificadas"),
        check("indicator_scale", summary["survey_indicators"] == 80 and len(indicators) == 80, "80 indicadores de encuesta o sondeo"),
        check("new_studies", new_studies <= study_ids, "CLEI, ETDH y fondos de pregrado incorporados"),
        check("pdf_integrity", all(study["pages"] > 0 and len(study["sha256"]) == 64 for study in studies), "11 PDF con páginas y huella SHA-256"),
        check("method_contract", all(item["universe"] and item["caveat"] and item["decision_use"] and item["evidence"] == "encuesta" for item in indicators), "80 indicadores con universo, uso, cautela y clasificación"),
        check("key_values", values["odes-clei-does-not-know-sapiencia-2023"] == 72.18 and values["odes-etdh-own-resources-2022"] == 68.3 and values["odes-funds-no-ies-job-support-2022"] == 61.13 and values["odes-funds-salary-below-expected-2022"] == 44.03, "cuatro señales ejecutivas coinciden con los PDF"),
        check("registry_scale", sources["summary"]["sources"] == 44 and sources["summary"]["indicators"] == 147, "44 fuentes y 147 indicadores en Fuentes vivas"),
        check("registry_distribution", sources["summary"]["evidence"] == {"derivada": 7, "directa": 50, "encuesta": 80, "reportada": 10}, "80 encuestas separadas de registros y cálculos"),
        check("registry_links", new_studies <= source_ids and new_indicators <= indicator_ids, "nuevas fuentes e indicadores conectados al registro"),
        check("scrape_validation", sapiencia["validation"]["status"] == "correcto" and sum(value for key, value in sapiencia["validation"].items() if key != "status") == 0, "scraping sin duplicados ni verificaciones faltantes"),
        check("ui_contract", all(token in html for token in ('id="sapiencia"', "113 recursos públicos", "Tableros de estudios", "Explorar las 147 cifras", "Fuentes vivas V37")), "interfaz V37 expone recursos, filtros y escala"),
        check("audit_contract", audit["sapiencia_odes_v37"]["recursos_catalogados"] == 113 and audit["fuentes_v37"]["indicadores_sistematizados"] == 147, "auditoría V37 sincronizada"),
    ]
    payload = {
        "meta": {
            "title": "Verificación V37 · expansión Sapiencia ODES",
            "validated_on": date(2026, 7, 17).isoformat(),
            "method": "Controles de catálogo PDF/Power BI, huellas, páginas, esquema, cifras destacadas, registro, interfaz y auditoría.",
        },
        "summary": {"status": "correcto", "checks": len(checks), "errors": 0},
        "checks": checks,
        "caveats": [
            *sapiencia["reading_rules"],
            "Las diferencias salariales por sexo son descriptivas y no equivalen a una brecha ajustada.",
            "Los resultados laborales de beneficiarios no identifican el efecto causal de los fondos.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
