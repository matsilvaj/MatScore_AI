document.addEventListener('DOMContentLoaded', function() {
    const track = document.querySelector('.carousel-track');
    if (!track) return;

    const prevButton = document.querySelector('.carousel-button.prev');
    const nextButton = document.querySelector('.carousel-button.next');
    
    nextButton.addEventListener('click', () => {
        const itemWidth = track.querySelector('.carousel-item').offsetWidth;
        // Adiciona um pequeno gap ao scroll para não colar as bordas
        track.scrollBy({ left: itemWidth + 24, top: 0, behavior: 'smooth' });
    });

    prevButton.addEventListener('click', () => {
        const itemWidth = track.querySelector('.carousel-item').offsetWidth;
        track.scrollBy({ left: -(itemWidth + 24), top: 0, behavior: 'smooth' });
    });
});