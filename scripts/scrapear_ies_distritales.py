#!/usr/bin/env python3
"""Construye el corte reproducible de las tres IES adscritas al Distrito.

Combina tres granos que no deben confundirse:
1. convocatoria de admisiones 2026-2 publicada por el Distrito;
2. catálogos visibles en los portales institucionales al día de consulta;
3. registros comparables SNIES 2024 que ya alimentan MaterIA Gris.

El resultado queda en public/ies-distritales.json. Los valores financieros se
transcriben de los estados oficiales citados y se expresan en millones de COP.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
DATOS = ROOT / "public" / "datos.json"
SALIDA = ROOT / "public" / "ies-distritales.json"
CORTE = date(2026, 7, 15)


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headings: list[tuple[str, str]] = []
        self.anchors: list[tuple[str, str]] = []
        self._heading: dict | None = None
        self._anchor: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = {"tag": tag, "parts": []}
        if tag == "a" and values.get("href"):
            self._anchor = {"href": values["href"], "parts": []}

    def handle_data(self, data: str) -> None:
        if self._heading is not None:
            self._heading["parts"].append(data)
        if self._anchor is not None:
            self._anchor["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._heading is not None and tag == self._heading["tag"]:
            text = clean(" ".join(self._heading["parts"]))
            if text:
                self.headings.append((tag, text))
            self._heading = None
        if self._anchor is not None and tag == "a":
            text = clean(" ".join(self._anchor["parts"]))
            if text:
                self.anchors.append((self._anchor["href"], text))
            self._anchor = None


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def fetch(url: str) -> str:
    """Descarga una fuente oficial con TLS verificado por el almacén del sistema."""
    result = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "45",
         "--user-agent", "MaterIA-Gris/28 auditoria-educativa", url],
        check=True, capture_output=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def collect(url: str) -> Collector:
    parser = Collector()
    parser.feed(fetch(url))
    return parser


def itm_catalogo() -> list[dict]:
    pages = [
        ("Universitaria", "https://www.itm.edu.co/aspirante-pregrado/programas-profesionales/"),
        ("Tecnológica", "https://www.itm.edu.co/aspirante-pregrado/tecnologias/"),
        ("Especialización", "https://www.itm.edu.co/especializaciones/"),
        ("Maestría", "https://www.itm.edu.co/maestrias/"),
        ("Doctorado", "https://www.itm.edu.co/doctorado/"),
    ]
    exclusions = {"La mostra", "Tabla periodica", "- Virtual -"}
    rows: list[dict] = []
    for level, url in pages:
        headings = [text for tag, text in collect(url).headings if tag == "h2"]
        for title in headings:
            if title in exclusions:
                continue
            if level == "Tecnológica" and not title.startswith("Tecnología"):
                continue
            if level == "Especialización" and not title.startswith("Especialización"):
                continue
            if level == "Maestría" and not title.startswith("Maestría"):
                continue
            if level == "Doctorado" and not title.startswith("Doctorado"):
                continue
            rows.append({"programa": title, "nivel": level, "fuente": url})
    return rows


def pascual_catalogo() -> list[dict]:
    faculty_urls = [
        "https://pascualbravo.edu.co/facultades/facultad-de-ingenieria/programas/",
        "https://pascualbravo.edu.co/facultades/facultad-de-produccion-y-diseno/programas/",
    ]
    prefixes = ("Ingeniería", "Técnica", "Tecnología", "Profesional", "Especialización", "Maestría", "Doctorado")
    by_name: dict[str, dict] = {}
    for url in faculty_urls:
        for tag, title in collect(url).headings:
            if tag not in {"h4", "h5"} or not title.startswith(prefixes):
                continue
            level = next((x for x in prefixes if title.startswith(x)), "Otro")
            if level in {"Ingeniería", "Profesional"}:
                level = "Universitaria"
            elif level == "Técnica":
                level = "Técnica profesional"
            by_name[title.casefold()] = {"programa": title, "nivel": level, "fuente": url}

    rest = json.loads(fetch("https://pascualbravo.edu.co/wp-json/wp/v2/programas?per_page=100&_fields=link,title"))
    for item in rest:
        title = clean(item["title"]["rendered"])
        level = next((x for x in ("Especialización", "Maestría", "Doctorado") if title.startswith(x)), "Posgrado")
        by_name[title.casefold()] = {"programa": title, "nivel": level, "fuente": item["link"]}
    return sorted(by_name.values(), key=lambda x: (x["nivel"], x["programa"]))


def colmayor_catalogo() -> list[dict]:
    url = "https://www.colmayor.edu.co/programas/"
    prefixes = (
        "Administración", "Arquitectura", "Comunicación Social", "Planeación y Desarrollo",
        "Gastronomía", "Tecnología", "Ingeniería", "Bacteriología", "Biotecnología",
        "Construcciones", "Licenciatura", "Maestría", "Especialización", "Profesional",
    )
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for href, title in collect(url).anchors:
        if not title.startswith(prefixes):
            continue
        if not any(part in href for part in ("/programas/", "/facultad-")):
            continue
        absolute = urljoin(url, href)
        key = (title.casefold(), absolute)
        if key in seen:
            continue
        seen.add(key)
        if title.startswith("Tecnología"):
            level = "Tecnológica"
        elif title.startswith("Especialización"):
            level = "Especialización"
        elif title.startswith("Maestría"):
            level = "Maestría"
        else:
            level = "Universitaria"
        rows.append({"programa": title, "nivel": level, "fuente": absolute})
    return rows


def summarize_programs(programs: list[dict]) -> dict:
    return {
        "registros": len(programs),
        "pregrado": sum(p["nivel"] in {"Técnica profesional", "Tecnológica", "Universitaria"} for p in programs),
        "posgrado": sum(p["nivel"] in {"Especialización", "Maestría", "Doctorado"} for p in programs),
        "niveles": dict(sorted(Counter(p["nivel"] for p in programs).items())),
        "modalidades": dict(sorted(Counter(p["modalidad"] for p in programs).items())),
        "areas": dict(sorted(Counter(p["area"] for p in programs).items())),
        "acreditados": sum(bool(p["acreditado"]) for p in programs),
        "matricula": sum(int(p["matricula24"]) for p in programs),
        "matricula_acreditada": sum(int(p["matricula24"]) for p in programs if p["acreditado"]),
    }


def main() -> None:
    data = json.loads(DATOS.read_text(encoding="utf-8"))
    configs = [
        {
            "id": "itm", "codigo_snies": 3302, "nombre_corto": "ITM",
            "nombre_snies": "Instituto Tecnologico Metropolitano",
            "rol": "Escala tecnológica, digital, científica y de ingeniería",
            "matricula_2025_2": 28107, "programas_convocatoria_2026_2": 60, "cupos_2026_2": 8600,
            "cupos_calificador": "exacto", "alcance_territorial_2026": "Medellín; cinco campus reportados",
            "catalogo": itm_catalogo(),
            "finanzas": {
                "presupuesto_2026_millones": 276368, "recaudo_2025_millones": 709115,
                "recursos_estado_pct": 50.3, "dependencia_real_nota": "Cerca de 75 % al incluir convenios públicos",
                "activo_millones": 430725.232, "pasivo_millones": 92307.116,
                "patrimonio_millones": 338418.115, "resultado_contable_millones": 15769.783,
                "corte_resultado": "2025-12-31", "deuda_financiera_millones": 0,
                "fuente_presupuesto_2026": "https://www.itm.edu.co/wp-content/uploads/adquisiciones-licitaciones/2026/Cuantias%20Contractuales%202026-%201.pdf",
                "fuente_ejecucion_2025": "https://www.itm.edu.co/download/12-estado-de-ejecucion-pptal-diciembre/?wpdmdl=101073",
                "fuente_eeff": "https://www.itm.edu.co/wp-content/uploads/informes/ESTADOS-FINANCIEROS-A-DIC-2025_compressed.pdf",
            },
        },
        {
            "id": "pascual", "codigo_snies": 3107, "nombre_corto": "Pascual Bravo",
            "nombre_snies": "Institución Universitaria Pascual Bravo",
            "rol": "Industria, manufactura, software, logística y diseño",
            "matricula_2025_2": 9931, "programas_convocatoria_2026_2": 42, "cupos_2026_2": 1600,
            "cupos_calificador": "más de", "alcance_territorial_2026": "Medellín y 47 municipios reportados por la institución",
            "catalogo": pascual_catalogo(),
            "finanzas": {
                "presupuesto_2026_millones": 152205, "recaudo_2025_millones": 287987,
                "recursos_estado_pct": 52.7, "dependencia_real_nota": None,
                "activo_millones": 323550.200, "pasivo_millones": 15141.215,
                "patrimonio_millones": 308408.985, "resultado_contable_millones": 29684.795,
                "corte_resultado": "2026-03-31", "deuda_financiera_millones": 0,
                "comparabilidad": "Corte trimestral: no comparar como cierre anual con ITM y Colmayor",
                "fuente_presupuesto_2026": "https://pascualbravo.edu.co/gestion-financiera/",
                "fuente_ejecucion_2025": "https://pascualbravo.edu.co/gestion-financiera/",
                "fuente_eeff": "https://pascualbravo.edu.co/wp-content/uploads/2026/05/FIRMADO_ANEXOS_FINANCIEROS_MARZO.pdf",
            },
        },
        {
            "id": "colmayor", "codigo_snies": 2110, "nombre_corto": "Colmayor",
            "nombre_snies": "Colegio Mayor de Antioquia",
            "rol": "Salud, hábitat, territorio, turismo y gastronomía",
            "matricula_2025_2": 5763, "programas_convocatoria_2026_2": 40, "cupos_2026_2": 2016,
            "programas_calificador": "cerca de", "cupos_calificador": "exacto",
            "alcance_territorial_2026": "Sedes Robledo y C4ta",
            "catalogo": colmayor_catalogo(),
            "finanzas": {
                "presupuesto_2026_millones": 112107, "recaudo_2025_millones": 170623,
                "recursos_estado_pct": 76.4, "dependencia_real_nota": "Mayor dependencia formal del Estado entre las tres",
                "activo_millones": 126830.006, "pasivo_millones": 10907.150,
                "patrimonio_millones": 115922.856, "resultado_contable_millones": 9263.175,
                "corte_resultado": "2025-12-31", "deuda_financiera_millones": 0,
                "fuente_presupuesto_2026": "https://www.colmayor.edu.co/institucional/vicerrectoria-administrativa-financiera/",
                "fuente_ejecucion_2025": "https://www.colmayor.edu.co/institucional/vicerrectoria-administrativa-financiera/",
                "fuente_eeff": "https://www.colmayor.edu.co/wp-content/uploads/2026/02/12.-ESTADO-DE-RESULTADO-DICIEMBRE-2025.pdf",
            },
        },
    ]

    all_programs: list[dict] = []
    for cfg in configs:
        nombre_snies = cfg.pop("nombre_snies")
        programs = [p for p in data["programas"] if p["ies"] == nombre_snies]
        cfg["snies_2024"] = summarize_programs(programs)
        catalogo = cfg.pop("catalogo")
        cfg["catalogo_web"] = {
            "consultado": CORTE.isoformat(),
            "registros_visibles": len(catalogo),
            "programas": catalogo,
            "advertencia": "El catálogo web puede incluir modalidades o programas sin cupo abierto en la convocatoria vigente.",
        }
        for p in programs:
            all_programs.append({**p, "ies_id": cfg["id"], "ies_corto": cfg["nombre_corto"]})

    output = {
        "meta": {
            "titulo": "Las tres IES del Distrito de Medellín",
            "version": "V28", "corte": CORTE.isoformat(),
            "unidad_financiera": "millones de pesos colombianos",
            "metodo": "Scraping de catálogos oficiales + convocatoria distrital 2026-2 + SNIES consolidado 2024 + estados financieros oficiales",
        },
        "sistema": {
            "matricula_2025_2": sum(x["matricula_2025_2"] for x in configs),
            "cupos_2026_2_publicados_minimo": sum(x["cupos_2026_2"] for x in configs),
            "programas_convocatoria_2026_2_aproximado": sum(x["programas_convocatoria_2026_2"] for x in configs),
            "registros_catalogos_web": sum(x["catalogo_web"]["registros_visibles"] for x in configs),
            "registros_snies_2024": len(all_programs),
            "matricula_snies_2024": sum(x["matricula24"] for x in all_programs),
            "presupuesto_2026_millones": sum(x["finanzas"]["presupuesto_2026_millones"] for x in configs),
            "nota": "Los programas anunciados, las páginas del catálogo y los registros SNIES son universos con cortes y definiciones diferentes; no se igualan.",
        },
        "instituciones": configs,
        "programas_snies_2024": sorted(all_programs, key=lambda x: (-x["matricula24"], x["programa"])),
        "fuentes": [
            {"nombre": "Convocatoria distrital 2026-2", "url": "https://www.medellin.gov.co/es/sala-de-prensa/noticias/hay-mas-de-12-200-cupos-disponibles-para-estudiar-desde-el-segundo-semestre-pregrado-y-posgrado-en-medellin/"},
            {"nombre": "Matrícula distrital 2025-2", "url": "https://www.medellin.gov.co/es/sala-de-prensa/noticias/medellin-fortalece-el-acceso-a-la-educacion-superior-publica-mas-de-43-000-estudiantes-matriculados/"},
            {"nombre": "Catálogo ITM", "url": "https://www.itm.edu.co/aspirante-pregrado/programas-profesionales/"},
            {"nombre": "Catálogo Pascual Bravo", "url": "https://pascualbravo.edu.co/aspirantes/"},
            {"nombre": "Catálogo Colmayor", "url": "https://www.colmayor.edu.co/programas/"},
            {"nombre": "SNIES consolidado 2024", "url": "https://snies.mineducacion.gov.co/portal/ESTADISTICAS/Bases-consolidadas/"},
            {"nombre": "CUIPO — ingresos presupuestales", "url": "https://www.datos.gov.co/Hacienda-y-Cr-dito-P-blico/Ingresos-Presupuestales/9axr-9gnb/about_data"},
        ],
        "limites": [
            "La convocatoria informa cupos y programas agregados, no cupos por programa para las tres IES bajo una sola estructura.",
            "El catálogo institucional puede conservar páginas de programas sin admisión abierta y contar modalidades por separado.",
            "La matrícula SNIES 2024 es comparable entre IES; las cifras institucionales 2025-2 son más recientes pero autorreportadas.",
            "El resultado contable de Pascual Bravo corresponde a marzo de 2026 y no es comparable con los cierres anuales 2025 de ITM y Colmayor.",
            "Presupuesto, recaudo y resultado contable son magnitudes distintas; no se restan entre sí.",
        ],
    }
    SALIDA.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{SALIDA}: {len(all_programs)} registros SNIES y {sum(x['catalogo_web']['registros_visibles'] for x in configs)} entradas web visibles")


if __name__ == "__main__":
    main()
