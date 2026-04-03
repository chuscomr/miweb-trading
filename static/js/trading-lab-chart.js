// static/js/trading-lab.js - Parte del gráfico con indicadores

async dibujarGrafico(data, indicadores) {
    const fechas = data.data.map(d => new Date(d.Date));
    const ticker = document.getElementById('ticker').value;
    
    // ====================================
    // PREPARAR TRAZAS
    // ====================================
    const trazas = [];
    
    // ---- GRÁFICO PRINCIPAL (VELAS) ----
    trazas.push({
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
    });
    
    // Añadir medias móviles al gráfico principal
    if (indicadores.includes('MM20') && data.data[0].MM20) {
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.MM20),
            type: 'scatter',
            mode: 'lines',
            name: 'MM20',
            line: { color: '#FF9800', width: 1.5 },
            xaxis: 'x',
            yaxis: 'y'
        });
    }
    
    if (indicadores.includes('MM50') && data.data[0].MM50) {
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.MM50),
            type: 'scatter',
            mode: 'lines',
            name: 'MM50',
            line: { color: '#4CAF50', width: 1.5 },
            xaxis: 'x',
            yaxis: 'y'
        });
    }
    
    if (indicadores.includes('MM200') && data.data[0].MM200) {
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.MM200),
            type: 'scatter',
            mode: 'lines',
            name: 'MM200',
            line: { color: '#F44336', width: 1.5 },
            xaxis: 'x',
            yaxis: 'y'
        });
    }
    
    // Bandas de Bollinger
    if (indicadores.includes('BB') && data.data[0].BB_SUPERIOR) {
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.BB_SUPERIOR),
            type: 'scatter',
            mode: 'lines',
            name: 'BB Superior',
            line: { color: 'rgba(33, 150, 243, 0.5)', width: 1 },
            xaxis: 'x',
            yaxis: 'y'
        });
        
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.BB_INFERIOR),
            type: 'scatter',
            mode: 'lines',
            name: 'BB Inferior',
            line: { color: 'rgba(33, 150, 243, 0.5)', width: 1 },
            xaxis: 'x',
            yaxis: 'y',
            fill: 'tonexty',
            fillcolor: 'rgba(33, 150, 243, 0.1)'
        });
    }
    
    // ====================================
    // INDICADORES EN PANEL INFERIOR
    // ====================================
    let fila = 1; // El gráfico principal es la fila 1
    
    // ---- RSI ----
    if (indicadores.includes('RSI') && data.data[0].RSI !== undefined) {
        fila++;
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.RSI),
            type: 'scatter',
            mode: 'lines',
            name: 'RSI',
            line: { color: '#9C27B0', width: 1.5 },
            xaxis: 'x',
            yaxis: `y${fila}`
        });
    }
    
    // ---- MACD ----
    if (indicadores.includes('MACD') && data.data[0].MACD !== undefined) {
        fila++;
        
        // Línea MACD
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.MACD),
            type: 'scatter',
            mode: 'lines',
            name: 'MACD',
            line: { color: '#2196F3', width: 1.5 },
            xaxis: 'x',
            yaxis: `y${fila}`
        });
        
        // Línea de señal
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.MACD_SEÑAL),
            type: 'scatter',
            mode: 'lines',
            name: 'Señal',
            line: { color: '#FF9800', width: 1.5 },
            xaxis: 'x',
            yaxis: `y${fila}`
        });
        
        // Histograma
        const coloresHist = data.data.map(d => 
            d.MACD_HIST >= 0 ? 'rgba(0, 200, 83, 0.5)' : 'rgba(255, 61, 0, 0.5)'
        );
        
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.MACD_HIST),
            type: 'bar',
            name: 'Histograma',
            marker: { color: coloresHist },
            xaxis: 'x',
            yaxis: `y${fila}`
        });
    }
    
    // ---- ATR ----
    if (indicadores.includes('ATR') && data.data[0].ATR !== undefined) {
        fila++;
        trazas.push({
            x: fechas,
            y: data.data.map(d => d.ATR),
            type: 'scatter',
            mode: 'lines',
            name: 'ATR',
            line: { color: '#FF5722', width: 1.5 },
            xaxis: 'x',
            yaxis: `y${fila}`
        });
    }
    
    // ====================================
    // CREAR LAYOUT CON SUBPLOTS
    // ====================================
    const numFilas = fila; // Número total de filas (incluyendo precio)
    
    // Calcular alturas: precio 50%, resto 50% repartido
    const alturaPrecio = 0.5;
    const alturaResto = 0.5 / (numFilas - 1);
    
    // Configurar dominios para cada subplot
    const dominios = [];
    let acumulado = 0;
    
    for (let i = 1; i <= numFilas; i++) {
        if (i === 1) {
            dominios[i] = [acumulado, acumulado + alturaPrecio];
            acumulado += alturaPrecio;
        } else {
            dominios[i] = [acumulado, acumulado + alturaResto];
            acumulado += alturaResto;
        }
    }
    
    // Crear layout base
    const layout = {
        template: 'plotly_dark',
        paper_bgcolor: '#1A1F2E',
        plot_bgcolor: '#1A1F2E',
        font: { color: '#8C98B0', family: 'Inter, sans-serif' },
        margin: { l: 60, r: 40, t: 30, b: 50 },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#8C98B0' },
            orientation: 'h',
            y: 1.02
        },
        grid: {
            rows: numFilas,
            columns: 1,
            pattern: 'independent',
            roworder: 'top to bottom'
        }
    };
    
    // Configurar cada eje Y con su dominio
    for (let i = 1; i <= numFilas; i++) {
        const yaxis = i === 1 ? 'yaxis' : `yaxis${i}`;
        layout[yaxis] = {
            domain: dominios[i],
            gridcolor: '#2F3545',
            linecolor: '#2F3545',
            tickfont: { size: 10 },
            title: this.obtenerTituloEje(i, indicadores)
        };
        
        // Configurar formato según el indicador
        if (i === 1) {
            layout[yaxis].tickformat = '.2f';
        } else if (i === 2 && indicadores.includes('RSI')) {
            layout[yaxis].range = [0, 100];
            layout[yaxis].tickvals = [30, 50, 70];
        }
    }
    
    // Configurar ejes X (todos sincronizados)
    layout.xaxis = {
        type: 'date',
        tickformat: '%d/%m/%Y',
        gridcolor: '#2F3545',
        linecolor: '#2F3545',
        tickfont: { size: 10 },
        domain: [0, 1]
    };
    
    for (let i = 2; i <= numFilas; i++) {
        layout[`xaxis${i}`] = {
            type: 'date',
            matches: 'x',
            showticklabels: false,
            gridcolor: '#2F3545',
            domain: [0, 1]
        };
    }
    
    // ====================================
    // DIBUJAR GRÁFICO
    // ====================================
    await Plotly.newPlot('main-chart', trazas, layout, {
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        responsive: true
    });
    
    // Mostrar panel de indicadores si hay
    const panelIndicators = document.getElementById('indicators-panel');
    if (numFilas > 1) {
        panelIndicators.classList.add('active');
    } else {
        panelIndicators.classList.remove('active');
    }
    
    // Añadir líneas de RSI si está activo
    if (indicadores.includes('RSI')) {
        this.anadirLineasRSI();
    }
    
    // Añadir niveles SR
    if (indicadores.includes('SR') && data.soportes?.length) {
        this.anadirNivelesSR(data.soportes, data.resistencias);
    }
}

obtenerTituloEje(fila, indicadores) {
    if (fila === 1) return 'Precio (€)';
    
    let idx = 2;
    if (indicadores.includes('RSI')) {
        if (fila === idx++) return 'RSI';
    }
    if (indicadores.includes('MACD')) {
        if (fila === idx++) return 'MACD';
    }
    if (indicadores.includes('ATR')) {
        if (fila === idx++) return 'ATR';
    }
    return 'Valor';
}

anadirLineasRSI() {
    const formas = [
        {
            type: 'line',
            xref: 'paper',
            yref: 'y2',
            x0: 0,
            y0: 70,
            x1: 1,
            y1: 70,
            line: { color: 'rgba(255, 61, 0, 0.3)', width: 1, dash: 'dash' }
        },
        {
            type: 'line',
            xref: 'paper',
            yref: 'y2',
            x0: 0,
            y0: 30,
            x1: 1,
            y1: 30,
            line: { color: 'rgba(0, 200, 83, 0.3)', width: 1, dash: 'dash' }
        }
    ];
    
    Plotly.relayout('main-chart', { shapes: formas });
}

anadirNivelesSR(soportes, resistencias) {
    const formas = [];
    
    soportes?.forEach(s => {
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

    resistencias?.forEach(r => {
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