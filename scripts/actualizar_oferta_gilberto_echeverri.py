#!/usr/bin/env python3
"""Descarga y estructura la oferta publica 2026 de la Corporacion Gilberto Echeverri.

El PDF oficial organiza una fila por combinacion sede-institucion-programa. El
resultado conserva ese grano: no lo presenta como cupos, matriculas ni personas.
"""

from __future__ import annotations

import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "oferta-gilberto-echeverri.json"
CUT = date(2026, 7, 16)
OFFER_URL = "https://corporaciongilbertoecheverri.gov.co/wp-content/uploads/2026/07/Oferta-Academica-09Jul26.pdf"

PAGE_REGIONS = {
    1: ["Bajo Cauca"],
    2: ["Magdalena Medio"],
    3: ["Nordeste"],
    4: ["Nordeste", "Norte"],
    5: ["Norte", "Occidente"],
    6: ["Oriente"],
    7: ["Oriente"],
    8: ["Oriente", "Suroeste"],
    9: ["Suroeste"],
    10: ["Suroeste", "Urabá"],
    11: ["Urabá"],
    12: ["Urabá", "Valle de Aburrá"],
    13: ["Valle de Aburrá"],
}

INSTITUTIONS = {
    "ceipa": "Fundación Universitaria CEIPA",
    "instituto cruz roja": "Instituto Cruz Roja",
    "cruz roja": "Instituto Cruz Roja",
    "pascual bravo": "Institución Universitaria Pascual Bravo",
    "uniminuto": "UNIMINUTO",
    "fundacion universitaria catolica del norte": "Fundación Universitaria Católica del Norte",
    "tecnologico coredi": "Tecnológico COREDI",
    "uco": "Universidad Católica de Oriente",
    "politecnico colombiano jaime isaza cadavid": "Politécnico Colombiano Jaime Isaza Cadavid",
    "corporacion universitaria remington": "Corporación Universitaria Remington",
    "uniremington": "Corporación Universitaria Remington",
    "universidad cooperativa de colombia": "Universidad Cooperativa de Colombia",
    "corum tec": "CORUM",
    "tecoc": "TECOC",
    "ces": "Universidad CES",
    "fundesa": "FUNDESA",
    "cedecamara": "CEDECÁMARA",
    "uniban": "UNIBAN",
}

AREAS = {
    "nuevas tecnologias": "Nuevas tecnologías",
    "tecnologia para el agro": "Tecnología para el agro",
    "industrias creativas": "Industrias creativas",
    "recreacion y deporte": "Recreación y deporte",
    "turismo": "Turismo",
    "logistica y comercio": "Logística y comercio",
    "atencion y cuidado": "Atención y cuidado",
}

MUNICIPALITIES = {
    "amaga": "Amagá", "ciudad bolivar": "Ciudad Bolívar", "gomez plata": "Gómez Plata",
    "nechi": "Nechí", "puerto berrio": "Puerto Berrío", "santa barbara": "Santa Bárbara",
    "vegachi": "Vegachí", "yali": "Yalí",
}

FUNDS = [
    "Becas Jóvenes Pa'Lante Antioquia",
    "Fortalecimiento Educativo Semestre Cero",
    "Fondo Becas Educación Superior El Peñol",
    "Guatapé Vive la U",
    "Programa de Estímulos Superé",
    "Guarne para la U",
    "Becas Mejores Bachilleres",
    "Becas Regiones",
    "Becas Saber Rionegro",
]


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def key(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def institution(value: str) -> str:
    normalized = key(value)
    if normalized not in INSTITUTIONS:
        raise ValueError(f"Institucion sin homologar: {value!r}")
    return INSTITUTIONS[normalized]


def area(value: str) -> str:
    normalized = key(value)
    if normalized not in AREAS:
        raise ValueError(f"Area sin homologar: {value!r}")
    return AREAS[normalized]


def municipality(location: str) -> str:
    base = re.split(r"\s+Ver(?:eda|da)\s+", clean(location), maxsplit=1, flags=re.I)[0]
    return MUNICIPALITIES.get(key(base), base.title())


def parse_pdf(content: bytes) -> list[dict]:
    raw_rows: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        assert len(pdf.pages) == 13, "Cambio inesperado en la paginacion del PDF"
        for page_number, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            regions = PAGE_REGIONS[page_number]
            for table_index, table in enumerate(tables):
                region = regions[min(table_index, len(regions) - 1)]
                if page_number == 1 and table_index == 0:
                    current: list[str] | None = None
                    for row in table[1:]:
                        place = clean(row[0] or row[1])
                        provider = clean(row[3] or row[4])
                        field = clean(row[6] or row[7])
                        program = clean(row[9] or row[10])
                        if place:
                            if current:
                                raw_rows.append(current)
                            current = [region, place, provider, field, program]
                        elif current:
                            if provider:
                                current[2] = clean(f"{current[2]} {provider}")
                            if field:
                                current[3] = clean(f"{current[3]} {field}")
                            if program:
                                current[4] = clean(f"{current[4]} {program}")
                    if current:
                        raw_rows.append(current)
                    continue
                if page_number == 1:
                    continue
                for row in table:
                    if len(row) != 4:
                        continue
                    values = [clean(value) for value in row]
                    if not values[0] or key(values[0]) == "municipio":
                        continue
                    raw_rows.append([region, *values])

    offers = []
    for index, (region, location, provider, field, program) in enumerate(raw_rows, 1):
        offers.append({
            "id": f"cgem-2026-{index:03d}",
            "subregion": region,
            "municipality": municipality(location),
            "location": location,
            "institution": institution(provider),
            "area": area(field),
            "program": clean(program),
            "modality": "Presencial",
            "training_type": "Educación para el Trabajo y el Desarrollo Humano",
        })
    return offers


def validate(offers: list[dict]) -> dict:
    assert len(offers) == 165, f"Se esperaban 165 combinaciones y llegaron {len(offers)}"
    assert len({item["id"] for item in offers}) == len(offers), "Identificadores duplicados"
    assert len({item["subregion"] for item in offers}) == 9, "Subregiones incompletas"
    assert len({item["institution"] for item in offers}) == 16, "Instituciones inesperadas"
    assert len({item["area"] for item in offers}) == 7, "Areas inesperadas"
    assert len({item["municipality"] for item in offers}) == 78, "Municipios inesperados"
    assert all(all(item[field] for field in ("municipality", "institution", "area", "program")) for item in offers)
    return {
        "status": "correcto",
        "rows": len(offers),
        "duplicate_ids": 0,
        "missing_required_fields": 0,
        "subregions": 9,
        "municipalities": 78,
        "institutions": 16,
        "areas": 7,
    }


def main() -> None:
    request = urllib.request.Request(OFFER_URL, headers={"User-Agent": "MaterIA-Gris/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()
    offers = parse_pdf(content)
    checks = validate(offers)
    by_area = Counter(item["area"] for item in offers)
    by_region = Counter(item["subregion"] for item in offers)
    payload = {
        "meta": {
            "title": "Oferta pública operada por la Corporación Gilberto Echeverri Mejía",
            "version": "V33",
            "research_cut": CUT.isoformat(),
            "offer_publication": "2026-07-09",
            "grain": "Una fila es una combinación subregión-sede-institución-programa; no representa cupos, matrículas ni beneficiarios.",
            "status": "Convocatoria cerrada; legalización y matrícula del 17 de julio al 16 de agosto de 2026.",
        },
        "summary": {
            "offer_combinations": len(offers),
            "municipalities": len({item["municipality"] for item in offers}),
            "locations": len({item["location"] for item in offers}),
            "institutions": len({item["institution"] for item in offers}),
            "areas": len(by_area),
            "subregions": len(by_region),
            "announced_scholarships_2026": 10000,
            "tuition_coverage_pct": 100,
            "support_max_cop": 530000,
        },
        "budget_2026": {
            "total_cop": 46291208375,
            "investment_cop": 42088010483,
            "operations_cop": 4203197892,
            "scholarships_cop": 33976693277,
            "semester_zero_cop": 4927057799,
            "higher_education_fund_cop": 2990891887,
            "research_1_cop": 98078730,
            "research_2_cop": 95288790,
            "note": "Presupuesto inicial aprobado; no equivale a ejecución ni a costo por beneficiario.",
        },
        "call_2026": {
            "application_start": "2026-06-04",
            "application_end": "2026-07-13",
            "legalization_start": "2026-07-17",
            "legalization_end": "2026-08-16",
            "eligibility": "Personas colombianas residentes en municipios de Antioquia definidos por la convocatoria, con grado noveno culminado y estratos 1, 2 o 3, sujetas al reglamento.",
            "opening_condition": "Los grupos abren al alcanzar el minimo requerido y garantizar condiciones logisticas, operativas y academicas.",
        },
        "counts": {
            "by_area": dict(by_area.most_common()),
            "by_subregion": dict(sorted(by_region.items())),
        },
        "funds_and_programs_visible_on_portal": FUNDS,
        "sources": [
            {"id": "cgem-offer", "title": "Oferta academica por subregiones", "url": OFFER_URL, "cut": "2026-07-09"},
            {"id": "cgem-program", "title": "Becas Jovenes Pa'Lante Antioquia", "url": "https://corporaciongilbertoecheverri.gov.co/becas-jovenes-pa-lante-antioquia/", "cut": "2026-07-16"},
            {"id": "cgem-budget", "title": "Presupuesto inicial 2026", "url": "https://corporaciongilbertoecheverri.gov.co/wp-content/uploads/2026/03/Acuerdo-01-de-2025-Aprobacion-presupuesto-2026_-1.pdf", "cut": "2026"},
            {"id": "gob-cgem-2026", "title": "Convocatoria 2026 de Becas Jovenes Pa'Lante", "url": "https://www.antioquia.gov.co/index.php/antioquiacuenta/gobernacion-de-antioquia-abre-nueva-convocatoria-de-becas-jovenes-pa-lante-para-impulsar-el-acceso-a-la-educacion-superior", "cut": "2026-06"},
        ],
        "offers": offers,
        "validation": checks,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"], **checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
