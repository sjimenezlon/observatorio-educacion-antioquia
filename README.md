# MaterIA Gris · El cerebro de datos de la educación superior de Antioquia

**https://materia-gris.vercel.app** (antes «Observatorio de Educación Superior de Antioquia»; la URL vieja sigue activa como espejo).

Tablero de la educación superior del departamento de Antioquia — **pregrado y posgrado, pública y privada** — con lente de detalle sobre la formación técnica y tecnológica (TyT).

**En línea:** https://materia-gris.vercel.app
**Espejo:** https://observatorio-educacion-antioquia.vercel.app
**Autor:** Santiago Jiménez Londoño · Última versión: V21 (julio de 2026)

---

## Qué responde

| Sección | Pregunta que contesta |
|---|---|
| **Panorama** | ¿Cómo evolucionó la matrícula 2018-2024 por nivel, sector y modalidad? |
| **Instituciones** | ¿Quién forma a Antioquia? 73 IES, comparador de hasta 3, docentes y radar de cifras 2025-2026 autorreportadas |
| **Territorio** | ¿Dónde llega la oferta? Mapa municipal interactivo y comparador sincronizado de razón de oferta, presencia municipal y peso TyT |
| **Oferta** | ¿Qué se puede estudiar? 2.107 programas con explorador filtrable |
| **Mercado laboral** | ¿Cómo les va a los graduados? Demanda, embudo, vinculación formal y salario de enganche por nivel y área |
| **Calidad** | Acreditación de alta calidad, Saber TyT vs. nacional (y por municipio), bilingüismo (MCER) |
| **Innovación** | 815 grupos de investigación reconocidos (Conv. 957 de 2024) |
| **Impacto social** | ¿Quiénes estudian? Estrato, trabajo, educación de la madre, brecha de género y STEM |

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
public/
  index.html             # tablero completo (HTML+JS vanilla, SVG a mano, sin dependencias)
  datos.js               # datos agregados (generado — no editar a mano)
  datos.json             # mismo contenido, para reutilizar
  mapa.js                # geometría MGN de los 125 municipios (DANE, vía ArcGIS)
  auditoria.html         # lectura pública de resultados, método y fuentes
  auditoria-cifras.json  # comprobante público de la última auditoría del atlas
data/                    # insumos crudos — NO versionados (ver .gitignore)
```

## Reproducir desde cero

```bash
pip install pandas openpyxl pdfplumber      # dependencias
python3 scripts/descargar_datos.py          # ≈500 MB; el archivo del DANE (126 MB) es lento
python3 scripts/preparar_poblacion.py       # población 17-21 por municipio y subregión
python3 scripts/procesar.py                 # regenera public/datos.json y public/datos.js
python3 scripts/auditar_atlas.py            # debe terminar con "estado": "correcto"
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
| **ICFES** (`iwgf-bkfk`, datos.gov.co) | Saber TyT: puntajes, niveles MCER de inglés, perfil socioeconómico | 2017–**2022** (hasta donde llega el microdato abierto) |
| **MinCiencias** (PDF Res. 1531/2025 + `hrhc-c4wu`) | Grupos de investigación reconocidos | **Conv. 957 de 2024** (resultados dic-2025) |
| **DANE** (proyecciones CNPV 2018) | Población 17-21 por municipio, para la cobertura | **2024** |
| **DANE — GEIH** | Desempleo Medellín A.M. (8,6 %) | trimestre mar–may **2026** |
| **Gobernación de Antioquia** (`t2ca-uae5`) | Correspondencia municipio ↔ subregión | — |
| **Rendiciones de cuentas de las IES** | Radar institucional (cifras autorreportadas, con enlace) | **2025–2026** |
| **MEN — balance territorial e infraestructura** | Gratuidad, primer ingreso, articulación con colegios y proyectos de infraestructura | **2025–2027** |
| **uniRank + perfiles oficiales** | Audiencia pública y señales observables de gestión en Instagram, Facebook, YouTube, X, TikTok y LinkedIn | **2025–jul. 2026** |

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

## Pendientes / ideas para la próxima versión

- **Saber Pro** (nivel universitario): no está completo como microdato abierto en datos.gov.co; habría que traerlo desde DataIcfes.
- **Deserción (SPADIES)**: no hay dataset abierto; requiere consulta directa al MEN.
- **Demanda laboral por vacantes**: no existe dataset del Servicio Público de Empleo en datos abiertos; alternativa es GEIH.
- Bases SNIES 2025 cuando el MEN las publique.

---

© 2026 · Santiago Jiménez Londoño


## Scripts de análisis adicionales

- `scripts/benchmark_deptos.py` — matrícula por departamento (semestre pico) desde las bases SNIES nacionales → benchmark interdepartamental indexado 2018=100.
- `scripts/proyeccion_demografica.py` — población 17-21 por subregión 2018-2042 (proyecciones municipales DANE CNPV-2018) → «el impuesto demográfico».
- `scripts/oferta_demanda.py` — demanda revelada por área (inscritos 2018 vs 2024), aspirantes por silla y salario típico de enganche (bandas OLE 2023).
