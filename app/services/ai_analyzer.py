# app/services/ai_analyzer.py (Com validação JSON)
import os
import openai
import json
from flask import current_app
from . import football_api

client = None
try:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("A chave da API da OpenAI não foi encontrada nas variáveis de ambiente.")
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    print("✅ Cliente da OpenAI configurado com sucesso.")
except Exception as e:
    print(f"❌ ERRO: Não foi possível configurar a IA da OpenAI. Erro: {e}")

def gerar_analise_ia(partida):
    """Gera a análise de uma partida usando dados da API e o modelo da OpenAI."""
    if not client:
        current_app.logger.error("Tentativa de gerar análise com o cliente da OpenAI não configurado.")
        return None, "Erro na IA: IA não configurada."
    
    # 1. Buscar dados da API (Resultados e IDs)
    ultimos_jogos_mandante, mandante_ids = football_api.buscar_ultimos_jogos(partida['mandante_id'])
    ultimos_jogos_visitante, visitante_ids = football_api.buscar_ultimos_jogos(partida['visitante_id'])
    confrontos_diretos, h2h_ids = football_api.buscar_h2h(partida['mandante_id'], partida['visitante_id'])

    # 2. Buscar estatísticas detalhadas usando os IDs
    stats_mandante_txt = football_api.buscar_estatisticas_jogos(mandante_ids)
    stats_visitante_txt = football_api.buscar_estatisticas_jogos(visitante_ids)
    stats_h2h_txt = football_api.buscar_estatisticas_jogos(h2h_ids)

    # 3. Preparar dados formatados para o JSON de saída
    dados_formatados_mandante = ultimos_jogos_mandante.replace("\n", "\\n")
    dados_formatados_visitante = ultimos_jogos_visitante.replace("\n", "\\n")
    dados_formatados_h2h = confrontos_diretos.replace("\n", "\\n")
    stats_formatados_mandante = stats_mandante_txt.replace("\n", "\\n")
    stats_formatados_visitante = stats_visitante_txt.replace("\n", "\\n")
    stats_formatados_h2h = stats_h2h_txt.replace("\n", "\\n")


    # 4. Prompt final combinando o original com a nova secção
    prompt = f"""
    Você é o "Mat, o Analista", um especialista em apostas esportivas CONSERVADORAS.
    Crie um relatório pré-jogo para a partida entre {partida['mandante_nome']} e {partida['visitante_nome']}, 
    utilizando os dados fornecidos e preenchendo a estrutura JSON obrigatória.

    ---
    **PARTE 1: DADOS PARA ANÁLISE PRINCIPAL**
    
    - Últimos 5 jogos de {partida['mandante_nome']}:
    {ultimos_jogos_mandante}

    - Últimos 5 jogos de {partida['visitante_nome']}:
    {ultimos_jogos_visitante}

    - Últimos 5 confrontos diretos:
    {confrontos_diretos}

    ⚠️ INSTRUÇÕES PARA A ANÁLISE PRINCIPAL (`analise_detalhada`):
    - Com base nos dados acima, faça uma análise focada no resultado da partida.
    - O campo "cenario_provavel" deve conter a sua recomendação PRINCIPAL e MAIS SEGURA.
    - Sugira 3 mercados conservadores e de baixa variância em "mercados_favoraveis", como:
      * Dupla Chance (1X, X2, 12)
      * Over/Under 1.5, 2.5, 3,5, 4.5 gols
      * Handicap +1.5 ou +2.5
    - Sugerir mercados de risco como "Over/Under 2.5 gols", "Resultado", "Handicap -1.5, -2,5...", Apenas se existir um padrão MUITO FORTE e justificado.
    - O objetivo é **tendência**, **segurança** e **consistência**, não ousadia. Apenas se estiver muito clara, forte e justificável a tendência.

    ---
    **PARTE 2: DADOS PARA OUTRAS ANÁLISES (ESTATÍSTICAS)**

    - Estatísticas dos últimos 5 jogos de {partida['mandante_nome']} (C=Escanteios, K=Cartões, O=Impedimentos):
    {stats_mandante_txt}
    - Estatísticas dos últimos 5 jogos de {partida['visitante_nome']}:
    {stats_visitante_txt}
    - Estatísticas dos últimos 5 confrontos diretos:
    {stats_h2h_txt}.
    
    ⚠️ INSTRUÇÕES PARA AS OUTRAS ANÁLISES (`outras_analises`):
    - Com base nos dados de estatísticas, faça uma análise QUANTITATIVA.
    - Calcule a média de escanteios e cartões para as equipas.
    - Sugira um mercado claro de Over/Under (ex: "Over 8.5 escanteios").
    - Se a tendência não for clara, afirme explicitamente: "Nenhuma tendência clara identificada".

    ---
    **ESTRUTURA JSON OBRIGATÓRIA:**
    Preencha TODOS os campos do JSON abaixo com as suas análises.

    {{
      "analise_detalhada": {{
        "desempenho_mandante": {{"forma": "...", "ponto_forte": "...", "ponto_fraco": "..."}},
        "desempenho_visitante": {{"forma": "...", "ponto_forte": "...", "ponto_fraco": "..."}},
        "confronto_direto": "...",
        "informacoes_relevantes": "...",
        "mercados_favoraveis": [
            {{"mercado": "...", "justificativa": "..."}}
        ],
        "cenario_provavel": {{"mercado": "Esta é a sua principal e mais segura recomendação.", "justificativa": "..."}}
      }},
      "outras_analises": {{
          "analise_escanteios": "Análise quantitativa de escanteios com sugestão de mercado Over/Under.",
          "analise_cartoes": "Análise quantitativa de cartões com sugestão de mercado Over/Under.",
          "analise_impedimentos": "Breve análise sobre a tendência de impedimentos."
      }},
      "dados_utilizados": {{
        "ultimos_jogos_mandante": "{dados_formatados_mandante}",
        "ultimos_jogos_visitante": "{dados_formatados_visitante}",
        "ultimos_confrontos_diretos": "{dados_formatados_h2h}",
        "stats_ultimos_jogos_mandante": "{stats_formatados_mandante}",
        "stats_ultimos_jogos_visitante": "{stats_formatados_visitante}",
        "stats_ultimos_confrontos_diretos": "{stats_formatados_h2h}"
      }}
    }}
    """

    try:
        current_app.logger.info(f"Gerando análise de IA para: {partida['mandante_nome']} vs {partida['visitante_nome']}")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é um analista de futebol que gera análises detalhadas em formato JSON, seguindo duas lógicas distintas (análise de resultado e análise de estatísticas)."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        response_text = chat_completion.choices[0].message.content
        response_json = json.loads(response_text)
        return response_json, None

    except json.JSONDecodeError as e:
        current_app.logger.error(f"Erro ao validar JSON da IA para {partida['mandante_nome']} vs {partida['visitante_nome']}: {e}")
        current_app.logger.warning(f"--- JSON INVÁLIDO RECEBIDO --- \n{response_text}\n-----------------------------")
        return None, "Erro no formato da resposta da IA. Não foi possível decodificar o JSON."
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar análise da IA para {partida['mandante_nome']} vs {partida['visitante_nome']}: {e}")
        return None, f"Não foi possível obter a análise da IA. Detalhes: {str(e)}"