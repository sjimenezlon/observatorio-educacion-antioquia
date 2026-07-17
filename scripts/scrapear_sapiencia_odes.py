#!/usr/bin/env python3
"""Scrapea la biblioteca pública de ODES y valida indicadores curados.

El inventario de informes y boletines se obtiene del sitio de Sapiencia. Para
ocho estudios priorizados se descarga el PDF, se calcula su huella, se extrae
el texto y se comprueban tokens antes de publicar indicadores de encuesta.
Los PDF no se versionan: el JSON conserva URL, huella, páginas y metadatos.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "sapiencia-observatorio.json"
CUT = date(2026, 7, 17)
HEADERS = {"User-Agent": "MaterIA-Gris/1.0 (+https://materia-gris.vercel.app)"}
COLLECTIONS = {
    "informe": "https://sapiencia.gov.co/observatorio-informes/",
    "boletín": "https://sapiencia.gov.co/observatorio-boletines/",
}
DASHBOARD_COLLECTIONS = {
    "tablero_estudio": "https://sapiencia.gov.co/observatorio-estudios-tableros/",
    "tablero_cifras": "https://sapiencia.gov.co/observatorio-educacion-superior-en-cifras/",
}


def metric(
    id_: str,
    title: str,
    value: float,
    display: str,
    unit: str,
    topic: str,
    universe: str,
    decision_use: str,
    caveat: str,
) -> dict:
    return {
        "id": id_,
        "title": title,
        "value": value,
        "display": display,
        "unit": unit,
        "topic": topic,
        "universe": universe,
        "evidence": "encuesta",
        "decision_use": decision_use,
        "caveat": caveat,
    }


STUDIES = [
    {
        "id": "odes-expectativas-2024",
        "title": "Expectativas de estudiantes de grado 11° de Medellín",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2024/12/expectativas-de-estudiantes-de-grado-11-2024-17-12-2024_compressed-2.pdf",
        "publication_date": "2024-12",
        "data_cut": "Noviembre de 2024 · avance parcial",
        "period": "2024 · avance parcial",
        "level": "Transición media–superior",
        "territory": "Medellín",
        "universe": "1.839 estudiantes de grado 11° de instituciones oficiales, privadas y de cobertura contratada",
        "method": "Encuesta telefónica con apoyo de aplicativo en línea",
        "sample": 1839,
        "verification_tokens": ["1.839", "78,80%", "89,07%", "94,28%", "16,42%", "37,59%"],
        "caveat": "Resultados parciales a noviembre de 2024. Son expectativas declaradas, no solicitudes, matrículas ni tránsito observado.",
        "indicators": [
            metric("odes-expect-apply-2024", "Estudiantes que esperan presentar solicitudes de admisión", 78.80, "78,80 %", "porcentaje", "Expectativas", "Estudiantes encuestados de grado 11°", "Dimensionar intención de acceso y compararla, sin convertirla en tasa de matrícula.", "Expectativa declarada en un avance parcial; no mide solicitudes efectivas."),
            metric("odes-expect-study-2025", "Estudiantes que esperan estudiar al año siguiente", 89.07, "89,07 %", "porcentaje", "Expectativas", "Estudiantes encuestados de grado 11°", "Observar aspiración general y diseñar orientación antes del egreso.", "Incluye cualquier estudio esperado; no equivale a ingreso postsecundario."),
            metric("odes-expect-undecided-2024", "No decisión de programa entre quienes no presentarían solicitud", 30.59, "30,59 %", "porcentaje", "Orientación", "Estudiantes que señalaron razones para no presentar solicitudes", "Focalizar exploración vocacional e información de programas.", "Porcentaje dentro del subconjunto que no prioriza presentar solicitudes, no de toda la muestra."),
            metric("odes-expect-university-2024", "Preferencia por carrera universitaria", 74.48, "74,48 %", "porcentaje", "Preferencias", "Estudiantes encuestados con preferencia de nivel", "Contrastar aspiraciones con la oferta técnica, tecnológica y universitaria.", "Preferencia declarada; no predice matrícula ni permanencia."),
            metric("odes-expect-technology-2024", "Preferencia por formación tecnológica", 11.24, "11,24 %", "porcentaje", "Preferencias", "Estudiantes encuestados con preferencia de nivel", "Detectar el espacio aspiracional de la formación tecnológica.", "Preferencia declarada; no es participación en matrícula."),
            metric("odes-expect-inperson-2024", "Preferencia por modalidad presencial", 94.28, "94,28 %", "porcentaje", "Modalidad", "Estudiantes encuestados con preferencia de modalidad", "Diseñar mezclas de presencialidad y flexibilidad acordes con expectativas juveniles.", "Preferencia declarada antes del ingreso; no mide desempeño por modalidad."),
            metric("odes-expect-no-internet-2024", "Estudiantes que reportan no tener conexión a internet", 16.42, "16,42 %", "porcentaje", "Brecha digital", "Estudiantes encuestados de grado 11°", "Evitar que la virtualización reproduzca barreras de acceso.", "Autorreporte de conexión, sin medición de velocidad, estabilidad o uso."),
            metric("odes-expect-sapiencia-funds-2024", "Estudiantes que esperan financiarse con fondos o becas de Sapiencia", 37.59, "37,59 %", "porcentaje", "Financiación", "Estudiantes encuestados que proyectan formas de pago", "Anticipar demanda de información y financiación pública.", "Expectativa de financiación; no es postulación, elegibilidad ni adjudicación."),
        ],
    },
    {
        "id": "odes-seguimiento-bachilleres-2024",
        "title": "Seguimiento a la continuidad postsecundaria de bachilleres",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2024/12/presentacion-seguimiento-a-bachilleres_2024-ok.pdf",
        "publication_date": "2024-12",
        "data_cut": "Noviembre–diciembre de 2024 · avance",
        "period": "Seguimiento 2024",
        "level": "Transición media–superior",
        "territory": "Medellín",
        "universe": "509 bachilleres del año anterior que habían respondido la encuesta de expectativas",
        "method": "Encuesta telefónica con apoyo de aplicativo en línea",
        "sample": 509,
        "verification_tokens": ["509", "57,76%", "40,91%", "23,20%", "35,81%", "77,60%"],
        "caveat": "Seguimiento de una muestra de antiguos encuestados; no es la tasa administrativa oficial de tránsito inmediato del MEN.",
        "indicators": [
            metric("odes-followup-continuity-2024", "Bachilleres encuestados con continuidad postsecundaria", 57.76, "57,76 %", "porcentaje", "Transición", "Bachilleres de la muestra de seguimiento", "Complementar el tránsito administrativo con seguimiento declarado.", "Muestra de seguimiento, no tasa oficial ni representación de todos los bachilleres de Medellín."),
            metric("odes-followup-applications-2024", "Bachilleres encuestados que presentaron solicitudes de admisión", 87.0, "87,0 %", "porcentaje", "Acceso", "Bachilleres de la muestra de seguimiento", "Separar intención, solicitud y continuidad observada.", "Solicitud declarada; una persona puede presentarse a varias instituciones."),
            metric("odes-followup-money-barrier-2024", "Falta de dinero como razón para no continuar", 40.91, "40,91 %", "porcentaje", "Barreras", "Bachilleres que reportaron razones para no continuar", "Priorizar financiación, información de costos y acompañamiento temprano.", "Porcentaje del subconjunto que no continuó; no de las 509 personas completas."),
            metric("odes-followup-free-tuition-2024", "Estudiantes que reportan matrícula gratuita como financiación", 23.20, "23,20 %", "porcentaje", "Financiación", "Personas de la muestra que continuaron estudiando", "Observar el papel de gratuidad y becas dentro de las trayectorias.", "Autorreporte de forma de pago; no identifica programa ni valor del beneficio."),
            metric("odes-followup-family-tuition-2024", "Estudiantes que financian matrícula con apoyo familiar", 35.81, "35,81 %", "porcentaje", "Financiación", "Personas de la muestra que continuaron estudiando", "Dimensionar la carga financiera que permanece en los hogares.", "Autorreporte; puede coexistir con trabajo, gratuidad u otras fuentes."),
            metric("odes-followup-working-2024", "Bachilleres encuestados que trabajan actualmente", 17.68, "17,68 %", "porcentaje", "Trabajo", "Bachilleres de la muestra de seguimiento", "Reconocer simultaneidad entre estudio, trabajo y sostenimiento.", "La encuesta permite más de una ocupación; no es tasa de empleo."),
            metric("odes-followup-knows-sapiencia-2024", "Bachilleres encuestados que conocen Sapiencia", 77.60, "77,60 %", "porcentaje", "Información", "Bachilleres de la muestra de seguimiento", "Medir alcance institucional e identificar brechas de información.", "Reconocimiento de la entidad no equivale a conocer todas sus oportunidades."),
        ],
    },
    {
        "id": "odes-desercion-beneficiarios-2023",
        "title": "Panorama de la deserción de beneficiarios de Sapiencia 2020–2022",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/12/desercion_2023.pdf",
        "publication_date": "2023-12",
        "data_cut": "Encuesta octubre de 2023 · desertores 2020–2022",
        "period": "2020–2022 · encuesta 2023",
        "level": "Educación superior",
        "territory": "Medellín y beneficiarios residentes en otros territorios",
        "universe": "433 desertores de becas y créditos condonables de Sapiencia que respondieron la encuesta",
        "method": "Encuesta autodiligenciable en aplicativo web",
        "sample": 433,
        "verification_tokens": ["433", "21,7%", "21,5%", "20,6%", "65,1%", "46,7%"],
        "caveat": "Describe a quienes respondieron entre personas que perdieron o abandonaron beneficios; no calcula la tasa de deserción del total de beneficiarios.",
        "indicators": [
            metric("odes-dropout-first-semester", "Deserción reportada durante el primer semestre", 21.5, "21,5 %", "porcentaje", "Permanencia", "Personas desertoras encuestadas", "Ubicar el momento temprano en el que se requieren apoyos.", "Distribución dentro de desertores encuestados; no es probabilidad de desertar en primer semestre."),
            metric("odes-dropout-third-semester", "Deserción reportada durante el tercer semestre", 21.7, "21,7 %", "porcentaje", "Permanencia", "Personas desertoras encuestadas", "Evitar que el acompañamiento se concentre solo en el ingreso.", "Distribución dentro de desertores encuestados; no es tasa de cohorte."),
            metric("odes-dropout-work-reason", "Asuntos laborales como razón principal de abandono", 20.6, "20,6 %", "porcentaje", "Barreras", "Personas desertoras encuestadas", "Diseñar flexibilidad horaria y apoyos compatibles con el trabajo.", "Razón declarada y no necesariamente única o causal."),
            metric("odes-dropout-low-performance", "Bajo rendimiento como razón de abandono", 6.7, "6,7 %", "porcentaje", "Aprendizaje", "Personas desertoras encuestadas", "Articular alertas académicas con apoyos financieros y psicosociales.", "Razón declarada dentro de una encuesta a desertores."),
            metric("odes-dropout-continued-study", "Personas que siguieron estudiando tras perder el beneficio", 65.1, "65,1 %", "porcentaje", "Trayectorias", "Personas desertoras encuestadas", "Distinguir pérdida del beneficio de abandono total del sistema.", "Continuidad autorreportada; no identifica duración, institución ni graduación."),
            metric("odes-dropout-would-return", "Personas que retomarían estudios con apoyo de Sapiencia", 46.7, "46,7 %", "porcentaje", "Reingreso", "Personas desertoras encuestadas", "Dimensionar potencial de rutas de reingreso y recuperación.", "Intención hipotética; no garantiza retorno efectivo."),
        ],
    },
    {
        "id": "odes-asistencia-2023",
        "title": "Tasa de asistencia a la educación postsecundaria",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/12/tasaasistencia_2023.pdf",
        "publication_date": "2023-12",
        "data_cut": "Octubre de 2023",
        "period": "2023",
        "level": "Educación postsecundaria",
        "territory": "Comunas y corregimientos de Medellín",
        "universe": "2.643 personas bachilleres de 16 a 28 años residentes en Medellín que respondieron el sondeo",
        "method": "Encuesta autodiligenciable en aplicativo web",
        "sample": 2643,
        "verification_tokens": ["2643", "40.48%", "59,52%", "33,44%", "28,67%"],
        "caveat": "El informe no documenta un diseño muestral probabilístico; se publica como estimación del sondeo y no como cobertura oficial.",
        "indicators": [
            metric("odes-attendance-2023", "Asistencia postsecundaria estimada en el sondeo", 40.48, "40,48 %", "porcentaje", "Acceso", "Personas bachilleres de 16 a 28 años encuestadas", "Incorporar una lectura de participación por residencia y no solo oferta.", "Estimación de encuesta autodiligenciable; no es cobertura oficial ni matrícula."),
            metric("odes-not-studying-2023", "Personas encuestadas que no estaban estudiando", 59.52, "59,52 %", "porcentaje", "Acceso", "Personas bachilleres de 16 a 28 años encuestadas", "Dimensionar el universo potencial para reingreso y educación flexible.", "Complemento del sondeo de asistencia; no es cifra poblacional expandida."),
            metric("odes-not-study-work-2023", "Trabajo como razón para no estudiar", 33.44, "33,44 %", "porcentaje", "Barreras", "Personas encuestadas que no estaban estudiando", "Diseñar oferta compatible con responsabilidades laborales.", "Porcentaje del subconjunto que no estudia; razón declarada."),
            metric("odes-not-study-resources-2023", "Falta de recursos como razón para no estudiar", 28.67, "28,67 %", "porcentaje", "Barreras", "Personas encuestadas que no estaban estudiando", "Conectar financiación de matrícula y sostenimiento con rutas de retorno.", "Porcentaje del subconjunto que no estudia; no identifica el costo específico."),
        ],
    },
    {
        "id": "odes-matricula-cero-2023",
        "title": "Contribución de Matrícula Cero al acceso y la permanencia",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/11/informe_matriculacero-2023.pdf",
        "publication_date": "2023-11",
        "data_cut": "Junio de 2023",
        "period": "2023",
        "level": "Educación superior",
        "territory": "Medellín · tres IES distritales",
        "universe": "2.517 estudiantes beneficiarios de Matrícula Cero en ITM, Pascual Bravo y Colmayor",
        "method": "Encuesta autodiligenciable estratificada por IES",
        "sample": 2517,
        "verification_tokens": ["2517", "99 %", "88 %", "98 %", "21,73 %", "49,07 %"],
        "caveat": "Mide percepciones de participantes beneficiarios y no identifica el efecto causal del programa frente a un grupo de comparación.",
        "indicators": [
            metric("odes-zero-facilitated-access-2023", "Beneficiarios que dicen que Matrícula Cero facilitó su acceso", 99.0, "99,0 %", "porcentaje", "Acceso", "Beneficiarios encuestados en las tres IES distritales", "Escuchar la valoración del programa junto con métricas administrativas.", "Percepción de beneficiarios; no es una estimación causal de acceso adicional."),
            metric("odes-zero-full-dedication-2023", "Beneficiarios que atribuyen mayor dedicación al estudio", 88.0, "88,0 %", "porcentaje", "Permanencia", "Beneficiarios encuestados en las tres IES distritales", "Explorar cómo el alivio financiero modifica el tiempo disponible para estudiar.", "Autorreporte; no mide horas efectivas ni permanencia observada."),
            metric("odes-zero-performance-challenge-2023", "Beneficiarios que sienten el reto de mejorar su desempeño", 98.0, "98,0 %", "porcentaje", "Aprendizaje", "Beneficiarios encuestados en las tres IES distritales", "Vincular financiación con acompañamiento y desempeño académico.", "Percepción aspiracional; no es variación de notas ni valor agregado."),
            metric("odes-zero-stratum-one-2023", "Participantes de Matrícula Cero residentes en estrato 1", 21.73, "21,73 %", "porcentaje", "Equidad", "Beneficiarios encuestados en las tres IES distritales", "Revisar focalización socioeconómica del beneficio.", "Composición de la muestra, no del universo total de beneficiarios."),
            metric("odes-zero-stratum-two-2023", "Participantes de Matrícula Cero residentes en estrato 2", 49.07, "49,07 %", "porcentaje", "Equidad", "Beneficiarios encuestados en las tres IES distritales", "Revisar focalización socioeconómica del beneficio.", "Composición de la muestra, no del universo total de beneficiarios."),
        ],
    },
    {
        "id": "odes-destino-universitario-2023",
        "title": "Satisfacción de Medellín como destino universitario",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/12/satisfaccion_2023.pdf",
        "publication_date": "2023-12",
        "data_cut": "Septiembre de 2023",
        "period": "2023",
        "level": "Educación postsecundaria",
        "territory": "Medellín",
        "universe": "2.364 estudiantes, egresados, docentes y estudiantes de movilidad de instituciones domiciliadas en Medellín",
        "method": "Encuesta autodiligenciable en aplicativo web",
        "sample": 2364,
        "verification_tokens": ["2.364", "78,06%", "68,83%", "72,32%", "63,56%", "12,94%"],
        "caveat": "Percepción de una muestra autoseleccionada con tamaños muy distintos por público; no representa un ranking de ciudades o instituciones.",
        "indicators": [
            metric("odes-destination-students-2023", "Satisfacción de estudiantes con Medellín como destino universitario", 78.06, "78,06 %", "porcentaje", "Experiencia", "1.544 estudiantes encuestados", "Incorporar experiencia estudiantil a las decisiones de ciudad universitaria.", "Percepción de participantes; no se ajusta por institución, origen o programa."),
            metric("odes-destination-graduates-2023", "Satisfacción de egresados con Medellín como destino universitario", 68.83, "68,83 %", "porcentaje", "Experiencia", "572 egresados encuestados", "Conectar experiencia de ciudad con permanencia y atracción de talento.", "Percepción de participantes; no es resultado laboral."),
            metric("odes-destination-teachers-2023", "Satisfacción de docentes con Medellín como destino universitario", 72.32, "72,32 %", "porcentaje", "Experiencia", "224 docentes encuestados", "Incorporar condiciones de atracción y retención docente.", "Muestra pequeña y autoseleccionada; no representa a todo el cuerpo docente."),
            metric("odes-destination-mobility-2023", "Satisfacción de estudiantes de movilidad con Medellín", 63.56, "63,56 %", "porcentaje", "Internacionalización", "24 estudiantes de movilidad encuestados", "Identificar oportunidades de mejora para movilidad académica.", "Solo 24 respuestas; el porcentaje es muy sensible a pocos casos."),
            metric("odes-destination-cost-life-2023", "Satisfacción con el costo de vida", 12.94, "12,94 %", "porcentaje", "Sostenimiento", "Públicos participantes del estudio", "Poner vivienda, alimentación y transporte dentro de la política de permanencia.", "Dimensión perceptual agregada; no estima gasto real ni costo por estudiante."),
        ],
    },
    {
        "id": "odes-talento-laboral-2022",
        "title": "Vinculación laboral de personas beneficiarias de Talento Especializado",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/09/informe.vinculacion.laboral.t.e..pdf",
        "publication_date": "2023-09",
        "data_cut": "Octubre de 2022",
        "period": "2022",
        "level": "Educación continua",
        "territory": "Medellín",
        "universe": "675 personas certificadas por el programa Talento Especializado",
        "method": "Encuesta telefónica",
        "sample": 675,
        "verification_tokens": ["675", "271", "166", "46 personas", "59 %", "52 %", "66 %"],
        "caveat": "Estudio de 2022 sobre personas certificadas; las categorías de ocupación no necesariamente agotan ni dividen de forma exclusiva la muestra.",
        "indicators": [
            metric("odes-talent-working-2022", "Personas certificadas que reportaron trabajar como actividad principal", 271, "271", "personas", "Trabajo", "Personas certificadas encuestadas", "Seguir inserción declarada después de formación corta.", "Conteo de encuesta, no tasa de empleo ni vinculación formal."),
            metric("odes-talent-jobseekers-2022", "Personas certificadas que reportaron buscar trabajo", 166, "166", "personas", "Trabajo", "Personas certificadas encuestadas", "Dimensionar necesidades de intermediación y certificaciones complementarias.", "Conteo de encuesta; puede no cubrir todas las situaciones ocupacionales."),
            metric("odes-talent-business-2022", "Personas certificadas con negocio propio", 46, "46", "personas", "Emprendimiento", "Personas certificadas encuestadas", "Observar emprendimiento como resultado alternativo al empleo.", "Existencia declarada de negocio; no informa ventas, permanencia o formalidad."),
            metric("odes-talent-contract-2022", "Personas ocupadas que reportan contrato laboral", 59.0, "59,0 %", "porcentaje", "Formalidad", "271 personas que trabajan", "Distinguir ocupación de protección laboral.", "Autorreporte entre quienes trabajan; contrato no garantiza todas las cotizaciones."),
            metric("odes-talent-low-relation-2022", "Personas ocupadas con baja relación entre empleo y curso", 52.0, "52,0 %", "porcentaje", "Pertinencia", "271 personas que trabajan", "Revisar alineación curricular y mecanismos de inserción.", "Relación percibida por la persona; no evalúa competencias del curso."),
            metric("odes-talent-knowledge-contribution-2022", "Personas ocupadas que valoran aporte alto del conocimiento al trabajo", 66.0, "66,0 %", "porcentaje", "Pertinencia", "271 personas que trabajan", "Contrastar pertinencia percibida con la relación directa curso–ocupación.", "Valoración subjetiva; puede coexistir con baja relación ocupacional."),
        ],
    },
    {
        "id": "odes-brecha-digital-2023",
        "title": "Brecha digital en la población estudiantil de Medellín",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/11/informe-brecha-digital.pdf",
        "publication_date": "2023-11",
        "data_cut": "Mayo–junio de 2023",
        "period": "2023",
        "level": "Media y educación postsecundaria",
        "territory": "Medellín",
        "universe": "1.269 estudiantes de media, ETDH y educación superior que respondieron el sondeo",
        "method": "Sondeo autodiligenciable por correo electrónico",
        "sample": 1269,
        "verification_tokens": ["1.269", "34,9 %", "66 %", "61 %", "51 %", "14,6 %", "11,8 %"],
        "caveat": "El propio informe define el sondeo como no representativo de la población; sirve para identificar hipótesis y necesidades.",
        "indicators": [
            metric("odes-digital-regular-signal-2023", "Personas que califican como regular la señal de internet", 34.9, "34,9 %", "porcentaje", "Brecha digital", "Personas participantes del sondeo", "Priorizar calidad de conexión, no solo disponibilidad.", "Sondeo no representativo y valoración subjetiva de la señal."),
            metric("odes-digital-low-excel-media-2023", "Estudiantes de media con desempeño bajo o muy bajo en Excel", 66.0, "66,0 %", "porcentaje", "Competencias digitales", "Estudiantes de educación media participantes", "Focalizar alfabetización de datos y herramientas productivas.", "Autovaloración en un sondeo no representativo; no es prueba de desempeño."),
            metric("odes-digital-low-word-media-2023", "Estudiantes de media con desempeño bajo o muy bajo en Word", 61.0, "61,0 %", "porcentaje", "Competencias digitales", "Estudiantes de educación media participantes", "Detectar habilidades instrumentales que condicionan estudio y trabajo.", "Autovaloración en un sondeo no representativo."),
            metric("odes-digital-low-slides-media-2023", "Estudiantes de media con desempeño bajo o muy bajo en PowerPoint", 51.0, "51,0 %", "porcentaje", "Competencias digitales", "Estudiantes de educación media participantes", "Diseñar formación digital básica conectada con tareas académicas.", "Autovaloración en un sondeo no representativo."),
            metric("odes-digital-violence-women-2023", "Mujeres que reportan haber sufrido violencia digital", 14.6, "14,6 %", "porcentaje", "Bienestar digital", "Mujeres participantes del sondeo", "Integrar seguridad y ciudadanía digital a la permanencia.", "Autorreporte en sondeo no representativo; no es prevalencia poblacional."),
            metric("odes-digital-violence-men-2023", "Hombres que reportan haber sufrido violencia digital", 11.8, "11,8 %", "porcentaje", "Bienestar digital", "Hombres participantes del sondeo", "Comparar experiencias declaradas y orientar prevención.", "Autorreporte en sondeo no representativo; no es prevalencia poblacional."),
        ],
    },
    {
        "id": "odes-expectativas-clei-2023",
        "title": "Expectativas de estudiantes CLEI 5 y 6 para continuar a la educación postsecundaria",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/12/expectativasclei_2023.pdf",
        "publication_date": "2023-12",
        "data_cut": "Septiembre de 2023",
        "period": "2023",
        "level": "Transición media–superior · CLEI",
        "territory": "Medellín",
        "universe": "363 estudiantes de CLEI 5 y 6 de instituciones oficiales, privadas y de cobertura",
        "method": "Encuesta autodiligenciable en aplicativo web",
        "sample": 363,
        "verification_tokens": ["363 personas", "78,79%", "67,77%", "15,70%", "41,36%", "35,24%", "57,30%", "72,18 %"],
        "caveat": "Muestra de estudiantes CLEI participantes; expectativas, preferencias y barreras declaradas no equivalen a solicitudes, matrícula o tránsito observado.",
        "indicators": [
            metric("odes-clei-internet-home-2023", "Estudiantes CLEI con acceso a internet en casa", 67.77, "67,77 %", "porcentaje", "Brecha digital", "363 estudiantes CLEI encuestados", "Dimensionar necesidades de conectividad para acompañamiento flexible.", "Autorreporte de acceso; no mide velocidad, estabilidad o dispositivo disponible."),
            metric("odes-clei-no-device-2023", "Estudiantes CLEI sin los dispositivos consultados", 15.70, "15,70 %", "porcentaje", "Brecha digital", "363 estudiantes CLEI encuestados", "Evitar que la orientación y postulación dependan solo de canales digitales.", "Autorreporte; la lista de dispositivos no agota todas las formas de acceso."),
            metric("odes-clei-apply-2023", "Estudiantes CLEI que piensan presentar solicitudes de admisión", 78.79, "78,79 %", "porcentaje", "Expectativas", "363 estudiantes CLEI encuestados", "Diseñar rutas de orientación y postulación para educación de adultos.", "Intención declarada, no solicitud efectiva ni ingreso."),
            metric("odes-clei-university-2023", "Preferencia CLEI por carrera universitaria", 42.66, "42,66 %", "porcentaje", "Preferencias", "Estudiantes CLEI con preferencia de nivel", "Contrastar aspiraciones con opciones técnicas, tecnológicas y universitarias.", "Preferencia declarada; no predice matrícula."),
            metric("odes-clei-technical-2023", "Preferencia CLEI por formación técnica profesional", 23.78, "23,78 %", "porcentaje", "Preferencias", "Estudiantes CLEI con preferencia de nivel", "Visibilizar la demanda potencial de trayectorias técnicas.", "Preferencia declarada; no equivale a demanda efectiva."),
            metric("odes-clei-work-tuition-2023", "Estudiantes CLEI que prevén pagar matrícula con empleo", 36.52, "36,52 %", "porcentaje", "Financiación", "Estudiantes CLEI que proyectan formas de pago", "Diseñar horarios y apoyos compatibles con el trabajo.", "Fuente prevista de pago; no es gasto observado ni empleo verificado."),
            metric("odes-clei-work-sustenance-2023", "Estudiantes CLEI que prevén financiar sostenimiento con empleo", 56.86, "56,86 %", "porcentaje", "Sostenimiento", "Estudiantes CLEI que proyectan formas de sostenimiento", "Incorporar tiempo, transporte y alimentación a la política de acceso.", "Expectativa de financiación, no ingreso laboral medido."),
            metric("odes-clei-work-barrier-2023", "Necesidad de trabajar como razón para no solicitar admisión", 41.36, "41,36 %", "porcentaje", "Barreras", "Subconjunto CLEI que no presentaría solicitudes", "Priorizar modalidades y calendarios compatibles con responsabilidades laborales.", "Porcentaje del subconjunto que no solicitaría admisión, no de toda la muestra."),
            metric("odes-clei-money-barrier-2023", "Falta de dinero como razón para no solicitar admisión", 35.24, "35,24 %", "porcentaje", "Barreras", "Subconjunto CLEI que no presentaría solicitudes", "Conectar orientación con información de becas, gratuidad y costos.", "Porcentaje del subconjunto que no solicitaría admisión, no de toda la muestra."),
            metric("odes-clei-study-next-year-2023", "Estudiantes CLEI que proyectan estudiar al año siguiente", 57.30, "57,30 %", "porcentaje", "Trayectorias", "363 estudiantes CLEI encuestados", "Dimensionar aspiración inmediata después del bachillerato flexible.", "Proyección declarada; no es tránsito observado."),
            metric("odes-clei-does-not-know-sapiencia-2023", "Estudiantes CLEI que manifiestan no conocer Sapiencia", 72.18, "72,18 %", "porcentaje", "Información", "363 estudiantes CLEI encuestados", "Focalizar difusión de oportunidades en jornadas y sedes CLEI.", "Reconocimiento institucional no mide conocimiento específico de cada beneficio."),
        ],
    },
    {
        "id": "odes-financiacion-etdh-2022",
        "title": "Financiación de estudiantes de Educación para el Trabajo y el Desarrollo Humano",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/05/financiacion.etdh-disenado_03-05.pdf",
        "publication_date": "2023-05",
        "data_cut": "Noviembre de 2022",
        "period": "2022",
        "level": "Educación para el Trabajo y el Desarrollo Humano",
        "territory": "Medellín",
        "universe": "298 estudiantes matriculados en instituciones ETDH que respondieron el sondeo",
        "method": "Sondeo autodiligenciable enviado por correo electrónico",
        "sample": 298,
        "verification_tokens": ["298 estudiantes", "68,3 %", "14,3 %", "11,8 %", "17,3 %", "83,2 %", "98,2 %"],
        "caveat": "Primer sondeo ETDH de ODES, sin diseño probabilístico documentado. Las fuentes de financiación pueden tener bases y posibilidades de respuesta distintas.",
        "indicators": [
            metric("odes-etdh-own-resources-2022", "Estudiantes ETDH que financian estudios con recursos propios", 68.3, "68,3 %", "porcentaje", "Financiación", "298 estudiantes ETDH participantes", "Dimensionar el peso directo que asumen estudiantes y hogares.", "Sondeo no representativo; la fuente puede coexistir con otros apoyos."),
            metric("odes-etdh-scholarships-2022", "Estudiantes ETDH que reportan becas o subsidios", 14.3, "14,3 %", "porcentaje", "Financiación", "298 estudiantes ETDH participantes", "Observar el alcance declarado de apoyos no reembolsables.", "Sondeo no representativo; no identifica monto ni duración."),
            metric("odes-etdh-credit-2022", "Estudiantes ETDH que reportan crédito educativo", 11.8, "11,8 %", "porcentaje", "Financiación", "298 estudiantes ETDH participantes", "Reconocer exposición a deuda dentro de la financiación ETDH.", "Sondeo no representativo; no informa saldo, tasa o entidad para toda la muestra."),
            metric("odes-etdh-public-funds-2022", "Estudiantes ETDH financiados con recursos distritales o de Sapiencia", 17.3, "17,3 %", "porcentaje", "Financiación pública", "298 estudiantes ETDH participantes", "Dimensionar el papel declarado de recursos públicos locales.", "Cifra del sondeo; no equivale a cobertura administrativa ni ejecución presupuestal."),
            metric("odes-etdh-family-work-sustenance-2022", "Apoyo familiar y trabajo dentro de las fuentes de sostenimiento ETDH", 83.2, "83,2 %", "porcentaje", "Sostenimiento", "298 estudiantes ETDH participantes", "Vincular permanencia con ingresos y redes de apoyo.", "Suma de categorías reportadas en el sondeo; no representa personas únicas si hubo respuesta múltiple."),
            metric("odes-etdh-household-income-2022", "Hogares ETDH con ingresos de hasta tres salarios mínimos", 98.2, "98,2 %", "porcentaje", "Equidad", "Hogares de estudiantes ETDH participantes con respuesta", "Contextualizar capacidad de pago y necesidad de sostenimiento.", "Ingreso declarado dentro de un sondeo y no verificado administrativamente."),
        ],
    },
    {
        "id": "odes-fondos-pregrado-laboral-2022",
        "title": "Vinculación laboral de personas beneficiarias de fondos de pregrado",
        "url": "https://sapiencia.gov.co/wp-content/uploads/2023/05/informevinculacionlaboralfondos_.pdf",
        "publication_date": "2023-05",
        "data_cut": "Octubre de 2022",
        "period": "2022",
        "level": "Educación superior · graduados",
        "territory": "Medellín y residencia posterior declarada",
        "universe": "301 personas graduadas desde 2018 con beneficios de fondos de pregrado de Sapiencia",
        "method": "Encuesta telefónica",
        "sample": 301,
        "verification_tokens": ["301", "80,73 %", "83,75 %", "86,8 %", "82,7 %", "22,92 %", "19,60 %", "17,94 %", "61,13 %"],
        "caveat": "Encuesta a personas beneficiarias graduadas que respondieron; no tiene grupo de comparación y no identifica el efecto causal del fondo sobre empleo o salario.",
        "indicators": [
            metric("odes-funds-working-2022", "Personas graduadas beneficiarias que reportan estar trabajando", 80.73, "80,73 %", "porcentaje", "Trabajo", "301 personas beneficiarias graduadas encuestadas", "Seguir inserción declarada después de la graduación.", "Autorreporte; no equivale a cotización formal ni efecto del beneficio."),
            metric("odes-funds-business-2022", "Personas graduadas beneficiarias dedicadas a negocio propio", 2.66, "2,66 %", "porcentaje", "Emprendimiento", "301 personas beneficiarias graduadas encuestadas", "Observar emprendimiento como trayectoria laboral alternativa.", "Autorreporte; no informa sostenibilidad, ventas o formalidad."),
            metric("odes-funds-first-job-six-months-2022", "Personas beneficiarias cuyo primer empleo llegó en seis meses o menos", 83.75, "83,75 %", "porcentaje", "Inserción laboral", "Personas beneficiarias encuestadas con trayectoria laboral", "Observar velocidad declarada de inserción laboral.", "Autorreporte retrospectivo; no tiene comparación con graduados no beneficiarios."),
            metric("odes-funds-job-study-relation-2022", "Empleo con relación alta o media con los estudios", 86.8, "86,8 %", "porcentaje", "Pertinencia", "Personas beneficiarias que trabajan", "Contrastar inserción con correspondencia entre formación y ocupación.", "Valoración subjetiva entre quienes trabajan; no es medición ocupacional independiente."),
            metric("odes-funds-knowledge-contribution-2022", "Conocimientos del programa que aportaron al empleo actual", 82.7, "82,7 %", "porcentaje", "Pertinencia", "Personas beneficiarias que trabajan", "Identificar pertinencia percibida de la formación.", "Percepción entre quienes trabajan; no mide productividad ni valor agregado."),
            metric("odes-funds-no-health-contribution-2022", "Personas beneficiarias que no aportan a salud", 21.59, "21,59 %", "porcentaje", "Protección social", "Personas beneficiarias graduadas encuestadas", "Separar ocupación declarada de protección social efectiva.", "Autorreporte; no se contrasta con PILA ni otra fuente administrativa."),
            metric("odes-funds-no-pension-contribution-2022", "Personas beneficiarias que no aportan a pensión", 22.26, "22,26 %", "porcentaje", "Protección social", "Personas beneficiarias graduadas encuestadas", "Visibilizar vulnerabilidad laboral más allá de tener trabajo.", "Autorreporte; no se contrasta con PILA."),
            metric("odes-funds-language-gap-2022", "Idiomas entre competencias necesarias no adquiridas", 22.92, "22,92 %", "porcentaje", "Brechas de competencias", "Personas beneficiarias graduadas encuestadas", "Orientar refuerzo curricular y formación complementaria.", "Necesidad percibida; no es prueba estandarizada de competencia."),
            metric("odes-funds-programming-gap-2022", "Programación entre competencias necesarias no adquiridas", 19.60, "19,60 %", "porcentaje", "Brechas de competencias", "Personas beneficiarias graduadas encuestadas", "Identificar demanda transversal de habilidades digitales.", "Necesidad percibida; no evalúa nivel de programación."),
            metric("odes-funds-data-gap-2022", "Análisis de datos entre competencias necesarias no adquiridas", 17.94, "17,94 %", "porcentaje", "Brechas de competencias", "Personas beneficiarias graduadas encuestadas", "Informar módulos de alfabetización y análisis de datos.", "Necesidad percibida; no es una prueba de desempeño."),
            metric("odes-funds-salary-below-expected-2022", "Personas beneficiarias con salario inferior al esperado", 44.03, "44,03 %", "porcentaje", "Ingresos", "Personas beneficiarias que trabajan y respondieron", "Contrastar inserción con suficiencia y expectativas salariales.", "Comparación subjetiva con expectativa individual; no mide retorno financiero."),
            metric("odes-funds-no-ies-job-support-2022", "Personas beneficiarias sin apoyo de su IES para buscar empleo", 61.13, "61,13 %", "porcentaje", "Intermediación laboral", "Personas beneficiarias que trabajan", "Fortalecer servicios de carrera y acompañamiento a graduados.", "Autorreporte; no evalúa cobertura o calidad objetiva de los servicios."),
            metric("odes-funds-women-one-two-wages-2022", "Mujeres ocupadas que ganan entre uno y dos salarios mínimos", 53.62, "53,62 %", "porcentaje", "Brecha de género", "Mujeres beneficiarias ocupadas de la encuesta", "Examinar concentración femenina en rangos salariales bajos.", "Distribución descriptiva sin controlar programa, experiencia, jornada o cargo."),
            metric("odes-funds-men-one-two-wages-2022", "Hombres ocupados que ganan entre uno y dos salarios mínimos", 39.18, "39,18 %", "porcentaje", "Brecha de género", "Hombres beneficiarios ocupados de la encuesta", "Comparar composición salarial por sexo con cautela.", "Distribución descriptiva sin controles; no identifica una brecha salarial ajustada."),
            metric("odes-funds-women-over-four-wages-2022", "Mujeres ocupadas que ganan más de cuatro salarios mínimos", 3.62, "3,62 %", "porcentaje", "Brecha de género", "Mujeres beneficiarias ocupadas de la encuesta", "Observar representación femenina en el rango superior.", "Muestra y distribución descriptiva; no controla diferencias ocupacionales."),
            metric("odes-funds-men-over-four-wages-2022", "Hombres ocupados que ganan más de cuatro salarios mínimos", 13.40, "13,40 %", "porcentaje", "Brecha de género", "Hombres beneficiarios ocupados de la encuesta", "Observar representación masculina en el rango superior.", "Muestra y distribución descriptiva; no prueba discriminación salarial."),
        ],
    },
]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def scrape_collection(kind: str, url: str, session: requests.Session) -> list[dict]:
    response = session.get(url, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows = []
    seen = set()
    for anchor in soup.select(".mk-image a[href]"):
        href = urljoin(url, anchor.get("href", ""))
        if not urlparse(href).path.lower().endswith(".pdf") or href in seen:
            continue
        seen.add(href)
        column = anchor.find_parent(class_=lambda classes: classes and "wpb_column" in classes)
        title = ""
        if column:
            block = column.select_one(".mk-text-block")
            if block:
                title = " ".join(block.stripped_strings)
        if not title:
            image = anchor.find("img")
            title = image.get("alt", "") if image else Path(urlparse(href).path).stem
        title = re.sub(r"\s+", " ", title).strip(" .")
        match = re.search(r"/uploads/(\d{4})/(\d{2})/", href)
        rows.append({
            "id": hashlib.sha1(href.encode()).hexdigest()[:12],
            "collection": kind,
            "title": title,
            "url": href,
            "published_folder": f"{match.group(1)}-{match.group(2)}" if match else "sin-fecha",
        })
    return rows


def scrape_dashboards(kind: str, url: str, session: requests.Session) -> list[dict]:
    response = session.get(url, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows = []
    seen = set()
    for anchor in soup.select('h4 a[href*="app.powerbi.com/view"]'):
        href = anchor.get("href", "").strip()
        title = re.sub(r"\s+", " ", " ".join(anchor.stripped_strings)).strip()
        key = (title, href)
        if not title or not href or key in seen:
            continue
        seen.add(key)
        rows.append({
            "id": hashlib.sha1(f"{kind}|{title}|{href}".encode()).hexdigest()[:12],
            "collection": kind,
            "title": title,
            "url": href,
            "source_page": url,
        })
    return rows


def validate_study(study: dict, session: requests.Session) -> dict:
    response = session.get(study["url"], timeout=90)
    response.raise_for_status()
    content = response.content
    assert content.startswith(b"%PDF"), f"{study['id']}: el recurso no es un PDF"
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        pages = len(pdf.pages)
    normalized = normalize_text(text)
    missing = [token for token in study["verification_tokens"] if normalize_text(token) not in normalized]
    assert not missing, f"{study['id']}: tokens no verificados {missing}"
    result = {key: value for key, value in study.items() if key != "verification_tokens"}
    result["pages"] = pages
    result["sha256"] = hashlib.sha256(content).hexdigest()
    return result


def main() -> None:
    session = requests.Session()
    session.headers.update(HEADERS)
    publications = []
    for kind, url in COLLECTIONS.items():
        publications.extend(scrape_collection(kind, url, session))
    dashboards = []
    for kind, url in DASHBOARD_COLLECTIONS.items():
        dashboards.extend(scrape_dashboards(kind, url, session))
    assert len(publications) == len({item["url"] for item in publications}), "Publicaciones duplicadas"
    assert len([item for item in publications if item["collection"] == "informe"]) >= 30
    assert len([item for item in publications if item["collection"] == "boletín"]) >= 30
    assert len([item for item in dashboards if item["collection"] == "tablero_estudio"]) >= 18
    assert len([item for item in dashboards if item["collection"] == "tablero_cifras"]) >= 30
    assert len(dashboards) == len({item["id"] for item in dashboards}), "Tableros duplicados"

    publication_urls = {item["url"] for item in publications}
    assert all(study["url"] in publication_urls for study in STUDIES), "Estudio curado fuera del catálogo"
    studies = [validate_study(study, session) for study in STUDIES]
    indicators = [
        {**indicator, "study_id": study["id"], "source_id": study["id"], "period": study["period"],
         "level": study["level"], "territory": study["territory"]}
        for study in studies
        for indicator in study["indicators"]
    ]
    ids = [item["id"] for item in indicators]
    assert len(ids) == len(set(ids)), "Indicadores ODES duplicados"
    assert all(item["value"] >= 0 and item["caveat"] for item in indicators)

    report_count = sum(item["collection"] == "informe" for item in publications)
    bulletin_count = sum(item["collection"] == "boletín" for item in publications)
    payload = {
        "meta": {
            "title": "Biblioteca e indicadores del Observatorio de Educación Postsecundaria de Sapiencia",
            "version": "V37",
            "scraped_on": CUT.isoformat(),
            "method": "Inventario raspado desde las páginas públicas de ODES; indicadores curados desde PDF con verificación de tokens, huella SHA-256 y cautela metodológica.",
            "collection_urls": {**COLLECTIONS, **DASHBOARD_COLLECTIONS},
        },
        "summary": {
            "publications": len(publications),
            "reports": report_count,
            "bulletins": bulletin_count,
            "dashboards": len(dashboards),
            "study_dashboards": sum(item["collection"] == "tablero_estudio" for item in dashboards),
            "data_dashboards": sum(item["collection"] == "tablero_cifras" for item in dashboards),
            "catalog_resources": len(publications) + len(dashboards),
            "curated_studies": len(studies),
            "survey_indicators": len(indicators),
            "downloaded_pages": sum(study["pages"] for study in studies),
        },
        "studies": studies,
        "indicators": indicators,
        "publications": sorted(publications, key=lambda item: (item["published_folder"], item["title"]), reverse=True),
        "dashboards": sorted(dashboards, key=lambda item: (item["collection"], item["title"])),
        "validation": {
            "status": "correcto",
            "duplicate_publication_urls": 0,
            "duplicate_dashboard_ids": 0,
            "duplicate_indicator_ids": 0,
            "missing_verification_tokens": 0,
            "missing_curated_studies_in_catalog": 0,
        },
        "reading_rules": [
            "Encuesta, sondeo, registro administrativo y matrícula no son sinónimos.",
            "Las expectativas de grado 11 y el seguimiento a bachilleres corresponden a muestras distintas; no forman un embudo.",
            "El estudio de desertores describe razones entre quienes respondieron; no calcula una tasa de deserción del programa.",
            "Las percepciones de beneficiarios de Matrícula Cero no identifican el efecto causal del beneficio.",
            "El sondeo de brecha digital se declara no representativo y se usa para formular hipótesis, no para estimar prevalencias.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **payload["summary"], **payload["validation"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
