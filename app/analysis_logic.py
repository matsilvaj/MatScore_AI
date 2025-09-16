import requests
from datetime import date
import time
import json
import os
import google.generativeai as genai

# --- CONFIGURAÇÕES GLOBAIS DA ANÁLISE ---
API_TOKEN_FD = os.getenv('API_TOKEN_FD')
HEADERS_FD = {"X-Auth-Token": API_TOKEN_FD}

# LISTA DE LIGAS GRATUITAS (PÚBLICAS)
LIGAS_GRATUITAS = {
    "Brasileirão Série A": "BSA"
}

# LISTA DE LIGAS PARA MEMBROS REGISTRADOS
LIGAS_MEMBROS = {
    "Brasileirão Série A": "BSA",
    "Premier League": "PL",
    "La Liga": "PD"
}

# --- CONFIGURAÇÃO DA IA ---
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)

    # Ativa a ferramenta de busca na internet (Grounding)
    ferramenta_de_busca = genai.protos.Tool(
        google_search_retrieval=genai.protos.GoogleSearchRetrieval()
    )

    # Configura o modelo para usar a ferramenta de busca
    model = genai.GenerativeModel(
      model_name='gemini-1.5-pro-latest', # Usando o modelo Pro, que é ótimo com ferramentas
      tools=[ferramenta_de_busca],
    )
    
    print("✅ Modelo de IA configurado com sucesso e com ferramenta de busca.")

except Exception as e:
    print(f"❌ ERRO: Não foi possível configurar a IA. Erro: {e}")
    model = None


# --- FUNÇÕES DE ANÁLISE ---
def buscar_jogos_do_dia(codigo_liga, nome_liga, data):
    # Esta função permanece a mesma.
    print(f"\nBuscando jogos para '{nome_liga}' na data: {data}...")
    url = f"https://api.football-data.org/v4/competitions/{codigo_liga}/matches"
    params = {"dateFrom": data, "dateTo": data}
    try:
        response = requests.get(url, headers=HEADERS_FD, params=params)
        response.raise_for_status()
        dados = response.json()
        
        lista_partidas = []
        for jogo in dados.get('matches', []):
            lista_partidas.append({
                "id": jogo['id'], "data": jogo['utcDate'],
                "mandante_id": jogo['homeTeam']['id'], "mandante_nome": jogo['homeTeam']['name'], "mandante_escudo": jogo['homeTeam']['crest'],
                "visitante_id": jogo['awayTeam']['id'], "visitante_nome": jogo['awayTeam']['name'], "visitante_escudo": jogo['awayTeam']['crest'],
                "liga_nome": jogo['competition']['name']
            })
        print(f"--> {len(lista_partidas)} jogos encontrados.")
        return lista_partidas
    except Exception as e:
        print(f"Erro ao buscar jogos do dia: {e}"); return []


def gerar_analise_ia(partida):
    if not model: 
        return "Erro na IA", "IA não configurada."
    
    prompt = f"""
    Você é o "Mat, o Analista", um especialista em dados esportivos. Sua tarefa é criar um relatório de análise pré-jogo. No Flashscore, encontre as últimas 5 partidas {partida['mandante_nome']} e {partida['visitante_nome']} e os últimos 5 confrontos diretos entre eles . Use os dados fornecidos abaixo para fundamentar sua análise para o confronto.

    Sua resposta deve ser 100% neutra, informativa e seguir rigorosamente a estrutura e as instruções abaixo. NÃO use placeholders como "[Análise aqui]". Gere conteúdo real e específico para cada tópico.

    **Análise da Partida: {partida['mandante_nome']} vs. {partida['visitante_nome']}**

    Inicie com uma introdução de uma frase sobre a análise.

    **Análise de Desempenho Recente**
    **{partida['mandante_nome']}:**
    * **Forma:** Descreva a forma recente da equipe mandante.

    * **Ponto Forte:** Identifique e descreva o principal ponto forte da equipe mandante.

    * **Ponto Fraco:** Identifique e descreva o principal ponto fraco da equipe mandante.

    **{partida['visitante_nome']}:**
    * **Forma:** Descreva a forma recente da equipe visitante.

    * **Ponto Forte:** Identifique e descreva o principal ponto forte da equipe visitante.

    * **Ponto Fraco:** Identifique e descreva o principal ponto fraco da equipe visitante.

    **Análise do Confronto Direto**
    Forneça uma análise detalhada dos últimos 5 confrontos diretos (H2H) entre as duas equipes.

    **Informações Relevantes (Elenco e Contexto)**
    Comente sobre o fator casa, momento das equipes, possíveis lesões, suspensões ou outros fatores contextuais importantes.

    **Cenários e Tendências da Partida**
    "Com base na análise detalhada, estas são as tendências para o confronto." (Use exatamente essa frase antes das tendências)

    **Principais Tendências**

    * TENDÊNCIA 1**(Ex: Ambas as Equipes Marcam):** Nomeie a tendência e forneça uma justificativa analítica para ela.

    * TENDÊNCIA 2**(Ex: {partida['mandante_nome']} - Empate Anula):** Nomeie a tendência e forneça uma justificativa analítica para ela.
    
    * TENDÊNCIA 3**(Ex: Acima de 2.0 Gols):** Nomeie a tendência e forneça uma justificativa analítica para ela.
    ("TENDÊNCIA 1, 2 e 3" não é para ter esse texto e isso é só um exemplo, não use esse texto)
    

    **Cenário de Maior Probabilidade**
    * **(Ex: Dupla Hipótese - {partida['mandante_nome']} ou Empate):** Nomeie o cenário e forneça a justificativa final e conclusiva (TEM SER A MAIS CONSERVADORA DA ANÁLISE).
    ("Dupla Hipótese - {partida['mandante_nome']} ou Empate" é só um exemplo, não use esse texto)

    **Base de Dados Utilizada na Análise**
    "As informações abaixo serviram de fundamento para a análise e as tendências apontadas." (inclua apenas essa frase antes das tabelas)

    **Desempenho Recente das Equipes**

    **Últimos 5 jogos do {partida['mandante_nome']}:**
    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    **Últimos 5 jogos do {partida['visitante_nome']}:**
    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    **Últimos 5 Confrontos Diretos**
    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar

    dd.mm.aaaa | Competição | Jogo - Placar
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip(), None
        
    except Exception as e:
        print(f"Erro ao gerar análise da IA: {e}")
        return None, f"Não foi possível obter a análise da IA. Detalhes: {str(e)}"


def analisar_partida(partida):
    print(f"\n--- Analisando Jogo (via IA): {partida['mandante_nome']} vs {partida['visitante_nome']} ---")
    
    texto_completo_ia, erro = gerar_analise_ia(partida)

    if erro:
        return {
            "mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'],
            "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'],
            "recomendacao": "Erro na IA", "detalhes": [erro]
        }
    
    try:
        # Extrai o "Cenário de Maior Probabilidade" para usar como destaque no card
        cenario_principal = texto_completo_ia.split("**Cenário de Maior Probabilidade**")[1].split("**Base de Dados Utilizada na Análise**")[0]
        # Limpa o cenário para pegar apenas a primeira linha
        recomendacao_final = cenario_principal.strip().replace('*','').split('\n')[0].strip()

        # Formata a análise completa para ser exibida nos detalhes, incluindo tabelas
        analise_completa = texto_completo_ia.replace('\n', '<br>').replace('**', '<b>').replace('*', '&bull;')
        # Converte tabelas Markdown para HTML (simplificado)
        analise_completa = analise_completa.replace('|', '</td><td>')
        analise_completa = analise_completa.replace('</td><td> :---', '</th><th>')
        analise_completa = analise_completa.replace('<br></td><td>', '<tr><td>')
        
    except IndexError:
        # Se a IA não seguir o formato, a extração falha e mostramos um fallback
        recomendacao_final = "Ver Análise Detalhada"
        texto_ia_formatado = texto_completo_ia.replace('\n', '<br>')
        analise_completa = "A IA não respondeu no formato esperado. Resposta recebida:<br><hr>" + texto_ia_formatado

    return {
        "mandante_nome": partida['mandante_nome'], 
        "visitante_nome": partida['visitante_nome'], 
        "mandante_escudo": partida['mandante_escudo'], 
        "visitante_escudo": partida['visitante_escudo'], 
        "recomendacao": recomendacao_final, 
        "detalhes": [analise_completa]
    }

# --- FUNÇÃO GERADORA ---
def gerar_analises(data_para_buscar, tipo_usuario):
    watchlist = LIGAS_GRATUITAS if tipo_usuario == 'public' else LIGAS_MEMBROS

    jogos_encontrados_total = 0
    for nome_liga, id_liga in watchlist.items():
        jogos_da_liga = buscar_jogos_do_dia(id_liga, nome_liga, data_para_buscar) 
        if jogos_da_liga:
            jogos_encontrados_total += len(jogos_da_liga)
            for jogo in jogos_da_liga:
                resultado_jogo = analisar_partida(jogo) 
                yield f"data: {json.dumps(resultado_jogo)}\n\n"
    if jogos_encontrados_total == 0:
        resultado_vazio = {"partida_info": f"Nenhum jogo encontrado para as ligas selecionadas no dia {data_para_buscar}.", "recomendacao": "-"}
        yield f"data: {json.dumps(resultado_vazio)}\n\n"
    yield f"data: {json.dumps({'status': 'done'})}\n\n"