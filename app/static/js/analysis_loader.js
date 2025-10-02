// app/static/js/analysis_loader.js

function initializeAnalysisLoader(apiUrl) {
    const container = document.getElementById('resultados-container');
    const skeletonLoader = document.getElementById('skeleton-loader');
    const skeletonGrid = document.getElementById('skeleton-grid');
    const loaderText = document.getElementById('loader-text');
    const datePicker = document.getElementById('date-picker');
    const prevDayBtn = document.getElementById('prev-day');
    const nextDayBtn = document.getElementById('next-day');
    
    let eventSource = null;
    let loadingInterval = null; 

    if (!container || !skeletonLoader || !skeletonGrid || !loaderText || !datePicker || !prevDayBtn || !nextDayBtn) {
        console.error("Elementos essenciais não encontrados na página.");
        return;
    }

    function startLoadingAnimation(baseText) {
        stopLoadingAnimation(); 
        let dotCount = 0;
        loaderText.textContent = baseText;
        loadingInterval = setInterval(() => {
            dotCount = (dotCount + 1) % 4;
            const dots = '.'.repeat(dotCount);
            loaderText.textContent = baseText + dots;
        }, 400); 
    }

    function stopLoadingAnimation() {
        if (loadingInterval) {
            clearInterval(loadingInterval);
            loadingInterval = null;
        }
    }

    datePicker.value = new Date().toISOString().split('T')[0];
    fetchAnalyses();

    datePicker.addEventListener('change', fetchAnalyses);
    prevDayBtn.addEventListener('click', () => changeDay(-1));
    nextDayBtn.addEventListener('click', () => changeDay(1));

    function changeDay(offset) {
        const currentDate = new Date(datePicker.value + 'T00:00:00Z');
        currentDate.setUTCDate(currentDate.getUTCDate() + offset);
        datePicker.value = currentDate.toISOString().split('T')[0];
        fetchAnalyses();
    }

    function fetchAnalyses() {
        if (eventSource) {
            eventSource.close();
        }
        const selectedDate = datePicker.value;
        if (!selectedDate) return;
        
        container.innerHTML = ''; 
        skeletonLoader.style.display = 'block';
        skeletonGrid.style.display = 'grid';
        loaderText.style.display = 'block';
        startLoadingAnimation('Encontrando partidas');

        const fullApiUrl = `${apiUrl}?date=${selectedDate}`;
        eventSource = new EventSource(fullApiUrl);

        let currentLeagueContainer = null;
        let leagueId = '';
        let hasFoundGames = false;

        eventSource.onmessage = function(event) {
            const resultado = JSON.parse(event.data);
            
            if (skeletonGrid.style.display === 'grid') {
                skeletonGrid.style.display = 'none';
            }

            if (resultado.status) {
                switch (resultado.status) {
                    case 'league_start':
                        hasFoundGames = true;
                        startLoadingAnimation('Gerando análises');
                        
                        leagueId = resultado.liga_nome.replace(/\s+/g, '-').toLowerCase();
                        const flagImg = resultado.pais_flag ? `<img src="${resultado.pais_flag}" alt="${resultado.pais_nome}" class="league-flag">` : '';
                        
                        container.insertAdjacentHTML('beforeend', `
                            <details id="container-${leagueId}" open>
                                <summary>${flagImg} ${resultado.liga_nome}</summary>
                                <div class="grid league-grid"></div>
                            </details>
                        `);
                        currentLeagueContainer = document.querySelector(`#container-${leagueId} .league-grid`);
                        break;
                    case 'no_games':
                        stopLoadingAnimation();
                        skeletonLoader.style.display = 'none';
                        break;
                    case 'done':
                        stopLoadingAnimation();
                        if (!hasFoundGames) {
                            skeletonLoader.style.display = 'none';
                            container.innerHTML = `<p style="text-align: center;">Nenhum jogo encontrado para esta data.</p>`;
                        }
                        loaderText.style.display = 'none';
                        container.insertAdjacentHTML('beforeend', `<p style="text-align: center; color: var(--success); margin-top: 2em;">✅ Busca Concluída!</p>`);
                        eventSource.close();
                        break;
                }
                return;
            }

            if (!currentLeagueContainer) return;

            // --- LÓGICA DO CARD ATUALIZADA ---
            const link = resultado.error ? `<a href="#" role="button" class="outline secondary disabled">Indisponível</a>` : `<a href="/analysis/${resultado.analysis_id}" role="button" class="outline">Ver Análise</a>`;
            const recommendation = resultado.error ? `<strong style="color: var(--danger);">${resultado.recomendacao}</strong>` : `<strong>${resultado.recomendacao}</strong>`;

            const cardHtml = `
                <article class="match-card">
                    <div class="match-card-time">${resultado.horario || 'N/A'}</div>
                    <div class="match-card-header">
                        <div class="team">
                            <img src="${resultado.mandante_escudo}" alt="Escudo do ${resultado.mandante_nome}">
                            <strong>${resultado.mandante_nome}</strong>
                        </div>
                        <span class="vs">vs</span>
                        <div class="team">
                            <img src="${resultado.visitante_escudo}" alt="Escudo do ${resultado.visitante_nome}">
                            <strong>${resultado.visitante_nome}</strong>
                        </div>
                    </div>
                    <footer class="match-card-footer">
                        <div class="scenario">
                            <span>Cenário Provável:</span>
                            ${recommendation}
                        </div>
                        ${link}
                    </footer>
                </article>
            `;
            currentLeagueContainer.insertAdjacentHTML('beforeend', cardHtml);
        };

        eventSource.onerror = function() {
            eventSource.close();
            stopLoadingAnimation();
            skeletonLoader.style.display = 'none';
            container.innerHTML = '<p style="color: var(--danger); text-align: center;">Erro ao conectar com o servidor.</p>';
        };
    }
}