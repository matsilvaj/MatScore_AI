# app/services/analysis_logic.py
import json
from app import cache, db
from . import football_api, ai_analyzer
from app.models import Analysis, Match
from flask import current_app

# --- GESTÃO DE CACHE MANUAL PARA AS LIGAS ---
def obter_ligas_disponiveis():
    """Busca as ligas da API ou do cache. Deve ser chamada dentro de um contexto de app."""
    cached_ligas = cache.get("lista_de_ligas_futebol")
    if cached_ligas:
        current_app.logger.info("Lista de ligas encontrada no cache.")
        return cached_ligas
    
    ligas = football_api.carregar_ligas_da_api()
    cache.set("lista_de_ligas_futebol", ligas, timeout=86400)
    return ligas

def analisar_partida(partida, analysis_date):
    """Gera a análise de uma partida, com logging e tratamento de erros."""
    from app import db
    from app.models import Analysis

    partida_info = f"{partida['mandante_nome']} vs {partida['visitante_nome']}"
    current_app.logger.info(f"Analisando Jogo: {partida_info}")
    
    cached_analysis = Analysis.query.filter_by(match_api_id=partida['id'], analysis_date=analysis_date).first()
    if cached_analysis:
        current_app.logger.info(f"--> Análise para '{partida_info}' encontrada no cache do banco de dados.")
        resultado_cache = json.loads(cached_analysis.content)
        resultado_cache['analysis_id'] = cached_analysis.id
        return resultado_cache

    current_app.logger.info(f"--> Análise para '{partida_info}' não encontrada no cache. Gerando com a IA...")
    dados_ia, erro = ai_analyzer.gerar_analise_ia(partida)

    if erro:
        current_app.logger.error(f"Erro retornado pelo gerador de IA para '{partida_info}': {erro}")
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": "Erro na Análise", "error": True}
    
    try:
        # ** REATORAÇÃO PRINCIPAL AQUI **
        # Agora, simplesmente combinamos os dados da partida com a resposta da IA.
        resultado_final = {
            "mandante_nome": partida['mandante_nome'],
            "visitante_nome": partida['visitante_nome'],
            "mandante_escudo": partida['mandante_escudo'],
            "visitante_escudo": partida['visitante_escudo'],
            "liga_nome": partida['liga_nome'],
            "recomendacao": dados_ia.get("mercado_principal", "Ver Análise Detalhada"),
            "analise_detalhada": dados_ia.get("analise_detalhada", {}),
            "outras_analises": dados_ia.get("outras_analises", {}),
            "dados_utilizados": dados_ia.get("dados_utilizados", {})
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


def gerar_analises(data_para_buscar, user_tier='free'):
    """Gera o stream de análises, com cache de partidas e logging."""
    from app import db 

    LIGAS_DISPONIVEIS = obter_ligas_disponiveis()
    LIGAS_GRATUITAS = {
        "Brasileirão Série A": LIGAS_DISPONIVEIS.get("Brasileirão Série A", 71),
        "La Liga": LIGAS_DISPONIVEIS.get("La Liga", 140)
    }
    LIGAS_MEMBROS = LIGAS_DISPONIVEIS

    watchlist = LIGAS_GRATUITAS if user_tier == 'free' else LIGAS_MEMBROS
    jogos_encontrados_total = 0
    
    try:
        for nome_liga, id_liga in watchlist.items():
            jogos_da_liga = []
            
            jogos_cacheados = Match.query.filter_by(match_date=data_para_buscar, league_name=nome_liga).all()

            if jogos_cacheados:
                current_app.logger.info(f"Jogos para '{nome_liga}' em {data_para_buscar} encontrados no cache do BD.")
                jogos_da_liga = [jogo.to_dict() for jogo in jogos_cacheados]
            else:
                current_app.logger.info(f"Cache de jogos para '{nome_liga}' em {data_para_buscar} vazio. Buscando na API.")
                jogos_da_api = football_api.buscar_jogos_do_dia(id_liga, nome_liga, data_para_buscar)
                
                if jogos_da_api:
                    for jogo_api in jogos_da_api:
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
                                league_name=jogo_api['liga_nome']
                            )
                            db.session.add(novo_jogo)
                    
                    if db.session.new:
                        db.session.commit()
                        current_app.logger.info(f"{len(jogos_da_api)} jogos de '{nome_liga}' salvos no cache do BD.")
                    
                    jogos_da_liga = jogos_da_api

            if jogos_da_liga:
                jogos_encontrados_total += len(jogos_da_liga)
                yield f"data: {json.dumps({'status': 'league_start', 'liga_nome': nome_liga})}\n\n"
                
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