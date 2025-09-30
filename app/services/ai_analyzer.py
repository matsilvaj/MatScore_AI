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

def gerar_analise_ia(partida, dados_para_analise): # <-- ALTERAÇÃO AQUI
    """Gera a análise de uma partida usando o modelo da OpenAI."""
    if not client:
        current_app.logger.error("Tentativa de gerar análise com o cliente da OpenAI não configurado.")
        return None, "Erro na IA: IA não configurada."
    
    # Esta linha agora funcionará corretamente
    dados_json_str = json.dumps(dados_para_analise, indent=2)

    prompt = f"""
    Você é o "Mat, o Analista", um especialista em apostas esportivas que segue um sistema rigoroso e conservador baseado em dados quantitativos. Sua análise deve ser baseada EXCLUSIVAMENTE nos dados fornecidos.

    Crie um relatório pré-jogo para a partida entre {partida['mandante_nome']} e {partida['visitante_nome']}.

    ⚠️ INSTRUÇÕES DE ANÁLISE (SIGA ESTA LÓGICA PASSO A PASSO):

    **PASSO 1: Análise de Gols (Over/Under)**
    1.  Observe a quantidade de gols nos "ultimos_jogos_mandante", "ultimos_jogos_visitante" e "confrontos_diretos", analise "total_gols" de cada jogo e encontre padrões.
    2.  Para sugerir um mercado de "Over", a tendência de jogos com muitos gols deve ser consistente nos QUATROS conjuntos de dados.
        - Exemplo de Lógica Conservadora: Se em 4 de 5 jogos a linha de mais 1.5 gols foi batida, a sugestão conservadora é "Mais de 1.5 Gols".
    3.  Para sugerir um mercado de "Under", a lógica é a mesma. A tendência de poucos gols deve ser consistente nos QUATROS conjuntos de dados.
        - Exemplo de Lógica Conservadora: Se em 4 de 5 jogos a linha de menos 3.5 gols foi batida, a sugestão segura é "Menos de 3.5 Gols".
    4.  **REGRA CRÍTICA:** Se as tendências de gols "total_gols" de cada jogo forem diferentes entre os últimos jogos e o confronto direto, NÃO SUGIRA um mercado de gols. A consistência é obrigatória.

    **PASSO 2: Análise do Vencedor (Resultado/Dupla Chance/Handicap)**
    1.  **O Confronto Direto (H2H) tem o maior peso para este mercado.**
    2.  Se o H2H mostra uma tendência clara de vitórias ou empates para uma equipe (ex: 4 de 5 resultados favoráveis), sugira "Dupla Chance" para essa equipe.
    3.  Se o H2H mostra um domínio absoluto de uma equipe (ex: venceu os últimos 4 ou 5 jogos), sugira "Vitória" para essa equipe.
    4.  Se o H2H é equilibrado com vencedores diferentes, analise a "diferenca_gols" de cada jogo (handicap). Se houver um padrão consistente de vitórias por uma margem pequena, sugira um mercado de "Handicap Positivo" (ex: +1.5 ou 2.5) para a equipe que costuma perder por pouco ou para o time da casa.
    5.  **REGRA CRÍTICA:** Se não houver confronto direto evite sugerir mercados de vencedor. É necessário ter dados de H2H para tomar uma decisão para este mercado.

    **PASSO 3: Análise de Escanteios e Cartões**
    1. **Análise o total de escanteios e o total de cartões para cada partida individualmente dos ultimos jogos de ambas as equipas e nos confrontos diretos.**
    2. Procure um padrão consistente nos totais. A tendência (consistentemente acima ou abaixo de um número) deve repetir-se na maioria dos jogos e ser semelhante nos quatros conjuntos de dados (forma do mandante, forma do visitante e H2H).
    3. Se encontrar um padrão claro, sugira um mercado com uma margem de segurança.
        Exemplo Over: Se os totais de escanteios são consistentemente 10, 11, 12, uma sugestão conservadora é "Mais de 8.5 Escanteios".
        Exemplo Under: Se os totais de cartões são consistentemente 3, 4, 4, uma sugestão conservadora é "Menos de 5.5 Cartões".
    **REGRA CRÍTICA: Se não houver um padrão claro e consistente nos três cenários, NÃO SUGIRA um mercado de escanteios ou cartões.**

    **PASSO 4: Seleção do Cenário Mais Provável e Mercado Principal**
    1.  Depois de analisar todos os mercados nos passos anteriores, Selecione UM mercado que você considera o mais seguro e com maior probabilidade de acontecer. Este será o seu "mercado_principal".
    3.  **REGRA CRÍTICA DE CONSISTÊNCIA:** O valor que você definir em "cenário_provavel" DEVE SER EXATAMENTE O MESMO mercado que você descrever em "cenário_provavel". Devem estar perfeitamente alinhados.

    DADOS ESTATÍSTICOS PARA ANÁLISE:
    ```json
    {dados_json_str}
    ```
    ---
    Com base na sua análise passo a passo dos dados acima, preencha a seguinte estrutura JSON obrigatória:
    {{
      "mercado_principal": "O mercado mais seguro encontrado após seguir a sua lógica.",
      "analise_detalhada": {{
        "desempenho_mandante": {{"forma": "Descreva a forma recente com base nos dados de gols.", "ponto_forte": "...", "ponto_fraco": "..." }},
        "desempenho_visitante": {{"forma": "Descreva a forma recente com base nos dados de gols.", "ponto_forte": "...", "ponto_fraco": "..." }},
        "confronto_direto": "Descreva a tendência do H2H, focando no vencedor e no padrão de gols.",
        "informacoes_relevantes": "Destaque as tendências consistentes que você encontrou ou a falta delas (ex: 'Tendência de Over consistente nos três cenários' ou 'Tendência de gols inconsistente entre forma e H2H').",
        "mercados_favoraveis": [
            {{"mercado": "...", "justificativa": "Justifique com base nas regras que você seguiu." }},
            {{"mercado": "...", "justificativa": "..." }},
            {{"mercado": "...", "justificativa": "..." }}
        ],
        "cenario_provavel": {{"mercado": "...", "justificativa": "Justifique o cenário mais provável com base na sua análise." }}
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
            temperature=0.5        )
        
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