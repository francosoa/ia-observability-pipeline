import os
import json
from pathlib import Path
import polars as pl
from datetime import datetime
# Pega o diretório onde este script está (pipeline/) e sobe um nível (.parent) para a raiz
raiz_projeto = Path(__file__).resolve().parent.parent

def read_parquet():
    # Monta o caminho correto até o parquet
    caminho_parquet = raiz_projeto / "data" / "silver" / "pokemons.parquet"
    # Lê o arquivo
    return pl.read_parquet(caminho_parquet)


df_silver = read_parquet()

# REGRAS DE QUALIDADE DE DADOS (DATA QUALITY)
print("\n[QUALITY CHECK] Validando atributos com Polars...")
quality_logs = []

# Regra 1: Altura e Peso devem ser maiores que zero
bad_physics_df = df_silver.filter((pl.col("altura_dm") <= 0) | (pl.col("peso_hg") <= 0))
if len(bad_physics_df) > 0:
    samples = bad_physics_df.head(3).to_dicts()
    quality_logs.append({
        "log_id": f"LOG_PHYSICS_{int(datetime.now().timestamp())}",
        "table_name": "silver_pokemons",
        "column_name": "altura_dm/peso_hg",
        "rule_type": "PHYSICS_VIOLATION",
        "rule_description": "Pokémon com peso ou altura nula ou negativa.",
        "failed_records_count": len(bad_physics_df),
        "sample_failed_data": json.dumps(samples),
        "severity": "HIGH",
        "created_at": datetime.now().isoformat()
    })

# Regra 2: Pelo menos 1 Tipo registrado
bad_types_df = df_silver.filter(pl.col("qtd_tipos") == 0)
if len(bad_types_df) > 0:
    samples = bad_types_df.head(3).to_dicts()
    quality_logs.append({
        "log_id": f"LOG_TYPE_{int(datetime.now().timestamp())}",
        "table_name": "silver_pokemons",
        "column_name": "qtd_tipos",
        "rule_type": "MISSING_ELEMENT",
        "rule_description": "Pokémon sem nenhum elemento/tipo associado.",
        "failed_records_count": len(bad_types_df),
        "sample_failed_data": json.dumps(samples),
        "severity": "CRITICAL",
        "created_at": datetime.now().isoformat()
    })

# Regra 3: Atributos de Batalha (HP e Ataque entre 1 e 255)
bad_stats_df = df_silver.filter(
    (pl.col("stat_hp") < 1) | (pl.col("stat_hp") > 255) |
    (pl.col("stat_ataque") < 1) | (pl.col("stat_ataque") > 255)
)
if len(bad_stats_df) > 0:
    samples = bad_stats_df.head(3).to_dicts()
    quality_logs.append({
        "log_id": f"LOG_STATS_{int(datetime.now().timestamp())}",
        "table_name": "silver_pokemons",
        "column_name": "stat_hp/stat_ataque",
        "rule_type": "OUT_OF_BOUNDS",
        "rule_description": "Atributos de batalha fora dos limites válidos (1 - 255).",
        "failed_records_count": len(bad_stats_df),
        "sample_failed_data": json.dumps(samples),
        "severity": "MEDIUM",
        "created_at": datetime.now().isoformat()
    })

# GRAVAÇÃO DA TABELA DE OBSERVABILIDADE
obs_filepath = raiz_projeto / "observability" / "quality_logs.parquet"

if quality_logs:
    new_obs_df = pl.DataFrame(quality_logs)
    
    # Se a tabela de observabilidade já existir, acumula os novos erros
    if os.path.exists(obs_filepath):
        existing_obs_df = pl.read_parquet(obs_filepath)
        final_obs_df = pl.concat([existing_obs_df, new_obs_df])
    else:
        final_obs_df = new_obs_df
        
    final_obs_df.write_parquet(obs_filepath)
    print(f"⚠️ [OBSERVABILIDADE] {len(quality_logs)} anomalia(s) registrada(s) em '{obs_filepath}'")