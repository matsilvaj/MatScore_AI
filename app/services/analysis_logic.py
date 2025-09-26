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
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": "Erro na Análise", "detalhes": [erro], "error": True}
    
    try:
        recomendacao_final = dados_ia.get("mercado_principal", "Ver Análise Detalhada")
        analise_json = dados_ia.get("analise_detalhada", {})
        stats_json = dados_ia.get("outras_analises", {})
        dados_brutos = dados_ia.get("dados_utilizados", {})
        
        html_parts = []
        
        # --- Título da Análise Principal ---
        html_parts.append("<h2 style='border-bottom: 2px solid #007bff; padding-bottom: 5px; margin-top: 0;'>Análise Principal</h2>")
        
        html_parts.append("<b>Análise de Desempenho Recente</b>")
        dm = analise_json.get('desempenho_mandante', {})
        html_parts.append(f"<br><b>{partida['mandante_nome']}:</b>")
        html_parts.append(f"<ul><li><b>Forma:</b> {dm.get('forma', 'N/A')}</li><li><b>Ponto Forte:</b> {dm.get('ponto_forte', 'N/A')}</li><li><b>Ponto Fraco:</b> {dm.get('ponto_fraco', 'N/A')}</li></ul>")
        dv = analise_json.get('desempenho_visitante', {})
        html_parts.append(f"<b>{partida['visitante_nome']}:</b>")
        html_parts.append(f"<ul><li><b>Forma:</b> {dv.get('forma', 'N/A')}</li><li><b>Ponto Forte:</b> {dv.get('ponto_forte', 'N/A')}</li><li><b>Ponto Fraco:</b> {dv.get('ponto_fraco', 'N/A')}</li></ul>")
        
        confronto_direto_html = str(analise_json.get('confronto_direto', 'N/A')).replace('\n', '<br>')
        informacoes_relevantes_html = str(analise_json.get('informacoes_relevantes', 'N/A')).replace('\n', '<br>')
        html_parts.append(f"<b>Análise do Confronto Direto</b><br>{confronto_direto_html}<br><br>")
        html_parts.append(f"<b>Informações Relevantes (Elenco e Contexto)</b><br>{informacoes_relevantes_html}<br><br>")
        
        html_parts.append("<b>Mercados Favoráveis da Partida</b>")
        html_parts.append("<ul>")
        for mercado in analise_json.get('mercados_favoraveis', []):
            html_parts.append(f"<li><b>{mercado.get('mercado', 'N/A')}:</b> {mercado.get('justificativa', 'N/A')}</li>")
        html_parts.append("</ul>")
        
        cp = analise_json.get('cenario_provavel', {})
        html_parts.append("<b>Cenário de Maior Probabilidade</b>")
        html_parts.append(f"<ul><li><b>{cp.get('mercado', 'N/A')}:</b> {cp.get('justificativa', 'N/A')}</li></ul>")
        
        # --- Título das Outras Análises ---
        html_parts.append("<h2 style='border-bottom: 2px solid #6c757d; padding-bottom: 5px; margin-top: 2em;'>Outras Análises</h2>")
        analise_escanteios_html = str(stats_json.get('analise_escanteios', 'N/A')).replace('\n', '<br>')
        html_parts.append(f"<b>Análise de Escanteios</b><br>{analise_escanteios_html}<br><br>")
        analise_cartoes_html = str(stats_json.get('analise_cartoes', 'N/A')).replace('\n', '<br>')
        html_parts.append(f"<b>Análise de Cartões</b><br>{analise_cartoes_html}<br><br>")
        analise_impedimentos_html = str(stats_json.get('analise_impedimentos', 'N/A')).replace('\n', '<br>')
        html_parts.append(f"<b>Análise de Impedimentos</b><br>{analise_impedimentos_html}<br><br>")

        # --- Título da Base de Dados ---
        html_parts.append("<h2 style='border-bottom: 2px solid #ccc; padding-bottom: 5px; margin-top: 2em;'>Base de Dados Utilizada</h2>")
        html_parts.append("<p>As informações abaixo serviram de fundamento para a análise e as tendências apontadas.</p>")
        
        # Dados de Resultados
        ultimos_jogos_mandante_html = str(dados_brutos.get('ultimos_jogos_mandante', 'N/A')).replace('\n', '<br>')
        ultimos_jogos_visitante_html = str(dados_brutos.get('ultimos_jogos_visitante', 'N/A')).replace('\n', '<br>')
        ultimos_confrontos_diretos_html = str(dados_brutos.get('ultimos_confrontos_diretos', 'N/A')).replace('\n', '<br>')
        html_parts.append(f"<b>Últimos 5 jogos do {partida['mandante_nome']} (Resultados):</b><br>{ultimos_jogos_mandante_html}<br><br>")
        html_parts.append(f"<b>Últimos 5 jogos do {partida['visitante_nome']} (Resultados):</b><br>{ultimos_jogos_visitante_html}<br><br>")
        html_parts.append(f"<b>Últimos 5 Confrontos Diretos (Resultados):</b><br>{ultimos_confrontos_diretos_html}<br><br>")
        
        # Dados de Estatísticas (já vêm formatados em HTML)
        stats_mandante_html = dados_brutos.get('stats_ultimos_jogos_mandante', '<p>N/A</p>')
        stats_visitante_html = dados_brutos.get('stats_ultimos_jogos_visitante', '<p>N/A</p>')
        stats_h2h_html = dados_brutos.get('stats_ultimos_confrontos_diretos', '<p>N/A</p>')
        html_parts.append(f"<b>Últimos 5 jogos do {partida['mandante_nome']} (Estatísticas):</b>{stats_mandante_html}<br>")
        html_parts.append(f"<b>Últimos 5 jogos do {partida['visitante_nome']} (Estatísticas):</b>{stats_visitante_html}<br>")
        html_parts.append(f"<b>Últimos 5 Confrontos Diretos (Estatísticas):</b>{stats_h2h_html}")

        analise_completa = "".join(html_parts)
        
        resultado_final = {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": recomendacao_final, "detalhes": [analise_completa], "liga_nome": partida['liga_nome']}

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