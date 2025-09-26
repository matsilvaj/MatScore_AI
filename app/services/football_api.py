# app/services/football_api.py
import requests
import os
from flask import current_app

API_KEY = os.getenv('API_FOOTBALL_KEY')
API_HOST = "v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-host': API_HOST,
    'x-rapidapi-key': API_KEY
}
BASE_URL = "https://v3.football.api-sports.io/"

def carregar_ligas_da_api():
    """Busca as competições disponíveis na API-Football."""
    current_app.logger.info("Buscando lista de ligas da API-Football.")
    url = f"{BASE_URL}leagues"
    ligas = {}
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        dados = response.json().get('response', [])
        for item in dados:
            liga_info = item.get('league')
            if liga_info:
                ligas[liga_info['name']] = liga_info['id']
        current_app.logger.info(f"{len(ligas)} ligas carregadas com sucesso da API-Football.")
        return ligas
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Não foi possível buscar as ligas da API-Football. Erro: {e}")
        return {"Premier League": 39, "Brasileirão Série A": 71} # Fallback

def buscar_jogos_do_dia(id_liga, nome_liga, data):
    """Busca os jogos do dia na API-Football."""
    current_app.logger.info(f"Buscando jogos para '{nome_liga}' (ID: {id_liga}) na data: {data}...")
    url = f"{BASE_URL}fixtures"
    params = {"league": id_liga, "season": "2024", "date": data} # O ano da temporada pode precisar de ajuste
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        dados = response.json().get('response', [])
        lista_partidas = []
        for jogo in dados:
            fixture = jogo.get('fixture', {})
            teams = jogo.get('teams', {})
            home_team = teams.get('home', {})
            away_team = teams.get('away', {})
            league_info = jogo.get('league', {})
            
            lista_partidas.append({
                "id": fixture.get('id'),
                "data": fixture.get('date'),
                "mandante_id": home_team.get('id'),
                "mandante_nome": home_team.get('name'),
                "mandante_escudo": home_team.get('logo'),
                "visitante_id": away_team.get('id'),
                "visitante_nome": away_team.get('name'),
                "visitante_escudo": away_team.get('logo'),
                "liga_nome": league_info.get('name')
            })
        current_app.logger.info(f"--> {len(lista_partidas)} jogos encontrados para '{nome_liga}'.")
        return lista_partidas
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erro ao buscar jogos do dia para {nome_liga}: {e}")
        return []