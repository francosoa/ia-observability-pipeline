## Caracteristicas importantes:
1. O Charmander é um Pokémon do tipo Fire, conhecido por sua aparência de pequeno lagarto e pela chama que queima constantemente na ponta de sua cauda. A chama é uma característica importante de sua vida: acredita-se que ela indique sua condição física e emocional. Ele é um Pokémon Laranja, qualquer cor diferente dessa no meu dataset está errada. Na última medição, ele tinha Altura: 0,6 m e Peso: 8,5 kg. Suas evoluções são: Charmander → Charmeleon → Charizard

2. O Bulbasaur é um Pokémon do tipo Grass/Poison, conhecido pela pequena planta em forma de bulbo que carrega nas costas desde o nascimento. Ele é um Pokémon amigável, resistente e capaz de usar ataques relacionados a plantas e veneno. Ele é verde, com manchas verde-escuras. Suas evoluções passam por: Bulbasaur → Ivysaur → Venusaur

## Problemas que já aconteceram na base:
Alguns Pokémons retornaram valores negativos. Isso impactou a forma como os treinadores alimentavam seus pokémons e também impactou diretamente os dados da pokedex, fazendo com que os treinadores não capturasse o pokémon por achar que ele seria fraco demais

## Alguns problemas resolvidos:
Quando existe algum campo negativo, é utilizado o valor do dia anterior como base, caso não tenha retornado com erro. Se o valor passado também foi vazio, é necessário avaliar com o fornecedor da API ou consultar o sistema



## Histórico de Incidentes Aprendidos
PARTE 1 - O RELATÓRIO DE ANÁLISE:

- **🛠️ DIAGNÓSTICO TÉCNICO:** 
  - **Causa Raiz:** Ocorreu a ingestão de um registro anômalo/corrompido denominado `missingno_bug` (`pokemon_id`: 0). Este registro viola simultaneamente múltiplas regras de integridade do pipeline: 
    1. *Violação de Física (`PHYSICS_VIOLATION`):* Peso negativo (`peso_hg`: -99) e altura nula (`altura_dm`: 0).
    2. *Limites de Batalha (`OUT_OF_BOUNDS`):* Valores fora da faixa permitida de 1 a 255 (`stat_hp`: 999 e `stat_ataque`: -10).
    3. *Elementos Faltantes (`MISSING_ELEMENT`):* Ausência total de tipo primário e secundário (`qtd_tipos`: 0, `null`).
  - **Correção no Polars:** 
    Deve-se implementar uma etapa de validação e limpeza no Polars. Para tratar valores negativos/nulos de registros válidos, utiliza-se a estratégia de preenchimento com o valor do dia anterior (`forward fill`). Para registros corrompidos de origem (como ID 0 ou nomes nulos/bugados), o dado deve ser direcionado para quarentena.
    ```python
    import polars as pl

    # 1. Isolar registros corrompidos de sistema (ID 0)
    df_valid = df.filter(pl.col("pokemon_id") != 0)

    # 2. Corrigir valores negativos/inválidos com o dia anterior (forward fill) ou nulo para tratamento
    df_cleaned = df_valid.with_columns([
        pl.when(pl.col("peso_hg") <= 0)
          .then(None)
          .otherwise(pl.col("peso_hg"))
          .forward_fill()
          .alias("peso_hg"),
        
        pl.when(pl.col("altura_dm") <= 0)
          .then(None)
          .otherwise(pl.col("altura_dm"))
          .forward_fill()
          .alias("altura_dm"),

        pl.when((pl.col("stat_ataque") < 1) | (pl.col("stat_ataque") > 255))
          .then(None)
          .otherwise(pl.col("stat_ataque"))
          .forward_fill()
          .alias("stat_ataque")
    ])
    ```

- **📊 IMPACTO DE NEGÓCIO:** 
  - **Uso Incorreto da Pokedex e Abandono:** A exibição de métricas físicas e de batalha negativas/zeradas faz com que os treinadores julguem o Pokémon como fraco ou defeituoso, abandonando a captura.
  - **Riscos à Saúde dos Pokémons:** Conforme mapeado no manual de governança, o peso negativo compromete a rotina de alimentação prescrita pelos treinadores, afetando o desenvolvimento e a condição física dos Pokémons.
  - **Distorção em Analytics de Batalha:** Estatísticas aberrantes (como HP 999) corrompem as médias e os relatórios de balanceamento do sistema da Pokedex.

---

PARTE 2 - O REGISTRO DE APRENDIZADO (Obrigatório para atualização automática):

### Incidente Registrado: Corrupção de Dados / Registros Anômalos (missingno_bug)
- **Problema Detectado:** Ingestão do registro 'missingno_bug' (ID 0) contendo atributos físicos zerados/negativos (altura 0, peso -99), estatísticas fora do limite legal (HP 999, Ataque -10) e ausência de tipos associados.
- **Tipo / Severidade:** PHYSICS_VIOLATION / OUT_OF_BOUNDS / MISSING_ELEMENT - CRITICAL
- **Solução Recomendada:** O pipeline em Polars deve filtrar e mover para quarentena registros com ID 0 ou identificadores inválidos. Caso Pokémons válidos apresentem métricas negativas, aplicar fallback/forward fill recuperando o valor do dia anterior. Se o histórico persistir nulo, acionar o fornecedor da API.