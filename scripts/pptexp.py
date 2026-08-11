#!/usr/bin/env python3
"""Genera public/pptexp.html, la versión ejecutiva del deck.

La versión corta comparte con /presentacion todo el envoltorio —estilos, motor
de navegación, índice, notas del expositor, gráficas y mapas— y solo cambia las
láminas. En vez de duplicar ese envoltorio (que se desalinearía a la primera
edición), este script lo recorta de public/presentacion.html y le inserta las
secciones de scripts/pptexp_laminas.html.

Los ayudantes de gráficas y mapas del motor compartido salen sin hacer nada
cuando su contenedor no existe, así que la versión corta puede usar solo los
que necesite.

Uso: python3 scripts/pptexp.py   (correr después de scripts/mapa_presentacion.py)
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LARGO = RAIZ / "public" / "presentacion.html"
LAMINAS = Path(__file__).resolve().parent / "pptexp_laminas.html"
SALIDA = RAIZ / "public" / "pptexp.html"

ABRE = '<main id="escenario">'
CIERRA = "</main>"

# El encabezado cambia: título, descripción, canonical y og. Todo lo demás
# —incluida la hoja de estilo completa— se hereda tal cual.
CAMBIOS_CABEZA = [
    (
        "<title>IA para transformar el territorio · Educación superior como una oportunidad de oro</title>",
        "<title>IA para transformar el territorio · Versión ejecutiva</title>",
    ),
    (
        'content="https://materia-gris.vercel.app/presentacion"',
        'content="https://materia-gris.vercel.app/pptexp"',
    ),
    (
        'href="https://materia-gris.vercel.app/presentacion"',
        'href="https://materia-gris.vercel.app/pptexp"',
    ),
    (
        'content="IA para transformar el territorio · Educación superior como una oportunidad de oro"',
        'content="IA para transformar el territorio · Versión ejecutiva"',
    ),
    (
        'content="Conferencia: la educación superior como motor de desarrollo — lectura global, regional, colombiana, antioqueña y del Bajo Cauca — y el papel de la inteligencia artificial para cerrar la brecha técnica y de conocimiento. Santiago Jiménez Londoño, Universidad EAFIT.">',
        'content="Versión ejecutiva: por qué apostarle a la educación superior en el Bajo Cauca — complejidad económica, evidencia de qué funciona, modelos probados y recursos disponibles. Santiago Jiménez Londoño, Universidad EAFIT.">',
    ),
    (
        'content="Del dato global al Bajo Cauca: por qué la educación superior sigue siendo la mejor apuesta de desarrollo y cómo la IA ayuda a cerrar la brecha.">',
        'content="Veinte láminas estratégicas: por qué la educación superior es la mejor apuesta productiva del Bajo Cauca, y con qué recursos empezar hoy.">',
    ),
]


def main():
    largo = LARGO.read_text(encoding="utf-8")
    i, j = largo.index(ABRE) + len(ABRE), largo.rindex(CIERRA)
    cabeza, cola = largo[:i], largo[j:]

    for viejo, nuevo in CAMBIOS_CABEZA:
        if viejo not in cabeza:
            raise SystemExit(f"no se encontró en el encabezado: {viejo[:60]}…")
        cabeza = cabeza.replace(viejo, nuevo)

    laminas = LAMINAS.read_text(encoding="utf-8")
    SALIDA.write_text(cabeza + "\n" + laminas + "\n" + cola, encoding="utf-8")

    n = len(re.findall(r'<section class="lam', laminas))
    print(f"pptexp.html generado · {n} láminas · {SALIDA.stat().st_size/1024:.0f} KB")
    largo_n = len(re.findall(r'<section class="lam', largo))
    print(f"(la versión completa tiene {largo_n})")


if __name__ == "__main__":
    main()
