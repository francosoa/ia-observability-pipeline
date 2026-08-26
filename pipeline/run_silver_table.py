import os
import json
import glob
from datetime import datetime
import polars as pl

print("Engine de processamento iniciada")

# Garante que os diretórios existem
os.makedirs("data/silver", exist_ok=True)
os.makedirs("data/gold", exist_ok=True)
os.makedirs("observability", exist_ok=True)

# 1. LEITURA DA CAMADA RAW (Lendo arquivos JSON da PokéAPI)
json_files = glob.glob("data/raw/*.json")

if not json_files:
    print("Nenhum arquivo encontrado em 'data/raw/'. Execute o trigger_ingestion.py primeiro.")
    exit()

# Carrega todos os JSONs da RAW
raw_data = []
for file_path in json_files:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data.extend(json.load(f))

raw_df = pl.DataFrame(raw_data)

# TRANSFORMACÃO PARA A CAMADA SILVER (Usando Expressões Polars)
# Funções auxiliares para extrair os atributos aninhados de forma segura
def get_type(index_num: int):
    return (
        pl.col("types")
        .list.get(index_num, null_on_oob=True)
        .struct.field("type")
        .struct.field("name")
    )

def get_stat(stat_name: str):
    return (
        pl.col("stats")
        .list.eval(
            pl.element().filter(
                pl.element().struct.field("stat").struct.field("name") == stat_name
            )
        )
        .list.first()
        .struct.field("base_stat")
    )

silver_df = raw_df.select([
    pl.col("id").alias("pokemon_id"),
    pl.col("name").str.to_lowercase().alias("nome"),
    pl.col("height").alias("altura_dm"),
    pl.col("weight").alias("peso_hg"),
    pl.col("types").list.len().alias("qtd_tipos"),
    get_type(0).alias("tipo_primario"),
    get_type(1).alias("tipo_secundario"),
    get_stat("hp").alias("stat_hp"),
    get_stat("attack").alias("stat_ataque"),
    get_stat("defense").alias("stat_defesa"),
    get_stat("speed").alias("stat_velocidade"),
    pl.lit(datetime.now().isoformat()).alias("processed_at")
])

# Grava na Camada Silver em Parquet
silver_df.write_parquet("data/silver/pokemons.parquet")
print("[SILVER] Dados processados e salvos em 'data/silver/pokemons.parquet'")
