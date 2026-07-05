import os
import json
import traceback
import pandas as pd
from io import BytesIO
from flask import Flask, render_template, jsonify, request, send_file
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

app = Flask(__name__)

if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    for ruta in [
        r"C:\Script_Python\Conexion_BigQuery.json",
        os.path.join(os.path.dirname(__file__), "Conexion_BigQuery.json")
    ]:
        if os.path.exists(ruta):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ruta
PROYECTO = "databigquery-488922"
DATASET = "datos_mysql"

client = bigquery.Client(project=PROYECTO)

TABLAS = [
    "oc", "oc_dash", "oc_report", "fletes_report", "fletes_validacion",
    "on_time_report", "on_time_report_mes", "reg_on_time",
    "Vista_Despacho_Planta", "transitos_flt", "viajes_pendientes"
]

def query(sql, params=None):
    try:
        if params:
            job_config = QueryJobConfig(query_parameters=params)
            return client.query(sql, job_config=job_config).to_dataframe()
        return client.query(sql).to_dataframe()
    except Exception as e:
        print(f"ERROR query: {e}\n{traceback.format_exc()}")
        raise

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/resumen")
def api_resumen():
    data = {}
    data["total_oc"] = int(query(f"SELECT COUNT(*) as n FROM `{PROYECTO}.{DATASET}.oc`").iloc[0]["n"])
    data["total_fletes"] = int(query(f"SELECT COUNT(*) as n FROM `{PROYECTO}.{DATASET}.fletes_report`").iloc[0]["n"])
    data["total_despachos"] = int(query(f"SELECT COUNT(*) as n FROM `{PROYECTO}.{DATASET}.Vista_Despacho_Planta`").iloc[0]["n"])
    data["total_on_time"] = int(query(f"SELECT COUNT(*) as n FROM `{PROYECTO}.{DATASET}.on_time_report` WHERE on_time = 'ON TIME'").iloc[0]["n"])
    total_ot = int(query(f"SELECT COUNT(*) as n FROM `{PROYECTO}.{DATASET}.on_time_report`").iloc[0]["n"])
    data["on_time_pct"] = round(data["total_on_time"] / total_ot * 100, 1) if total_ot else 0
    data["total_viajes_pend"] = int(query(f"SELECT COUNT(*) as n FROM `{PROYECTO}.{DATASET}.viajes_pendientes`").iloc[0]["n"])
    return jsonify(data)

@app.route("/api/fletes_mes")
def api_fletes_mes():
    df = query(f"""
        SELECT FORMAT_TIMESTAMP('%Y-%m', fecha_creacion) as mes,
               COUNT(*) as cantidad,
               ROUND(SUM(tarifa_final), 2) as total_tarifas
        FROM `{PROYECTO}.{DATASET}.facturacion_crisar`
        WHERE fecha_creacion IS NOT NULL
        GROUP BY mes ORDER BY mes
    """)
    return df.to_json(orient="records")

@app.route("/api/oc_estado")
def api_oc_estado():
    df = query(f"""
        SELECT estado, COUNT(*) as cantidad
        FROM `{PROYECTO}.{DATASET}.oc`
        GROUP BY estado ORDER BY cantidad DESC
    """)
    return df.to_json(orient="records")

@app.route("/api/despachos_planta")
def api_despachos_planta():
    df = query(f"""
        SELECT nom_planta, COUNT(*) as cantidad
        FROM `{PROYECTO}.{DATASET}.Vista_Despacho_Planta`
        GROUP BY nom_planta ORDER BY cantidad DESC
    """)
    return df.to_json(orient="records")

@app.route("/api/on_time_trend")
def api_on_time_trend():
    df = query(f"""
        SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
               COUNTIF(on_time = 'ON TIME') as on_time,
               COUNTIF(on_time != 'ON TIME') as off_time,
               COUNT(*) as total
        FROM `{PROYECTO}.{DATASET}.on_time_report`
        WHERE fecha IS NOT NULL
        GROUP BY mes ORDER BY mes
    """)
    return df.to_json(orient="records")

@app.route("/api/transportistas")
def api_transportistas():
    df = query(f"""
        SELECT nombre_compania, COUNT(*) as viajes, ROUND(SUM(tarifa_final), 2) as total
        FROM `{PROYECTO}.{DATASET}.facturacion_crisar`
        WHERE nombre_compania IS NOT NULL
        GROUP BY nombre_compania ORDER BY total DESC LIMIT 15
    """)
    return df.to_json(orient="records")

@app.route("/api/validacion")
def api_validacion():
    df = query(f"""
        SELECT estado_conciliacion, COUNT(*) as cantidad
        FROM `{PROYECTO}.{DATASET}.facturacion_crisar`
        GROUP BY estado_conciliacion ORDER BY cantidad DESC
    """)
    return df.to_json(orient="records")

@app.route("/api/viajes_pendientes_zona")
def api_viajes_pendientes_zona():
    df = query(f"""
        SELECT zona, COUNT(*) as cantidad,
               ROUND(AVG(porcentaje_cumplimiento), 1) as cumplimiento_pct
        FROM `{PROYECTO}.{DATASET}.viajes_pendientes`
        WHERE zona IS NOT NULL
        GROUP BY zona ORDER BY cantidad DESC
    """)
    return df.to_json(orient="records")

@app.route("/api/tabla/<nombre>")
def api_tabla(nombre):
    if nombre not in TABLAS:
        return jsonify({"error": "tabla no encontrada"}), 404
    df = query(f"SELECT * FROM `{PROYECTO}.{DATASET}.{nombre}` LIMIT 100")
    return df.to_json(orient="records")

TABLA_VIAJES = f"`{PROYECTO}.{DATASET}.viajes_pendientes`"

def where_filtros():
    planta = request.args.get("planta", "")
    destino = request.args.get("destino", "")
    zona = request.args.get("zona", "")
    ns = request.args.get("ns", "")
    clauses = []
    params = []
    if planta:
        clauses.append("origen_carga = @planta")
        params.append(ScalarQueryParameter("planta", "STRING", planta))
    if destino:
        clauses.append("destino_carga = @destino")
        params.append(ScalarQueryParameter("destino", "STRING", destino))
    if zona:
        clauses.append("zona = @zona")
        params.append(ScalarQueryParameter("zona", "STRING", zona))
    if ns == "ON_TIME":
        clauses.append("NS = @ns")
        params.append(ScalarQueryParameter("ns", "STRING", "ON TIME"))
    elif ns == "OFF_TIME":
        clauses.append("NS = @ns")
        params.append(ScalarQueryParameter("ns", "STRING", "OFF TIME"))
    return " AND ".join(clauses) if clauses else "1=1", params

@app.route("/viajes")
def viajes():
    return render_template("viajes.html")

@app.route("/api/viajes/filtros")
def api_viajes_filtros():
    plantas = query(f"SELECT DISTINCT origen_carga as val FROM {TABLA_VIAJES} WHERE origen_carga IS NOT NULL AND origen_carga != '' ORDER BY val")
    destinos = query(f"SELECT DISTINCT destino_carga as val FROM {TABLA_VIAJES} WHERE destino_carga IS NOT NULL AND destino_carga != '' ORDER BY val")
    zonas = query(f"SELECT DISTINCT zona as val FROM {TABLA_VIAJES} WHERE zona IS NOT NULL AND zona != '' ORDER BY val")
    return jsonify({
        "plantas": plantas["val"].tolist(),
        "destinos": destinos["val"].tolist(),
        "zonas": zonas["val"].tolist()
    })

@app.route("/api/viajes/resumen")
def api_viajes_resumen():
    try:
        w, params = where_filtros()
        df = query(f"""
            SELECT
                COUNT(*) as total,
                COUNTIF(NS = 'ON TIME') as on_time_ct,
                COUNTIF(NS = 'OFF TIME') as off_time_ct,
                ROUND(AVG(porcentaje_cumplimiento), 1) as cumpl_prom,
                ROUND(AVG(dias_retrazo), 1) as retraso_prom,
                COUNTIF(placa IS NOT NULL AND placa != '' AND placa != '---') as con_placa,
                MAX(actualizacion) as ultima_actualizacion
            FROM {TABLA_VIAJES} WHERE {w}
        """, params)
        r = df.iloc[0]
        return jsonify({
            "total": int(r["total"]),
            "on_time_ct": int(r["on_time_ct"]),
            "off_time_ct": int(r["off_time_ct"]),
            "on_time_pct": round(int(r["on_time_ct"]) / int(r["total"]) * 100, 1) if int(r["total"]) else 0,
            "off_time_pct": round(int(r["off_time_ct"]) / int(r["total"]) * 100, 1) if int(r["total"]) else 0,
            "cumpl_prom": float(r["cumpl_prom"]) if r["cumpl_prom"] else 0,
            "retraso_prom": float(r["retraso_prom"]) if r["retraso_prom"] else 0,
            "con_placa": int(r["con_placa"]),
            "con_placa_pct": round(int(r["con_placa"]) / int(r["total"]) * 100, 1) if int(r["total"]) else 0,
            "ultima_actualizacion": str(r["ultima_actualizacion"]) if r["ultima_actualizacion"] else "-"
        })
    except Exception as e:
        print(f"ERROR api_viajes_resumen: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/viajes/zona")
def api_viajes_zona():
    try:
        w, params = where_filtros()
        df = query(f"""
            SELECT zona, COUNT(*) as cantidad
            FROM {TABLA_VIAJES} WHERE {w} AND zona IS NOT NULL AND zona != ''
            GROUP BY zona ORDER BY cantidad DESC
        """, params)
        return df.to_json(orient="records")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/viajes/departamentos")
def api_viajes_departamentos():
    try:
        w, params = where_filtros()
        df = query(f"""
            SELECT departamento, COUNT(*) as cantidad,
                   ROUND(AVG(porcentaje_cumplimiento), 1) as cumpl
            FROM {TABLA_VIAJES} WHERE {w} AND departamento IS NOT NULL AND departamento != ''
            GROUP BY departamento ORDER BY cantidad DESC
        """, params)
        return df.to_json(orient="records")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/viajes/retraso")
def api_viajes_retraso():
    try:
        w, params = where_filtros()
        df = query(f"""
            SELECT
                CASE
                    WHEN dias_retrazo IS NULL OR dias_retrazo <= 0 THEN 'A tiempo'
                    WHEN dias_retrazo BETWEEN 1 AND 3 THEN '1-3 d\u00edas'
                    WHEN dias_retrazo BETWEEN 4 AND 7 THEN '4-7 d\u00edas'
                    ELSE '+7 d\u00edas'
                END as rango, COUNT(*) as cantidad
            FROM {TABLA_VIAJES} WHERE {w}
            GROUP BY rango ORDER BY MIN(IFNULL(dias_retrazo,0))
        """, params)
        return df.to_json(orient="records")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/viajes/proximos")
def api_viajes_proximos():
    try:
        w, params = where_filtros()
        df = query(f"""
            SELECT referencia, destino, destino_carga, cliente_final,
                   fecha_carga, compromiso_de_carga, estado_viaje, NS, on_time
            FROM {TABLA_VIAJES}
            WHERE {w} AND (NS = 'OFF TIME' OR (compromiso_de_carga IS NOT NULL AND compromiso_de_carga <= DATE_ADD(CURRENT_DATE(), INTERVAL 2 DAY)))
            ORDER BY compromiso_de_carga ASC
            LIMIT 8
        """, params)
        return df.to_json(orient="records", date_format="iso")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/viajes/tabla")
def api_viajes_tabla():
    try:
        w, params = where_filtros()
        df = query(f"""
            SELECT referencia, origen, destino, zona, cliente_final,
                   placa, compromiso_de_carga, fecha_carga, NS,
                   dias_retrazo, porcentaje_cumplimiento, estado_viaje
            FROM {TABLA_VIAJES}
            WHERE {w}
            ORDER BY porcentaje_cumplimiento ASC, referencia DESC
            LIMIT 100
        """, params)
        return df.to_json(orient="records", date_format="iso")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

TABLA_FACT = f"`{PROYECTO}.{DATASET}.facturacion_crisar`"

def where_fact():
    fields = [
        ("compania", "nombre_compania"),
        ("estado_contable", "estado_contable"),
        ("estado_flete", "estado_flete"),
        ("estado_flt", "estado_flt"),
        ("estado_conciliacion", "estado_conciliacion"),
        ("status_crisar", "status_crisar"),
        ("tipo_fact", "tipo_fact"),
        ("status_cont_aje", "status_contabilidad_aje"),
        ("aprobacion", "aprobacion"),
        ("tipo_proceso", "tipo_proceso"),
        ("estado_envio_factura", "estado_envio_factura"),
    ]
    clauses = []
    params = []
    for arg_key, col_name in fields:
        val = request.args.get(arg_key, "")
        if val:
            clauses.append(f"{col_name} = @{arg_key}")
            params.append(ScalarQueryParameter(arg_key, "STRING", val))
    mes_desde = request.args.get("mes_desde", "")
    mes_hasta = request.args.get("mes_hasta", "")
    if mes_desde:
        clauses.append("fecha_creacion >= @mes_desde")
        params.append(ScalarQueryParameter("mes_desde", "STRING", f"{mes_desde}-01"))
    if mes_hasta:
        clauses.append("fecha_creacion < DATE_ADD(@mes_hasta, INTERVAL 1 MONTH)")
        params.append(ScalarQueryParameter("mes_hasta", "STRING", f"{mes_hasta}-01"))
    return " AND ".join(clauses) if clauses else "1=1", params

@app.route("/facturacion")
@app.route("/fletes")
def facturacion():
    return render_template("fletes.html")

@app.route("/api/fact/filtros")
def api_fact_filtros():
    try:
        comp = query(f"SELECT DISTINCT nombre_compania as val FROM {TABLA_FACT} WHERE nombre_compania IS NOT NULL AND nombre_compania != '' ORDER BY val")
        ec = query(f"SELECT DISTINCT estado_contable as val FROM {TABLA_FACT} WHERE estado_contable IS NOT NULL AND estado_contable != '' ORDER BY val")
        ef = query(f"SELECT DISTINCT estado_flete as val FROM {TABLA_FACT} WHERE estado_flete IS NOT NULL AND estado_flete != '' ORDER BY val")
        eflt = query(f"SELECT DISTINCT estado_flt as val FROM {TABLA_FACT} WHERE estado_flt IS NOT NULL AND estado_flt != '' ORDER BY val")
        econc = query(f"SELECT DISTINCT estado_conciliacion as val FROM {TABLA_FACT} WHERE estado_conciliacion IS NOT NULL AND estado_conciliacion != '' ORDER BY val")
        sc = query(f"SELECT DISTINCT status_crisar as val FROM {TABLA_FACT} WHERE status_crisar IS NOT NULL AND status_crisar != '' ORDER BY val")
        tf = query(f"SELECT DISTINCT tipo_fact as val FROM {TABLA_FACT} WHERE tipo_fact IS NOT NULL AND tipo_fact != '' ORDER BY val")
        sca = query(f"SELECT DISTINCT status_contabilidad_aje as val FROM {TABLA_FACT} WHERE status_contabilidad_aje IS NOT NULL AND status_contabilidad_aje != '' ORDER BY val")
        aprob = query(f"SELECT DISTINCT aprobacion as val FROM {TABLA_FACT} WHERE aprobacion IS NOT NULL AND aprobacion != '' ORDER BY val")
        tp = query(f"SELECT DISTINCT tipo_proceso as val FROM {TABLA_FACT} WHERE tipo_proceso IS NOT NULL AND tipo_proceso != '' ORDER BY val")
        env_fact = query(f"SELECT DISTINCT estado_envio_factura as val FROM {TABLA_FACT} WHERE estado_envio_factura IS NOT NULL AND estado_envio_factura != '' ORDER BY val")
        meses = query(f"SELECT DISTINCT FORMAT_TIMESTAMP('%Y-%m', fecha_creacion) as val FROM {TABLA_FACT} WHERE fecha_creacion IS NOT NULL ORDER BY val")
        return jsonify({
            "companias": comp["val"].tolist(),
            "estados_contables": ec["val"].tolist(),
            "estados_flete": ef["val"].tolist(),
            "estados_flt": eflt["val"].tolist(),
            "estados_conciliacion": econc["val"].tolist(),
            "status_crisar": sc["val"].tolist(),
            "tipos_fact": tf["val"].tolist(),
            "status_cont_aje": sca["val"].tolist(),
            "aprobaciones": aprob["val"].tolist(),
            "tipos_proceso": tp["val"].tolist(),
            "estados_envio_factura": env_fact["val"].tolist(),
            "meses": meses["val"].tolist()
        })
    except Exception as e:
        print(f"ERROR api_fact_filtros: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/kpi")
def api_fact_kpi():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT
                COUNT(*) as total_viajes,
                COUNT(DISTINCT nombre_compania) as companias,
                ROUND(SUM(tarifa_final), 2) as tarifa_total,
                ROUND(AVG(tarifa_final), 2) as tarifa_prom,
                COUNTIF(estado_contable = 'Facturado') as facturados,
                ROUND(SUM(IF(estado_contable='Facturado', tarifa_final, 0)), 2) as facturado_total,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable='Facturado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_facturado,
                COUNTIF(estado_contable = 'Sin Facturar') as sin_facturar,
                ROUND(SUM(IF(estado_contable='Sin Facturar', tarifa_final, 0)), 2) as sin_facturar_total,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable='Sin Facturar', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_sin_facturar,
                COUNTIF(estado_contable = 'Anulado') as anulados,
                ROUND(SUM(IF(estado_contable='Anulado', tarifa_final, 0)), 2) as anulado_total,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable='Anulado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_anulado,
                COUNTIF(estado_flt = 'Con FLT') as con_flt,
                COUNTIF(estado_flete = 'CONFIRMADO') as confirmados,
                COUNTIF(estado_flete = 'POR CONFIRMAR') as por_confirmar,
                COUNTIF(status_crisar = 'COBRADO') as cobrados,
                ROUND(SUM(IF(status_crisar='COBRADO', tarifa_final, 0)), 2) as cobrado_total
            FROM {TABLA_FACT} WHERE {w}
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_kpi: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/tendencia_mensual")
def api_fact_tendencia_mensual():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT FORMAT_TIMESTAMP('%Y-%m', fecha_creacion) as mes,
                ROUND(SUM(tarifa_final), 2) as total,
                ROUND(SUM(IF(estado_contable='Facturado', tarifa_final, 0)), 2) as facturado,
                ROUND(SUM(IF(estado_contable='Sin Facturar', tarifa_final, 0)), 2) as pendiente,
                ROUND(SUM(IF(status_crisar='COBRADO', tarifa_final, 0)), 2) as cobrado,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable='Facturado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_fact,
                ROUND(SAFE_DIVIDE(SUM(IF(status_crisar='COBRADO', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_cobrado,
                COUNT(*) as viajes,
                COUNTIF(estado_flete = 'CONFIRMADO') as confirmados,
                COUNTIF(estado_flt = 'Con FLT') as con_flt
            FROM {TABLA_FACT}
            WHERE fecha_creacion IS NOT NULL AND {w}
            GROUP BY mes ORDER BY mes
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_tendencia_mensual: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/ranking_compania")
def api_fact_ranking_compania():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT nombre_compania,
                COUNT(*) as viajes,
                ROUND(SUM(tarifa_final), 2) as total,
                ROUND(SUM(IF(estado_contable='Facturado', tarifa_final, 0)), 2) as facturado,
                ROUND(SUM(IF(estado_contable='Sin Facturar', tarifa_final, 0)), 2) as pendiente,
                ROUND(SUM(IF(estado_contable='Anulado', tarifa_final, 0)), 2) as anulado,
                ROUND(SUM(IF(status_crisar='COBRADO', tarifa_final, 0)), 2) as cobrado,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable='Facturado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_fact,
                ROUND(SAFE_DIVIDE(SUM(IF(status_crisar='COBRADO', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_cobrado,
                ROUND(AVG(tarifa_final), 2) as promedio
            FROM {TABLA_FACT}
            WHERE nombre_compania IS NOT NULL AND {w}
            GROUP BY nombre_compania ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_ranking_compania: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/status_crisar")
def api_fact_status_crisar():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT status_crisar,
                   COUNT(*) as viajes,
                   ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE status_crisar IS NOT NULL AND status_crisar != '' AND {w}
            GROUP BY status_crisar ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_status_crisar: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/envio_factura")
def api_fact_envio_factura():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT estado_envio_factura,
                   COUNT(*) as viajes,
                   ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE estado_envio_factura IS NOT NULL AND estado_envio_factura != '' AND {w}
            GROUP BY estado_envio_factura ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_envio_factura: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/tipo_fact")
def api_fact_tipo_fact():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT tipo_fact,
                   COUNT(*) as viajes,
                   ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE tipo_fact IS NOT NULL AND tipo_fact != '' AND {w}
            GROUP BY tipo_fact ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_tipo_fact: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/estados")
def api_fact_estados():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT 'Contable' as grupo, estado_contable as nombre,
                   COUNT(*) as viajes, ROUND(SUM(tarifa_final), 2) as total
            FROM {TABLA_FACT}
            WHERE estado_contable IS NOT NULL AND {w}
            GROUP BY estado_contable
            UNION ALL
            SELECT 'FLT' as grupo, estado_flt as nombre,
                   COUNT(*) as viajes, ROUND(SUM(tarifa_final), 2) as total
            FROM {TABLA_FACT}
            WHERE estado_flt IS NOT NULL AND {w}
            GROUP BY estado_flt
            UNION ALL
            SELECT 'Conciliacion' as grupo, estado_conciliacion as nombre,
                   COUNT(*) as viajes, ROUND(SUM(tarifa_final), 2) as total
            FROM {TABLA_FACT}
            WHERE estado_conciliacion IS NOT NULL AND {w}
            GROUP BY estado_conciliacion
            UNION ALL
            SELECT 'Flete' as grupo, estado_flete as nombre,
                   COUNT(*) as viajes, ROUND(SUM(tarifa_final), 2) as total
            FROM {TABLA_FACT}
            WHERE estado_flete IS NOT NULL AND {w}
            GROUP BY estado_flete
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_estados: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/status_cont_aje")
def api_fact_status_cont_aje():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT status_contabilidad_aje,
                   COUNT(*) as viajes,
                   ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE status_contabilidad_aje IS NOT NULL AND status_contabilidad_aje != '' AND {w}
            GROUP BY status_contabilidad_aje ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_status_cont_aje: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/aprobacion")
def api_fact_aprobacion():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT aprobacion,
                   COUNT(*) as viajes,
                   ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE aprobacion IS NOT NULL AND aprobacion != '' AND {w}
            GROUP BY aprobacion ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_aprobacion: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/tipo_proceso")
def api_fact_tipo_proceso():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT tipo_proceso,
                   COUNT(*) as viajes,
                   ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE tipo_proceso IS NOT NULL AND tipo_proceso != '' AND {w}
            GROUP BY tipo_proceso ORDER BY total DESC
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_tipo_proceso: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/pendientes_top")
def api_fact_pendientes_top():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT nombre_compania, nombre_sucursal,
                   COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
            FROM {TABLA_FACT}
            WHERE estado_contable = 'Sin Facturar' AND {w}
            GROUP BY nombre_compania, nombre_sucursal
            ORDER BY total DESC LIMIT 10
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_pendientes_top: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/resumen_ejecutivo")
def api_fact_resumen_ejecutivo():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT
                COUNT(*) as total_viajes,
                ROUND(SUM(tarifa_final), 2) as total_tarifa,
                ROUND(AVG(tarifa_final), 2) as tarifa_prom,
                COUNT(DISTINCT nombre_compania) as companias,
                COUNTIF(estado_contable = 'Facturado') as fact_viajes,
                ROUND(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), 2) as fact_total,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_facturado,
                COUNTIF(estado_contable = 'Sin Facturar') as pend_viajes,
                ROUND(SUM(IF(estado_contable = 'Sin Facturar', tarifa_final, 0)), 2) as pend_total,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable = 'Sin Facturar', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_sin_facturar,
                COUNTIF(estado_contable = 'Anulado') as anul_viajes,
                ROUND(SUM(IF(estado_contable = 'Anulado', tarifa_final, 0)), 2) as anul_total,
                ROUND(SAFE_DIVIDE(SUM(IF(estado_contable = 'Anulado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_anulado,
                COUNTIF(status_crisar = 'COBRADO') as cob_viajes,
                ROUND(SUM(IF(status_crisar = 'COBRADO', tarifa_final, 0)), 2) as cob_total,
                ROUND(SAFE_DIVIDE(SUM(IF(status_crisar = 'COBRADO', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_cobrado,
                COUNTIF(estado_flt = 'Con FLT') as con_flt,
                COUNTIF(estado_flt = 'Sin FLT') as sin_flt,
                COUNTIF(estado_envio_factura = 'ACEPTADO') as env_aceptados,
                COUNTIF(estado_flete = 'CONFIRMADO') as conf_viajes,
                COUNTIF(estado_flete = 'POR CONFIRMAR') as por_confirmar
            FROM {TABLA_FACT} WHERE {w}
        """, p)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"ERROR api_fact_resumen_ejecutivo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/tabla")
def api_fact_tabla():
    try:
        w, p = where_fact()
        pagina = request.args.get("pagina", "1")
        limite = request.args.get("limite", "50")
        offset = (int(pagina) - 1) * int(limite)
        df = query(f"""
            SELECT nombre_compania, nombre_sucursal, fecha_creacion,
                   FORMAT_TIMESTAMP('%d-%m-%Y', fecha_creacion) as fecha,
                   titulo, id_envio, observacion,
                   tarifa_final, n_flete,
                   estado_contable, estado_conciliacion, estado_flt,
                   status_crisar, tipo_fact
            FROM {TABLA_FACT}
            WHERE {w}
            ORDER BY fecha_creacion DESC
            LIMIT {limite} OFFSET {offset}
        """, p)
        return df.to_json(orient="records", date_format="iso")
    except Exception as e:
        print(f"ERROR api_fact_tabla: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fact/exportar_excel")
def api_fact_exportar_excel():
    try:
        w, p = where_fact()
        df = query(f"""
            SELECT nombre_compania as compania, nombre_sucursal as sucursal,
                   FORMAT_TIMESTAMP('%d-%m-%Y', fecha_creacion) as fecha,
                   titulo, id_envio, observacion,
                   tarifa_final, n_flete,
                   estado_contable, estado_conciliacion, estado_flt,
                   status_crisar, tipo_fact, tipo_proceso,
                   aprobacion, estado_envio_factura
            FROM {TABLA_FACT}
            WHERE {w}
            ORDER BY fecha_creacion DESC
        """, p)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Facturacion", index=False)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="facturacion_crisar.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        print(f"ERROR api_fact_exportar_excel: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/tablas_info")
def api_tablas_info():
    info = []
    for t in TABLAS:
        ref = client.dataset(DATASET).table(t)
        table = client.get_table(ref)
        info.append({"nombre": t, "filas": table.num_rows})
    return jsonify(info)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
