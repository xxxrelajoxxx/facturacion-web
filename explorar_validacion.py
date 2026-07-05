import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery
client = bigquery.Client(project="databigquery-488922")

T = "`databigquery-488922.datos_mysql.fletes_validacion`"

# schema
ref = client.dataset("datos_mysql").table("fletes_validacion")
tbl = client.get_table(ref)
print("=== SCHEMA ===")
for s in tbl.schema:
    print(f"  {s.name:30s} {s.field_type:10s} {s.mode}")
print(f"  Filas: {tbl.num_rows}")

# sample
df = client.query(f"SELECT * FROM {T} LIMIT 3").to_dataframe()
print("\n=== MUESTRA ===")
print(df.to_string(max_colwidth=22))

# columnas extra vs fletes_report
df = client.query(f"SELECT column_name, data_type FROM `databigquery-488922.INFORMATION_SCHEMA.COLUMNS` WHERE table_name = 'fletes_validacion' AND column_name NOT IN (SELECT column_name FROM `databigquery-488922.INFORMATION_SCHEMA.COLUMNS` WHERE table_name = 'fletes_report')").to_dataframe()
print("\n=== COLUMNAS EXCLUSIVAS VALIDACION ===")
print(df.to_string())

# KPI principales
df = client.query(f"""
    SELECT
        COUNT(*) as total,
        COUNTIF(estado_contable = 'Facturado') as fact_viajes,
        ROUND(SUM(IF(estado_contable='Facturado',tarifa_final,0)),2) as fact_total,
        COUNTIF(estado_contable = 'Sin Facturar') as pend_viajes,
        ROUND(SUM(IF(estado_contable='Sin Facturar',tarifa_final,0)),2) as pend_total,
        COUNTIF(estado_contable = 'Anulado') as anul_viajes,
        ROUND(SUM(IF(estado_contable='Anulado',tarifa_final,0)),2) as anul_total,
        ROUND(SUM(tarifa_final),2) as tarifa_total,
        ROUND(AVG(tarifa_final),2) as tarifa_prom,
        COUNTIF(status_crisar IS NOT NULL AND status_crisar != '') as con_status
    FROM {T}
""").to_dataframe()
print("\n=== KPI GLOBALES ===")
print(df.to_string())

# status_crisar distribution
df = client.query(f"""
    SELECT status_crisar, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE status_crisar IS NOT NULL AND status_crisar != ''
    GROUP BY status_crisar ORDER BY total DESC
""").to_dataframe()
print("\n=== STATUS CRISAR ===")
print(df.to_string())

# motivo distribution
df = client.query(f"""
    SELECT motivo, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE motivo IS NOT NULL AND motivo != ''
    GROUP BY motivo ORDER BY total DESC
""").to_dataframe()
print("\n=== MOTIVO ===")
print(df.to_string())

# Filtro distribution
df = client.query(f"""
    SELECT Filtro, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE Filtro IS NOT NULL AND Filtro != ''
    GROUP BY Filtro ORDER BY total DESC
""").to_dataframe()
print("\n=== FILTRO ===")
print(df.to_string())

# observacion distribution
df = client.query(f"""
    SELECT observacion, COUNT(*) as viajes, ROUND(SUM(tarifa_final),2) as total
    FROM {T}
    WHERE observacion IS NOT NULL AND observacion != ''
    GROUP BY observacion ORDER BY total DESC
""").to_dataframe()
print("\n=== OBSERVACION ===")
print(df.to_string())
