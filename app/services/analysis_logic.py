# app/services/analysis_logic.py
import json
from app import cache, db
from . import football_api, ai_analyzer
from app.models import Analysis, Match
from flask import current_app
from datetime import datetime
import pytz
import math

# --- LISTA DE LIGAS E COPAS SELECIONADAS ---
# (código da lista de ligas permanece o mesmo)
LIGAS_SELECIONADAS = {
    # Ligas Nacionais
    "Brasileirão Série A": {"id": 71, "pais": "Brazil", "flag": "https://media.api-sports.io/flags/br.svg"},
    "Brasileirão Série B": {"id": 72, "pais": "Brazil", "flag": "https://media.api-sports.io/flags/br.svg"},
    "Premier League": {"id": 39, "pais": "England", "flag": "https://media.api-sports.io/flags/gb.svg"},
    "La Liga": {"id": 140, "pais": "Spain", "flag": "https://media.api-sports.io/flags/es.svg"},
    "Serie A": {"id": 135, "pais": "Italy", "flag": "https://media.api-sports.io/flags/it.svg"},
    "Bundesliga": {"id": 78, "pais": "Germany", "flag": "https://media.api-sports.io/flags/de.svg"},
    "Ligue 1": {"id": 61, "pais": "France", "flag": "https://media.api-sports.io/flags/fr.svg"},
    "Eredivisie": {"id": 88, "pais": "Netherlands", "flag": "https://media.api-sports.io/flags/nl.svg"},
    "Primeira Liga": {"id": 94, "pais": "Portugal", "flag": "https://media.api-sports.io/flags/pt.svg"},
    "Super Lig": {"id": 203, "pais": "Turkey", "flag": "https://media.api-sports.io/flags/tr.svg"},
    "Jupiler Pro League": {"id": 144, "pais": "Belgium", "flag": "https://media.api-sports.io/flags/be.svg"},
    
    # Copas Nacionais
    "FA Cup": {"id": 45, "pais": "England", "flag": "https://media.api-sports.io/flags/gb.svg"},
    "Copa do Brasil": {"id": 90, "pais": "Brazil", "flag": "https://media.api-sports.io/flags/br.svg"},
    
    # Copas Internacionais
    "Copa America": {"id": 9, "pais": "World", "flag": "https://media.api-sports.io/flags/un.svg"},
    "Euro Championship": {"id": 4, "pais": "World", "flag": "https://media.api-sports.io/flags/un.svg"},
    "World Cup": {"id": 1, "pais": "World", "flag": "https://media.api-sports.io/flags/un.svg"}
}


def convert_utc_to_sao_paulo_time(utc_dt_str):
    """Converte uma string de data UTC para o horário de São Paulo (HH:MM)."""
    if not utc_dt_str:
        return "N/A"
    try:
        utc_dt = datetime.fromisoformat(utc_dt_str.replace('Z', '+00:00'))
        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
        sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
        sao_paulo_dt = utc_dt.astimezone(sao_paulo_tz)
        return sao_paulo_dt.strftime('%H:%M')
    except (ValueError, TypeError):
        return "N/A"

def obter_ligas_definidas():
    """Retorna a lista de ligas pré-definidas, buscando do cache se disponível."""
    cached_ligas = cache.get("lista_ligas_definidas")
    if cached_ligas:
        return cached_ligas
    cache.set("lista_ligas_definidas", LIGAS_SELECIONADAS, timeout=86400)
    return LIGAS_SELECIONADAS

def analisar_partida(partida, analysis_date):
    """Gera a análise de uma partida, com logging e tratamento de erros."""
    partida_info = f"{partida['mandante_nome']} vs {partida['visitante_nome']}"
    current_app.logger.info(f"Analisando Jogo: {partida_info}")
    
    cached_analysis = Analysis.query.filter_by(match_api_id=partida['id'], analysis_date=analysis_date).first()
    if cached_analysis:
        current_app.logger.info(f"--> Análise para '{partida_info}' encontrada no cache do banco de dados.")
        resultado_cache = json.loads(cached_analysis.content)
        resultado_cache['analysis_id'] = cached_analysis.id
        return resultado_cache

    current_app.logger.info(f"--> Análise para '{partida_info}' não encontrada no cache. Gerando com a IA...")
    
    _, mandante_ids = football_api.buscar_ultimos_jogos(partida['mandante_id'])
    _, visitante_ids = football_api.buscar_ultimos_jogos(partida['visitante_id'])
    _, h2h_ids = football_api.buscar_h2h(partida['mandante_id'], partida['visitante_id'])

    ultimos_jogos_mandante_list = football_api.buscar_ultimos_jogos_estruturados(partida['mandante_id'])
    ultimos_jogos_visitante_list = football_api.buscar_ultimos_jogos_estruturados(partida['visitante_id'])
    confrontos_diretos_list = football_api.buscar_h2h_estruturado(partida['mandante_id'], partida['visitante_id'])
    
    stats_mandante = football_api.buscar_estatisticas_time_em_jogos(partida['mandante_id'], mandante_ids)
    stats_visitante = football_api.buscar_estatisticas_time_em_jogos(partida['visitante_id'], visitante_ids)
    stats_h2h_mandante = football_api.buscar_estatisticas_time_em_jogos(partida['mandante_id'], h2h_ids)
    stats_h2h_visitante = football_api.buscar_estatisticas_time_em_jogos(partida['visitante_id'], h2h_ids)

    def calculate_avg(data_list):
        return round(sum(data_list) / len(data_list), 1) if data_list else 0.0

    estatisticas = {
        "individuais": {
            "mandante": {
                "escanteios": {"jogos": stats_mandante['corners'], "media": calculate_avg(stats_mandante['corners'])},
                "cartoes": {"jogos": stats_mandante['cards'], "media": calculate_avg(stats_mandante['cards'])}
            },
            "visitante": {
                "escanteios": {"jogos": stats_visitante['corners'], "media": calculate_avg(stats_visitante['corners'])},
                "cartoes": {"jogos": stats_visitante['cards'], "media": calculate_avg(stats_visitante['cards'])}
            }
        },
        "h2h": {
            "mandante": {
                "escanteios": {"jogos": stats_h2h_mandante['corners'], "media": calculate_avg(stats_h2h_mandante['corners'])},
                "cartoes": {"jogos": stats_h2h_mandante['cards'], "media": calculate_avg(stats_h2h_mandante['cards'])}
            },
            "visitante": {
                "escanteios": {"jogos": stats_h2h_visitante['corners'], "media": calculate_avg(stats_h2h_visitante['corners'])},
                "cartoes": {"jogos": stats_h2h_visitante['cards'], "media": calculate_avg(stats_h2h_visitante['cards'])}
            }
        }
    }

    def processar_historico(lista_jogos):
        if not lista_jogos:
            return {"jogos": [], "media_total_gols": 0.0, "media_diferenca_gols": 0.0, "media_handicap_abs": 0.0}
        
        total_gols = [jogo['total_gols'] for jogo in lista_jogos]
        diferenca_gols = [jogo['diferenca_gols'] for jogo in lista_jogos]
        
        return {
            "jogos": lista_jogos,
            "media_total_gols": calculate_avg(total_gols),
            "media_diferenca_gols": calculate_avg(diferenca_gols),
            "media_handicap_abs": calculate_avg([abs(g) for g in diferenca_gols])
        }

    dados_brutos = {
        "ultimos_jogos_mandante": processar_historico(ultimos_jogos_mandante_list),
        "ultimos_jogos_visitante": processar_historico(ultimos_jogos_visitante_list),
        "confrontos_diretos": processar_historico(confrontos_diretos_list)
    }

    dados_ia, erro = ai_analyzer.gerar_analise_ia(partida)

    if erro:
        current_app.logger.error(f"Erro retornado pelo gerador de IA para '{partida_info}': {erro}")
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": "Erro na Análise", "error": True}
    
    try:
        horario_jogo = convert_utc_to_sao_paulo_time(partida.get('data'))
        
        recomendacao_principal = dados_ia.get("mercado_principal", "Ver Análise Detalhada")

        resultado_final = {
            "horario": horario_jogo,
            "mandante_nome": partida['mandante_nome'],
            "visitante_nome": partida['visitante_nome'],
            "mandante_escudo": partida['mandante_escudo'],
            "visitante_escudo": partida['visitante_escudo'],
            "liga_nome": partida['liga_nome'],
            "recomendacao": recomendacao_principal,
            "analise_detalhada": dados_ia.get("analise_detalhada", {}),
            "estatisticas": estatisticas,
            "dados_brutos": dados_brutos
        }
        
        nova_analise = Analysis(match_api_id=partida['id'], analysis_date=analysis_date, content=json.dumps(resultado_final))
        db.session.add(nova_analise)
        db.session.commit()
        current_app.logger.info(f"--> Nova análise para '{partida_info}' guardada no banco de dados.")
        
        resultado_final['analysis_id'] = nova_analise.id
        return resultado_final

    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao processar a resposta da IA para '{partida_info}': {e}")
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "recomendacao": "Erro inesperado.", "error": True}


    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao processar a resposta da IA para '{partida_info}': {e}")
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "recomendacao": "Erro inesperado.", "error": True}


def gerar_analises(data_para_buscar, user_tier='free'):
    """Gera o stream de análises, com cache de partidas e logging."""
    
    todas_as_ligas = obter_ligas_definidas()
    
    LIGAS_GRATUITAS_NOMES = ["Brasileirão Série A", "Brasileirão Série B", "La Liga", "Serie A"]
    LIGAS_GRATUITAS = {nome: todas_as_ligas[nome] for nome in LIGAS_GRATUITAS_NOMES if nome in todas_as_ligas}
    LIGAS_MEMBROS = todas_as_ligas

    watchlist = LIGAS_GRATUITAS if user_tier == 'free' else LIGAS_MEMBROS
    jogos_encontrados_total = 0
    
    try:
        for nome_liga, liga_dados in watchlist.items():
            id_liga = liga_dados['id']
            pais_liga = liga_dados.get('pais', '')
            flag_liga = liga_dados.get('flag', '')
            jogos_da_liga = []
            
            jogos_cacheados = Match.query.filter_by(match_date=data_para_buscar, league_name=nome_liga).all()

            if jogos_cacheados:
                current_app.logger.info(f"Jogos para '{nome_liga}' em {data_para_buscar} encontrados no cache do BD.")
                jogos_da_liga = [jogo.to_dict() for jogo in jogos_cacheados]
            else:
                current_app.logger.info(f"Cache de jogos para '{nome_liga}' em {data_para_buscar} vazio. Buscando na API.")
                jogos_da_api = football_api.buscar_jogos_do_dia(id_liga, nome_liga, data_para_buscar)
                
                if jogos_da_api:
                    jogos_filtrados_para_salvar = []
                    for jogo_api in jogos_da_api:
                        if jogo_api.get('liga_id') != id_liga:
                            continue

                        existe = Match.query.filter_by(api_id=jogo_api['id']).first()
                        if not existe:
                            novo_jogo = Match(
                                api_id=jogo_api['id'],
                                match_date=data_para_buscar,
                                home_team_id=jogo_api['mandante_id'],
                                home_team_name=jogo_api['mandante_nome'],
                                home_team_crest=jogo_api['mandante_escudo'],
                                away_team_id=jogo_api['visitante_id'],
                                away_team_name=jogo_api['visitante_nome'],
                                away_team_crest=jogo_api['visitante_escudo'],
                                league_name=nome_liga
                            )
                            db.session.add(novo_jogo)
                        
                        jogo_api['liga_nome'] = nome_liga
                        jogos_filtrados_para_salvar.append(jogo_api)

                    if db.session.new:
                        db.session.commit()
                        current_app.logger.info(f"{len(db.session.new)} jogos de '{nome_liga}' salvos no cache do BD.")
                    
                    jogos_da_liga = jogos_filtrados_para_salvar

            if jogos_da_liga:
                jogos_encontrados_total += len(jogos_da_liga)
                yield f"data: {json.dumps({'status': 'league_start', 'liga_nome': nome_liga, 'pais_nome': pais_liga, 'pais_flag': flag_liga})}\n\n"
                
                for jogo in jogos_da_liga:
                    resultado_jogo = analisar_partida(jogo, data_para_buscar)
                    yield f"data: {json.dumps(resultado_jogo)}\n\n"

        if jogos_encontrados_total == 0:
            yield f"data: {json.dumps({'status': 'no_games'})}\n\n"
        
        yield f"data: {json.dumps({'status': 'done'})}\n\n"

    except GeneratorExit:
        current_app.logger.warning("Conexão do cliente fechada. Interrompendo a busca de análises.")
    except Exception as e:
        current_app.logger.error(f"Erro inesperado no gerador de análises: {e}", exc_info=True)
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"