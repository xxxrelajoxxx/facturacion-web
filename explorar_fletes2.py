import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery
client = bigquery.Client(project="databigquery-488922")
T = "`databigquery-488922.datos_mysql.fletes_report`"

for col in ["nombre_compania", "transportista", "estado_contable", "estado_flete", "tipo_transporte", "estado_conciliacion", "nombre_sucursal"]:
    df = client.query(f"SELECT DISTINCT {col} as val FROM {T} WHERE {col} IS NOT NULL AND {col} != '' ORDER BY val").to_dataframe()
    print(f"=== {col} ({len(df)}) ===")
    print(df.to_string(index=False))
    print()

# meses disponibles
df = client.query(f"SELECT DISTINCT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes FROM {T} WHERE fecha IS NOT NULL ORDER BY mes").to_dataframe()
print("=== MESES ===")
print(df.to_string(index=False))
