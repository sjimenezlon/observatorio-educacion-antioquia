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
FUENTE_PLAN_2026 = "https://www.medellin.gov.co/es/wp-content/uploads/2026/04/Sgto_PI_28Feb2026.pdf"
FUENTE_MATRICULA_CERO_2026 = "https://www.medellin.gov.co/es/sala-de-prensa/noticias/matricula-cero-trae-46-667-oportunidades-en-educacion-superior-para-el-primer-semestre-de-2026/"


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
            "matricula_2025_2": 28107, "matricula_2026_1": 29822,
            "programas_convocatoria_2026_2": 60, "cupos_2026_2": 8600,
            "cupos_calificador": "exacto", "alcance_territorial_2026": "Medellín; cinco campus reportados",
            "distrito_2026_02_28": {
                "programas_acreditados_vigentes": 23,
                "programas_acreditados_desglose": {"tecnologias": 12, "profesionales": 9, "maestrias": 2},
                "grupos_investigacion_a1_a_b": 11, "programas_media_tecnica": 28,
                "programas_ftdh": 7, "programas_comunas_corregimientos": 9,
                "semilleros_activos": 125, "estudiantes_semilleros": 2391,
                "publicaciones_indexadas": 44,
            },
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
            "matricula_2025_2": 9931, "matricula_2026_1": 10068,
            "programas_convocatoria_2026_2": 42, "cupos_2026_2": 1600,
            "cupos_calificador": "más de", "alcance_territorial_2026": "Medellín y 47 municipios reportados por la institución",
            "distrito_2026_02_28": {
                "programas_acreditados_vigentes": 7,
                "programas_acreditados_desglose": {"tecnologias": 6, "profesionales": 1},
                "grupos_investigacion_a1_a_b": 5, "programas_media_tecnica": 11,
                "programas_ftdh": 6, "programas_comunas_corregimientos": 4,
                "semilleros_activos": 26, "estudiantes_semilleros": 1968,
                "publicaciones_indexadas": 3,
            },
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
            "matricula_2025_2": 5763, "matricula_2026_1": 6599,
            "programas_convocatoria_2026_2": 40, "cupos_2026_2": 2016,
            "programas_calificador": "cerca de", "cupos_calificador": "exacto",
            "alcance_territorial_2026": "Sedes Robledo y C4ta",
            "distrito_2026_02_28": {
                "programas_acreditados_vigentes": 10,
                "programas_acreditados_desglose": {"tecnologias": 3, "profesionales": 7},
                "grupos_investigacion_a1_a_b": 5, "programas_media_tecnica": 5,
                "programas_ftdh": 17, "programas_comunas_corregimientos": 8,
                "semilleros_activos": 12, "estudiantes_semilleros": 610,
                "publicaciones_indexadas": 4,
            },
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
            "version": "V30", "corte": CORTE.isoformat(),
            "unidad_financiera": "millones de pesos colombianos",
            "metodo": "Seguimiento Plan Indicativo 2026-1 + scraping de catálogos oficiales + convocatoria distrital 2026-2 + SNIES consolidado 2024 + estados financieros oficiales",
        },
        "sistema": {
            "matricula_2025_2": sum(x["matricula_2025_2"] for x in configs),
            "matricula_2026_1": sum(x["matricula_2026_1"] for x in configs),
            "variacion_matricula_vs_2025_2_absoluta": sum(x["matricula_2026_1"] - x["matricula_2025_2"] for x in configs),
            "variacion_matricula_vs_2025_2_pct": round(100 * (sum(x["matricula_2026_1"] for x in configs) / sum(x["matricula_2025_2"] for x in configs) - 1), 2),
            "corte_indicadores_distrito": "2026-02-28",
            "programas_acreditados_vigentes_2026": sum(x["distrito_2026_02_28"]["programas_acreditados_vigentes"] for x in configs),
            "grupos_investigacion_a1_a_b_2026": sum(x["distrito_2026_02_28"]["grupos_investigacion_a1_a_b"] for x in configs),
            "programas_media_tecnica_2026": sum(x["distrito_2026_02_28"]["programas_media_tecnica"] for x in configs),
            "programas_ftdh_2026": sum(x["distrito_2026_02_28"]["programas_ftdh"] for x in configs),
            "programas_comunas_corregimientos_2026": sum(x["distrito_2026_02_28"]["programas_comunas_corregimientos"] for x in configs),
            "semilleros_activos_2026": sum(x["distrito_2026_02_28"]["semilleros_activos"] for x in configs),
            "estudiantes_semilleros_2026": sum(x["distrito_2026_02_28"]["estudiantes_semilleros"] for x in configs),
            "publicaciones_indexadas_2026": sum(x["distrito_2026_02_28"]["publicaciones_indexadas"] for x in configs),
            "matricula_cero_2026_1": {
                "beneficios_proyectados": 46667,
                "inversion_minima_millones": 37000,
                "ies_publicas_elegibles": 8,
                "universo": "Beneficios proyectados para estudiantes de ocho IES públicas con sede en Medellín; no equivale a matrícula ni se limita a las tres IES adscritas al Distrito.",
                "fuente": FUENTE_MATRICULA_CERO_2026,
            },
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
            {"nombre": "Seguimiento Plan Indicativo — corte 28 feb. 2026", "url": FUENTE_PLAN_2026},
            {"nombre": "Matrícula Cero 2026-1 — beneficios proyectados", "url": FUENTE_MATRICULA_CERO_2026},
            {"nombre": "Catálogo ITM", "url": "https://www.itm.edu.co/aspirante-pregrado/programas-profesionales/"},
            {"nombre": "Catálogo Pascual Bravo", "url": "https://pascualbravo.edu.co/aspirantes/"},
            {"nombre": "Catálogo Colmayor", "url": "https://www.colmayor.edu.co/programas/"},
            {"nombre": "SNIES consolidado 2024", "url": "https://snies.mineducacion.gov.co/portal/ESTADISTICAS/Bases-consolidadas/"},
            {"nombre": "CUIPO — ingresos presupuestales", "url": "https://www.datos.gov.co/Hacienda-y-Cr-dito-P-blico/Ingresos-Presupuestales/9axr-9gnb/about_data"},
        ],
        "limites": [
            "La convocatoria informa cupos y programas agregados, no cupos por programa para las tres IES bajo una sola estructura.",
            "El catálogo institucional puede conservar páginas de programas sin admisión abierta y contar modalidades por separado.",
            "La matrícula distrital 2026-1 es el corte consolidado al 28 de febrero; la matrícula SNIES 2024 conserva el grano comparable por programa.",
            "La variación frente a 2025-2 compara semestres consecutivos y puede contener estacionalidad; no se interpreta como crecimiento anual.",
            "Los 40 programas acreditados del corte distrital 2026 usan vigencia administrativa; los registros acreditados SNIES 2024 tienen otro corte y grano.",
            "Los 46.667 beneficios de Matrícula Cero son una proyección para ocho IES públicas: no representan estudiantes adicionales, beneficiarios únicos ejecutados ni la matrícula de las tres IES distritales.",
            "El resultado contable de Pascual Bravo corresponde a marzo de 2026 y no es comparable con los cierres anuales 2025 de ITM y Colmayor.",
            "Presupuesto, recaudo y resultado contable son magnitudes distintas; no se restan entre sí.",
        ],
    }
    SALIDA.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{SALIDA}: {len(all_programs)} registros SNIES y {sum(x['catalogo_web']['registros_visibles'] for x in configs)} entradas web visibles")


if __name__ == "__main__":
    main()
