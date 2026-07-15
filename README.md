# MaterIA Gris · El cerebro de datos de la educación superior de Antioquia

**https://materia-gris.vercel.app** (antes «Observatorio de Educación Superior de Antioquia»; la URL vieja sigue activa como espejo).

Tablero de la educación superior del departamento de Antioquia — **pregrado y posgrado, pública y privada** — con lente de detalle sobre la formación técnica y tecnológica (TyT).

**En línea:** https://materia-gris.vercel.app
**Espejo:** https://observatorio-educacion-antioquia.vercel.app
**Autor:** Santiago Jiménez Londoño · Última versión: V31 (julio de 2026)

---

## Qué responde

| Sección | Pregunta que contesta |
|---|---|
| **Sala Ejecutiva** | ¿Qué exige decisión ahora? Tensiones, prioridades y rutas diferenciadas para gobierno, rectoría y planeación |
| **Trayectorias y retorno** | ¿Dónde se rompe la oportunidad? Conecta aspiración, acceso, permanencia, aprendizaje, graduación y vínculo laboral sin fingir una cohorte única |
| **Fuentes vivas** | ¿Qué sabemos hoy y con qué alcance? 13 fuentes y 23 indicadores con corte, universo, uso decisional y cautela |
| **Panorama** | ¿Cómo evolucionó la matrícula 2018-2024 por nivel, sector y modalidad? |
| **Instituciones** | ¿Quién forma a Antioquia? 73 IES, comparador de hasta 3, docentes y radar de cifras 2025-2026 autorreportadas |
| **IES del Distrito** | ¿Cómo se articulan ITM, Pascual Bravo y Colmayor? Matrícula e indicadores oficiales 2026-1, oferta 2026-2, SNIES, finanzas y perfiles institucionales |
| **Territorio** | ¿Dónde llega la oferta? Mapa municipal interactivo y comparador sincronizado de razón de oferta, presencia municipal y peso TyT |
| **Modo Decisión** | ¿Cómo reducir opciones? Cruza territorio, nivel, modalidad y área sin fabricar un ranking de “mejores” programas |
| **Producto comparado** | ¿Qué aprende MaterIA de OTE, College Scorecard, Discover Uni, Mi Futuro y Our World in Data? Matriz sin puntuación total y adopciones V27 |
| **Oferta** | ¿Qué se puede estudiar? 2.107 programas con explorador filtrable |
| **Mercado laboral** | ¿Cómo les va a los graduados? Demanda, embudo, vinculación formal y salario de enganche por nivel y área |
| **Calidad** | Acreditación de alta calidad, Saber TyT vs. nacional (y por municipio), bilingüismo (MCER) |
| **Acreditación** | ¿Cómo se obtiene la alta calidad? Guía protegida, ruta, evidencias y monitor institucional |
| **Innovación** | 815 grupos de investigación reconocidos (Conv. 957 de 2024) |
| **Impacto social** | ¿Quiénes estudian? Estrato, trabajo, educación de la madre, brecha de género y STEM |
| **Redes sociales** | ¿Quién gestiona mejor su presencia digital? Audiencia pública, seis plataformas, índice y límites |
| **Finanzas** | ¿Qué sostiene a las IES públicas? Presupuesto, dependencia estatal, resultados y alertas |
| **Metodología** | ¿Qué cifras son oficiales, autorreportadas o cálculos editoriales y cómo se reproducen? |

El panorama incorpora además un bloque de **acceso e infraestructura 2025–2027**: gratuidad, nuevos estudiantes de primer ingreso, Educación Superior en tu Colegio y cartera de proyectos de infraestructura, siempre separado de las estadísticas SNIES para evitar mezclar indicadores administrativos con matrícula consolidada.

### Hallazgos que sostiene el dato

- **El sistema crece hacia arriba y se angosta en la base.** Desde 2018 la matrícula universitaria creció 6,8 % y la técnica y tecnológica cayó 28,5 % (112.129 → 80.135), justo la puerta de entrada de los hogares de menores ingresos: 69,8 % de los evaluados Saber TyT vive en estratos 1 y 2.
- **La brecha territorial es la noticia.** Solo 51 de 125 municipios tienen oferta activa. La razón propia de oferta 17-21 va de **87,7 % en el Valle de Aburrá a 1,9 % en el Suroeste** (Antioquia: 54,1 %); mide capacidad instalada, no la cobertura oficial ni la asistencia de residentes.
- **Empleo sí, salarios apretados.** Los tecnólogos se vinculan al empleo formal casi como los universitarios (72,7 % vs. 71,7 %), pero el 42 % gana menos de 1,5 SMMLV.
- **El repunte de 2024 continuó.** Las rendiciones de cuentas 2025-2026 (ITM, TdeA, Pascual Bravo, IU Digital…) reportan matrículas récord, empujadas por la gratuidad.

---

## Estructura

```
scripts/
  descargar_datos.py     # baja TODOS los insumos a data/ (≈500 MB, no versionados)
  preparar_poblacion.py  # extrae población 17-21 por municipio/subregión (DANE)
  procesar.py            # motor: data/ → public/datos.json + public/datos.js
  auditar_atlas.py       # contrasta el atlas publicado contra los XLSX oficiales
  scrapear_ies_distritales.py # captura catálogos y construye el corte de las tres IES del Distrito
public/
  index.html             # tablero completo (HTML+JS vanilla, SVG a mano, sin dependencias)
  ies/                   # perfiles V29 de ITM, Pascual Bravo y Colmayor
  datos.js               # datos agregados (generado — no editar a mano)
  datos.json             # mismo contenido, para reutilizar
  mapa.js                # geometría MGN de los 125 municipios (DANE, vía ArcGIS)
  auditoria.html         # lectura pública de resultados, método y fuentes
  auditoria-cifras.json  # comprobante público de la última auditoría del atlas
  verificacion-v25.json  # controles reproducibles de la Sala Ejecutiva y sus cortes
  verificacion-v26.json  # seis etapas, fórmulas, jurisdicciones y límites de Trayectorias
  comparativo-producto.json # referentes, escala, capacidades, fuentes y adopciones V27
  ies-distritales.json   # corte 2026-1, oferta, matrícula, finanzas, fuentes y límites del capítulo V30
  fuentes-antioquia.json # 13 fuentes y 23 indicadores trazables del registro V31
data/                    # insumos crudos — NO versionados (ver .gitignore)
```

## Reproducir desde cero

```bash
pip install pandas openpyxl pdfplumber      # dependencias
python3 scripts/descargar_datos.py          # ≈500 MB; el archivo del DANE (126 MB) es lento
python3 scripts/preparar_poblacion.py       # población 17-21 por municipio y subregión
python3 scripts/procesar.py                 # regenera public/datos.json y public/datos.js
python3 scripts/auditar_atlas.py            # debe terminar con "estado": "correcto"
python3 scripts/scrapear_ies_distritales.py # refresca catálogos y comprobante distrital
python3 scripts/actualizar_fuentes_antioquia.py # valida y regenera el registro de fuentes vivas
vercel --prod                               # despliegue (prebuilt, sin build step)
```

El tablero es **estático**: `public/index.html` lee `datos.js` y `mapa.js`. Para verlo en local:
`cd public && python3 -m http.server 8137`

### Actualizar con una vigencia nueva del SNIES

Cuando el MEN publique la vigencia siguiente (histórico: hacia julio de cada año):

1. Busque los números de artículo en [Bases consolidadas SNIES](https://snies.mineducacion.gov.co/portal/ESTADISTICAS/Bases-consolidadas/).
2. Agréguelos al diccionario `ARTICULOS` de `scripts/descargar_datos.py`.
3. Extienda `ANIOS` en `scripts/procesar.py` (hoy `range(2018, 2025)`).
4. Corra los tres scripts y redespliegue.

---

## Fuentes

| Fuente | Qué aporta | Corte usado |
|---|---|---|
| **SNIES — MEN** (bases consolidadas) | Matriculados, graduados, inscritos, admitidos, primer curso, docentes | 2018–**2024** (última publicada) |
| **OLE — MEN** (Base IBC) | Vinculación laboral formal y salario de cotización de graduados | **2023** (última publicada) |
| **ICFES** (`iwgf-bkfk`, datos.gov.co + resultados agregados) | Saber TyT: puntajes, inglés y perfil; Saber Pro/TyT agregado para comparación reciente | microdato 2017–**2022**; agregados **2023–2025** |
| **SPADIES — MEN** | Deserción anual y ausencia intersemestral como referencia nacional | **2023**, cierre estadístico 2024 |
| **Observatorio de Trayectorias — MEN** | Graduación acumulada y marco de indicadores de acceso, permanencia y retorno | cohortes hasta **2021** en el documento temático usado |
| **MinCiencias** (PDF Res. 1531/2025 + `hrhc-c4wu`) | Grupos de investigación reconocidos | **Conv. 957 de 2024** (resultados dic-2025) |
| **DANE** (proyecciones CNPV 2018) | Población 17-21 por municipio, para la cobertura | **2024** |
| **DANE — GEIH** | Desempleo Medellín A.M. (8,6 %) | trimestre mar–may **2026** |
| **Gobernación de Antioquia** (`t2ca-uae5`) | Correspondencia municipio ↔ subregión | — |
| **Rendiciones de cuentas de las IES** | Radar institucional (cifras autorreportadas, con enlace) | **2025–2026** |
| **MEN — balance territorial e infraestructura** | Gratuidad, primer ingreso, articulación con colegios y proyectos de infraestructura | **2025–2027** |
| **uniRank + perfiles oficiales** | Audiencia pública y señales observables de gestión en Instagram, Facebook, YouTube, X, TikTok y LinkedIn | **2025–jul. 2026** |
| **Gobernación de Antioquia** | Sistema oficial no certificado, conectividad educativa y Semestre Cero | **abr.–jul. 2026** |
| **Proantioquia** | Alfabetización inicial, inversión privada y perfiles subregionales | datos **2025**, publicados en **2026** |
| **Distrito de Medellín · Sapiencia** | Matrícula, calidad, investigación y beneficios proyectados del sistema público distrital | **2026-1** |
| **Antioquia Cómo Vamos** | Contraste analítico del sistema con bases MEN, DANE, ICFES, SNIES y LEA | informe **2024**, publicado en 2025 |

## Decisiones metodológicas (las trampas de los datos oficiales)

1. **Matrícula anual = semestre pico**, no la suma de semestres (que duplicaría personas). En 2024 el semestre pico de Antioquia es **2024-II: 313.583 matriculados** (2024-I: 300.246). Las vistas de corte territorial, institucional, de oferta y calidad lo rotulan explícitamente como 2024-II. Validado además contra la cifra oficial del MEN: 2.561.707 nacional vs. 2.553.560 publicado (0,3 % de diferencia).
2. **La serie 2015-2017 de la base histórica (`5wck-szir`) se descartó**: el reporte semestral es inconsistente (S2 colapsado). La serie arranca en 2018 desde los XLSX.
3. **OLE se restringe a IES con domicilio en Antioquia** — se excluyen SENA y UNAD, de alcance nacional y no separables por departamento en esa base. La Especialización se omite de la tasa de vinculación por cobertura insuficiente (169 de 8.391).
4. **El sector de cada IES se toma del SNIES**, no del ICFES, que tiene errores de registro (marcaba la IU Digital como privada).
5. **La razón de oferta no es cobertura ni asistencia**: matrícula de pregrado ofertada en la subregión / población 17-21 residente. Por eso las subregiones que atraen estudiantes de fuera pueden superar el 100 %. La interfaz la identifica como cálculo propio y no como tasa oficial.
6. **El listado de grupos de MinCiencias es un PDF sin departamento**: se asigna por código GrupLAC contra la base histórica (90 % de cobertura) y, para grupos nuevos, por institución avaladora antioqueña.
7. **El radar institucional es autorreportado**: cortes y definiciones propias de cada IES, no comparables 1:1 con el SNIES. Cada cifra enlaza a su fuente.
8. Saber TyT usa la escala 0–200 vigente desde 2017-3; los rótulos MCER históricos (A-, -A1, Pre-A1, B+) se homologan a la escala actual. El puntaje por municipio solo se reporta con 50+ evaluados.
9. **Seguidores no son alcance**: el capítulo de redes sociales suma audiencias públicas sin deduplicar y calcula un índice editorial sobre señales observables. El alcance único, las impresiones, la retención, el crecimiento y las conversiones requieren exportaciones privadas de cada plataforma. Datos y fórmula: `public/redes-sociales.json`.
10. **Trayectorias no es un embudo longitudinal**: inscripciones y primer curso son registros SNIES 2024; Saber Pro corresponde a evaluados 2025; OLE observa cotización formal de graduados 2022; permanencia y graduación son referencias nacionales. Cada etapa conserva universo, jurisdicción y corte, y nunca se multiplican sus porcentajes.
11. **El comparativo de producto no es un ranking**: observa capacidades públicas al 15 de julio de 2026 con una escala editorial de 0 a 3, pero no suma puntos. “No observada” significa que no apareció en las fuentes públicas revisadas, no que una funcionalidad privada sea imposible.
12. **El sistema distrital tiene cinco universos**: el Plan Indicativo consolida matrícula e indicadores al 28 de febrero de 2026; la convocatoria 2026-2 informa programas y cupos abiertos; los catálogos web muestran páginas visibles; el SNIES 2024 permite la comparación homogénea; los estados financieros tienen cortes propios. Programa acreditado vigente, entrada web y registro SNIES no son sinónimos. La variación frente a 2025-2 es semestral, no anual. Presupuesto, recaudo y resultado contable tampoco se restan entre sí.
13. **Actualidad no significa comparabilidad**: V31 conserva SNIES 2024-II como último corte comparable disponible al 15 de julio de 2026 y presenta los datos 2025–2026 como señales administrativas, de programa o de contexto. Beneficios, participantes, matrícula, sedes, inversión y resultados no se suman ni se usan como sinónimos.

### Fuentes vivas V31

- **13 fuentes revisadas**: nueve oficiales y cuatro observatorios o centros de análisis reconocidos.
- **23 indicadores sistematizados**: 14 publicaciones directas, cuatro cálculos reproducibles y cinco cifras reportadas.
- **Metadatos obligatorios**: cada cifra declara periodo, nivel, tema, territorio, universo, fuente, uso para decisiones y limitación.
- **Validación automática**: cero identificadores duplicados, referencias rotas dentro del registro, universos faltantes o cautelas vacías.
- **Próximo hito**: SNIES prevé publicar la vigencia 2025 entre el 27 y el 31 de julio de 2026; el registro no anticipa esos resultados.
- **Reproducción**: `python3 scripts/actualizar_fuentes_antioquia.py` genera `public/fuentes-antioquia.json`.

### Sistema público distrital V30

- **46.489 estudiantes en 2026-1**: ITM 29.822, Pascual Bravo 10.068 y Colmayor 6.599, según el Seguimiento al Plan Indicativo con corte al 28 de febrero.
- **40 programas acreditados vigentes**, 21 grupos de investigación A1/A/B y 51 publicaciones indexadas en el reporte distrital.
- **44 programas articulados con media técnica**, 30 de Formación para el Trabajo y 21 ofertas pertinentes en comunas y corregimientos.
- **163 semilleros activos con 4.969 estudiantes vinculados**: ITM 2.391, Pascual Bravo 1.968 y Colmayor 610.
- **46.667 beneficios de Matrícula Cero proyectados para 2026-1**, con más de $37.000 millones para ocho IES públicas; no equivalen a estudiantes adicionales ni a beneficios ejecutados.
- **Al menos 12.216 cupos para 2026-2**: 8.600 en ITM, más de 1.600 en Pascual y 2.016 en Colmayor.
- **138 registros comparables SNIES 2024**: 98 de pregrado y 40 de posgrado, con explorador por IES, nivel, modalidad, área y acreditación.
- **$540.680 millones de presupuesto aprobado para 2026**, con presupuesto, recaudo y resultado contable presentados como magnitudes distintas.
- **Agenda común**: portafolio articulado, cupos por programa y jornada, seguimiento de cohortes, resultados laborales y sostenibilidad por fuente de ingreso.

### Perfiles institucionales V29

- **Tres páginas conectadas** desde el capítulo distrital: ITM, Pascual Bravo y Colmayor.
- **Una arquitectura comparable**: lectura ejecutiva, composición de oferta, explorador SNIES, catálogo web, finanzas y agenda de decisiones.
- **Una sola fuente de verdad**: los perfiles cargan `public/ies-distritales.json`; no duplican cifras manualmente.

### Mejoras V27 tomadas de referentes

- **Discover Uni:** selección persistente de hasta seis programas y memoria de la comparación institucional.
- **College Scorecard:** enlaces compartibles y briefs que reúnen resultados, fuente y límites.
- **OTE–MEN:** trayectorias organizadas por etapas sin simular una cohorte única.
- **Our World in Data:** datos reutilizables, metadatos y fuente pública junto a la visualización.
- **Mi Futuro:** costo y retorno se tratan como una pareja; MaterIA publica el vacío de costo neto en vez de estimarlo sin una base comparable.

## Ruta de potenciación

- **Actualización SNIES 2025** entre el 27 y el 31 de julio de 2026, según el cronograma oficial del MEN.
- **Modo decisión** que combine territorio, costo, modalidad, calidad y resultados laborales sin producir un ranking absoluto.
- **Asistente explicable** sobre el corpus publicado: toda respuesta deberá mostrar fuente, corte, cálculo y limitación, sin perfilar estudiantes.
- **Alertas de frescura** para detectar nuevas bases, resoluciones de acreditación y cambios en informes institucionales.
- **Permanencia departamental**: incorporar cohortes SPADIES/OTE de Antioquia por IES, nivel y modalidad cuando exista una extracción pública reproducible; hasta entonces, mantener los valores nacionales únicamente como referencia.
- **Costo neto y resultado de apoyos**: vincular gratuidad, becas y fondos con continuidad y graduación mediante datos gobernados, sin perfilar ni automatizar decisiones sobre estudiantes.
- **Demanda laboral por vacantes**: integrar el Servicio Público de Empleo si publica una base abierta; mientras tanto, mantener GEIH y OLE como fuentes comparables.

---

© 2026 · Santiago Jiménez Londoño


## Scripts de análisis adicionales

- `scripts/benchmark_deptos.py` — matrícula por departamento (semestre pico) desde las bases SNIES nacionales → benchmark interdepartamental indexado 2018=100.
- `scripts/proyeccion_demografica.py` — población 17-21 por subregión 2018-2042 (proyecciones municipales DANE CNPV-2018) → «el impuesto demográfico».
- `scripts/oferta_demanda.py` — demanda revelada por área (inscritos 2018 vs 2024), aspirantes por silla y salario típico de enganche (bandas OLE 2023).
