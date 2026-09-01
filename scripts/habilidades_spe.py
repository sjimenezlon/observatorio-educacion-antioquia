#!/usr/bin/env python3
"""Habilidades que las empresas piden en Antioquia (Servicio Público de Empleo).

Traduce el rastreo de vacantes del SPE —`~/Habilidades Antioquia/`, donde se
descargan y clasifican los avisos— al JSON que consume el capítulo «Habilidades»
de MaterIA Gris. El rastreo hace el trabajo pesado (paginar el API, limpiar los
textos, aplicar el léxico de 69 habilidades); aquí sólo se selecciona, se
homologa contra los niveles del SNIES y se calculan las medidas del capítulo.

Dos cálculos propios que no vienen del rastreo:

1. **El plano frecuencia × pago.** Se grafican las 15 habilidades más pedidas
   unidas a las 15 mejor pagadas, entre las que aparecen en al menos el 0,4 %
   de las vacantes. La correlación de Pearson entre el logaritmo de la
   frecuencia y el porcentaje que supera los $3 millones se calcula sobre
   TODAS las habilidades elegibles, no sobre las 28 dibujadas: seleccionarlas
   por los extremos de los dos ejes fuerza la correlación (−0,87 contra −0,51),
   así que el número de las 28 mediría la regla de selección, no el mercado.

2. **El puente con la matrícula.** El nivel educativo que declara el empleador
   se homologa a los niveles del SNIES y se compara la distribución de las
   vacantes que exigen educación superior contra la distribución de la
   matrícula del departamento. Las dos series se normalizan sobre el mismo
   universo (sólo educación superior) para que la comparación sea legítima.

Fuente del rastreo: SPE, API pública buscadordeempleo.gov.co/backbue.
Fuente de la matrícula: `public/datos.json` (SNIES, semestre pico de la vigencia).

Salida: public/habilidades.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
RASTREO = Path.home() / "Habilidades Antioquia" / "data" / "hallazgos.json"

# --- constantes de corte (cambiar aquí para un corte nuevo, no en el JSON) ---
AS_OF = "2026-09-01"
UMBRAL_ALTO = 3_000_000          # el SPE publica bandas: la mediana no discrimina
PISO_PLANO = 0.4                 # % mínimo de vacantes para entrar al plano
TOP_PLANO = 15                   # 15 más pedidas ∪ 15 mejor pagadas
URL_FUENTE = "https://www.serviciodeempleo.gov.co/"

AMBITOS = ["antioquia", "amva", "resto_antioquia", "colombia"]

# El empleador declara el nivel con las etiquetas del SPE (con sus erratas de
# origen: «Tecnológico» y «Especialización» van mal escritas en la base).
NIVEL_SPE = {
    "Primaria": "media", "Básica Secundaria": "media", "Media": "media",
    "No Aplica": "sin_declarar", "Otro": "sin_declarar",
    "Técnico": "tyt", "Tecnológico": "tyt", "Tecnólogico": "tyt",
    "Universitarios": "universitaria",
    "Especialización": "posgrado", "Especilización": "posgrado",
    "Maestria": "posgrado", "Maestría": "posgrado", "Doctorado": "posgrado",
}
NIVEL_SNIES = {
    "Técnica profesional": "tyt", "Tecnológica": "tyt",
    "Universitaria": "universitaria",
    "Especialización": "posgrado", "Maestría": "posgrado", "Doctorado": "posgrado",
}
ETIQUETA = {
    "media": "Media o menos", "tyt": "Técnica y tecnológica",
    "universitaria": "Universitaria", "posgrado": "Posgrado",
    "sin_declarar": "Sin nivel declarado",
}


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0.0


def redondear(x: float, d: int = 1) -> float:
    return round(x + 0.0, d)


def resumen_ambito(a: dict) -> dict:
    """Los agregados de un ámbito, sin la lista completa de habilidades."""
    return {
        "ambito": a["ambito"],
        "vacantes": a["vacantes"],
        "posiciones": a["posiciones"],
        "desde": a["rango_fechas"][0],
        "hasta": a["rango_fechas"][1],
        "pct_con_salario": a["pct_con_salario"],
        "pct_mas_3m": a["pct_mas_3m"],
        "banda_modal": a["banda_modal"],
        "familias": a["familias"],
        "educacion": a["educacion"],
        "contrato": a["contrato"],
        "sin_habilidad": a["sin_habilidad_detectada"],
        "teletrabajo_pct": a["teletrabajo_pct"],
        "sin_experiencia_pct": a["sin_experiencia_pct"],
        "sectores": a["sectores"][:8],
        "cargos": a["cargos"][:10],
    }


def habilidad_web(h: dict, pais: dict[str, dict]) -> dict:
    """Una habilidad con lo que el capítulo necesita, y nada más.

    `indice` es el cociente de localización contra Colombia: 1,0 es pedirla
    tanto como el país. Se calcula aquí y no se toma del rastreo porque allí
    sólo existe para las quince más especializadas.
    """
    base = pais.get(h["habilidad"], {}).get("pct", 0.0)
    return {
        "h": h["habilidad"],
        "fam": h["familia"],
        "familia": h["familia_nombre"],
        "vac": h["vacantes"],
        "pct": h["pct"],
        "pct3m": h["pct_mas_3m"],
        "sup": h["pct_superior"],
        "media": h["pct_media_o_menos"],
        "salmed": h["salario_mediano"],
        "sector": h["sector_top"],
        "cargos": h["cargos_top"][:3],
        "pct_pais": base,
        "indice": redondear(h["pct"] / base, 2) if base else None,
    }


def puente_nivel(educacion: list[dict], serie: list[dict]) -> dict:
    """La comparación honesta entre lo que el mercado exige y lo que se matricula.

    Las dos distribuciones se normalizan sobre el mismo universo —sólo lo que es
    educación superior— porque el 44 % de las vacantes no pide ningún título de
    ese sistema y la matrícula, por definición, no tiene esa categoría. Sin la
    normalización se estaría comparando un reparto de cuatro casillas contra uno
    de tres.
    """
    vac: dict[str, int] = {}
    for fila in educacion:
        clave = NIVEL_SPE.get(fila["nivel"])
        if clave is None:
            raise SystemExit(f"nivel del SPE sin homologar: {fila['nivel']!r}")
        vac[clave] = vac.get(clave, 0) + fila["vacantes"]

    ultimo = serie[-1]
    mat: dict[str, int] = {}
    for nivel, n in ultimo["niveles"].items():
        clave = NIVEL_SNIES.get(nivel)
        if clave is None:
            raise SystemExit(f"nivel del SNIES sin homologar: {nivel!r}")
        mat[clave] = mat.get(clave, 0) + n

    superiores = ["tyt", "universitaria", "posgrado"]
    tot_vac_sup = sum(vac[k] for k in superiores)
    tot_vac = sum(vac.values())
    # el nivel es un campo que el empleador puede dejar en blanco: los avisos sin
    # nivel declarado no se reparten ni se cuentan como «media o menos»
    declarados = tot_vac - vac["sin_declarar"]
    tot_mat = sum(mat.values())

    return {
        "anio_matricula": ultimo["anio"],
        "vacantes_total": tot_vac,
        "vacantes_declaradas": declarados,
        "vacantes_superior": tot_vac_sup,
        "pct_exige_superior": redondear(100 * tot_vac_sup / declarados),
        "pct_sin_superior": redondear(100 * vac["media"] / declarados),
        "sin_declarar": vac["sin_declarar"],
        "pct_sin_declarar": redondear(100 * vac["sin_declarar"] / tot_vac),
        "matricula_total": tot_mat,
        "niveles": [
            {
                "nivel": ETIQUETA[k],
                "vac": vac[k],
                "vac_pct": redondear(100 * vac[k] / tot_vac_sup),
                "mat": mat[k],
                "mat_pct": redondear(100 * mat[k] / tot_mat),
            }
            for k in superiores
        ],
        "media": {
            "nivel": ETIQUETA["media"], "vac": vac["media"],
            "pct_declaradas": redondear(100 * vac["media"] / declarados),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rastreo", type=Path, default=RASTREO,
                    help="hallazgos.json del rastreo del SPE")
    args = ap.parse_args()

    if not args.rastreo.exists():
        raise SystemExit(f"no encuentro el rastreo en {args.rastreo}")
    R = json.loads(args.rastreo.read_text(encoding="utf-8"))
    D = json.loads((PUBLIC / "datos.json").read_text(encoding="utf-8"))

    ant = R["antioquia"]
    pais = {h["habilidad"]: h for h in R["colombia"]["habilidades"]}
    habilidades = sorted((habilidad_web(h, pais) for h in ant["habilidades"]),
                         key=lambda x: -x["pct"])

    # --- el plano: 15 más pedidas ∪ 15 mejor pagadas, con piso de frecuencia ---
    elegibles = [h for h in habilidades if h["pct"] >= PISO_PLANO]
    mas_pedidas = sorted(elegibles, key=lambda x: -x["pct"])[:TOP_PLANO]
    mejor_pagadas = sorted(elegibles, key=lambda x: -x["pct3m"])[:TOP_PLANO]
    seleccion = {h["h"]: h for h in mas_pedidas + mejor_pagadas}
    plano = sorted(seleccion.values(), key=lambda x: -x["pct"])
    # sobre las elegibles, no sobre las 28 dibujadas (ver el encabezado)
    r = pearson([math.log(h["pct"]) for h in elegibles], [h["pct3m"] for h in elegibles])
    r_sel = pearson([math.log(h["pct"]) for h in plano], [h["pct3m"] for h in plano])

    media_pago = ant["pct_mas_3m"]
    payload = {
        "meta": {
            "as_of": AS_OF,
            "ventana": R["ventana"],
            "desde": ant["rango_fechas"][0],
            "hasta": ant["rango_fechas"][1],
            "fuente": R["fuente"],
            "url": URL_FUENTE,
            "smmlv": R["smmlv_2026"],
            "umbral_alto": UMBRAL_ALTO,
            "lexico": {
                "habilidades": len(ant["habilidades"]),
                "familias": len(ant["familias"]),
            },
        },
        "ambitos": {k: resumen_ambito(R[k]) for k in AMBITOS},
        "habilidades": habilidades,
        "plano": {
            "regla": (f"Las {TOP_PLANO} más pedidas unidas a las {TOP_PLANO} mejor "
                      f"pagadas, entre las que aparecen en al menos el "
                      f"{PISO_PLANO} % de las vacantes."),
            "n": len(plano),
            "piso_pct": PISO_PLANO,
            "media_pct3m": media_pago,
            "r": redondear(r, 2),
            "r_n": len(elegibles),
            "r_seleccionadas": redondear(r_sel, 2),
            "items": plano,
            "sobre_media": sum(1 for h in mas_pedidas if h["pct3m"] > media_pago),
        },
        "especializacion": [
            {"h": e["habilidad"], "fam": e["familia"], "familia": e["familia_nombre"],
             "vac": e["vacantes"], "pct": e["pct"], "pct_pais": e["pct_base"],
             "indice": e["indice"], "pct3m": e["pct_mas_3m"], "sup": e["pct_superior"]}
            for e in R["esp_antioquia_vs_pais"]
        ],
        "municipios_amva": R["municipios_amva"],
        "departamentos": R["departamentos"],
        "puente_nivel": puente_nivel(ant["educacion"], D["serie"]),
    }

    salida = PUBLIC / "habilidades.json"
    salida.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")

    p = payload["puente_nivel"]
    print(json.dumps({
        "output": str(salida),
        "kb": round(salida.stat().st_size / 1024, 1),
        "vacantes_antioquia": ant["vacantes"],
        "habilidades": len(habilidades),
        "plano_n": len(plano),
        "r_elegibles": f'{payload["plano"]["r"]} sobre {len(elegibles)}',
        "r_si_solo_las_28": payload["plano"]["r_seleccionadas"],
        "sobre_media_entre_las_15_mas_pedidas": payload["plano"]["sobre_media"],
        "puente": {n["nivel"]: f"vacantes {n['vac_pct']} % · matrícula {n['mat_pct']} %"
                   for n in p["niveles"]},
        "exige_superior_pct": p["pct_exige_superior"],
        "sin_nivel_declarado_pct": p["pct_sin_declarar"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
