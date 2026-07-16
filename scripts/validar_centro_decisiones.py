#!/usr/bin/env python3
"""Valida contratos de datos y controles del Centro de Decisiones V34."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


def require(condition: bool, message: str, checks: list[dict]) -> None:
    checks.append({"control": message, "estado": "correcto" if condition else "error"})
    if not condition:
        raise AssertionError(message)


def main() -> None:
    data = json.loads((PUBLIC / "datos.json").read_text(encoding="utf-8"))
    audit = json.loads((PUBLIC / "auditoria-cifras.json").read_text(encoding="utf-8"))
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    checks: list[dict] = []

    center_match = re.search(r'<section id="centro".*?</section>', html, flags=re.S)
    require(center_match is not None, "La sección #centro existe", checks)
    center = center_match.group(0)

    roles = set(re.findall(r'data-role="([^"]+)"', center))
    goals = set(re.findall(r'data-goal="([^"]+)"', center))
    require(roles == {"gobierno", "rectoria", "planeacion", "comunidad"}, "Hay cuatro perspectivas únicas", checks)
    require(goals == {"ampliar", "oportunidades", "portafolio", "permanencia", "calidad", "sostenibilidad"}, "Hay seis propósitos únicos", checks)

    subregions = data["subregiones"]["agg"]
    municipalities = data["municipios"]
    subregion_names = {row["subregion"] for row in subregions}
    coverage_names = {row["subregion"] for row in data["subregiones"]["cobertura"] if "total" not in row["subregion"].lower()}
    require(len(subregion_names) == 9, "Las nueve subregiones son únicas", checks)
    require(len(municipalities) == 51, "Hay 51 municipios con oferta activa", checks)
    require(len({row["codigo"] for row in municipalities}) == 51, "Los códigos municipales no están duplicados", checks)
    require(coverage_names == subregion_names, "Cada subregión tiene razón de oferta", checks)
    require(all(row["subregion"] in subregion_names for row in municipalities), "Todos los municipios pertenecen a una subregión válida", checks)

    required_municipal = {"codigo", "municipio", "subregion", "matricula24", "tyt24", "graduados24", "ies", "programas", "oficial"}
    require(all(required_municipal <= row.keys() for row in municipalities), "Los municipios tienen los campos requeridos", checks)
    require(all(row["matricula24"] >= 0 and row["tyt24"] >= 0 and row["oficial"] >= 0 for row in municipalities), "Las magnitudes municipales son no negativas", checks)
    require(all(row["tyt24"] <= row["matricula24"] and row["oficial"] <= row["matricula24"] for row in municipalities), "Los subtotales municipales no exceden la matrícula", checks)

    latest = data["serie"][-1]
    series_total = sum(latest["niveles"].values())
    require(series_total == data["embudo"]["matriculados"] == 313583, "La matrícula total coincide por dos rutas", checks)
    require(sum(row["matricula24"] for row in subregions) == 313583, "Las subregiones suman el total departamental", checks)
    require(sum(latest["sector"].values()) == 313583, "Los sectores suman el total departamental", checks)
    require(data["embudo"]["inscritos"] > 0 and data["embudo"]["primer_curso"] <= data["embudo"]["inscritos"], "La razón administrativa tiene denominador válido", checks)

    accredited = sum(row["mat_acreditada"] for row in data["acreditacion"])
    require(0 <= accredited <= 313583, "La matrícula acreditada está dentro del universo", checks)
    ole_levels = data["ole"]["vinculacion_por_nivel"]
    pregrad = [ole_levels[name] for name in ("Técnica profesional", "Tecnológica", "Universitaria")]
    require(all(row["graduados"] > 0 and row["vinculados"] <= row["graduados"] for row in pregrad), "La cotización formal de pregrado usa denominadores válidos", checks)

    ids = re.findall(r'\bid="([^"]+)"', html)
    duplicates = sorted(name for name, count in Counter(ids).items() if count > 1)
    require(not duplicates, "No hay identificadores HTML duplicados", checks)
    section_ids = set(re.findall(r'<(?:section|header|footer)\b[^>]*\bid="([^"]+)"', html)) | {"top"}
    chapter_targets = set(re.findall(r'class="nav-chapter-link" href="#([^"]+)"', html))
    require(chapter_targets <= section_ids, "Todos los enlaces del panel apuntan a capítulos existentes", checks)

    expected_scopes = 1 + len(subregion_names) + len(municipalities)
    v34 = audit["centro_decisiones_v34"]
    require(expected_scopes == 61 == v34["universos_territoriales"], "El comprobante declara 61 universos territoriales", checks)
    require(v34["perspectivas"] == len(roles) and v34["propositos"] == len(goals), "El comprobante coincide con los controles visibles", checks)

    output = {
        "estado": "correcto",
        "fecha_validacion": date(2026, 7, 16).isoformat(),
        "version": "V34",
        "resumen": {
            "perspectivas": len(roles),
            "propositos": len(goals),
            "subregiones": len(subregion_names),
            "municipios_con_oferta": len(municipalities),
            "universos_territoriales": expected_scopes,
            "matricula_reconciliada": series_total,
            "controles": len(checks),
            "errores": 0,
        },
        "controles": checks,
        "limitaciones": [
            "Los municipios seleccionables son los 51 con oferta activa en SNIES 2024-II; los otros 74 aparecen en el atlas como ausencia de oferta, no como registros vacíos del selector.",
            "La razón territorial mide matrícula ofertada frente a población 17–21 y no cobertura de residentes.",
            "Las lecturas para actuar son editoriales; las reglas de interpretación solo seleccionan un propósito y no generan cifras.",
            "La mesa de trabajo usa almacenamiento local y no es un repositorio institucional compartido.",
        ],
    }
    target = PUBLIC / "verificacion-centro-v34.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["resumen"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
