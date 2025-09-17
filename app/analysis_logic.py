# app/analysis_logic.py

import requests
from datetime import date
import time
import json
import os
import google.generativeai as genai
from app import cache # Importa o objeto de cache da sua aplicação

# --- CONFIGURAÇÕES GLOBAIS DA ANÁLISE ---
API_TOKEN_FD = os.getenv('API_TOKEN_FD')
HEADERS_FD = {"X-Auth-Token": API_TOKEN_FD}

# --- FUNÇÃO DINÂMICA PARA CARREGAR AS LIGAS DA API ---
# O cache.memoize(timeout=86400) guarda o resultado desta função por 1 dia (86400 segundos).
# A aplicação só vai chamar a API para buscar as ligas uma vez por dia.
@cache.memoize(timeout=86400)
def carregar_ligas_da_api():
    """
    Busca todas as competições disponíveis na API football-data.org
    e as formata num dicionário. O resultado fica em cache.
    """
    print("--- BUSCANDO LISTA DE LIGAS DA API (operação em cache) ---")
    url = "https://api.football-data.org/v4/competitions"
    ligas = {}
    try:
        response = requests.get(url, headers=HEADERS_FD)
        response.raise_for_status() # Lança um erro se a resposta não for 200 OK
        dados = response.json()
        
        for competicao in dados.get('competitions', []):
            # Usamos o 'code' da competição, que é o que precisamos para as outras chamadas
            if competicao.get('code'):
                ligas[competicao['name']] = competicao['code']
        
        print(f"--> {len(ligas)} ligas carregadas com sucesso.")
        return ligas
    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO: Não foi possível buscar as ligas da API. Erro: {e}")
        # Retorna um dicionário de fallback em caso de erro
        return {
            "Premier League": "PL",
            "La Liga": "PD",
            "Bundesliga": "BL1",
            "Serie A": "SA",
            "Ligue 1": "FL1",
            "Brasileirão Série A": "BSA",
            "Copa do Mundo": "WC"
        }

# --- DEFINIÇÃO DOS PLANOS DE ACESSO ---
LIGAS_DISPONIVEIS = carregar_ligas_da_api()

# Plano Gratuito
LIGAS_GRATUITAS = {
    "Brasileirão Série A": LIGAS_DISPONIVEIS.get("Brasileirão Série A", "BSA"),
    "Ligue 1": LIGAS_DISPONIVEIS.get("Ligue 1", "FL1"),
    "Serie A": LIGAS_DISPONIVEIS.get("Serie A", "SA"),
    "La liga": LIGAS_DISPONIVEIS.get("La Liga", "PD"),
}

# Plano para Membros (Premium) - Acesso a TODAS as ligas carregadas da API
LIGAS_MEMBROS = LIGAS_DISPONIVEIS


# --- CONFIGURAÇÃO DA IA ---
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    ferramenta_de_busca = genai.protos.Tool(
        google_search_retrieval=genai.protos.GoogleSearchRetrieval()
    )
    model = genai.GenerativeModel(
      model_name='gemini-1.5-pro-latest',
      tools=[ferramenta_de_busca],
    )
    print("✅ Modelo de IA configurado com sucesso e com ferramenta de busca.")
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
    except Exception as e:
        print(f"Erro ao buscar jogos do dia: {e}"); return []


def gerar_analise_ia(partida):
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


def analisar_partida(partida):
    print(f"\n--- Analisando Jogo (via IA): {partida['mandante_nome']} vs {partida['visitante_nome']} ---")
    
    texto_completo_ia, erro = gerar_analise_ia(partida)

    if erro:
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": "Erro na IA", "detalhes": [erro]}
    
    try:
        clean_json_str = texto_completo_ia.strip().replace('```json', '').replace('```', '')
        dados_ia = json.loads(clean_json_str)
        recomendacao_final = dados_ia.get("mercado_principal", "Ver Análise Detalhada")
        analise = dados_ia.get("analise_detalhada", {})
        dados_brutos = dados_ia.get("dados_utilizados", {})
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
    except json.JSONDecodeError as e:
        print(f"Erro ao processar JSON da IA: {e}")
        print("--- JSON INVÁLIDO RECEBIDO ---")
        print(texto_completo_ia)
        print("-----------------------------")
        recomendacao_final = "Ver Análise Detalhada"
        analise_completa = "A IA não respondeu no formato esperado. Resposta recebida:<br><hr>" + texto_completo_ia.replace('\n', '<br>')
    return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": recomendacao_final, "detalhes": [analise_completa]}

# --- FUNÇÃO GERADORA ---
def gerar_analises(data_para_buscar, user_tier='free'):
    watchlist = LIGAS_GRATUITAS if user_tier == 'free' else LIGAS_MEMBROS
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