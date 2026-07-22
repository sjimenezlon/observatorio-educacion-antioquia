"""Financiación del estudiante (Antioquia) → data/financiacion.json

Fuentes (API Socrata, datos.gov.co — sin login):
  · 26bn-e42j  ICETEX — Créditos Otorgados (2015-2025, nuevos beneficiarios).
                Sin columna de monto: solo `rango_del_valor_total` (decil del
                valor desembolsado por vigencia y línea), inservible como pesos.
  · nvcf-b8a3  ICETEX — Créditos Renovados (2015-2025).
  · dugh-vkir  ICETEX — Comportamiento de Cartera y Crédito (cortes
                trimestrales mar-2022 → jun-2026, por depto de residencia y
                época: ESTUDIOS / AMORTIZACION).
  · ya7f-466y  Gobernación de Antioquia — Beneficiarios de becas y créditos de
                acceso a educación superior (convocatorias 2013-2024).

Tasa de graduación de becarios: la columna `graduado` (SI/NO) es una foto al
corte de la base (may-2024), sin fecha de grado. La tasa honesta se calcula
sobre cohortes con tiempo suficiente para graduarse (convocatorias 2013-2018,
≥6 años al corte); la bruta sobre todos los beneficiarios se reporta aparte.

Uso:  python3 scripts/financiacion.py
"""
import json
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
SOC = "https://www.datos.gov.co/resource/{}.json"
ANT_ICETEX = "departamento_de_origen='ANTIOQUIA'"

SUBREGION = {  # nomenclatura del dataset → la que ya usa el sitio
    "VALLE DE ABURRA": "Valle de Aburrá", "URABA": "Urabá", "ORIENTE": "Oriente",
    "OCCIDENTE": "Occidente", "SUROESTE": "Suroeste", "NORTE": "Norte",
    "NORDESTE": "Nordeste", "BAJO CAUCA": "Bajo Cauca", "MAGDALENA MEDIO": "Magdalena Medio",
}


def soql(dataset, **params):
    """GET a la API Socrata con parámetros $-SoQL → DataFrame."""
    r = requests.get(SOC.format(dataset), params={f"${k}": v for k, v in params.items()},
                     timeout=120)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def pesos(s):
    """'$ 365,649,654,993' → 365649654993 (int)."""
    return int(str(s).replace("$", "").replace(",", "").strip())


def serie_anual(dataset, col_medida, etiqueta):
    """Serie anual Antioquia (suma de la medida por vigencia), con verificaciones."""
    df = soql(dataset, select=f"vigencia,sum({col_medida}) as n",
              where=ANT_ICETEX, group="vigencia", order="vigencia")
    df["anio"], df["n"] = df["vigencia"].astype(int), df["n"].astype(int)
    # Verificación: sin años duplicados ni huecos en la serie
    assert df["anio"].is_unique, f"{etiqueta}: años duplicados"
    assert df["anio"].tolist() == list(range(df["anio"].min(), df["anio"].max() + 1)), \
        f"{etiqueta}: huecos en la serie"
    assert (df["n"] > 0).all(), f"{etiqueta}: años en cero"
    print(f"{etiqueta}: {df['anio'].min()}-{df['anio'].max()} | "
          + " ".join(f"{a}:{n:,}" for a, n in zip(df["anio"], df["n"])))
    return [{"anio": int(a), "n": int(n)} for a, n in zip(df["anio"], df["n"])]


out = {}

# ---------------------------------------------------------- 1. ICETEX otorgados
print("== ICETEX — créditos otorgados (26bn-e42j) ==")
otorgados = serie_anual("26bn-e42j", "numero_de_nuevos_beneficiarios", "Antioquia")
# Serie nacional: el sitio cita −83,6 % en créditos nuevos 2025 — se contrasta aquí
nal = soql("26bn-e42j", select="vigencia,sum(numero_de_nuevos_beneficiarios) as n",
           group="vigencia", order="vigencia")
nal["anio"], nal["n"] = nal["vigencia"].astype(int), nal["n"].astype(int)
nacional = [{"anio": int(a), "n": int(n)} for a, n in zip(nal["anio"], nal["n"])]
d = {r["anio"]: r["n"] for r in otorgados}
dn = {r["anio"]: r["n"] for r in nacional}
var_ant = round(100 * (d[2025] / d[2024] - 1), 1)
var_nal = round(100 * (dn[2025] / dn[2024] - 1), 1)
print(f"Desplome 2025 vs 2024 — Antioquia: {var_ant} % ({d[2024]:,}→{d[2025]:,}) | "
      f"Nacional: {var_nal} % ({dn[2024]:,}→{dn[2025]:,})  [el sitio cita −83,6 % = nacional]")
# 2025 sí trae los dos semestres (no es media vigencia)
per = soql("26bn-e42j", select="periodo_otorgamiento,sum(numero_de_nuevos_beneficiarios) as n",
           where=f"{ANT_ICETEX} AND vigencia='2025'", group="periodo_otorgamiento",
           order="periodo_otorgamiento")
assert per["periodo_otorgamiento"].tolist() == ["2025-1", "2025-2"], "2025 incompleto"
print("2025 Antioquia por periodo:", dict(zip(per["periodo_otorgamiento"], per["n"])))

# ---------------------------------------------------------- 2. ICETEX renovados
print("\n== ICETEX — créditos renovados (nvcf-b8a3) ==")
renovados = serie_anual("nvcf-b8a3", "numero_de_renovaciones", "Antioquia")

# ----------------------------------------------------------- 3. ICETEX cartera
print("\n== ICETEX — cartera (dugh-vkir) ==")
corte = soql("dugh-vkir", select="max(fecha_corte) as f").iloc[0, 0][:10]
car = soql("dugh-vkir", where=f"deptoresidencia='ANTIOQUIA' AND fecha_corte='{corte}T00:00:00.000'")
assert len(car) == 2, f"se esperaban 2 épocas para Antioquia, llegaron {len(car)}"
cartera = {"fecha_corte": corte, "epocas": {}}
tot = {"creditos": 0, "en_mora": 0, "saldo_total": 0, "saldo_mora": 0}
for _, r in car.iterrows():
    al_dia, mora, mora90 = (int(r[c]) for c in
                            ("cantidad_creditos_al_dia", "cantidad_creditos_con_mora",
                             "cantidad_creditos_mora_mayor"))
    total = int(r["total_creditos"])
    # Verificación: al día + mora 1-90d + mora >90d = total
    assert al_dia + mora + mora90 == total, f"cartera {r['epoca_cartera']}: no cuadra el total"
    ep = {"creditos": total, "al_dia": al_dia, "mora_1_90d": mora, "mora_mas_90d": mora90,
          "saldo_total": pesos(r["saldo_total"]), "saldo_mora": pesos(r["saldo_mora"]),
          "pct_creditos_en_mora": round(100 * (mora + mora90) / total, 1),
          "indicador_cartera_vencida_pct": round(100 * float(r["indicador_cartera_vencida"]), 1)}
    cartera["epocas"][r["epoca_cartera"].upper()] = ep
    tot["creditos"] += total
    tot["en_mora"] += mora + mora90
    tot["saldo_total"] += ep["saldo_total"]
    tot["saldo_mora"] += ep["saldo_mora"]
cartera["total"] = {**tot, "pct_creditos_en_mora": round(100 * tot["en_mora"] / tot["creditos"], 1)}
print(f"Corte {corte} | créditos: {tot['creditos']:,} ({tot['en_mora']:,} en mora, "
      f"{cartera['total']['pct_creditos_en_mora']} %) | saldo total: ${tot['saldo_total']:,} "
      f"| en mora: ${tot['saldo_mora']:,}")

# --------------------------------------------- 4. Becas Gobernación de Antioquia
print("\n== Becas Gobernación (ya7f-466y) ==")
total_becas = int(soql("ya7f-466y", select="count(*) as n").iloc[0, 0])
an = soql("ya7f-466y", select="convocatoria,count(*) as n", group="convocatoria",
          order="convocatoria")
an["n"] = an["n"].astype(int)
serie_becas = [[int(a), int(n)] for a, n in zip(an["convocatoria"], an["n"])]
sub = soql("ya7f-466y", select="subregi_n_de_residencia,count(*) as n",
           group="subregi_n_de_residencia", order="n DESC")
sub["n"] = sub["n"].astype(int)
subregion = [[SUBREGION[s.strip().upper()], int(n)]
             for s, n in zip(sub["subregi_n_de_residencia"], sub["n"])]
est = soql("ya7f-466y", select="upper(estrato) as e,count(*) as n", group="upper(estrato)")
est["n"] = est["n"].astype(int)
est["e"] = est["e"].str.replace("ESTRATO ", "", regex=False).str.strip()
est = est.groupby("e", as_index=False)["n"].sum().sort_values("e")
estrato = [[e, int(n)] for e, n in est.values]
# Verificaciones: la suma por cada corte reproduce el total
assert sum(n for _, n in serie_becas) == total_becas, "serie anual ≠ total"
assert sum(n for _, n in subregion) == total_becas, "subregiones ≠ total"
assert sum(n for _, n in estrato) == total_becas, "estratos ≠ total"
print(f"Total beneficiarios: {total_becas:,} | serie {serie_becas[0][0]}-{serie_becas[-1][0]} ✓ "
      f"| subregiones suman ✓ | estratos suman ✓")

# Graduación: `graduado` es foto al corte (sin fecha de grado). Tasa honesta =
# cohortes 2013-2018 (≥6 años de haber entrado al corte de la base, may-2024).
gr = soql("ya7f-466y", select="convocatoria,graduado,count(*) as n",
          group="convocatoria,graduado")
gr["n"] = gr["n"].astype(int)
gr["anio"] = gr["convocatoria"].astype(int)
piv = gr.pivot_table(index="anio", columns="graduado", values="n",
                     aggfunc="sum", fill_value=0)
por_cohorte = [[int(a), int(piv.loc[a].get("SI", 0)), int(piv.loc[a].sum())]
               for a in piv.index]
viejas = piv.loc[2013:2018]
grad_v, univ_v = int(viejas.get("SI", pd.Series(0)).sum()), int(viejas.sum().sum())
grad_t = int(piv.get("SI", pd.Series(0)).sum())
print(f"Graduación cohortes 2013-2018: {grad_v:,}/{univ_v:,} = {100*grad_v/univ_v:.1f} % "
      f"| bruta todas las cohortes: {grad_t:,}/{total_becas:,} = {100*grad_t/total_becas:.1f} %")

# ------------------------------------------------------------------- Escritura
out = {
    "corte": {
        "icetex_otorgados": "vigencias 2015-2025 (2025 con ambos semestres); filas actualizadas 2026-05-20",
        "icetex_renovados": "vigencias 2015-2025; filas actualizadas 2026-05-20",
        "icetex_cartera": f"cortes trimestrales 2022-03-31 → {corte}; filas actualizadas 2026-07-15",
        "becas_gob": "convocatorias 2013-2024 (2024 parcial: 43); filas actualizadas 2024-05-20",
    },
    "icetex": {
        "otorgados": otorgados,
        "otorgados_nacional": nacional,
        "var_2025_pct": {"antioquia": var_ant, "nacional": var_nal},
        "renovados": renovados,
        "cartera": cartera,
        "nota": ("Otorgados/renovados: nº de beneficiarios por depto de ORIGEN; el dataset no trae "
                 "montos (solo decil del valor). Cartera: depto de RESIDENCIA, dos épocas "
                 "(estudios/amortización); indicador oficial = % del saldo de capital vencido >30 días."),
    },
    "becas_gob": {
        "total": total_becas,
        "serie": serie_becas,
        "subregion": subregion,
        "estrato": estrato,
        "graduacion": {
            "graduados": grad_v, "universo": univ_v,
            "tasa_pct": round(100 * grad_v / univ_v, 1),
            "bruta_graduados": grad_t, "bruta_universo": total_becas,
            "bruta_pct": round(100 * grad_t / total_becas, 1),
            "por_cohorte": por_cohorte,  # [convocatoria, graduados, beneficiarios]
            "nota": ("Tasa sobre cohortes 2013-2018 (≥6 años al corte de la base, may-2024); "
                     "las cohortes recientes aún no alcanzan a graduarse y deprimen la bruta."),
        },
    },
}
destino = DATA / "financiacion.json"
destino.write_text(json.dumps(out, ensure_ascii=False))
print(f"\nok → data/financiacion.json ({destino.stat().st_size / 1024:.1f} KB)")
