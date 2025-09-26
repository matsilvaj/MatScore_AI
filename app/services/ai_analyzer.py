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
    
    # 1. Buscar dados da API
    ultimos_jogos_mandante = football_api.buscar_ultimos_jogos(partida['mandante_id'])
    ultimos_jogos_visitante = football_api.buscar_ultimos_jogos(partida['visitante_id'])
    confrontos_diretos = football_api.buscar_h2h(partida['mandante_id'], partida['visitante_id'])

    # 2. Preparar dados formatados
    dados_formatados_mandante = ultimos_jogos_mandante.replace("\n", "\\n")
    dados_formatados_visitante = ultimos_jogos_visitante.replace("\n", "\\n")
    dados_formatados_h2h = confrontos_diretos.replace("\n", "\\n")

    # 3. Prompt focado em mercados conservadores
    prompt = f"""
    Você é o "Mat, o Analista", um especialista em apostas esportivas CONSERVADORAS.
    Crie um relatório pré-jogo para a partida entre {partida['mandante_nome']} e {partida['visitante_nome']}, 
    utilizando os dados fornecidos. 

    ⚠️ INSTRUÇÕES IMPORTANTES:
    - Sugira APENAS mercados conservadores e de baixa variância, como:
      * Dupla Chance (1X, X2, 12)
      * Under 3.5, 4.5... | Over 0.5, 1.5...
      * Handicap +1.5, +2.5...
    - Sugerir mercados de risco como "Mais de 2.5 gols", "Resultado", "Handicap -0,5, ...", Apenas se existir um padrão muito forte e justificado.
    - O objetivo é **segurança** e **consistência**, não ousadia.

    DADOS PARA ANÁLISE:
    - Últimos 5 jogos de {partida['mandante_nome']}:
    {ultimos_jogos_mandante}

    - Últimos 5 jogos de {partida['visitante_nome']}:
    {ultimos_jogos_visitante}

    - Últimos 5 confrontos diretos:
    {confrontos_diretos}

    ---
    Estrutura JSON obrigatória:
    {{
      "mercado_principal": "Nome do mercado mais conservador",
      "analise_detalhada": {{
        "desempenho_mandante": {{"forma": "...", "ponto_forte": "...", "ponto_fraco": "..." }},
        "desempenho_visitante": {{"forma": "...", "ponto_forte": "...", "ponto_fraco": "..." }},
        "confronto_direto": "...",
        "informacoes_relevantes": "...",
        "mercados_favoraveis": [
            {{"mercado": "...", "justificativa": "..." }},
            {{"mercado": "...", "justificativa": "..." }},
            {{"mercado": "...", "justificativa": "..." }}
        ],
        "cenario_provavel": {{"mercado": "...", "justificativa": "..." }}
      }},
      "dados_utilizados": {{
        "ultimos_jogos_mandante": "{dados_formatados_mandante}",
        "ultimos_jogos_visitante": "{dados_formatados_visitante}",
        "ultimos_confrontos_diretos": "{dados_formatados_h2h}"
      }}
    }}
    """

    try:
        current_app.logger.info(f"Gerando análise de IA para: {partida['mandante_nome']} vs {partida['visitante_nome']}")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é um analista esportivo que gera análises CONSERVADORAS em formato JSON."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        response_text = chat_completion.choices[0].message.content
        response_json = json.loads(response_text) # Valida e converte a string JSON para um objeto Python
        return response_json, None # Retorna o objeto JSON, não a string

    except json.JSONDecodeError as e:
        current_app.logger.error(f"Erro ao validar JSON da IA para {partida['mandante_nome']} vs {partida['visitante_nome']}: {e}")
        current_app.logger.warning(f"--- JSON INVÁLIDO RECEBIDO --- \n{response_text}\n-----------------------------")
        return None, "Erro no formato da resposta da IA. Não foi possível decodificar o JSON."
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar análise da IA para {partida['mandante_nome']} vs {partida['visitante_nome']}: {e}")
        return None, f"Não foi possível obter a análise da IA. Detalhes: {str(e)}"
