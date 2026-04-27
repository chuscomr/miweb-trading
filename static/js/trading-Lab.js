// static/js/trading-lab.js
class TradingLab {
    constructor() {
        this.chart = null;
        this.data = null;
        this.activeIndicators = new Set(['MM20', 'RSI', 'SR']);
        this.init();
    }

    init() {
        this.initEventListeners();
        this.initIndicators();
        this.cargarDatosIniciales();
    }

    initEventListeners() {
        // Botones de indicadores
        document.querySelectorAll('.ind-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const ind = btn.dataset.ind;
                if (this.activeIndicators.has(ind)) {
                    this.activeIndicators.delete(ind);
                    btn.classList.remove('active');
                } else {
                    this.activeIndicators.add(ind);
                    btn.classList.add('active');
                }
                this.actualizarIndicadoresActivos();
            });
        });

        // Cambio de timeframe
        document.getElementById('tf').addEventListener('change', () => this.analizar());
        document.getElementById('ticker').addEventListener('change', () => this.analizar());
    }

    initIndicators() {
        // Activar indicadores por defecto
        this.activeIndicators.forEach(ind => {
            const btn = document.querySelector(`[data-ind="${ind}"]`);
            if (btn) btn.classList.add('active');
        });
        this.actualizarIndicadoresActivos();
    }

    async cargarDatosIniciales() {
        await this.analizar();
    }

    async analizar() {
        try {
            this.mostrarLoading(true);
            
            const ticker = document.getElementById('ticker').value;
            const tf = document.getElementById('tf').value;
            const indicadores = Array.from(this.activeIndicators);

            // Llamar a la API
            const response = await fetch(`/indicadores/api?ticker=${ticker}&tf=${tf}&ind=${indicadores.join(',')}`);
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.data = data;
            this.actualizarInfoPanel(data);
            this.dibujarGrafico(data, indicadores);
            
        } catch (error) {
            console.error('Error:', error);
            this.mostrarError(error.message);
        } finally {
            this.mostrarLoading(false);
        }
    }

    dibujarGrafico(data, indicadores) {
        const fechas = data.data.map(d => new Date(d.Date));
        
        // Preparar trazas
        const trazas = [{
            x: fechas,
            open: data.data.map(d => d.Open),
            high: data.data.map(d => d.High),
            low: data.data.map(d => d.Low),
            close: data.data.map(d => d.Close),
            type: 'candlestick',
            name: ticker,
            xaxis: 'x',
            yaxis: 'y',
            increasing: { line: { color: '#00C853' } },
            decreasing: { line: { color: '#FF3D00' } }
        }];

        // Layout profesional
        const layout = {
            template: 'plotly_dark',
            paper_bgcolor: '#1A1F2E',
            plot_bgcolor: '#1A1F2E',
            font: { color: '#8C98B0' },
            margin: { l: 50, r: 30, t: 30, b: 50 },
            xaxis: {
                type: 'date',
                tickformat: '%d/%m/%Y',
                gridcolor: '#2F3545',
                linecolor: '#2F3545'
            },
            yaxis: {
                gridcolor: '#2F3545',
                linecolor: '#2F3545',
                tickformat: '.2f'
            },
            showlegend: true,
            legend: {
                bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#8C98B0' }
            }
        };

        Plotly.newPlot('main-chart', trazas, layout, {
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        });

        // Añadir niveles SR
        if (indicadores.includes('SR') && data.soportes?.length) {
            this.anadirNivelesSR(data.soportes, data.resistencias);
        }
    }

    anadirNivelesSR(soportes, resistencias) {
        const formas = [];
        
        soportes.forEach(s => {
            formas.push({
                type: 'line',
                xref: 'paper',
                yref: 'y',
                x0: 0,
                y0: s.precio,
                x1: 1,
                y1: s.precio,
                line: { color: '#00C853', width: 1, dash: 'dot' }
            });
        });

        resistencias.forEach(r => {
            formas.push({
                type: 'line',
                xref: 'paper',
                yref: 'y',
                x0: 0,
                y0: r.precio,
                x1: 1,
                y1: r.precio,
                line: { color: '#FF3D00', width: 1, dash: 'dot' }
            });
        });

        Plotly.relayout('main-chart', { shapes: formas });
    }

    actualizarInfoPanel(data) {
        if (!data.data?.length) return;

        const ultimo = data.data[data.data.length - 1];
        const anterior = data.data[data.data.length - 2];
        
        // Precio actual y cambio
        const cambio = ((ultimo.Close - anterior.Close) / anterior.Close * 100).toFixed(2);
        document.getElementById('current-price').textContent = `${ultimo.Close.toFixed(2)} €`;
        document.getElementById('price-change').textContent = `${cambio > 0 ? '+' : ''}${cambio}%`;
        document.getElementById('price-change').style.color = cambio >= 0 ? '#00C853' : '#FF3D00';

        // Última vela
        document.getElementById('last-candle').innerHTML = `
            <div class="stat-row"><span class="stat-label">Apertura:</span><span class="stat-value">${ultimo.Open.toFixed(2)} €</span></div>
            <div class="stat-row"><span class="stat-label">Máximo:</span><span class="stat-value">${ultimo.High.toFixed(2)} €</span></div>
            <div class="stat-row"><span class="stat-label">Mínimo:</span><span class="stat-value">${ultimo.Low.toFixed(2)} €</span></div>
            <div class="stat-row"><span class="stat-label">Cierre:</span><span class="stat-value highlight">${ultimo.Close.toFixed(2)} €</span></div>
            <div class="stat-row"><span class="stat-label">Volumen:</span><span class="stat-value">${(ultimo.Volume / 1000000).toFixed(2)}M</span></div>
        `;

        // Soportes
        if (data.soportes?.length) {
            document.getElementById('soportes-count').textContent = data.soportes.length;
            document.getElementById('soportes-list').innerHTML = data.soportes.map(s => `
                <div class="level-item soporte">
                    <span class="level-price">${s.precio.toFixed(2)} €</span>
                    <span class="level-strength">${s.fuerza || 1} toques</span>
                </div>
            `).join('');
        }

        // Resistencias
        if (data.resistencias?.length) {
            document.getElementById('resistencias-count').textContent = data.resistencias.length;
            document.getElementById('resistencias-list').innerHTML = data.resistencias.map(r => `
                <div class="level-item resistencia">
                    <span class="level-price">${r.precio.toFixed(2)} €</span>
                    <span class="level-strength">${r.fuerza || 1} toques</span>
                </div>
            `).join('');
        }
    }

    actualizarIndicadoresActivos() {
        const container = document.getElementById('active-indicators');
        const nombres = {
            'MM20': 'Media 20', 'MM50': 'Media 50', 'MM200': 'Media 200',
            'RSI': 'RSI', 'MACD': 'MACD', 'BB': 'Bollinger',
            'ATR': 'ATR', 'SR': 'S/R'
        };
        
        container.innerHTML = Array.from(this.activeIndicators)
            .map(ind => `<span class="indicator-badge">${nombres[ind] || ind}</span>`)
            .join('');
    }

    mostrarLoading(show) {
        // Implementar loading spinner
    }

    mostrarError(msg) {
        // Implementar toast de error
    }

    guardarConfig() {
        const config = {
            ticker: document.getElementById('ticker').value,
            tf: document.getElementById('tf').value,
            indicadores: Array.from(this.activeIndicators)
        };
        localStorage.setItem('trading-lab-config', JSON.stringify(config));
        // Mostrar notificación
    }

    exportar() {
        Plotly.downloadImage('main-chart', {
            format: 'png',
            width: 1200,
            height: 800,
            filename: 'analisis-tecnico'
        });
    }

    compartir() {
        // Implementar compartir
    }
}

// Inicializar
const tradingLab = new TradingLab();
window.tradingLab = tradingLab;