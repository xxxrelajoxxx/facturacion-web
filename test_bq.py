import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Script_Python\Conexion_BigQuery.json"
from google.cloud import bigquery

client = bigquery.Client(project="databigquery-488922")

df = client.query("SELECT COUNT(*) as n FROM `databigquery-488922.datos_mysql.oc`").to_dataframe()
print("Conexion BQ OK:", df.iloc[0]["n"], "OC registradas")

df2 = client.query("""
    SELECT FORMAT_TIMESTAMP('%Y-%m', fecha) as mes, COUNT(*) as cantidad
    FROM `databigquery-488922.datos_mysql.fletes_report`
    WHERE fecha IS NOT NULL GROUP BY mes ORDER BY mes LIMIT 3
""").to_dataframe()
print("Fletes por mes OK:", len(df2), "meses")
print("TODO OK - app lista para iniciar")
