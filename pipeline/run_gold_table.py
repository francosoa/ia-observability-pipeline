import os
import json
from pathlib import Path
import polars as pl
from datetime import datetime
from run_quality_logs import read_parquet, raiz_projeto

PATH_GOLD = raiz_projeto / "data" / "gold"

df_silver = read_parquet()

clean_pokemon = df_silver.filter(
    (pl.col("altura_dm") > 0) & 
    (pl.col("peso_hg") > 0) & 
    (pl.col("qtd_tipos") > 0) &
    (pl.col("stat_hp").is_between(1, 255))
)

gold_df = clean_pokemon.group_by("tipo_primario").agg([
    pl.count("pokemon_id").alias("total_pokemons"),
    pl.mean("stat_hp").alias("media_hp"),
    pl.mean("stat_ataque").alias("media_ataque"),
    pl.mean("stat_defesa").alias("media_defesa")
])

gold_df.write_parquet(f"{PATH_GOLD}/stats_by_type.parquet")
print("[GOLD] Tabela agregada salva em 'data/gold/stats_by_type.parquet'\n")