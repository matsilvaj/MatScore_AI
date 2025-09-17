# app/analysis_logic.py

import requests
from datetime import date
import json
import os
import google.generativeai as genai
from app import cache, db
from app.models import Analysis # Importa o novo modelo

# --- CONFIGURAÇÕES GLOBAIS DA ANÁLISE ---
API_TOKEN_FD = os.getenv('API_TOKEN_FD')
HEADERS_FD = {"X-Auth-Token": API_TOKEN_FD}

# --- FUNÇÃO DINÂMICA PARA CARREGAR AS LIGAS DA API ---
@cache.memoize(timeout=86400)
def carregar_ligas_da_api():
    print("--- BUSCANDO LISTA DE LIGAS DA API (operação em cache) ---")
    url = "https://api.football-data.org/v4/competitions"
    ligas = {}
    try:
        response = requests.get(url, headers=HEADERS_FD)
        response.raise_for_status()
        dados = response.json()
        for competicao in dados.get('competitions', []):
            if competicao.get('code'):
                ligas[competicao['name']] = competicao['code']
        print(f"--> {len(ligas)} ligas carregadas com sucesso.")
        return ligas
    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO: Não foi possível buscar as ligas da API. Erro: {e}")
        return {"Premier League": "PL", "La Liga": "PD", "Bundesliga": "BL1", "Serie A": "SA", "Ligue 1": "FL1", "Brasileirão Série A": "BSA", "Copa do Mundo": "WC"}

# --- DEFINIÇÃO DOS PLANOS DE ACESSO ---
LIGAS_DISPONIVEIS = carregar_ligas_da_api()
LIGAS_GRATUITAS = {"Brasileirão Série A": LIGAS_DISPONIVEIS.get("Brasileirão Série A", "BSA")}
LIGAS_MEMBROS = LIGAS_DISPONIVEIS

# --- CONFIGURAÇÃO DA IA ---
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(model_name='gemini-1.5-pro-latest', tools=[genai.protos.Tool(google_search_retrieval=genai.protos.GoogleSearchRetrieval())])
    print("✅ Modelo de IA configurado com sucesso.")
except Exception as e:
    print(f"❌ ERRO: Não foi possível configurar a IA. Erro: {e}")
    model = None

# --- FUNÇÕES DE ANÁLISE ---
def buscar_jogos_do_dia(codigo_liga, nome_liga, data):
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
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar jogos do dia para {nome_liga}: {e}")
        return []


def gerar_analise_ia(partida):
    # (Esta função permanece a mesma, pois a lógica de prompt está boa)
    # ... (código da sua função gerar_analise_ia sem alterações) ...
    if not model:
        return "Erro na IA", "IA não configurada."
    
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
        response = model.generate_content(prompt)
        return response.text.strip(), None
    except Exception as e:
        print(f"Erro ao gerar análise da IA: {e}")
        return None, f"Não foi possível obter a análise da IA. Detalhes: {str(e)}"

def analisar_partida(partida, analysis_date):
    print(f"\n--- Analisando Jogo: {partida['mandante_nome']} vs {partida['visitante_nome']} ---")
    
    # 1. VERIFICAR CACHE NO BANCO DE DADOS PRIMEIRO
    cached_analysis = Analysis.query.filter_by(match_api_id=partida['id'], analysis_date=analysis_date).first()
    if cached_analysis:
        print("--> Análise encontrada no cache do banco de dados.")
        return json.loads(cached_analysis.content) # Retorna o conteúdo guardado

    # 2. SE NÃO ESTIVER EM CACHE, GERAR COM A IA
    print("--> Análise não encontrada no cache. Gerando com a IA...")
    texto_completo_ia, erro = gerar_analise_ia(partida)

    if erro:
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": "Erro na IA", "detalhes": [erro]}
    
    try:
        clean_json_str = texto_completo_ia.strip().replace('```json', '').replace('```', '')
        dados_ia = json.loads(clean_json_str)
        
        recomendacao_final = dados_ia.get("mercado_principal", "Ver Análise Detalhada")
        analise = dados_ia.get("analise_detalhada", {})
        dados_brutos = dados_ia.get("dados_utilizados", {})
        
        # Montagem do HTML (o seu código de montagem continua aqui)
        html_parts = []
        html_parts.append("<b>Análise de Desempenho Recente</b>")
        dm = analise.get('desempenho_mandante', {})
        html_parts.append(f"<br><b>{partida['mandante_nome']}:</b>")
        html_parts.append(f"<ul><li><b>Forma:</b> {dm.get('forma', 'N/A')}</li><li><b>Ponto Forte:</b> {dm.get('ponto_forte', 'N/A')}</li><li><b>Ponto Fraco:</b> {dm.get('ponto_fraco', 'N/A')}</li></ul>")
        dv = analise.get('desempenho_visitante', {})
        html_parts.append(f"<b>{partida['visitante_nome']}:</b>")
        html_parts.append(f"<ul><li><b>Forma:</b> {dv.get('forma', 'N/A')}</li><li><b>Ponto Forte:</b> {dv.get('ponto_forte', 'N/A')}</li><li><b>Ponto Fraco:</b> {dv.get('ponto_fraco', 'N/A')}</li></ul>")
        confronto_direto_html = analise.get('confronto_direto', 'N/A').replace('\n', '<br>')
        informacoes_relevantes_html = analise.get('informacoes_relevantes', 'N/A').replace('\n', '<br>')
        html_parts.append(f"<b>Análise do Confronto Direto</b><br>{confronto_direto_html}<br><br>")
        html_parts.append(f"<b>Informações Relevantes (Elenco e Contexto)</b><br>{informacoes_relevantes_html}<br><br>")
        html_parts.append("<b>Mercados Favoráveis da Partida</b>")
        html_parts.append("<ul>")
        for mercado in analise.get('mercados_favoraveis', []):
            html_parts.append(f"<li><b>{mercado.get('mercado', 'N/A')}:</b> {mercado.get('justificativa', 'N/A')}</li>")
        html_parts.append("</ul>")
        cp = analise.get('cenario_provavel', {})
        html_parts.append("<b>Cenário de Maior Probabilidade</b>")
        html_parts.append(f"<ul><li><b>{cp.get('mercado', 'N/A')}:</b> {cp.get('justificativa', 'N/A')}</li></ul>")
        html_parts.append("<b>Base de Dados Utilizada na Análise</b><br>")
        html_parts.append("As informações abaixo serviram de fundamento para a análise e as tendências apontadas.<br><br>")
        ultimos_jogos_mandante_html = dados_brutos.get('ultimos_jogos_mandante', 'N/A').replace('\n', '<br>')
        ultimos_jogos_visitante_html = dados_brutos.get('ultimos_jogos_visitante', 'N/A').replace('\n', '<br>')
        ultimos_confrontos_diretos_html = dados_brutos.get('ultimos_confrontos_diretos', 'N/A').replace('\n', '<br>')
        html_parts.append(f"<b>Últimos 5 jogos do {partida['mandante_nome']}:</b><br>{ultimos_jogos_mandante_html}<br><br>")
        html_parts.append(f"<b>Últimos 5 jogos do {partida['visitante_nome']}:</b><br>{ultimos_jogos_visitante_html}<br><br>")
        html_parts.append(f"<b>Últimos 5 Confrontos Diretos:</b><br>{ultimos_confrontos_diretos_html}")
        analise_completa = "".join(html_parts)
        
        resultado_final = {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": recomendacao_final, "detalhes": [analise_completa], "liga_nome": partida['liga_nome']}

        # 3. GUARDAR A NOVA ANÁLISE NO BANCO DE DADOS
        nova_analise = Analysis(match_api_id=partida['id'], analysis_date=analysis_date, content=json.dumps(resultado_final))
        db.session.add(nova_analise)
        db.session.commit()
        print("--> Nova análise guardada no banco de dados.")

        return resultado_final

    except json.JSONDecodeError as e:
        # (código de tratamento de erro inalterado) ...
        print(f"Erro ao processar JSON da IA: {e}")
        print("--- JSON INVÁLIDO RECEBIDO ---")
        print(texto_completo_ia)
        print("-----------------------------")
        recomendacao_final = "Ver Análise Detalhada"
        analise_completa = "A IA não respondeu no formato esperado. Resposta recebida:<br><hr>" + texto_completo_ia.replace('\n', '<br>')
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": recomendacao_final, "detalhes": [analise_completa]}

def gerar_analises(data_para_buscar, user_tier='free'):
    watchlist = LIGAS_GRATUITAS if user_tier == 'free' else LIGAS_MEMBROS
    jogos_encontrados_total = 0
    for nome_liga, id_liga in watchlist.items():
        yield f"data: {json.dumps({'status': 'league_start', 'liga_nome': nome_liga})}\n\n"
        jogos_da_liga = buscar_jogos_do_dia(id_liga, nome_liga, data_para_buscar)
        if jogos_da_liga:
            jogos_encontrados_total += len(jogos_da_liga)
            for jogo in jogos_da_liga:
                resultado_jogo = analisar_partida(jogo, data_para_buscar)
                yield f"data: {json.dumps(resultado_jogo)}\n\n"
    if jogos_encontrados_total == 0:
        yield f"data: {json.dumps({'status': 'no_games'})}\n\n"
    yield f"data: {json.dumps({'status': 'done'})}\n\n"