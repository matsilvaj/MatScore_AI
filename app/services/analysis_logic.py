import json
from app import cache
from . import football_api, ai_analyzer

# --- GESTÃO DE CACHE MANUAL PARA AS LIGAS ---
def obter_ligas_disponiveis():
    cached_ligas = cache.get("lista_de_ligas")
    if cached_ligas:
        print("--- LISTA DE LIGAS ENCONTRADA NO CACHE ---")
        return cached_ligas
    
    ligas = football_api.carregar_ligas_da_api()
    cache.set("lista_de_ligas", ligas, timeout=86400)
    return ligas

# --- DEFINIÇÃO DOS PLANOS DE ACESSO ---
LIGAS_DISPONIVEIS = obter_ligas_disponiveis()
LIGAS_GRATUITAS = {
    "Brasileirão Série A": LIGAS_DISPONIVEIS.get("Brasileirão Série A", "BSA"),
    "LaLiga": LIGAS_DISPONIVEIS.get("LaLiga", "PD")
    }
LIGAS_MEMBROS = LIGAS_DISPONIVEIS

def analisar_partida(partida, analysis_date):
    from app import db
    from app.models import Analysis

    print(f"\n--- Analisando Jogo: {partida['mandante_nome']} vs {partida['visitante_nome']} ---")
    
    cached_analysis = Analysis.query.filter_by(match_api_id=partida['id'], analysis_date=analysis_date).first()
    if cached_analysis:
        print("--> Análise encontrada no cache do banco de dados.")
        resultado_cache = json.loads(cached_analysis.content)
        resultado_cache['analysis_id'] = cached_analysis.id
        return resultado_cache

    print("--> Análise não encontrada no cache. Gerando com a IA...")
    texto_completo_ia, erro = ai_analyzer.gerar_analise_ia(partida)

    if erro:
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "mandante_escudo": partida['mandante_escudo'], "visitante_escudo": partida['visitante_escudo'], "recomendacao": "Erro na IA", "detalhes": [erro]}
    
    try:
        clean_json_str = texto_completo_ia.strip().replace('```json', '').replace('```', '')
        dados_ia = json.loads(clean_json_str)
        
        recomendacao_final = dados_ia.get("mercado_principal", "Ver Análise Detalhada")
        analise_json = dados_ia.get("analise_detalhada", {})
        dados_brutos = dados_ia.get("dados_utilizados", {})
        
        html_parts = []
        html_parts.append("<b>Análise de Desempenho Recente</b>")
        dm = analise_json.get('desempenho_mandante', {})
        html_parts.append(f"<br><b>{partida['mandante_nome']}:</b>")
        html_parts.append(f"<ul><li><b>Forma:</b> {dm.get('forma', 'N/A')}</li><li><b>Ponto Forte:</b> {dm.get('ponto_forte', 'N/A')}</li><li><b>Ponto Fraco:</b> {dm.get('ponto_fraco', 'N/A')}</li></ul>")
        dv = analise_json.get('desempenho_visitante', {})
        html_parts.append(f"<b>{partida['visitante_nome']}:</b>")
        html_parts.append(f"<ul><li><b>Forma:</b> {dv.get('forma', 'N/A')}</li><li><b>Ponto Forte:</b> {dv.get('ponto_forte', 'N/A')}</li><li><b>Ponto Fraco:</b> {dv.get('ponto_fraco', 'N/A')}</li></ul>")
        
        confronto_direto_html = analise_json.get('confronto_direto', 'N/A').replace('\n', '<br>')
        informacoes_relevantes_html = analise_json.get('informacoes_relevantes', 'N/A').replace('\n', '<br>')
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

        nova_analise = Analysis(match_api_id=partida['id'], analysis_date=analysis_date, content=json.dumps(resultado_final))
        db.session.add(nova_analise)
        db.session.commit()
        print("--> Nova análise guardada no banco de dados.")
        
        resultado_final['analysis_id'] = nova_analise.id
        return resultado_final

    except json.JSONDecodeError as e:
        print(f"Erro ao processar JSON da IA: {e}")
        print("--- JSON INVÁLIDO RECEBIDO ---")
        print(texto_completo_ia)
        print("-----------------------------")
        return {"mandante_nome": partida['mandante_nome'], "visitante_nome": partida['visitante_nome'], "recomendacao": "Erro ao processar análise."}

def gerar_analises(data_para_buscar, user_tier='free'):
    """Gera o stream de análises, agora com melhorias de controlo."""
    watchlist = LIGAS_GRATUITAS if user_tier == 'free' else LIGAS_MEMBROS
    jogos_encontrados_total = 0
    
    try:
        for nome_liga, id_liga in watchlist.items():
            # --- CORREÇÃO 2: VERIFICAR JOGOS ANTES DE MOSTRAR A LIGA ---
            # 1. Primeiro, buscamos os jogos da liga.
            jogos_da_liga = football_api.buscar_jogos_do_dia(id_liga, nome_liga, data_para_buscar)
            
            # 2. Só se encontrarmos jogos é que enviamos o sinal para criar o "box".
            if jogos_da_liga:
                jogos_encontrados_total += len(jogos_da_liga)
                yield f"data: {json.dumps({'status': 'league_start', 'liga_nome': nome_liga})}\n\n"
                
                for jogo in jogos_da_liga:
                    resultado_jogo = analisar_partida(jogo, data_para_buscar)
                    yield f"data: {json.dumps(resultado_jogo)}\n\n"

        if jogos_encontrados_total == 0:
            yield f"data: {json.dumps({'status': 'no_games'})}\n\n"
        
        yield f"data: {json.dumps({'status': 'done'})}\n\n"

    # --- CORREÇÃO 1: DETETAR DESCONEXÃO DO UTILIZADOR ---
    except GeneratorExit:
        # Esta exceção é ativada automaticamente quando o utilizador fecha a página.
        print("\n--- Conexão do cliente fechada. Interrompendo a busca de análises. ---")
        # A função simplesmente termina, parando o loop e as chamadas à API.