// app/static/js/analysis_loader.js

function initializeAnalysisLoader(apiUrl) {
    const container = document.getElementById('resultados-container');
    const datePicker = document.getElementById('date-picker');
    let eventSource = null;

    if (!container || !datePicker) {
        console.error("Elementos essenciais (container ou datePicker) não encontrados na página.");
        return;
    }

    datePicker.value = new Date().toISOString().split('T')[0];
    fetchAnalyses();

    datePicker.addEventListener('change', fetchAnalyses);

    function fetchAnalyses() {
        if (eventSource) {
            eventSource.close();
        }
        const selectedDate = datePicker.value;
        if (!selectedDate) return;

        container.innerHTML = `<h2>Análises para ${selectedDate}</h2>`;
        container.insertAdjacentHTML('beforeend', `<article aria-busy="true"></article>`);

        const fullApiUrl = `${apiUrl}?date=${selectedDate}`;
        eventSource = new EventSource(fullApiUrl);

        let currentLeagueContainer = null;
        let leagueId = '';

        eventSource.onmessage = function(event) {
            const resultado = JSON.parse(event.data);
            
            const existingSkeleton = container.querySelector('[aria-busy="true"]');
            if (existingSkeleton) {
                existingSkeleton.remove();
            }

            if (resultado.status) {
                switch (resultado.status) {
                    case 'league_start':
                        leagueId = resultado.liga_nome.replace(/\s+/g, '-').toLowerCase();
                        // ** MUDANÇA AQUI: Criar um elemento <details> para a liga **
                        container.insertAdjacentHTML('beforeend', `
                            <details id="container-${leagueId}" open>
                                <summary>${resultado.liga_nome}</summary>
                                <div class="grid league-grid"></div>
                            </details>
                        `);
                        currentLeagueContainer = document.querySelector(`#container-${leagueId} .league-grid`);
                        break;
                    case 'no_games':
                        break;
                    case 'done':
                        if (container.children.length <= 1) { // Apenas o H2 está lá
                            container.insertAdjacentHTML('beforeend', `<p>Nenhum jogo encontrado para esta data.</p>`);
                        }
                        container.insertAdjacentHTML('beforeend', `<p style="text-align: center; color: var(--success); margin-top: 2em;">✅ Busca Concluída!</p>`);
                        eventSource.close();
                        break;
                }
                return;
            }

            if (!currentLeagueContainer) return;

            // O HTML do card em si não muda, apenas onde ele é inserido
            const cardHtml = `
                <article class="match-card">
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
                    <footer>
                        <p><b>Cenário Provável:</b> ${resultado.recomendacao}</p>
                        <a href="/analysis/${resultado.analysis_id}" role="button" class="outline">Ver Análise</a>
                    </footer>
                </article>
            `;
            // Insere o card dentro da grelha da liga
            currentLeagueContainer.insertAdjacentHTML('beforeend', cardHtml);
        };

        eventSource.onerror = function() {
            eventSource.close();
            const skeleton = container.querySelector('[aria-busy="true"]');
            if (skeleton) {
                skeleton.outerHTML = '<p style="color: var(--danger); text-align: center;">Erro ao conectar com o servidor.</p>';
            }
        };
    }
}