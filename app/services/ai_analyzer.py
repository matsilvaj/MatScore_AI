import os
import google.generativeai as genai
from flask import current_app # Importa o current_app

model = None
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(model_name='gemini-1.5-pro-latest', tools=[genai.protos.Tool(google_search_retrieval=genai.protos.GoogleSearchRetrieval())])
    # Não usamos o logger aqui porque o app ainda não foi criado, mas o print inicial é aceitável.
    print("✅ Modelo de IA configurado com sucesso.")
except Exception as e:
    # O logger também não estaria disponível aqui.
    print(f"❌ ERRO: Não foi possível configurar a IA. Erro: {e}")

def gerar_analise_ia(partida):
    """Gera a análise de uma partida usando o modelo de IA, com logging."""
    if not model:
        current_app.logger.error("Tentativa de gerar análise com o modelo de IA não configurado.")
        return "Erro na IA", "IA não configurada."
    
    # ... (o seu prompt continua o mesmo) ...
    prompt = f"""
    Você é o "Mat, o Analista", um especialista em dados esportivos. Sua tarefa é criar um relatório de análise pré-jogo.
    INSTRUÇÃO DE BUSCA: Realize uma busca na web, focando em fontes de dados esportivos confiáveis como o Flashscore, para encontrar as últimas 5 partidas de {partida['mandante_nome']} e {partida['visitante_nome']}, e os últimos 5 confrontos diretos entre eles. Se não encontrar um histórico de confrontos diretos, afirme isso claramente na seção apropriada.

    Sua resposta deve ser 100% neutra e informativa, preenchendo a estrutura JSON solicitada.

    SEÇÕES DA ANÁLISE:
    1.  Análise de Desempenho Recente ({partida['mandante_nome']}): Forma, Ponto Forte, Ponto Fraco.
    2.  Análise de Desempenho Recente ({partida['visitante_nome']}): Forma, Ponto Forte, Ponto Fraco.
    3.  Análise do Confronto Direto: Análise detalhada do H2H.
    4.  Informações Relevantes: Comentários sobre fator casa, momento, lesões, etc.
    5.  Mercados Favoráveis da Partida: 3 mercados com justificativas.
    6.  Cenário de Maior Probabilidade: O mercado MAIS CONSERVADOR com justificativa final.
    7.  Base de Dados Utilizada: Lista dos últimos jogos de cada equipe e H2H.

    ---
    ATENÇÃO: Responda OBRIGATORIAMENTAMENTE em formato JSON. A sua resposta final deve ser um único bloco de código JSON, sem nenhum texto ou formatação fora dele. Antes de finalizar, valide a sintaxe do seu JSON para garantir que todas as vírgulas, aspas e chaves estão corretas.

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
        response = model.generate_content(prompt)
        return response.text.strip(), None
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar análise da IA para {partida['mandante_nome']} vs {partida['visitante_nome']}: {e}")
        return None, f"Não foi possível obter a análise da IA. Detalhes: {str(e)}"