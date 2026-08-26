import os
import json
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query

os.makedirs("data/raw", exist_ok=True)

app = FastAPI(title="PokéAPI Ingestion Service", version="1.0")

POKEAPI_URL = "https://pokeapi.co/api/v2/pokemon/"

@app.post("/v1/ingest/pokemons")
def ingest_pokemons(
    limit: int = Query(default=20, ge=1, le=151),
    inject_anomalies: bool = Query(default=True, description="Injeta bugs propositais para testar a IA")
):
    """
    Consome os N primeiros Pokémons da PokéAPI e salva na camada RAW.
    """
    raw_pokemons = []
    
    print(f"⚡ Baixando {limit} Pokémons da PokéAPI...")
    for pok_id in range(1, limit + 1):
        try:
            res = requests.get(f"{POKEAPI_URL}{pok_id}", timeout=10)
            if res.status_code == 200:
                raw_pokemons.append(res.json())
        except Exception as e:
            print(f"Erro ao baixar Pokémon ID {pok_id}: {e}")

    # Injeta anomalias sintéticas para testar os alertas da Tabela de Observabilidade
    if inject_anomalies:
        print("👾 Injetando dados corrompidos para teste de observabilidade...")
        raw_pokemons.append({
            "id": 0,
            "name": "missingno_bug",
            "height": 0,          # ERRO: Altura inválida
            "weight": -99,        # ERRO: Peso negativo
            "types": [],          # ERRO: Nenhum elemento associado
            "stats": [
                {"base_stat": 999, "stat": {"name": "hp"}},      # ERRO: HP acima de 255
                {"base_stat": -10, "stat": {"name": "attack"}}   # ERRO: Ataque negativo
            ]
        })

    # Grava na Landing Zone (data/raw)
    partition = datetime.now().strftime("%Y%m%d")
    filepath = f"data/raw/{partition}_pokemons_batch.json"
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(raw_pokemons, f, indent=2)

    return {
        "status": "SUCCESS",
        "file_created": filepath,
        "total_records": len(raw_pokemons),
        "anomalies_injected": inject_anomalies
    }