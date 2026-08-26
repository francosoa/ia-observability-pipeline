import os
import duckdb
from google import genai
from google.genai import types
from pipeline.run_quality_logs import raiz_projeto

# -------------------------------------------------------------
# CONFIGURAÇÕES
# -------------------------------------------------------------
os.environ["GEMINI_API"] = ""
RAG_FILE_PATH = f"{raiz_projeto}/rag_files/documents.md"
# -------------------------------------------------------------

print("[AGENTE RAG INTELIGENTE] Analisando logs de observabilidade...")

# 1. Carrega o contexto atual do RAG
if os.path.exists(RAG_FILE_PATH):
    with open(RAG_FILE_PATH, "r", encoding="utf-8") as f:
        rag_context = f.read()
else:
    rag_context = "# Base de Conhecimento Inicial\n"

# 2. Lê a tabela de observabilidade local via DuckDB
con = duckdb.connect()
logs_df = con.execute("""
    SELECT column_name, rule_type, rule_description, failed_records_count, sample_failed_data, severity
    FROM 'observability/quality_logs.parquet'
    ORDER BY created_at DESC LIMIT 3
""").df()

if logs_df.empty:
    print("✨ Nenhum erro encontrado na Pokédex. Todos os dados estão íntegros!")
    exit()

logs_json = logs_df.to_json(orient="records")

# 3. Prompt estruturado para instruir a IA a diagnosticar e formatar o aprendizado
system_instruction = f"""
Você é um Agente Sênior de Observabilidade e Engenharia de Dados.
Analise os erros da tabela de observabilidade cruzando-os com o nosso manual abaixo.

---
### 📚 BASE DE CONHECIMENTO ATUAL (RAG):
{rag_context}
---

Instruções estritas de resposta:
Divida sua resposta exatamente nestas duas partes:

PARTE 1 - O RELATÓRIO DE ANÁLISE:
- **🛠️ DIAGNÓSTICO TÉCNICO:** Causa raiz e correção no Polars.
- **📊 IMPACTO DE NEGÓCIO:** Consequências nos relatórios.

PARTE 2 - O REGISTRO DE APRENDIZADO (Obrigatório para atualização automática):
Forneça um bloco de texto markdown limpo e resumido que deva ser adicionado ao manual de governança com o novo incidente, estruturado exatamente assim:
### Incidente Registrado: [Nome do Tipo de Falha / Coluna]
- **Problema Detectado:** [Resumo claro do erro]
- **Tipo / Severidade:** [Tipo da regra e severidade]
- **Solução Recomendada:** [Como o pipeline deve tratar isso]
"""

user_prompt = f"Aqui estão os logs de falhas recentes:\n{logs_json}"

# 4. Chamada ao Gemini 3.6 Flash
client = genai.Client()

response = client.models.generate_content(
    model='gemini-3.6-flash',
    contents=user_prompt,
    config=types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
    ),
)

resposta_ia = response.text
print("\n" + resposta_ia)

# 5. AUTO-ATUALIZAÇÃO DO RAG (Feedback Loop)
# Vamos extrair e anexar o aprendizado gerado pela IA de volta ao arquivo Markdown
print("\n[RAG] Atualizando a base de conhecimento corporativa com o novo aprendizado...")

novo_aprendizado = f"\n\n## Histórico de Incidentes Aprendidos\n{resposta_ia}"

with open(RAG_FILE_PATH, "a", encoding="utf-8") as f:
    f.write(novo_aprendizado)

print("[RAG] Arquivo 'knowledge/data_governance_rules.md' atualizado com sucesso!")