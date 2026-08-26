# ia-observability-pipeline


## 🧭 Visão geral

Este projeto é um **laboratório/POC de Data Quality + Observabilidade + IA Generativa**, que simula um pipeline de dados real (usando a **PokéAPI** como fonte de dados de teste) para demonstrar um ciclo completo de:

1. **Ingestão de dados** via API (com possibilidade de **injetar anomalias propositalmente**, útil para testar regras de qualidade).
2. **Processamento e validação** dos dados (Polars/PySpark/Pandas).
3. **Registro de observabilidade** dos erros de qualidade encontrados em uma tabela (Parquet, lida via DuckDB).
4. **Análise automática com IA (agente RAG)**: um script lê os logs de qualidade, cruza com uma base de conhecimento em Markdown (RAG) e usa o **Google Gemini** para diagnosticar a causa raiz, sugerir correção e gerar um novo registro de aprendizado.
5. **Feedback loop**: o aprendizado gerado pela IA é **anexado automaticamente** ao arquivo de conhecimento (`rag_files/documents.md`), fazendo a base de governança de dados crescer sozinha a cada novo incidente.

Em resumo: é um pipeline de dados instrumentado com um **agente de IA que atua como "engenheiro de observabilidade sênior"**, aprendendo com os próprios erros do pipeline.

---

## 🏗️ Estrutura do repositório

```
ia-observability-pipeline/
├── app/                 # Provável API (FastAPI) - endpoint de ingestão
├── data/                # Dados brutos/processados
├── observability/       # Logs de qualidade de dados (ex: quality_logs.parquet)
├── pipeline/            # Lógica de processamento e regras de qualidade
├── rag_files/           # Base de conhecimento (RAG) em Markdown
├── agent_insights.py    # Agente de IA que analisa logs e atualiza o RAG
├── trigger_ingestion.py # Script para disparar a ingestão via API
├── requirements.txt     # Dependências Python
└── .gitignore
```

> As pastas `app/`, `data/`, `observability/` e `pipeline/` não puderam ter seus arquivos individuais listados neste momento (a navegação em árvore do GitHub bloqueou o acesso automatizado), mas seus papéis foram inferidos pelo uso que o código faz delas (ver seção "Como as peças se conectam"). Posso detalhar qualquer uma delas se você me passar o link direto do arquivo.

---

## ⚙️ Stack técnica (via `requirements.txt`)

| Categoria | Bibliotecas |
|---|---|
| API / Web | `fastapi`, `starlette`, `uvicorn`, `httpx`, `requests` |
| Processamento de dados | `pandas`, `polars`, `pyspark` (+ `py4j`), `numpy` |
| Banco analítico local | `duckdb` (consulta direto em arquivos Parquet) |
| IA / LLM | `google-genai` (Gemini), `ollama` (LLM local) |
| Validação de dados | `pydantic`, `pydantic_core`, `annotated-doc` |
| Utilitários | `python-dateutil`, `tzdata`, `click`, `colorama` |

Combinação que sugere: **ingestão via API → processamento distribuído/columnar (Spark/Polars) → validação com Pydantic → consulta analítica com DuckDB → enriquecimento com LLM (Gemini e/ou Ollama local)**.

---

## 🔗 Como as peças se conectam

### 1. Ingestão (`trigger_ingestion.py`)
```python
import requests
API_URL = "http://127.0.0.1:8000/v1/ingest/pokemons?limit=50&inject_anomalies=true"
response = requests.post(API_URL)
print("Resposta da API:", response.json())
```
- Dispara um `POST` contra uma API local (presumivelmente construída em `app/` com FastAPI, rodando em `localhost:8000`).
- O endpoint `/v1/ingest/pokemons` busca dados (da PokéAPI, dado o nome) e o parâmetro `inject_anomalies=true` **injeta erros propositais nos dados** — um recurso pensado para testar as regras de qualidade do pipeline de forma controlada e repetível.

### 2. Pipeline e observabilidade (`pipeline/`, `observability/`)
- O módulo `pipeline.run_quality_logs` expõe uma variável `raiz_projeto` (caminho raiz do projeto), usada por outros scripts para localizar arquivos.
- O pipeline roda regras de qualidade sobre os dados ingeridos e grava os resultados em `observability/quality_logs.parquet`, com o seguinte schema (inferido da query DuckDB usada em `agent_insights.py`):

| Coluna | Descrição |
|---|---|
| `column_name` | Coluna do dataset onde a regra foi aplicada |
| `rule_type` | Tipo da regra de qualidade violada |
| `rule_description` | Descrição da regra |
| `failed_records_count` | Quantidade de registros que falharam |
| `sample_failed_data` | Amostra dos dados que falharam |
| `severity` | Severidade do problema |
| `created_at` | Timestamp do log (usado para ordenação) |

### 3. Agente de IA (`agent_insights.py`)
Fluxo do script:
1. Carrega a base de conhecimento atual em `rag_files/documents.md` (RAG).
2. Consulta, via **DuckDB**, os 3 últimos registros de erro em `observability/quality_logs.parquet`.
3. Se não houver erros, encerra com uma mensagem de sucesso ("Pokédex" íntegra 🎮 — reforçando o tema Pokémon do projeto).
4. Se houver erros, monta um **prompt estruturado** instruindo a IA a atuar como "Agente Sênior de Observabilidade e Engenharia de Dados", cruzando os erros com a base RAG.
5. Chama o **Gemini** (`client.models.generate_content`, modelo `gemini-3.6-flash`) pedindo uma resposta em duas partes:
   - **Parte 1 — Relatório de análise:** diagnóstico técnico (causa raiz + correção em Polars) e impacto de negócio.
   - **Parte 2 — Registro de aprendizado:** um bloco Markdown padronizado, pronto para ser incorporado à base de governança.
6. **Fecha o loop de feedback**: anexa (`append`) a resposta da IA de volta ao arquivo `rag_files/documents.md`, fazendo a base de conhecimento crescer a cada execução.

### 4. Base de conhecimento (`rag_files/`)
- Arquivo `documents.md` funciona como uma "memória" incremental de incidentes de qualidade de dados, usada tanto como contexto de entrada (RAG) quanto como destino de escrita (auto-atualização).

---

## 🧩 Conceito central do projeto

O grande diferencial do repositório é o **loop fechado de observabilidade + IA generativa**:

```
Ingestão (com anomalias) → Pipeline detecta erros → Log em Parquet (DuckDB)
        ↑                                                     │
        │                                                     ▼
Base de conhecimento (RAG) ←── IA (Gemini) diagnostica e aprende
```

Isso é essencialmente um protótipo de **"self-healing data governance"**: em vez de um humano documentar manualmente cada incidente de qualidade de dados, a própria IA analisa, diagnostica e documenta o incidente na base de conhecimento corporativa, que por sua vez alimenta análises futuras (aprendizado cumulativo).

---

## 🚀 Como rodar (inferido a partir do código)

> Não há instruções oficiais de setup no README, mas o fluxo provável é:

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Subir a API de ingestão (provavelmente algo em app/, ex: app/main.py com uvicorn)
uvicorn app.main:app --reload

# 3. Disparar a ingestão de dados (com anomalias injetadas)
python trigger_ingestion.py

# 4. Rodar o pipeline de qualidade (gera observability/quality_logs.parquet)
python pipeline/run_quality_logs.py   # nome inferido, não confirmado

# 5. Rodar o agente de IA para analisar os logs e atualizar o RAG
python agent_insights.py
```

⚠️ É necessário configurar a variável de ambiente `GEMINI_API` (ou a autenticação padrão do SDK `google-genai`) — no código atual ela está inicializada como string vazia (`os.environ["GEMINI_API"] = ""`), o que é um ponto de atenção: a chave deveria vir de uma variável de ambiente real/`.env`, não hardcoded.

---

## 📌 Pontos de atenção observados no código

- **Chave de API vazia hardcoded** (`os.environ["GEMINI_API"] = ""`) em `agent_insights.py` — provavelmente um placeholder esquecido; o ideal seria carregar de `.env`/secret manager.
- **README essencialmente vazio** — falta documentação oficial de setup, arquitetura e propósito.
- Projeto tem cara de **estudo pessoal / portfólio / POC** (nome do repo, uso da PokéAPI como "dado de brincadeira", poucos commits), não de sistema em produção.

---

## ❓ Quer que eu aprofunde algo?

Como não consegui listar automaticamente os arquivos dentro de `app/`, `data/`, `observability/` e `pipeline/` (o GitHub bloqueou a navegação em árvore para acesso automatizado), esse MD foi montado com base nos arquivos que consegui abrir diretamente. Se você me passar os links diretos (formato `.../blob/main/pasta/arquivo.py`) de arquivos como:

- `app/main.py` (a API FastAPI)
- `pipeline/run_quality_logs.py`
- algum arquivo dentro de `data/`

eu completo o documento com os detalhes exatos de implementação em vez de inferências.