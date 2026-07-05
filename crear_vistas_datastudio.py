import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery

PROYECTO = "databigquery-488922"
DATASET = "datos_mysql"
client = bigquery.Client(project=PROYECTO)

TABLE = f"`{PROYECTO}.{DATASET}.fletes_validacion`"

def crear_vista(nombre, sql):
    ref = bigquery.Table(f"{PROYECTO}.{DATASET}.{nombre}")
    ref.view_query = sql
    ref.labels = {"tipo": "vista_datastudio"}
    try:
        client.delete_table(ref, not_found_ok=True)
        client.create_table(ref)
        print(f"  CREADA: {nombre}")
    except Exception as e:
        print(f"  ERROR {nombre}: {e}")

print("Creando vistas para Data Studio...\n")

crear_vista("v_fact_mensual", f"""
    SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
        DATE_TRUNC(fecha, MONTH) as mes_date,
        COUNT(*) as total_viajes,
        ROUND(SUM(tarifa_final), 2) as total_tarifa,
        ROUND(AVG(tarifa_final), 2) as tarifa_promedio,
        COUNTIF(estado_contable = 'Facturado') as fact_viajes,
        ROUND(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), 2) as fact_total,
        COUNTIF(estado_contable = 'Sin Facturar') as pend_viajes,
        ROUND(SUM(IF(estado_contable = 'Sin Facturar', tarifa_final, 0)), 2) as pend_total,
        ROUND(SAFE_DIVIDE(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_facturado
    FROM {TABLE}
    WHERE fecha IS NOT NULL
    GROUP BY mes, mes_date ORDER BY mes
""")

crear_vista("v_fact_compania", f"""
    SELECT nombre_compania,
        COUNT(*) as total_viajes,
        ROUND(SUM(tarifa_final), 2) as total_tarifa,
        ROUND(AVG(tarifa_final), 2) as tarifa_promedio,
        COUNTIF(estado_contable = 'Facturado') as fact_viajes,
        ROUND(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), 2) as fact_total,
        COUNTIF(estado_contable = 'Sin Facturar') as pend_viajes,
        ROUND(SUM(IF(estado_contable = 'Sin Facturar', tarifa_final, 0)), 2) as pend_total,
        ROUND(SAFE_DIVIDE(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), SUM(tarifa_final)) * 100, 1) as pct_facturado
    FROM {TABLE}
    WHERE nombre_compania IS NOT NULL
    GROUP BY nombre_compania ORDER BY fact_total DESC
""")

crear_vista("v_fact_transportista", f"""
    SELECT transportista,
        COUNT(*) as total_viajes,
        ROUND(SUM(tarifa_final), 2) as total_tarifa,
        ROUND(AVG(tarifa_final), 2) as tarifa_promedio,
        COUNTIF(estado_contable = 'Facturado') as fact_viajes,
        ROUND(SUM(IF(estado_contable = 'Facturado', tarifa_final, 0)), 2) as fact_total,
        COUNTIF(estado_contable = 'Sin Facturar') as pend_viajes,
        ROUND(SUM(IF(estado_contable = 'Sin Facturar', tarifa_final, 0)), 2) as pend_total
    FROM {TABLE}
    WHERE transportista IS NOT NULL AND transportista != ''
    GROUP BY transportista ORDER BY total_tarifa DESC
""")

crear_vista("v_status_crisar", f"""
    SELECT status_crisar,
        COUNT(*) as viajes,
        ROUND(SUM(tarifa_final), 2) as total_tarifa,
        ROUND(AVG(tarifa_final), 2) as tarifa_promedio
    FROM {TABLE}
    WHERE status_crisar IS NOT NULL AND status_crisar != ''
    GROUP BY status_crisar ORDER BY total_tarifa DESC
""")

crear_vista("v_envio_factura", f"""
    SELECT estado_envio_factura,
        COUNT(*) as viajes,
        ROUND(SUM(tarifa_final), 2) as total_tarifa,
        ROUND(AVG(tarifa_final), 2) as tarifa_promedio
    FROM {TABLE}
    WHERE estado_envio_factura IS NOT NULL AND estado_envio_factura != ''
    GROUP BY estado_envio_factura ORDER BY total_tarifa DESC
""")

crear_vista("v_pendientes_top", f"""
    SELECT nombre_compania, nombre_sucursal, transportista,
        COUNT(*) as viajes,
        ROUND(SUM(tarifa_final), 2) as total_pendiente
    FROM {TABLE}
    WHERE estado_contable = 'Sin Facturar'
    GROUP BY nombre_compania, nombre_sucursal, transportista
    ORDER BY total_pendiente DESC LIMIT 20
""")

crear_vista("v_fletes_detalle", f"""
    SELECT fecha, nombre_compania, nombre_sucursal, titulo,
        transportista, tarifa_final, estado_flete, estado_contable,
        estado_envio_factura, status_crisar, tipo_fact,
        estado_conciliacion, tipo_transporte, n_flete, nro_factura,
        FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
        FORMAT_TIMESTAMP('%Y', fecha) as anio
    FROM {TABLE}
    WHERE fecha IS NOT NULL
    ORDER BY fecha DESC
""")

crear_vista("v_on_time_resumen", f"""
    SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
        nombre_compania,
        COUNT(*) as total_viajes,
        COUNTIF(estado_viaje = 'Lleg\u00f3 a tiempo') as on_time,
        ROUND(SAFE_DIVIDE(COUNTIF(estado_viaje = 'Lleg\u00f3 a tiempo'), COUNT(*)) * 100, 1) as pct_on_time
    FROM {TABLE}
    WHERE fecha IS NOT NULL AND estado_viaje IS NOT NULL
    GROUP BY mes, nombre_compania ORDER BY mes
""")

print("\nVistas creadas.")
print("Ahora en Data Studio:")
print("1. Crear fuente de datos -> BigQuery -> databigquery-488922 -> datos_mysql")
print("2. Seleccionar la vista (v_fact_mensual, v_fact_compania, etc.)")
print("3. Crear reporte y conectar las fuentes")
