#!/usr/bin/env python3
"""Valida contratos, agregaciones y rotulos de la capa de oportunidades V33."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "verificacion-v33.json"


def check(name: str, condition: bool, detail: str) -> dict:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "correcto", "detail": detail}


def main() -> None:
    offer = json.loads((PUBLIC / "oferta-gilberto-echeverri.json").read_text(encoding="utf-8"))
    sources = json.loads((PUBLIC / "fuentes-antioquia.json").read_text(encoding="utf-8"))
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    rows = offer["offers"]
    budget = offer["budget_2026"]
    area_counts = Counter(row["area"] for row in rows)
    region_counts = Counter(row["subregion"] for row in rows)
    budget_investment_parts = sum(
        budget[key]
        for key in (
            "scholarships_cop",
            "semester_zero_cop",
            "higher_education_fund_cop",
            "research_1_cop",
            "research_2_cop",
        )
    )
    indicator_ids = {item["id"] for item in sources["indicators"]}
    checks = [
        check("offer_rows", len(rows) == 165, "165 combinaciones sede-institucion-programa"),
        check("offer_unique_ids", len({row["id"] for row in rows}) == 165, "cero identificadores duplicados"),
        check("offer_municipalities", len({row["municipality"] for row in rows}) == 78, "78 municipios homologados desde 82 localidades"),
        check("offer_institutions", len({row["institution"] for row in rows}) == 16, "16 instituciones homologadas"),
        check("offer_areas", len(area_counts) == 7 and sum(area_counts.values()) == 165, "siete areas suman el total"),
        check("offer_subregions", len(region_counts) == 9 and sum(region_counts.values()) == 165, "nueve subregiones suman el total"),
        check("budget_total", budget["operations_cop"] + budget["investment_cop"] == budget["total_cop"], "funcionamiento + inversion = presupuesto total"),
        check("budget_investment", budget_investment_parts == budget["investment_cop"], "rubros de inversion suman la apropiacion de inversion"),
        check("source_registry", sources["summary"]["sources"] == 33 and sources["summary"]["indicators"] == 55, "33 fuentes y 55 indicadores validados en V35"),
        check("source_offer_indicators", {"cgem-offer-combinations-2026", "cgem-offer-municipalities-2026", "cgem-budget-total-2026"}.issubset(indicator_ids), "oferta y presupuesto presentes en Fuentes Vivas"),
        check("ui_contract", all(token in html for token in ('id="oportunidades"', 'id="opp-type"', 'id="opp-grid"', 'oferta-gilberto-echeverri.json')), "el detalle histórico permanece conectado como capa relacionada"),
        check("snies_freshness", "resultado agregado publicado" in html and "SNIES 2025 aún no se publica" not in html, "agregado nacional publicado; base departamental pendiente"),
    ]
    payload = {
        "meta": {
            "title": "Verificacion V33 · oportunidades publicas y frescura SNIES",
            "validated_on": date(2026, 7, 24).isoformat(),
            "method": "Controles de grano, unicidad, agregacion presupuestal, contratos de interfaz y rotulos de frescura.",
        },
        "summary": {"status": "correcto", "checks": len(checks), "errors": 0},
        "checks": checks,
        "caveats": [
            "Una combinacion de oferta no es un cupo, una matricula, un beneficiario ni un programa unico.",
            "El presupuesto es apropiacion inicial y no equivale a ejecucion ni impacto.",
            "La apertura de grupos depende del minimo de estudiantes y de condiciones logisticas, operativas y academicas.",
            "SNIES 2025 tiene agregado nacional publicado, pero la base departamental consolidada sigue pendiente al corte.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
