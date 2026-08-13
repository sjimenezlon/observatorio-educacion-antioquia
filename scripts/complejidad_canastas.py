#!/usr/bin/env python3
"""Baja del Atlas of Economic Complexity las canastas exportadoras de dos países
y las escribe embebidas en public/presentacion.html entre los marcadores
CANASTAS_INICIO / CANASTAS_FIN.

Uso:
  python3 scripts/complejidad_canastas.py            # baja y escribe
  python3 scripts/complejidad_canastas.py --dry-run  # solo informa

El Atlas expone un GraphQL público en /api/graphql (la web es una SPA: leerla con
WebFetch devuelve «Loading…», pero la API responde JSON sin autenticación).

⚠️ CLASIFICACIÓN: los perfiles de país del Atlas usan **HS12**, no HS92. Es la
única que reproduce los ECI que muestra la ficha —Corea 1,56 y Colombia 0,24 en
2024— y el puesto 4.º de Corea. Con HS92 dan 1,60 y 0,23.

⚠️ El sector 10 («Other») son las dos partidas basura del Atlas —«Trade data
discrepancies» y «Commodities not specified according to kind»—: la ficha las
excluye del treemap y aquí también. En Colombia pesan 4 % de las exportaciones,
así que dejarlas dentro desplazaría todas las proporciones.
"""
import argparse
import json
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DESTINO = ROOT / "public" / "presentacion.html"

API = "https://atlas.hks.harvard.edu/api/graphql"
CLASE = "HS12"
ANIO = 2024

PAISES = [
    # clave, countryId del Atlas, nombre, puesto en el ranking del ECI
    ("kor", 410, "Corea del Sur", 4),
    ("col", 170, "Colombia", 68),
]
PAISES_TOTAL_RANKING = 145

# El Atlas nombra los sectores en inglés en la API; estos son los rótulos del deck.
SECTORES = {
    "1": "Textiles",
    "2": "Agro y alimentos",
    "3": "Piedra y metales preciosos",
    "4": "Minerales",
    "5": "Metales",
    "6": "Química",
    "7": "Vehículos",
    "8": "Maquinaria",
    "9": "Electrónica",
    "services": "Servicios",
}
SECTOR_BASURA = "10"

# Un producto se dibuja solo si pesa al menos esto; el resto se acumula en un
# bloque «otros» dentro de su sector para que el área del sector no se deforme.
PISO = 0.0004  # 0,04 % de la canasta

# Cortes de PCI de la escala divergente: (-∞,-2) (-2,-1) (-1,0) (0,1) (1,+∞).
BANDAS = [-2, -1, 0, 1, float("inf")]

# ⚠️ HS12 no trae nombres en español en la API: los 1.231 vienen solo en inglés.
# HS92 sí los trae, y a cuatro dígitos las dos nomenclaturas comparten código en
# 1.209 de 1.231 partidas, así que el nombre en español se toma de HS92 por código.
# ALIAS cubre lo que queda —los servicios, las partidas que HS12 estrenó y los
# nombres que en una lámina proyectada quedan mejor cortos—.
ALIAS = {
    "travel": "Turismo y viajes",
    "transport": "Transporte",
    "ict": "Servicios a empresas",
    "financial": "Servicios financieros",
    "insurance": "Seguros",
    "0308": "Invertebrados acuáticos",
    "2852": "Compuestos de mercurio",
    "2853": "Otros compuestos inorgánicos",
    "3824": "Productos químicos n.c.p.",
    "3825": "Residuos de la industria química",
    "3826": "Biodiésel",
    "4112": "Cuero de ovino",
    "4113": "Cuero de caprino y otros",
    "4114": "Cuero agamuzado y charol",
    "4115": "Cuero regenerado y recortes",
    "6003": "Tejidos de punto estrechos",
    "6004": "Tejidos de punto elásticos",
    "6005": "Tejidos de punto por urdimbre",
    "6006": "Otros tejidos de punto",
    "8486": "Máquinas para semiconductores",
    "8487": "Partes de máquinas n.c.p.",
    "9619": "Compresas y pañales",
    "2709": "Petróleo crudo",
    "2710": "Derivados del petróleo",
    "8542": "Circuitos integrados",
    "8708": "Partes de vehículos",
    "8703": "Carros",
    "2701": "Carbón",
    "0901": "Café sin tostar",
    "0603": "Flores cortadas",
}


def consulta(query):
    respuesta = requests.post(API, json={"query": query}, timeout=120)
    respuesta.raise_for_status()
    cuerpo = respuesta.json()
    if "errors" in cuerpo:
        raise SystemExit("el Atlas devolvió errores: %s" % cuerpo["errors"])
    return cuerpo["data"]


def bajar():
    productos = consulta(
        "{productHs12(productLevel:4,servicesClass:unilateral){"
        "productId code nameShortEn topParent{code}}}"
    )["productHs12"]
    espanol = {
        p["code"]: p["nameShortEs"]
        for p in consulta(
            "{productHs92(productLevel:4,servicesClass:unilateral){code nameShortEs}}"
        )["productHs92"]
        if p["nameShortEs"]
    }
    pci = consulta(
        "{productYear(productClass:%s,servicesClass:unilateral,productLevel:4,"
        "yearMin:%d,yearMax:%d){productId pci}}" % (CLASE, ANIO, ANIO)
    )["productYear"]
    return (
        {p["productId"]: p for p in productos},
        espanol,
        {r["productId"]: r["pci"] for r in pci},
    )


def canasta(country_id, productos, espanol, pci, sin_traducir):
    filas = consulta(
        "{countryProductYear(countryId:%d,productClass:%s,servicesClass:unilateral,"
        "productLevel:4,yearMin:%d,yearMax:%d){productId exportValue}}"
        % (country_id, CLASE, ANIO, ANIO)
    )["countryProductYear"]

    limpias = []
    for fila in filas:
        producto = productos.get(fila["productId"])
        valor = fila["exportValue"] or 0
        if not producto or valor <= 0:
            continue
        sector = (producto["topParent"] or {}).get("code")
        if sector == SECTOR_BASURA or sector not in SECTORES:
            continue
        limpias.append((producto, valor, sector))

    total = sum(v for _, v, _ in limpias)

    # Reparto de TODA la canasta por banda de complejidad (no solo de lo que se
    # dibuja): es la cifra que sostiene el argumento de la lámina.
    bandas = [0.0] * len(BANDAS)
    suma_pci = 0.0
    con_pci = 0.0
    for producto, valor, _ in limpias:
        complejidad = pci.get(producto["productId"])
        if complejidad is None:
            continue
        suma_pci += complejidad * valor
        con_pci += valor
        for i, corte in enumerate(BANDAS):
            if complejidad < corte or i == len(BANDAS) - 1:
                bandas[i] += valor
                break

    por_sector = {}
    for producto, valor, sector in limpias:
        por_sector.setdefault(sector, {"v": 0.0, "p": [], "resto": 0.0, "n": 0})
        bloque = por_sector[sector]
        bloque["v"] += valor
        bloque["n"] += 1
        complejidad = pci.get(producto["productId"])
        # Un puñado de partidas residuales del Atlas no tienen PCI calculado; sin
        # complejidad no dicen nada en esta lámina, así que engordan el «otros».
        if valor / total >= PISO and complejidad is not None:
            codigo = producto["code"]
            nombre = ALIAS.get(codigo) or espanol.get(codigo)
            if not nombre:
                nombre = producto["nameShortEn"]
                sin_traducir.add(codigo + " · " + nombre)
            bloque["p"].append([nombre, round(valor / 1e6, 1), round(complejidad, 3)])
        else:
            bloque["resto"] += valor

    salida = []
    for sector, bloque in sorted(por_sector.items(), key=lambda t: -t[1]["v"]):
        bloque["p"].sort(key=lambda p: -p[1])
        if bloque["resto"] / total >= 0.0002:
            bloque["p"].append(["Otros productos", round(bloque["resto"] / 1e6, 1), None])
        salida.append(
            {
                "s": SECTORES[sector],
                "v": round(bloque["v"] / 1e6, 1),
                "n": bloque["n"],
                "p": bloque["p"],
            }
        )
    resumen = {
        "bandas": [round(100 * b / con_pci, 1) for b in bandas],
        "pciProm": round(suma_pci / con_pci, 2),
    }
    return total, salida, resumen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    productos, espanol, pci = bajar()
    sin_traducir = set()
    eci = {}
    for _, country_id, _, _ in PAISES:
        eci[country_id] = consulta(
            "{countryYear(countryId:%d,productClass:%s,servicesClass:unilateral,"
            "yearMin:%d,yearMax:%d){eci exportValue}}" % (country_id, CLASE, ANIO, ANIO)
        )["countryYear"][0]

    blob = {"anio": ANIO, "clase": CLASE, "deN": PAISES_TOTAL_RANKING, "paises": []}
    for clave, country_id, nombre, puesto in PAISES:
        total, sectores, resumen = canasta(country_id, productos, espanol, pci, sin_traducir)
        blob["paises"].append(
            {
                "k": clave,
                "n": nombre,
                # El Atlas trunca el ECI a dos decimales en la ficha (0,2451 → 0,24;
                # 1,5611 → 1,56): redondeando no cuadraría con lo que se ve en pantalla.
                "eci": int(eci[country_id]["eci"] * 100) / 100,
                "puesto": puesto,
                "total": round(total / 1e9, 1),
                "bandas": resumen["bandas"],
                "pciProm": resumen["pciProm"],
                "sec": sectores,
            }
        )
        dibujados = sum(len(s["p"]) for s in sectores)
        print(
            "%-14s US$%6.1f mil M · ECI %5.2f · PCI medio %5.2f · %d sectores · %d bloques"
            % (nombre, total / 1e9, eci[country_id]["eci"], resumen["pciProm"], len(sectores), dibujados)
        )
        print(
            "    canasta por banda de PCI  <-2: %.1f %% · -2a-1: %.1f %% · -1a0: %.1f %% · 0a1: %.1f %% · >1: %.1f %%"
            % tuple(resumen["bandas"])
        )
        for s in sectores[:4]:
            print("    %-26s %5.1f %%  (%d partidas)" % (s["s"], 100 * s["v"] * 1e6 / total, s["n"]))

    if sin_traducir:
        print("\n⚠️ partidas dibujadas sin nombre en español (agregar a ALIAS):")
        for x in sorted(sin_traducir):
            print("    " + x)

    if args.dry_run:
        return

    texto = DESTINO.read_text(encoding="utf-8")
    compacto = json.dumps(blob, ensure_ascii=False, separators=(",", ":"))
    nuevo, cuantos = re.subn(
        r"/\* CANASTAS_INICIO \*/.*?/\* CANASTAS_FIN \*/",
        lambda _: "/* CANASTAS_INICIO */window.DECK_CANASTAS=" + compacto + ";/* CANASTAS_FIN */",
        texto,
        flags=re.S,
    )
    if not cuantos:
        raise SystemExit("no se encontraron los marcadores CANASTAS_INICIO/CANASTAS_FIN")
    DESTINO.write_text(nuevo, encoding="utf-8")
    print("escrito en %s (%.1f KB)" % (DESTINO, len(compacto) / 1024))


if __name__ == "__main__":
    main()
