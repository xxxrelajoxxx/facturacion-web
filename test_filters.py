import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery
client = bigquery.Client(project="databigquery-488922")

for col in ["origen_carga", "destino_carga", "zona", "atencion", "empresa"]:
    df = client.query(f"""
        SELECT DISTINCT {col} as val FROM `databigquery-488922.datos_mysql.viajes_pendientes`
        WHERE {col} IS NOT NULL AND {col} != '' ORDER BY val
    """).to_dataframe()
    print(f"=== {col} ===")
    print(df.to_string(index=False))
    print()
