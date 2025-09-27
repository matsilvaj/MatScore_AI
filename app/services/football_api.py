# app/services/football_api.py
import requests
import os
from flask import current_app
from datetime import datetime

API_KEY = os.getenv('API_FOOTBALL_KEY')
API_HOST = "v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-host': API_HOST,
    'x-rapidapi-key': API_KEY
}
BASE_URL = "https://v3.football.api-sports.io/"

def carregar_ligas_da_api():
    """Busca as competições e países (com bandeira) disponíveis na API-Football."""
    current_app.logger.info("Buscando lista de ligas da API-Football.")
    url = f"{BASE_URL}leagues"
    ligas = {}
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        dados = response.json().get('response', [])
        for item in dados:
            liga_info = item.get('league')
            pais_info = item.get('country')
            if liga_info and pais_info:
                ligas[liga_info['name']] = {
                    'id': liga_info['id'],
                    'pais': pais_info.get('name'),
                    'flag': pais_info.get('flag')
                }
        current_app.logger.info(f"{len(ligas)} ligas carregadas com sucesso da API-Football.")
        return ligas
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Não foi possível buscar as ligas da API-Football. Erro: {e}")
        return {
            "Premier League": {"id": 39, "pais": "England", "flag": "https://media.api-sports.io/flags/gb.svg"},
            "Brasileirão Série A": {"id": 71, "pais": "Brazil", "flag": "https://media.api-sports.io/flags/br.svg"}
        }

def buscar_jogos_do_dia(id_liga, nome_liga, data):
    """Busca os jogos do dia na API-Football."""
    current_app.logger.info(f"Buscando jogos para '{nome_liga}' (ID: {id_liga}) na data: {data}...")
    url = f"{BASE_URL}fixtures"
    
    ano_da_temporada = data.split('-')[0]
    params = {"league": id_liga, "season": ano_da_temporada, "date": data}

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

def _buscar_e_formatar_jogos(url, params, log_message):
    """Função auxiliar para buscar dados de jogos e formatar a saída."""
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        jogos = response.json().get('response', [])
        
        resultados_formatados = []
        jogos_ids = []
        for jogo in jogos:
            fixture = jogo.get('fixture', {})
            teams = jogo.get('teams', {})
            goals = jogo.get('goals', {})
            data_jogo = datetime.fromisoformat(fixture.get('date')).strftime('%d.%m.%Y')
            
            jogos_ids.append(fixture.get('id'))
            resultado = (f"{data_jogo} | "
                         f"{teams['home']['name']} {goals.get('home', 'N/A')} vs "
                         f"{goals.get('away', 'N/A')} {teams['away']['name']}")
            resultados_formatados.append(resultado)
            
        texto_formatado = "\\n".join(resultados_formatados) if resultados_formatados else "Nenhum dado recente encontrado."
        return texto_formatado, jogos_ids
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erro na API-Football: {log_message}. Detalhes: {e}")
        return "Erro ao buscar dados.", []

def buscar_ultimos_jogos(time_id: int):
    """Busca os últimos 5 jogos de um time."""
    current_app.logger.info(f"Buscando últimos 5 jogos para o time ID: {time_id}")
    url = f"{BASE_URL}fixtures"
    params = {'team': time_id, 'last': 5}
    log_message = f"buscar últimos jogos para o time ID {time_id}"
    return _buscar_e_formatar_jogos(url, params, log_message)

def buscar_h2h(time1_id: int, time2_id: int):
    """Busca os últimos 5 confrontos diretos."""
    current_app.logger.info(f"Buscando H2H entre os times: {time1_id} vs {time2_id}")
    url = f"{BASE_URL}fixtures/headtohead"
    params = {'h2h': f"{time1_id}-{time2_id}", 'last': 5}
    log_message = f"buscar H2H para os times {time1_id} e {time2_id}"
    return _buscar_e_formatar_jogos(url, params, log_message)

def buscar_estatisticas_jogos(jogos_ids: list):
    """Busca estatísticas para uma lista de IDs de jogos e retorna uma string simples formatada."""
    if not jogos_ids:
        return "Nenhuma partida para analisar."

    all_stats = []
    for jogo_id in jogos_ids:
        try:
            url = f"{BASE_URL}fixtures/statistics"
            params = {'fixture': jogo_id}
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json().get('response', [])
            
            if not data or len(data) < 2: continue
            
            home_team_data = data[0]
            away_team_data = data[1]

            stats_jogo = {
                'home': {'team_name': home_team_data['team']['name'], 'corners': 0, 'cards': 0, 'offsides': 0},
                'away': {'team_name': away_team_data['team']['name'], 'corners': 0, 'cards': 0, 'offsides': 0}
            }
            
            for team_data in [home_team_data, away_team_data]:
                team_side = 'home' if team_data['team']['id'] == home_team_data['team']['id'] else 'away'
                for stat in team_data['statistics']:
                    stat_type = stat.get('type')
                    stat_value = stat.get('value')
                    if stat_value is None: stat_value = 0
                    
                    if stat_type == 'Corner Kicks':
                        stats_jogo[team_side]['corners'] = stat_value
                    elif stat_type in ['Yellow Cards', 'Red Cards']:
                        stats_jogo[team_side]['cards'] += int(stat_value)
                    elif stat_type == 'Offsides':
                        stats_jogo[team_side]['offsides'] = stat_value
            
            stats_line = (f"{stats_jogo['home']['team_name']} (Escanteios: {stats_jogo['home']['corners']}, Cartões: {stats_jogo['home']['cards']}, Impedimentos: {stats_jogo['home']['offsides']}) vs "
                          f"{stats_jogo['away']['team_name']} (Escanteios: {stats_jogo['away']['corners']}, Cartões: {stats_jogo['away']['cards']}, Impedimentos: {stats_jogo['away']['offsides']})")
            all_stats.append(stats_line)

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Erro ao buscar estatísticas para o jogo ID {jogo_id}: {e}")
            continue

    return "\\n".join(all_stats) if all_stats else "Nenhuma estatística encontrada."