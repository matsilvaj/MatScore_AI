# app/services/ai_analyzer.py
import os
import openai
from flask import current_app

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
    """Gera a análise de uma partida usando o modelo da OpenAI (ChatGPT)."""
    if not client:
        current_app.logger.error("Tentativa de gerar análise com o cliente da OpenAI não configurado.")
        return "Erro na IA", "IA não configurada."
    
    prompt = f"""
    Você é o "Mat, o Analista", um especialista em dados esportivos. Sua tarefa é criar um relatório de análise pré-jogo para a partida entre {partida['mandante_nome']} e {partida['visitante_nome']}.

    Sua resposta deve ser 100% neutra e informativa, preenchendo a estrutura JSON solicitada. Baseie-se em conhecimentos gerais e estatísticos do futebol para preencher os campos.

    SEÇÕES DA ANÁLISE:
    1.  Análise de Desempenho Recente ({partida['mandante_nome']}): Forma, Ponto Forte, Ponto Fraco.
    2.  Análise de Desempenho Recente ({partida['visitante_nome']}): Forma, Ponto Forte, Ponto Fraco.
    3.  Análise do Confronto Direto: Análise detalhada do H2H (histórico de confrontos).
    4.  Informações Relevantes: Comentários sobre fator casa, momento, lesões, etc.
    5.  Mercados Favoráveis da Partida: 3 mercados com justificativas.
    6.  Cenário de Maior Probabilidade: O mercado MAIS CONSERVADOR com justificativa final.
    7.  Base de Dados Utilizada: (Opcional) Liste os últimos jogos de cada equipe e H2H se tiver essa informação.

    ---
    ATENÇÃO: Responda OBRIGATORIAMENTE em formato JSON. A sua resposta final deve ser um único bloco de código JSON, sem nenhum texto ou formatação fora dele. Antes de finalizar, valide a sintaxe do seu JSON para garantir que todas as vírgulas, aspas e chaves estão corretas.

    A estrutura deve ser a seguinte:
    {{
      "mercado_principal": "Nome do mercado de maior probabilidade",
      "analise_detalhada": {{
        "desempenho_mandante": {{"forma": "...", "ponto_forte": "...", "ponto_fraco": "..."}},
        "desempenho_visitante": {{"forma": "...", "ponto_forte": "...", "ponto_fraco": "..."}},
        "confronto_direto": "...",
        "informacoes_relevantes": "...",
        "mercados_favoraveis": [
            {{"mercado": "...", "justificativa": "..."}},
            {{"mercado": "...", "justificativa": "..."}},
            {{"mercado": "...", "justificativa": "..."}}
        ],
        "cenario_provavel": {{"mercado": "...", "justificativa": "..."}}
      }},
      "dados_utilizados": {{
        "ultimos_jogos_mandante": "dd.mm.aaaa | ...\\ndd.mm.aaaa | ...",
        "ultimos_jogos_visitante": "dd.mm.aaaa | ...\\ndd.mm.aaaa | ...",
        "ultimos_confrontos_diretos": "dd.mm.aaaa | ...\\ndd.mm.aaaa | ..."
      }}
    }}
    """

    try:
        current_app.logger.info(f"Gerando análise de IA para: {partida['mandante_nome']} vs {partida['visitante_nome']}")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Você é um analista de dados esportivos especialista em futebol.",
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-3.5-turbo", # Você pode escolher um modelo mais avançado se preferir
            response_format={ "type": "json_object" }
        )
        
        response_text = chat_completion.choices[0].message.content
        return response_text.strip(), None
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar análise da IA para {partida['mandante_nome']} vs {partida['visitante_nome']}: {e}")
        return None, f"Não foi possível obter a análise da IA. Detalhes: {str(e)}"