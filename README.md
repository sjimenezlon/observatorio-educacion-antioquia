# Observatorio de Educación Superior de Antioquia

Observatorio de la educación superior del departamento de Antioquia — pregrado y posgrado, pública y privada — con lente de detalle sobre la formación técnica y tecnológica (TyT).

**Autor:** Santiago Jiménez Londoño · 2026

## Qué mide

- **Panorama** — matrícula 2018-2024 por nivel de formación, sector y modalidad (SNIES, semestre pico).
- **Instituciones** — 73 IES con oferta en el departamento: tamaño, mezcla de niveles, acreditación, docentes.
- **Territorio** — 51 municipios con oferta activa; concentración en Medellín.
- **Oferta** — 2.107 programas activos, explorador con filtros por nivel/área/sector/modalidad/municipio.
- **Mercado laboral** — embudo de acceso, graduados por nivel, vinculación formal y salario de enganche (OLE 2023).
- **Calidad** — acreditación de alta calidad por nivel y resultados Saber TyT (Antioquia vs. nacional).
- **Innovación** — 834 grupos de investigación reconocidos (MinCiencias, Conv. 894/2021).
- **Impacto social** — perfil socioeconómico de los evaluados Saber TyT (estrato, trabajo, educación de la madre).

## Fuentes

Bases consolidadas SNIES (MEN) 2018-2024 · OLE base IBC 2023 · ICFES Saber TyT (datos.gov.co `iwgf-bkfk`) · MinCiencias grupos reconocidos (`hrhc-c4wu`).

## Reproducir

```bash
python3 scripts/procesar.py   # regenera public/datos.json y public/datos.js desde data/
```

Los insumos crudos (XLSX del SNIES/OLE y CSV del ICFES, ~250 MB) no se versionan; ver rutas de descarga en `scripts/procesar.py`.
