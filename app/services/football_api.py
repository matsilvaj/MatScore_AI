import requests
import os


API_TOKEN_FD = os.getenv('API_TOKEN_FD')
HEADERS_FD = {"X-Auth-Token": API_TOKEN_FD}

def carregar_ligas_da_api():
    """Busca todas as competições disponíveis na API e as formata num dicionário."""
    print("--- BUSCANDO LISTA DE LIGAS DA API ---")
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
        return {"Premier League": "PL", "Brasileirão Série A": "BSA"}

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