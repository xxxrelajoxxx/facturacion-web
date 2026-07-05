import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery
client = bigquery.Client(project="databigquery-488922")
T = "`databigquery-488922.datos_mysql.facturacion_crisar`"

# estado_envio_factura distribution
df = client.query(f"""
    SELECT estado_envio_factura, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE estado_envio_factura IS NOT NULL AND estado_envio_factura != ''
    GROUP BY estado_envio_factura ORDER BY total DESC
""").to_dataframe()
print("=== ESTADO ENVIO FACTURA ===")
print(df.to_string())
print()

# facturado vs sin facturar por compañía
df = client.query(f"""
    SELECT nombre_compania,
        COUNTIF(estado_contable='Facturado') as fact_viajes,
        ROUND(SUM(IF(estado_contable='Facturado',tarifa_final,0)),2) as fact_total,
        COUNTIF(estado_contable='Sin Facturar') as pend_viajes,
        ROUND(SUM(IF(estado_contable='Sin Facturar',tarifa_final,0)),2) as pend_total,
        COUNTIF(estado_contable='Anulado') as anul_viajes,
        ROUND(SUM(IF(estado_contable='Anulado',tarifa_final,0)),2) as anul_total
    FROM {T}
    WHERE nombre_compania IS NOT NULL
    GROUP BY nombre_compania ORDER BY fact_total DESC
""").to_dataframe()
print("=== FACTURACION POR COMPAÑIA ===")
print(df.to_string())
print()

# facturacion por mes
df = client.query(f"""
    SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
        COUNTIF(estado_contable='Facturado') as fact_viajes,
        ROUND(SUM(IF(estado_contable='Facturado',tarifa_final,0)),2) as fact_total,
        COUNTIF(estado_contable='Sin Facturar') as pend_viajes,
        ROUND(SUM(IF(estado_contable='Sin Facturar',tarifa_final,0)),2) as pend_total
    FROM {T}
    WHERE fecha IS NOT NULL
    GROUP BY mes ORDER BY mes
""").to_dataframe()
print("=== FACTURACION POR MES ===")
print(df.to_string())
print()

# sin facturar - detalle
df = client.query(f"""
    SELECT nombre_compania, nombre_sucursal, transportista,
           COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE estado_contable = 'Sin Facturar'
    GROUP BY nombre_compania, nombre_sucursal, transportista
    ORDER BY total DESC LIMIT 15
""").to_dataframe()
print("=== TOP PENDIENTES DE FACTURAR ===")
print(df.to_string())
print()

# ratio facturado/pendiente global por mes
df = client.query(f"""
    SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
        ROUND(SUM(IF(estado_contable='Facturado',tarifa_final,0)) / NULLIF(SUM(tarifa_final),0) * 100, 1) as pct_facturado
    FROM {T}
    WHERE fecha IS NOT NULL
    GROUP BY mes ORDER BY mes
""").to_dataframe()
print("=== % FACTURADO POR MES ===")
print(df.to_string())
