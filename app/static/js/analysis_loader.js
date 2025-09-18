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
        container.insertAdjacentHTML('beforeend', `<div class="skeleton pulse"><div style="height: 20px; background-color: #e0e0e0; border-radius: 4px;"></div></div>`);

        // Usa a URL base fornecida e adiciona a data
        const fullApiUrl = `${apiUrl}?date=${selectedDate}`;
        eventSource = new EventSource(fullApiUrl);

        let currentLeagueContainer = null;

        eventSource.onmessage = function(event) {
            const resultado = JSON.parse(event.data);
            
            const existingSkeleton = container.querySelector('.skeleton');
            if (existingSkeleton) {
                existingSkeleton.remove();
            }

            if (resultado.status) {
                switch (resultado.status) {
                    case 'league_start':
                        const leagueId = resultado.liga_nome.replace(/\s+/g, '-').toLowerCase();
                        container.insertAdjacentHTML('beforeend', `
                            <div class="league-container" id="container-${leagueId}">
                                <div class="league-header"><strong>${resultado.liga_nome}</strong></div>
                            </div>
                        `);
                        currentLeagueContainer = document.getElementById(`container-${leagueId}`);
                        currentLeagueContainer.insertAdjacentHTML('beforeend', `<div class="skeleton pulse"><div style="height: 20px; background-color: #e0e0e0; border-radius: 4px;"></div></div>`);
                        break;
                    case 'no_games':
                        // Não faz nada para podermos ver outras ligas
                        break;
                    case 'done':
                        container.insertAdjacentHTML('beforeend', `<p style="text-align: center; font-weight: bold; color: green;">✅ Busca Concluída!</p>`);
                        eventSource.close();
                        break;
                }
                return;
            }

            if (!currentLeagueContainer) return;

            const cardHtml = `
                <div class="match-card">
                    <h3>${resultado.mandante_nome} vs ${resultado.visitante_nome}</h3>
                    <p><b>Cenário de Maior Probabilidade:</b> ${resultado.recomendacao}</p>
                    <a href="/analysis/${resultado.analysis_id}" style="text-decoration: none; background-color: #007bff; color: white; padding: 8px 12px; border-radius: 5px; display: inline-block; margin-top: 10px;">
                        Ver Análise Detalhada
                    </a>
                </div>
            `;
            currentLeagueContainer.insertAdjacentHTML('beforeend', cardHtml);
            currentLeagueContainer.insertAdjacentHTML('beforeend', `<div class="skeleton pulse"><div style="height: 20px; background-color: #e0e0e0; border-radius: 4px;"></div></div>`);
        };

        eventSource.onerror = function() {
            eventSource.close();
            const skeleton = container.querySelector('.skeleton');
            if (skeleton) {
                skeleton.outerHTML = '<p style="color: red; text-align: center;">Erro ao conectar com o servidor.</p>';
            }
        };
    }
}