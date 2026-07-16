#!/usr/bin/env python3
"""Valida contratos, estados, fuentes e interfaz de Oportunidades V34."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "verificacion-v34.json"


def check(name: str, condition: bool, detail: str) -> dict:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "correcto", "detail": detail}


def main() -> None:
    opportunities = json.loads((PUBLIC / "oportunidades-antioquia.json").read_text(encoding="utf-8"))
    sources = json.loads((PUBLIC / "fuentes-antioquia.json").read_text(encoding="utf-8"))
    audit = json.loads((PUBLIC / "auditoria-cifras.json").read_text(encoding="utf-8"))
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    routes = opportunities["routes"]
    types = Counter(item["route_type"] for item in routes)
    statuses = Counter(item["status"] for item in routes)
    official_domains = {urlparse(item["source_url"]).netloc for item in routes}
    current = sum(item["status"] != "cerrada" for item in routes)
    open_or_closing = statuses["abierta"] + statuses["cierra_pronto"]
    summary = opportunities["summary"]
    audit_summary = audit["oportunidades_v34"]

    required_fields = {
        "id", "title", "provider", "route_type", "status", "status_label",
        "scope", "territory", "level", "audience", "benefit", "deadline",
        "as_of", "source_url", "decision_use", "caveat",
    }
    checks = [
        check("route_count", len(routes) == 14 == summary["routes"], "14 rutas públicas curadas"),
        check("unique_ids", len({item["id"] for item in routes}) == len(routes), "cero identificadores duplicados"),
        check("required_fields", all(required_fields <= item.keys() for item in routes), "cada ruta conserva decisión, fuente y cautela"),
        check("four_needs", set(types) == {"Estudiar", "Financiarse", "Postularse", "Prepararse"}, "cuatro necesidades generales presentes"),
        check("status_contract", set(statuses) == {"abierta", "cierra_pronto", "legalizacion", "en_curso", "permanente", "cerrada"}, "seis estados comparables presentes"),
        check("current_routes", current == 12 == summary["current_routes"], "12 rutas vigentes o consultables"),
        check("priority_routes", open_or_closing == 3 == summary["open_or_closing"], "tres rutas abiertas o próximas a cerrar"),
        check("source_security", all(item["source_url"].startswith("https://") for item in routes), f"{len(official_domains)} dominios servidos por HTTPS"),
        check("caveats", all(item["caveat"] and item["decision_use"] for item in routes), "cero cautelas o usos decisionales vacíos"),
        check("source_registry", sources["summary"]["sources"] == 26 and sources["summary"]["indicators"] == 45, "26 fuentes y 45 indicadores validados"),
        check("atlas_contract", summary["programs_in_atlas"] == 2107 and summary["institutions_in_atlas"] == 73 and summary["municipalities_with_active_offer"] == 51, "escala SNIES enlazada sin duplicarla"),
        check("audit_contract", audit_summary["rutas_verificadas"] == 14 and audit_summary["tipos"] == 4, "comprobante público sincronizado"),
        check("ui_contract", all(token in html for token in ('id="oportunidades"', 'id="opp-type"', 'id="opp-state"', 'id="opp-grid"', 'oportunidades-antioquia.json')), "buscador general y fuente conectados"),
        check("no_special_chapter", "Oportunidades públicas: del dato a una ruta concreta" not in html and "Oportunidades CGEM" not in html, "la Corporación no se presenta como capítulo especial"),
        check("general_narrative", "Oportunidades: estudiar, financiarse y avanzar" in html and "Conectar personas con oportunidades" in html, "narrativa general visible en capítulo y Centro de Decisiones"),
        check("cgem_as_route", sum("Corporación Gilberto Echeverri" in item["provider"] for item in routes) == 3, "la Corporación aparece en tres rutas dentro del ecosistema"),
    ]

    payload = {
        "meta": {
            "title": "Verificación V34 · ecosistema general de oportunidades",
            "validated_on": date(2026, 7, 16).isoformat(),
            "method": "Controles de esquema, unicidad, estados, fuentes, agregaciones, contrato de interfaz y neutralidad narrativa.",
        },
        "summary": {"status": "correcto", "checks": len(checks), "errors": 0},
        "checks": checks,
        "distribution": {"by_type": dict(types), "by_status": dict(statuses), "official_domains": sorted(official_domains)},
        "caveats": [
            "El directorio es curado y no exhaustivo; cada fuente oficial puede cambiar después del corte.",
            "Beca, gratuidad, estímulo, crédito condonable y crédito reembolsable no son equivalentes.",
            "Convocatoria, postulación, preselección, legalización, matrícula y graduación son etapas distintas.",
            "Las cifras de una ruta no se suman con la matrícula SNIES ni con los beneficiarios de otra.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
