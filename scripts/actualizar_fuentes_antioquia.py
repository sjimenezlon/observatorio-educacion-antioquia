#!/usr/bin/env python3
"""Construye el registro público de fuentes e indicadores de Antioquia.

El archivo resultante no intenta fabricar un único corte. Conserva el periodo,
el universo, el territorio y el tipo de evidencia de cada cifra para que la
interfaz pueda impedir sumas o comparaciones inválidas.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "fuentes-antioquia.json"
CUT = date(2026, 7, 15)


SOURCES = [
    {
        "id": "snies-bases-2024",
        "institution": "Ministerio de Educación Nacional · SNIES",
        "title": "Bases consolidadas de educación superior",
        "source_type": "oficial",
        "publication_date": "2025",
        "data_cut": "2024-II",
        "territory": "Antioquia",
        "level": "Educación superior",
        "url": "https://snies.mineducacion.gov.co/portal/ESTADISTICAS/Bases-consolidadas/",
        "role": "Base comparable para matrícula, instituciones y lugares de oferta.",
        "refresh": "Anual",
    },
    {
        "id": "snies-cronograma-2026",
        "institution": "Ministerio de Educación Nacional · SNIES",
        "title": "Calendario oficial de publicación estadística 2026",
        "source_type": "oficial",
        "publication_date": "2026",
        "data_cut": "Programación 2026",
        "territory": "Colombia",
        "level": "Educación superior",
        "url": "https://snies.mineducacion.gov.co/1778/w3-article-391228.html?_noredirect=1",
        "role": "Determina cuándo puede reemplazarse el corte comparable 2024.",
        "refresh": "27–31 de julio de 2026",
    },
    {
        "id": "men-antioquia-2026",
        "institution": "Ministerio de Educación Nacional",
        "title": "Balance territorial de educación en Antioquia",
        "source_type": "oficial",
        "publication_date": "2026-01-23",
        "data_cut": "2025-1 y balance frente a 2022",
        "territory": "Antioquia",
        "level": "Educación superior",
        "url": "https://www.mineducacion.gov.co/portal/micrositios-institucionales/Regiones/424404:Antioquia",
        "role": "Señales administrativas de gratuidad, nuevo ingreso y articulación con colegios.",
        "refresh": "Eventual",
    },
    {
        "id": "gob-aulas-2026",
        "institution": "Gobernación de Antioquia · Secretaría de Educación",
        "title": "Inicio del segundo semestre escolar 2026",
        "source_type": "oficial",
        "publication_date": "2026-07-05",
        "data_cut": "2026-II",
        "territory": "116 municipios no certificados",
        "level": "Preescolar, básica y media",
        "url": "https://www.antioquia.gov.co/index.php/secretaria-educacion/cerca-de-430-mil-estudiantes-regresan-a-las-aulas-para-iniciar-el-segundo-semestre-del-calendario-escolar-en-antioquia",
        "role": "Dimensiona la base escolar administrada por el departamento.",
        "refresh": "Semestral",
    },
    {
        "id": "gob-conectividad-2026",
        "institution": "Gobernación de Antioquia",
        "title": "Conectividad satelital y fibra óptica educativa",
        "source_type": "oficial",
        "publication_date": "2026-06-24",
        "data_cut": "Acumulado a junio de 2026",
        "territory": "Antioquia",
        "level": "Preescolar, básica y media",
        "url": "https://www.antioquia.gov.co/index.php/antioquiacuenta/antioquia-supera-los-3-mil-400-puntos-de-conexion-a-internet-mediante-antenas-satelitales-y-fibra-optica",
        "role": "Mide infraestructura habilitante en sedes educativas urbanas y rurales.",
        "refresh": "Eventual",
    },
    {
        "id": "gob-semestre-cero-2026",
        "institution": "Gobernación de Antioquia · Corporación Gilberto Echeverri Mejía",
        "title": "Semestre Cero 2026",
        "source_type": "oficial",
        "publication_date": "2026-04-21",
        "data_cut": "2026",
        "territory": "61 municipios",
        "level": "Transición media–superior",
        "url": "https://www.antioquia.gov.co/index.php/antioquiacuenta/semestre-cero-impulsa-la-educacion-superior-de-mas-de-4-mil-200-jovenes-en-antioquia",
        "role": "Describe escala, presencia territorial e inversión del programa de preparación.",
        "refresh": "Anual",
    },
    {
        "id": "proantioquia-capacidades-2026",
        "institution": "Proantioquia",
        "title": "Capacidades educativas y culturales",
        "source_type": "observatorio",
        "publication_date": "2026",
        "data_cut": "2025 y agenda 2026",
        "territory": "Antioquia",
        "level": "Trayectorias educativas",
        "url": "https://proantioquia.org.co/capacidades-educativas-y-culturales/",
        "role": "Aporta iniciativas privadas, cobertura territorial y vacíos de transición.",
        "refresh": "Continua",
    },
    {
        "id": "proantioquia-inversion-2025",
        "institution": "Proantioquia · Mesa Fundación de Fundaciones",
        "title": "Inversión privada en educación · balance 2025",
        "source_type": "observatorio",
        "publication_date": "2026-02-27",
        "data_cut": "2025",
        "territory": "Nueve subregiones de Antioquia",
        "level": "Sistema educativo",
        "url": "https://proantioquia.org.co/download/inversion-privada-en-educacion-balance-2025/",
        "role": "Sistematiza inversión autorreportada por organizaciones privadas.",
        "refresh": "Anual",
    },
    {
        "id": "proantioquia-valle-aburra-2026",
        "institution": "Proantioquia",
        "title": "Caracterización del sector educativo del Valle de Aburrá",
        "source_type": "observatorio",
        "publication_date": "2026-03-09",
        "data_cut": "2025",
        "territory": "Valle de Aburrá",
        "level": "Preescolar, básica y media",
        "url": "https://proantioquia.org.co/download/caracterizacion-y-perfil-de-sector-educativo-valle-de-aburra/",
        "role": "Perfila matrícula, sedes, sector y localización urbana de la principal subregión.",
        "refresh": "Anual",
    },
    {
        "id": "medellin-plan-2026",
        "institution": "Distrito de Medellín · Sapiencia",
        "title": "Seguimiento al Plan Indicativo",
        "source_type": "oficial",
        "publication_date": "2026-04",
        "data_cut": "2026-02-28",
        "territory": "Medellín · tres IES distritales",
        "level": "Educación superior",
        "url": "https://www.medellin.gov.co/es/wp-content/uploads/2026/04/Sgto_PI_28Feb2026.pdf",
        "role": "Corte administrativo de matrícula, calidad, investigación y articulación.",
        "refresh": "Periódica",
    },
    {
        "id": "medellin-matricula-cero-2026",
        "institution": "Distrito de Medellín · Sapiencia",
        "title": "Matrícula Cero 2026-1",
        "source_type": "oficial",
        "publication_date": "2025-12-19",
        "data_cut": "Convocatoria 2026-1",
        "territory": "Medellín · ocho IES públicas",
        "level": "Educación superior",
        "url": "https://www.medellin.gov.co/es/sala-de-prensa/noticias/matricula-cero-trae-46-667-oportunidades-en-educacion-superior-para-el-primer-semestre-de-2026/",
        "role": "Registra beneficios proyectados y recursos anunciados; no matrícula ejecutada.",
        "refresh": "Semestral",
    },
    {
        "id": "minciencias-957-2025",
        "institution": "Ministerio de Ciencia, Tecnología e Innovación",
        "title": "Resultados finales de la Convocatoria 957 de 2024",
        "source_type": "oficial",
        "publication_date": "2025-12-05",
        "data_cut": "Convocatoria 957 de 2024",
        "territory": "Colombia",
        "level": "Investigación",
        "url": "https://minciencias.gov.co/convocatorias/investigacion/convocatoria-nacional-actualizacion-y-transicion-para-el-reconocimiento",
        "role": "Lista oficial de grupos reconocidos; MaterIA deriva la ubicación departamental.",
        "refresh": "Por convocatoria",
    },
    {
        "id": "acv-icv-2024",
        "institution": "Antioquia Cómo Vamos",
        "title": "Informe de Calidad de Vida de Antioquia 2024",
        "source_type": "observatorio",
        "publication_date": "2025-09-11",
        "data_cut": "Series con disponibilidad hasta 2024",
        "territory": "Antioquia",
        "level": "Sistema educativo",
        "url": "https://www.antioquiacomovamos.org/wp-content/uploads/2025/09/20250911_ICV-2024.pdf",
        "role": "Contraste analítico de MEN, DANE, ICFES, SNIES y LEA; no reemplaza las bases primarias.",
        "refresh": "Anual",
    },
]


def indicator(
    id_: str,
    title: str,
    value: float,
    display: str,
    unit: str,
    period: str,
    level: str,
    topic: str,
    territory: str,
    universe: str,
    source_id: str,
    evidence: str,
    decision_use: str,
    caveat: str,
) -> dict:
    return {
        "id": id_, "title": title, "value": value, "display": display,
        "unit": unit, "period": period, "level": level, "topic": topic,
        "territory": territory, "universe": universe, "source_id": source_id,
        "evidence": evidence, "decision_use": decision_use, "caveat": caveat,
    }


INDICATORS = [
    indicator("he-enrolment", "Matrícula de educación superior", 313583, "313.583", "matrículas", "2024-II", "Educación superior", "Escala", "Antioquia", "Registros de matrícula en programas ofertados en el departamento", "snies-bases-2024", "derivada", "Dimensionar el sistema comparable y sus cambios por nivel, sector y modalidad.", "Es el semestre con mayor total de 2024; no son personas únicas del año ni residentes necesariamente."),
    indicator("he-ies", "IES con matrícula activa", 73, "73", "instituciones", "2024-II", "Educación superior", "Oferta", "Antioquia", "IES con al menos un registro de matrícula en el corte", "snies-bases-2024", "derivada", "Identificar capacidad institucional efectivamente activa.", "Una IES puede operar en varios municipios; no equivale a sedes físicas."),
    indicator("he-municipalities", "Municipios con oferta activa", 51, "51 de 125", "municipios", "2024-II", "Educación superior", "Territorio", "Antioquia", "Municipios con matrícula de educación superior por lugar de oferta", "snies-bases-2024", "derivada", "Focalizar expansión, articulación y modalidades flexibles.", "Oferta local no equivale a cobertura de residentes; los estudiantes pueden desplazarse o estudiar virtualmente."),
    indicator("tuition-free", "Beneficiarios de gratuidad", 118000, "Más de 118.000", "beneficiarios", "2025-1", "Educación superior", "Acceso", "Antioquia", "Beneficiarios reportados por el MEN", "men-antioquia-2026", "directa", "Seguir la escala del apoyo financiero y formular preguntas de permanencia.", "Es un umbral publicado, no matrícula adicional ni resultado de graduación."),
    indicator("new-entry", "Nuevos ingresos de primer curso frente a 2022", 36091, "36.091", "ingresos adicionales", "Balance a 2025", "Educación superior", "Acceso", "Antioquia", "Nuevos estudiantes de primer ingreso reportados por el MEN respecto a 2022", "men-antioquia-2026", "directa", "Contrastar expansión reciente con la serie comparable cuando se publique SNIES 2025.", "El comunicado no desagrega institución, semestre ni método; no se suma a la matrícula SNIES."),
    indicator("college-at-school", "Educación Superior en tu Colegio", 2659, "2.659", "estudiantes", "Balance a 2025", "Transición media–superior", "Acceso", "Antioquia", "Estudiantes vinculados a la estrategia", "men-antioquia-2026", "directa", "Seguir la articulación y su conversión posterior a matrícula y graduación.", "Participar no equivale a transitar ni graduarse de educación superior."),
    indicator("semester-zero-students", "Jóvenes en Semestre Cero", 4247, "4.247", "estudiantes", "2026", "Transición media–superior", "Acceso", "61 municipios", "Estudiantes de grado 11 beneficiados por preparación académica", "gob-semestre-cero-2026", "directa", "Priorizar apoyos de transición y medir ingreso posterior.", "Beneficiarios de preparación, no nuevos matriculados en educación superior."),
    indicator("semester-zero-territory", "Cobertura municipal de Semestre Cero", 61, "61", "municipios", "2026", "Transición media–superior", "Territorio", "Antioquia", "Municipios participantes, incluidos 16 rurales dispersos", "gob-semestre-cero-2026", "directa", "Revisar equilibrio territorial del programa.", "Presencia del programa no mide intensidad ni resultados por municipio."),
    indicator("district-enrolment", "Matrícula de las tres IES distritales", 46489, "46.489", "matrículas", "2026-1", "Educación superior", "Escala", "Medellín", "ITM, Pascual Bravo y Colegio Mayor de Antioquia", "medellin-plan-2026", "directa", "Gestionar capacidad conjunta del sistema público distrital.", "Corte administrativo al 28 de febrero; no sustituye SNIES por programa."),
    indicator("district-accredited", "Programas acreditados vigentes en las IES distritales", 40, "40", "programas", "2026-02-28", "Educación superior", "Calidad", "Medellín", "ITM, Pascual Bravo y Colegio Mayor de Antioquia", "medellin-plan-2026", "directa", "Seguir calidad certificada y renovaciones próximas.", "Conteo consolidado del Plan Indicativo; programa acreditado no es lo mismo que registro calificado."),
    indicator("district-research", "Grupos A1, A o B de las IES distritales", 21, "21", "grupos", "2026-02-28", "Investigación", "Investigación", "Medellín", "ITM, Pascual Bravo y Colegio Mayor de Antioquia", "medellin-plan-2026", "directa", "Orientar cooperación y fortalecimiento de capacidades de investigación.", "El indicador distrital usa categorías seleccionadas; no representa todos los grupos reconocidos."),
    indicator("zero-tuition-benefits", "Beneficios proyectados de Matrícula Cero", 46667, "46.667", "beneficios", "2026-1", "Educación superior", "Acceso", "Medellín", "Convocatoria para ocho IES públicas", "medellin-matricula-cero-2026", "reportada", "Planear demanda potencial y recursos del programa.", "Proyección de beneficios: no son estudiantes únicos, matrícula adicional ni ejecución verificada."),
    indicator("research-groups", "Grupos reconocidos vinculados a Antioquia", 815, "815", "grupos", "Convocatoria 957", "Investigación", "Investigación", "Antioquia", "Grupos únicos asignados por GrupLAC o institución avaladora antioqueña", "minciencias-957-2025", "derivada", "Mapear capacidades científicas y cooperación institucional.", "El PDF nacional no incluye departamento; MaterIA deriva la ubicación con 90 % de cruce histórico y aval institucional para grupos nuevos."),
    indicator("school-students", "Estudiantes del sistema oficial departamental", 430000, "Cerca de 430.000", "estudiantes", "2026-II", "Preescolar, básica y media", "Escala", "116 municipios no certificados", "Matrícula en instituciones educativas oficiales administradas por el departamento", "gob-aulas-2026", "reportada", "Dimensionar la cantera educativa bajo gestión departamental.", "Cifra aproximada: excluye los nueve municipios certificados y no puede sumarse con el perfil del Valle de Aburrá."),
    indicator("school-teachers", "Docentes del sistema oficial departamental", 20000, "Cerca de 20.000", "docentes", "2026-II", "Preescolar, básica y media", "Capacidad", "116 municipios no certificados", "Docentes de instituciones educativas oficiales", "gob-aulas-2026", "reportada", "Dimensionar capacidad de acompañamiento y desarrollo docente.", "Cifra aproximada de comunicado; no incluye los municipios certificados."),
    indicator("extended-day", "Instituciones con Jornada Extendida", 552, "552", "instituciones educativas", "2026-II", "Preescolar, básica y media", "Permanencia", "116 municipios no certificados", "Instituciones educativas oficiales alcanzadas", "gob-aulas-2026", "directa", "Vincular tiempo escolar adicional con aprendizaje y permanencia.", "Cobertura institucional, no número de estudiantes ni evaluación de impacto."),
    indicator("education-connectivity-points", "Puntos de conectividad educativa", 2290, "2.290", "puntos", "2026-06", "Preescolar, básica y media", "Infraestructura", "Antioquia", "Puntos satelitales o de fibra en sedes educativas", "gob-conectividad-2026", "directa", "Priorizar mantenimiento, uso pedagógico y brechas de calidad del servicio.", "Punto conectado no garantiza disponibilidad continua, velocidad suficiente ni uso efectivo."),
    indicator("education-connectivity-students", "Estudiantes alcanzados por conectividad", 272000, "Cerca de 272.000", "estudiantes", "2026-06", "Preescolar, básica y media", "Infraestructura", "Antioquia", "Estudiantes beneficiados reportados por la Gobernación", "gob-conectividad-2026", "reportada", "Dimensionar alcance y exigir métricas de calidad y uso.", "Cifra aproximada de alcance; no mide usuarios únicos, continuidad ni aprendizaje."),
    indicator("literacy-children", "Niñas y niños en la alianza de alfabetización inicial", 17192, "17.192", "niñas y niños", "2025", "Preescolar, básica y media", "Aprendizaje", "Cinco subregiones", "Beneficiarios de preescolar a quinto en 507 sedes", "proantioquia-capacidades-2026", "directa", "Conectar aprendizajes fundamentales con trayectorias educativas completas.", "Beneficiarios reportados por la alianza; no es una medición de aprendizaje ni un efecto causal."),
    indicator("private-investment", "Inversión privada educativa reportada", 399655, "$399.655 millones", "millones de pesos", "2025", "Sistema educativo", "Inversión", "Nueve subregiones", "Inversión reportada por 55 organizaciones privadas", "proantioquia-inversion-2025", "reportada", "Mapear complementariedades y vacíos de financiación territorial.", "No es gasto público, ejecución auditada ni impacto. La muestra cambió frente a 2024, por lo que no se presenta como crecimiento interanual."),
    indicator("private-initiatives", "Iniciativas privadas sistematizadas", 297, "297", "iniciativas", "2025", "Sistema educativo", "Inversión", "Nueve subregiones", "Ocho categorías de inversión educativa", "proantioquia-inversion-2025", "directa", "Reducir duplicidades y conectar actores por territorio y propósito.", "Una iniciativa puede variar mucho en escala; contar proyectos no mide intensidad ni resultado."),
    indicator("valley-school-enrolment", "Matrícula escolar del Valle de Aburrá", 608362, "608.362", "estudiantes", "2025", "Preescolar, básica y media", "Escala", "Valle de Aburrá", "Matrícula escolar oficial y no oficial de la subregión", "proantioquia-valle-aburra-2026", "directa", "Dimensionar la concentración de la demanda futura y la articulación metropolitana.", "Universo escolar subregional; no se suma con los 430.000 estudiantes de municipios no certificados."),
    indicator("valley-school-sites", "Sedes educativas del Valle de Aburrá", 1352, "1.352", "sedes", "2025", "Preescolar, básica y media", "Infraestructura", "Valle de Aburrá", "Sedes oficiales y no oficiales", "proantioquia-valle-aburra-2026", "directa", "Mapear nodos para orientación, media técnica y articulación con educación superior.", "Sede no equivale a institución ni informa por sí sola capacidad o calidad."),
]


COMPARABILITY_RULES = [
    {
        "title": "Matrícula comparable ≠ señal reciente",
        "text": "SNIES 2024-II permite comparar instituciones, programas y municipios. Los cortes 2025–2026 de gobiernos y programas son señales administrativas con otra definición.",
    },
    {
        "title": "Beneficios ≠ estudiantes adicionales",
        "text": "Gratuidad, Matrícula Cero, Semestre Cero y Educación Superior en tu Colegio reportan beneficiarios, beneficios o participantes; no se suman a la matrícula.",
    },
    {
        "title": "Territorios no aditivos",
        "text": "Los 116 municipios no certificados y el Valle de Aburrá tienen universos que se superponen de forma distinta; sus matrículas escolares nunca se suman.",
    },
    {
        "title": "Inversión reportada ≠ impacto",
        "text": "El balance privado describe recursos e iniciativas informados por 55 organizaciones. La muestra cambió y no demuestra ejecución auditada ni resultados causales.",
    },
]


UPDATE_QUEUE = [
    {
        "date": "2026-07-27/31",
        "title": "Publicación SNIES 2025",
        "action": "Descargar bases, recalcular totales y sustituir el corte comparable solo después de pasar la auditoría.",
        "source_id": "snies-cronograma-2026",
    },
    {
        "date": "Cuando exista base pública",
        "title": "Permanencia y graduación de Antioquia",
        "action": "Integrar SPADIES/OTE por cohorte, IES, nivel y modalidad sin usar referencias nacionales como resultado local.",
        "source_id": "snies-bases-2024",
    },
    {
        "date": "Próxima publicación",
        "title": "Línea base Antioquia First",
        "action": "Añadir inglés con un estándar común para los 125 municipios cuando Proantioquia publique resultados y metadatos.",
        "source_id": "proantioquia-capacidades-2026",
    },
]


def validate() -> dict:
    source_ids = [source["id"] for source in SOURCES]
    indicator_ids = [item["id"] for item in INDICATORS]
    assert len(source_ids) == len(set(source_ids)), "Hay fuentes duplicadas"
    assert len(indicator_ids) == len(set(indicator_ids)), "Hay indicadores duplicados"
    assert all(item["source_id"] in source_ids for item in INDICATORS), "Indicador sin fuente"
    assert all(item["value"] >= 0 for item in INDICATORS), "Valor negativo inesperado"
    assert all(source["url"].startswith("https://") for source in SOURCES), "URL no segura"
    assert all(item["caveat"] and item["universe"] for item in INDICATORS), "Falta universo o cautela"
    return {
        "status": "correcto",
        "source_reference_errors": 0,
        "duplicate_source_ids": 0,
        "duplicate_indicator_ids": 0,
        "missing_universes": 0,
        "missing_caveats": 0,
    }


def main() -> None:
    checks = validate()
    source_counts = Counter(source["source_type"] for source in SOURCES)
    evidence_counts = Counter(item["evidence"] for item in INDICATORS)
    payload = {
        "meta": {
            "title": "Fuentes vivas de educación en Antioquia",
            "version": "V31",
            "research_cut": CUT.isoformat(),
            "method": "Curaduría de fuentes primarias y observatorios reconocidos; cada cifra conserva periodo, territorio, universo, tipo de evidencia, uso y cautela.",
            "latest_comparable_higher_ed_cut": "2024-II",
            "next_expected_release": "SNIES 2025 · 27–31 de julio de 2026",
        },
        "summary": {
            "sources": len(SOURCES),
            "official_sources": source_counts["oficial"],
            "observatory_sources": source_counts["observatorio"],
            "indicators": len(INDICATORS),
            "evidence": dict(evidence_counts),
        },
        "sources": SOURCES,
        "indicators": INDICATORS,
        "comparability_rules": COMPARABILITY_RULES,
        "update_queue": UPDATE_QUEUE,
        "validation": checks,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"], **checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
