import requests
import os
from flask import current_app # Importa o current_app para acessar o logger

API_TOKEN_FD = os.getenv('API_TOKEN_FD')
HEADERS_FD = {"X-Auth-Token": API_TOKEN_FD}

def carregar_ligas_da_api():
    """Busca todas as competições disponíveis na API e as formata num dicionário."""
    current_app.logger.info("Buscando lista de ligas da API externa.")
    url = "https://api.football-data.org/v4/competitions"
    ligas = {}
    try:
        response = requests.get(url, headers=HEADERS_FD, timeout=10) # Adiciona um timeout
        response.raise_for_status()  # Levanta um erro para respostas 4xx ou 5xx
        dados = response.json()
        for competicao in dados.get('competitions', []):
            if competicao.get('code'):
                ligas[competicao['name']] = competicao['code']
        current_app.logger.info(f"{len(ligas)} ligas carregadas com sucesso da API.")
        return ligas
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Não foi possível buscar as ligas da API. Erro: {e}")
        # Retorna um fallback para que a aplicação não quebre totalmente
        return {"Premier League": "PL", "Brasileirão Série A": "BSA"}

def buscar_jogos_do_dia(codigo_liga, nome_liga, data):
    """Busca os jogos do dia, agora com logging e tratamento de erros aprimorado."""
    current_app.logger.info(f"Buscando jogos para '{nome_liga}' na data: {data}...")
    url = f"https://api.football-data.org/v4/competitions/{codigo_liga}/matches"
    params = {"dateFrom": data, "dateTo": data}
    try:
        response = requests.get(url, headers=HEADERS_FD, params=params, timeout=10)
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
        current_app.logger.info(f"--> {len(lista_partidas)} jogos encontrados para '{nome_liga}'.")
        return lista_partidas
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erro ao buscar jogos do dia para {nome_liga}: {e}")
        return [] # Retorna uma lista vazia em caso de falha