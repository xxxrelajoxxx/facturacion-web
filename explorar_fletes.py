import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery
client = bigquery.Client(project="databigquery-488922")

T = "`databigquery-488922.datos_mysql.fletes_report`"

# sample
df = client.query(f"SELECT * FROM {T} LIMIT 3").to_dataframe()
print("=== MUESTRA ===")
print(df.to_string(max_colwidth=25))
print()

# financial KPIs
df = client.query(f"""
    SELECT 
        COUNT(*) as total_fletes,
        COUNT(DISTINCT transportista) as transportistas,
        COUNT(DISTINCT compania) as companias,
        ROUND(SUM(tarifa_final), 2) as tarifa_total,
        ROUND(AVG(tarifa_final), 2) as tarifa_prom,
        ROUND(MIN(tarifa_final), 2) as tarifa_min,
        ROUND(MAX(tarifa_final), 2) as tarifa_max,
        COUNTIF(estado_conciliacion = 'CONCILIADO') as conciliados,
        COUNTIF(estado_conciliacion != 'CONCILIADO' OR estado_conciliacion IS NULL) as no_conciliados,
        COUNTIF(estado_flete = 'Facturado') as facturados,
        COUNTIF(estado_flete != 'Facturado') as no_facturados
    FROM {T}
""").to_dataframe()
print("=== KPIS GLOBALES ===")
print(df.to_string())
print()

# tarifa por mes
df = client.query(f"""
    SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total,
           ROUND(AVG(tarifa_final), 2) as promedio
    FROM {T}
    WHERE fecha IS NOT NULL
    GROUP BY mes ORDER BY mes
""").to_dataframe()
print("=== TARIFA POR MES ===")
print(df.to_string())
print()

# por transportista
df = client.query(f"""
    SELECT transportista,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total,
           ROUND(AVG(tarifa_final), 2) as promedio
    FROM {T}
    WHERE transportista IS NOT NULL AND transportista != ''
    GROUP BY transportista ORDER BY total DESC
""").to_dataframe()
print("=== POR TRANSPORTISTA ===")
print(df.to_string())
print()

# por compania
df = client.query(f"""
    SELECT nombre_compania,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total
    FROM {T}
    WHERE nombre_compania IS NOT NULL
    GROUP BY nombre_compania ORDER BY total DESC
""").to_dataframe()
print("=== POR COMPANIA ===")
print(df.to_string())
print()

# por estado contable
df = client.query(f"""
    SELECT estado_contable,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total
    FROM {T}
    WHERE estado_contable IS NOT NULL
    GROUP BY estado_contable ORDER BY total DESC
""").to_dataframe()
print("=== POR ESTADO CONTABLE ===")
print(df.to_string())
print()

# estado conciliacion
df = client.query(f"""
    SELECT estado_conciliacion,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total
    FROM {T}
    WHERE estado_conciliacion IS NOT NULL
    GROUP BY estado_conciliacion ORDER BY total DESC
""").to_dataframe()
print("=== POR CONCILIACION ===")
print(df.to_string())
print()

# tipo_transporte
df = client.query(f"""
    SELECT tipo_transporte,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total,
           ROUND(AVG(tarifa_final), 2) as promedio
    FROM {T}
    WHERE tipo_transporte IS NOT NULL AND tipo_transporte != ''
    GROUP BY tipo_transporte ORDER BY total DESC
""").to_dataframe()
print("=== POR TIPO TRANSPORTE ===")
print(df.to_string())
print()

# estado_flete
df = client.query(f"""
    SELECT estado_flete,
           COUNT(*) as viajes,
           ROUND(SUM(tarifa_final), 2) as total
    FROM {T}
    WHERE estado_flete IS NOT NULL
    GROUP BY estado_flete ORDER BY total DESC
""").to_dataframe()
print("=== POR ESTADO FLETE ===")
print(df.to_string())
print()

# rango de fechas
df = client.query(f"""
    SELECT MIN(fecha) as min_f, MAX(fecha) as max_f,
           MIN(fecha_creacion) as min_fc, MAX(fecha_creacion) as max_fc
    FROM {T}
""").to_dataframe()
print("=== RANGOS FECHA ===")
print(df.to_string())
print()

# como_factura
df = client.query(f"""
    SELECT como_factura, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE como_factura IS NOT NULL
    GROUP BY como_factura ORDER BY total DESC
""").to_dataframe()
print("=== COMO FACTURA ===")
print(df.to_string())
print()

# sucursal top
df = client.query(f"""
    SELECT nombre_sucursal, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE nombre_sucursal IS NOT NULL
    GROUP BY nombre_sucursal ORDER BY total DESC LIMIT 10
""").to_dataframe()
print("=== TOP SUCURSALES ===")
print(df.to_string())
