#!/usr/bin/env python3
"""Genera los dos mapas del deck /presentacion desde la geometría oficial.

Fuente: public/mapa.js (MGN del DANE vía ArcGIS REST, la misma que usa el mapa
del sitio). Aquí se reproyecta a coordenadas SVG, se simplifica con
Douglas-Peucker —a la escala de una lámina proyectada nadie distingue un vértice
cada 400 metros— y se escribe el resultado dentro de public/presentacion.html,
entre los marcadores MAPAS_INICIO / MAPAS_FIN.

Salen dos mapas:
  · ant — los 125 municipios de Antioquia, para ubicar la subregión.
  · bc  — los 6 municipios del Bajo Cauca, con centroide para rotular.

Uso: python3 scripts/mapa_presentacion.py
"""
import json
import math
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GEO = RAIZ / "public" / "mapa.js"
DECK = RAIZ / "public" / "presentacion.html"

BAJO_CAUCA = {
    "05154": "Caucasia",
    "05250": "El Bagre",
    "05120": "Cáceres",
    "05790": "Tarazá",
    "05895": "Zaragoza",
    "05495": "Nechí",
}

# Tolerancias en grados. El mapa departamental se ve a un tercio de lámina y
# admite mucha más simplificación que el subregional, que ocupa media lámina.
TOL_ANT = 0.0075
TOL_BC = 0.0016


def cargar_geo():
    txt = GEO.read_text(encoding="utf-8")
    inicio = txt.index("{")
    fin = txt.rindex("}") + 1
    return json.loads(txt[inicio:fin])


def anillos(feature):
    """Devuelve la lista de anillos exteriores, sea Polygon o MultiPolygon."""
    g = feature["geometry"]
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    return [poly[0] for poly in g["coordinates"]]


def dp(pts, tol):
    """Douglas-Peucker iterativo: conserva la silueta y bota los vértices que
    no cambian la lectura del contorno."""
    if len(pts) < 3:
        return pts
    guardar = [False] * len(pts)
    guardar[0] = guardar[-1] = True
    pila = [(0, len(pts) - 1)]
    while pila:
        ini, fin = pila.pop()
        if fin <= ini + 1:
            continue
        ax, ay = pts[ini]
        bx, by = pts[fin]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        peor, idx = 0.0, ini
        for i in range(ini + 1, fin):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > peor:
                peor, idx = d, i
        if peor > tol:
            guardar[idx] = True
            pila.append((ini, idx))
            pila.append((idx, fin))
    return [p for p, g in zip(pts, guardar) if g]


def dp_anillo(pts, tol):
    """Douglas-Peucker sobre un anillo cerrado.

    Aplicado directamente, el primer segmento va del punto inicial a sí mismo:
    la línea base es degenerada, todas las distancias dan cero y el polígono se
    reduce a dos vértices. Se parte el anillo en el punto más lejano al inicial
    y se simplifica cada mitad como una polilínea abierta.
    """
    if len(pts) < 4:
        return pts
    aro = pts[:-1] if pts[0] == pts[-1] else pts[:]
    if len(aro) < 4:
        return pts
    ax, ay = aro[0]
    lejos = max(range(1, len(aro)), key=lambda i: (aro[i][0] - ax) ** 2 + (aro[i][1] - ay) ** 2)
    a = dp(aro[: lejos + 1], tol)
    b = dp(aro[lejos:] + [aro[0]], tol)
    return a[:-1] + b[:-1]


def area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def centroide(pts):
    """Centroide del polígono (no del promedio de vértices, que se sesga hacia
    los tramos con más detalle)."""
    cx = cy = a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        cruz = x1 * y2 - x2 * y1
        a += cruz
        cx += (x1 + x2) * cruz
        cy += (y1 + y2) * cruz
    if abs(a) < 1e-12:
        return pts[0]
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


def construir(features, tol, ancho, con_centroide=False):
    """Reproyecta, simplifica y escala. La longitud se corrige por el coseno de
    la latitud media para que el departamento no salga achatado."""
    lats = [p[1] for f in features for r in anillos(f) for p in r]
    lons = [p[0] for f in features for r in anillos(f) for p in r]
    lat0 = math.radians(sum(lats) / len(lats))
    k = math.cos(lat0)

    def proy(p):
        return (p[0] * k, -p[1])

    x0 = min(lons) * k
    x1 = max(lons) * k
    y0 = -max(lats)
    y1 = -min(lats)
    esc = ancho / (x1 - x0)
    alto = round((y1 - y0) * esc, 1)

    salida = []
    for f in features:
        rings = []
        for r in anillos(f):
            r = dp_anillo(r, tol)
            if len(r) < 4 or area(r) < tol * tol * 4:
                continue
            rings.append(r)
        if not rings:
            continue
        d = []
        for r in rings:
            pl = []
            for p in r:
                px, py = proy(p)
                pl.append(f"{(px - x0) * esc:.1f},{(py - y0) * esc:.1f}")
            d.append("M" + "L".join(pl) + "Z")
        item = {
            "c": f["properties"]["c"],
            "n": f["properties"]["n"],
            "d": "".join(d),
        }
        if con_centroide:
            mayor = max(rings, key=area)
            cx, cy = centroide([proy(p) for p in mayor])
            item["x"] = round((cx - x0) * esc, 1)
            item["y"] = round((cy - y0) * esc, 1)
        salida.append(item)
    return {"vb": f"0 0 {ancho} {alto}", "p": salida}


def main():
    geo = cargar_geo()
    feats = geo["features"]
    ant = construir(feats, TOL_ANT, 460)
    bc_feats = [f for f in feats if f["properties"]["c"] in BAJO_CAUCA]
    faltan = BAJO_CAUCA.keys() - {f["properties"]["c"] for f in bc_feats}
    if faltan:
        raise SystemExit(f"faltan municipios en la geometría: {faltan}")
    bc = construir(bc_feats, TOL_BC, 520, con_centroide=True)

    blob = json.dumps({"ant": ant, "bc": bc}, ensure_ascii=False, separators=(",", ":"))
    html = DECK.read_text(encoding="utf-8")
    nuevo = re.sub(
        r"/\* MAPAS_INICIO \*/.*?/\* MAPAS_FIN \*/",
        "/* MAPAS_INICIO */window.DECK_MAPAS=" + blob + ";/* MAPAS_FIN */",
        html,
        flags=re.S,
    )
    if nuevo == html:
        raise SystemExit("no se encontraron los marcadores MAPAS_INICIO/MAPAS_FIN")
    DECK.write_text(nuevo, encoding="utf-8")
    print(f"Antioquia: {len(ant['p'])} municipios · viewBox {ant['vb']}")
    print(f"Bajo Cauca: {len(bc['p'])} municipios · viewBox {bc['vb']}")
    print(f"geometría embebida: {len(blob)/1024:.1f} KB")


if __name__ == "__main__":
    main()
