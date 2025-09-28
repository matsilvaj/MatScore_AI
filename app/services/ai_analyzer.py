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
    """Gera a análise de uma partida usando o modelo da OpenAI."""
    if not client:
        current_app.logger.error("Tentativa de gerar análise com o cliente da OpenAI não configurado.")
        return None, "Erro na IA: IA não configurada."

    prompt = f"""
    Você é o "Mat, o Analista", um especialista em apostas esportivas CONSERVADORAS.
    Crie um relatório pré-jogo para a partida entre {partida['mandante_nome']} e {partida['visitante_nome']}.

    ⚠️ INSTRUÇÕES IMPORTANTES:
    - Sugira APENAS mercados conservadores e de baixa variância, como:
      * Dupla Chance (1X, X2, 12)
      * Under/Over gols, escanteios e cartões
      * Handicap +1.5, +2.5...
      (Esses são exemplos, adapte conforme os dados) 
    - Sugerir mercados de risco como "Over/Under 2.5 gols", "Resultado", "Handicap -1.5, -2,5..."..., Apenas se existir um padrão MUITO FORTE e justificado.
    - O objetivo é **tendência**, **segurança** e **consistência**, não ousadia. Apenas se estiver muito clara, forte e justificável a tendência.

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
      }}
    }}
    """

    try:
        current_app.logger.info(f"Gerando análise de IA para: {partida['mandante_nome']} vs {partida['visitante_nome']}")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é um analista de futebol que gera análises detalhadas em formato JSON."},
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