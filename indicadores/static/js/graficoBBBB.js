// static/js/grafico.js
/**
 * CLASE PRINCIPAL - GESTIÓN DEL GRÁFICO DE INDICADORES
 * Maneja la descarga de datos, renderizado del gráfico y actualización de paneles
 */
class GraficoIndicadores {
    constructor() {
        this.chart = document.getElementById('grafico');
        this.tipoGrafico = 'velas'; // 'velas' o 'linea'
        this.ultimosDatos = null;

        this.initEventos();
    }

    /**
     * Inicializar event listeners
     */
    initEventos() {
        // Botón actualizar
        document.getElementById('btn-actualizar').addEventListener('click', () => {
            this.cargar();
        });

        // Botón de pantalla completa
        document.getElementById('btn-fullscreen').addEventListener('click', () => {
            const container = document.querySelector('.container');
            if (!document.fullscreenElement) {
                container.requestFullscreen().catch(err => {
                    console.error('Error al entrar en pantalla completa:', err);
                });
            } else {
                document.exitFullscreen();
            }
        });

        // Botón de limpiar líneas dibujadas
        document.getElementById('btn-limpiar-lineas').addEventListener('click', () => {
            const grafico = document.getElementById('grafico');
            if (grafico && grafico.layout) {
                // Mantener solo las shapes del análisis técnico automático
                // (soportes, resistencias, fibonacci, divergencias, patrones)
                const shapesOriginales = (grafico.layout.shapes || []).filter(shape => {
                    if (!shape.line) return false;
                    
                    // Mantener líneas punteadas de S/R
                    if (shape.line.dash === 'dot') return true;
                    
                    // Mantener líneas con name específico del sistema
                    if (shape.name && (
                        shape.name.includes('soporte_') || 
                        shape.name.includes('resistencia_') ||
                        shape.name.includes('patron_')
                    )) {
                        return true;
                    }
                    
                    // Mantener líneas con colores del análisis técnico
                    if (shape.line.color) {
                        const color = shape.line.color.toString().toLowerCase();
                        // Verde soporte, rojo resistencia, fibonacci, divergencias
                        if (color.includes('22c55e') || color.includes('ef4444') ||
                            color.includes('10b981') || color.includes('8b5cf6') ||
                            color.includes('f59e0b')) {
                            return true;
                        }
                    }
                    
                    return false;
                });

                Plotly.relayout('grafico', { shapes: shapesOriginales });
            }
        });

        // Botones de tipo de gráfico
        document.getElementById('btn-velas').addEventListener('click', () => {
            this.cambiarTipoGrafico('velas');
        });

        document.getElementById('btn-linea').addEventListener('click', () => {
            this.cambiarTipoGrafico('linea');
        });

        // Autocargar al cambiar ticker o timeframe
        document.getElementById('ticker').addEventListener('change', () => this.cargar());
        document.getElementById('tf').addEventListener('change', () => this.cargar());
    }

    /**
     * Cambiar tipo de gráfico
     */
    cambiarTipoGrafico(tipo) {
        this.tipoGrafico = tipo;

        document.getElementById('btn-velas').classList.toggle('active', tipo === 'velas');
        document.getElementById('btn-linea').classList.toggle('active', tipo === 'linea');

        if (this.ultimosDatos) {
            const indicadores = this.obtenerIndicadoresSeleccionados();
            this.dibujar(this.ultimosDatos, indicadores);
        }
    }

    /**
     * Obtener indicadores seleccionados
     */
    obtenerIndicadoresSeleccionados() {
        const indicadores = [];
        document.querySelectorAll('input[type=checkbox]:checked').forEach(cb => {
            indicadores.push(cb.value);
        });
        return indicadores;
    }

    /**
     * Cargar datos desde API
     */
    async cargar() {
        const ticker = document.getElementById('ticker').value;
        const tf = document.getElementById('tf').value;
        const indicadores = this.obtenerIndicadoresSeleccionados();

        const btnActualizar = document.getElementById('btn-actualizar');
        btnActualizar.textContent = 'Cargando...';
        btnActualizar.disabled = true;

        try {
            const response = await fetch(`/indicadores/api?ticker=${ticker}&tf=${tf}&ind=${indicadores.join(',')}`);

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                const text = await response.text();
                console.error('Respuesta no-JSON del servidor:', text);
                throw new Error('El servidor devolvió un error. Revisa la consola de Flask.');
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.ultimosDatos = data;
            this.dibujar(data, indicadores);
            this.actualizarPaneles(data, indicadores);

        } catch (error) {
            console.error('Error al cargar datos:', error);
            alert(`Error cargando ${ticker}: ${error.message}`);
        } finally {
            btnActualizar.textContent = 'Actualizar';
            btnActualizar.disabled = false;
        }
    }

    /**
     * Dibujar gráfico principal con Plotly
     */
    dibujar(data, indicadores) {
        if (!data.data || data.data.length === 0) {
            console.error('No hay datos para dibujar');
            return;
        }

        const fechas = data.data.map(d => new Date(d.Date));
        const traces = [];
        const shapes = [];
        const annotations = [];

        // ===========================
        // TRAZA PRINCIPAL: PRECIO
        // ===========================
        
        // Función auxiliar para formatear fecha en tooltip
        const formatearFechaTooltip = (fecha) => {
            const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
            const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
            
            const d = new Date(fecha);
            const dia = dias[d.getDay()];
            const numero = d.getDate();
            const mes = meses[d.getMonth()];
            const año = d.getFullYear();
            
            return `${dia} ${numero} ${mes} ${año}`;
        };
        
        if (this.tipoGrafico === 'velas') {
            traces.push({
                x: fechas,
                open: data.data.map(d => d.Open),
                high: data.data.map(d => d.High),
                low: data.data.map(d => d.Low),
                close: data.data.map(d => d.Close),
                type: 'candlestick',
                name: document.getElementById('ticker').value,
                increasing: { line: { color: '#22c55e' } },
                decreasing: { line: { color: '#ef4444' } },
                xaxis: 'x',
                yaxis: 'y',
                hovertext: fechas.map((fecha, i) => {
                    const d = data.data[i];
                    const fechaFormateada = formatearFechaTooltip(fecha);
                    return `${fechaFormateada}<br>` +
                           `Apertura: ${d.Open.toFixed(2)}€<br>` +
                           `Máximo: ${d.High.toFixed(2)}€<br>` +
                           `Mínimo: ${d.Low.toFixed(2)}€<br>` +
                           `Cierre: ${d.Close.toFixed(2)}€`;
                }),
                hoverinfo: 'text'
            });
        } else {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.Close),
                type: 'scatter',
                mode: 'lines',
                name: 'Precio',
                line: { color: '#2563eb', width: 2 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: '<b>%{x|%a %d %b %Y}</b><br>Precio: %{y:.2f}€<extra></extra>'
            });
        }

        // ===========================
        // MEDIAS MÓVILES
        // ===========================
        if (indicadores.includes('MM20') && data.data[0].MM20 !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.MM20),
                type: 'scatter',
                mode: 'lines',
                name: 'MM20',
                line: { color: '#f59e0b', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y'
            });
        }

        if (indicadores.includes('MM50') && data.data[0].MM50 !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.MM50),
                type: 'scatter',
                mode: 'lines',
                name: 'MM50',
                line: { color: '#8b5cf6', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y'
            });
        }

        if (indicadores.includes('MM200') && data.data[0].MM200 !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.MM200),
                type: 'scatter',
                mode: 'lines',
                name: 'MM200',
                line: { color: '#06b6d4', width: 2 },
                xaxis: 'x',
                yaxis: 'y'
            });
        }

        // ===========================
        // BANDAS DE BOLLINGER
        // ===========================
        if (indicadores.includes('BB') && data.data[0].BB_SUPERIOR !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.BB_SUPERIOR),
                type: 'scatter',
                mode: 'lines',
                name: 'BB Superior',
                line: { color: '#94a3b8', width: 1, dash: 'dot' },
                xaxis: 'x',
                yaxis: 'y'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.BB_INFERIOR),
                type: 'scatter',
                mode: 'lines',
                name: 'BB Inferior',
                line: { color: '#94a3b8', width: 1, dash: 'dot' },
                fill: 'tonexty',
                fillcolor: 'rgba(148, 163, 184, 0.1)',
                xaxis: 'x',
                yaxis: 'y'
            });
        }

        // ===========================
        // NUEVOS INDICADORES
        // ===========================

        // EMAs
        if (indicadores.includes('EMA9') && data.data[0].EMA9 !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.EMA9),
                type: 'scatter',
                mode: 'lines',
                name: 'EMA 9',
                line: { color: '#06b6d4', width: 1.5 },
                hovertemplate: 'EMA9: %{y:.2f}€<extra></extra>'
            });
        }

        if (indicadores.includes('EMA21') && data.data[0].EMA21 !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.EMA21),
                type: 'scatter',
                mode: 'lines',
                name: 'EMA 21',
                line: { color: '#14b8a6', width: 1.5 },
                hovertemplate: 'EMA21: %{y:.2f}€<extra></extra>'
            });
        }

        if (indicadores.includes('EMA50') && data.data[0].EMA50 !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.EMA50),
                type: 'scatter',
                mode: 'lines',
                name: 'EMA 50',
                line: { color: '#10b981', width: 2 },
                hovertemplate: 'EMA50: %{y:.2f}€<extra></extra>'
            });
        }

        // PARABOLIC SAR
        if (indicadores.includes('PSAR') && data.data[0].PSAR !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.PSAR),
                type: 'scatter',
                mode: 'markers',
                name: 'PSAR',
                marker: {
                    color: data.data.map((d, i) => d.PSAR < d.Close ? '#22c55e' : '#ef4444'),
                    size: 4,
                    symbol: 'circle'
                },
                hovertemplate: 'PSAR: %{y:.2f}€<extra></extra>'
            });
        }

        // ICHIMOKU CLOUD
        if (indicadores.includes('ICHIMOKU') && data.data[0].TENKAN !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.TENKAN),
                type: 'scatter',
                mode: 'lines',
                name: 'Tenkan',
                line: { color: '#ef4444', width: 1 },
                hovertemplate: 'Tenkan: %{y:.2f}€<extra></extra>'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.KIJUN),
                type: 'scatter',
                mode: 'lines',
                name: 'Kijun',
                line: { color: '#3b82f6', width: 1 },
                hovertemplate: 'Kijun: %{y:.2f}€<extra></extra>'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.SENKOU_A),
                type: 'scatter',
                mode: 'lines',
                name: 'Senkou A',
                line: { color: 'rgba(34, 197, 94, 0.3)', width: 1 },
                fill: 'tonexty',
                fillcolor: 'rgba(34, 197, 94, 0.1)',
                showlegend: false,
                hovertemplate: 'Senkou A: %{y:.2f}€<extra></extra>'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.SENKOU_B),
                type: 'scatter',
                mode: 'lines',
                name: 'Senkou B',
                line: { color: 'rgba(239, 68, 68, 0.3)', width: 1 },
                fill: 'tonexty',
                fillcolor: 'rgba(239, 68, 68, 0.1)',
                hovertemplate: 'Senkou B: %{y:.2f}€<extra></extra>'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.CHIKOU),
                type: 'scatter',
                mode: 'lines',
                name: 'Chikou',
                line: { color: '#a855f7', width: 1, dash: 'dot' },
                hovertemplate: 'Chikou: %{y:.2f}€<extra></extra>'
            });
        }

        // ===========================
        // MFI - CORREGIDO
        // ===========================
        let mfiYAxis = null;
        if (indicadores.includes('MFI') && data.data[0].MFI !== undefined) {
            // Determinar qué eje Y usar según los indicadores activos
            const tieneRSI = indicadores.includes('RSI');
            const tieneMACD = indicadores.includes('MACD');
            const tieneOBV = indicadores.includes('OBV');
            
            // Contar paneles antes de MFI
            let numPanelesAntes = 0;
            if (tieneRSI) numPanelesAntes++;
            if (tieneMACD) numPanelesAntes++;
            if (tieneOBV) numPanelesAntes++;
            
            // Asignar nombre del eje Y
            if (numPanelesAntes === 0) mfiYAxis = 'y2';
            else if (numPanelesAntes === 1) mfiYAxis = 'y3';
            else if (numPanelesAntes === 2) mfiYAxis = 'y4';
            else if (numPanelesAntes === 3) mfiYAxis = 'y5';
            
            // Añadir traza MFI
            traces.push({
                x: fechas,
                y: data.data.map(d => d.MFI),
                type: 'scatter',
                mode: 'lines',
                name: 'MFI',
                yaxis: mfiYAxis,
                line: { color: '#f59e0b', width: 2 },
                hovertemplate: 'MFI: %{y:.1f}<extra></extra>'
            });

            // Zonas sobrecompra/sobreventa
            shapes.push(
                {
                    type: 'rect',
                    xref: 'paper',
                    yref: mfiYAxis,
                    x0: 0, x1: 1,
                    y0: 80, y1: 100,
                    fillcolor: 'rgba(239, 68, 68, 0.05)',
                    line: { width: 0 },
                    layer: 'below'
                },
                {
                    type: 'rect',
                    xref: 'paper',
                    yref: mfiYAxis,
                    x0: 0, x1: 1,
                    y0: 0, y1: 20,
                    fillcolor: 'rgba(34, 197, 94, 0.05)',
                    line: { width: 0 },
                    layer: 'below'
                }
            );
        }

        // VWAP
        if (indicadores.includes('VWAP') && data.data[0].VWAP !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.VWAP),
                type: 'scatter',
                mode: 'lines',
                name: 'VWAP',
                line: { color: '#a855f7', width: 2, dash: 'dot' },
                hovertemplate: 'VWAP: %{y:.2f}€<extra></extra>'
            });
        }

        // VOLUME PROFILE - POC
        if (indicadores.includes('VOLPROFILE') && data.data[0].POC !== undefined && data.data[data.data.length-1].POC) {
            const pocValue = data.data[data.data.length-1].POC;
            shapes.push({
                type: 'line',
                xref: 'paper',
                yref: 'y',
                x0: 0,
                x1: 1,
                y0: pocValue,
                y1: pocValue,
                line: {
                    color: '#f59e0b',
                    width: 2,
                    dash: 'dash'
                }
            });

            annotations.push({
                x: 1,
                y: pocValue,
                xref: 'paper',
                yref: 'y',
                text: `POC: ${pocValue.toFixed(2)}€`,
                showarrow: false,
                xanchor: 'left',
                bgcolor: '#f59e0b',
                font: { color: '#ffffff', size: 10, weight: 'bold' },
                borderpad: 3
            });
        }

        // KELTNER CHANNELS
        if (indicadores.includes('KELTNER') && data.data[0].KELTNER_UPPER !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.KELTNER_UPPER),
                type: 'scatter',
                mode: 'lines',
                name: 'Keltner Superior',
                line: { color: 'rgba(59, 130, 246, 0.5)', width: 1 },
                hovertemplate: 'Keltner Superior: %{y:.2f}€<extra></extra>'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.KELTNER_MIDDLE),
                type: 'scatter',
                mode: 'lines',
                name: 'Keltner Media',
                line: { color: '#3b82f6', width: 1 },
                hovertemplate: 'Keltner Media: %{y:.2f}€<extra></extra>'
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.KELTNER_LOWER),
                type: 'scatter',
                mode: 'lines',
                name: 'Keltner Inferior',
                line: { color: 'rgba(59, 130, 246, 0.5)', width: 1 },
                fill: 'tonexty',
                fillcolor: 'rgba(59, 130, 246, 0.1)',
                hovertemplate: 'Keltner Inferior: %{y:.2f}€<extra></extra>'
            });
        }

        // PIVOT POINTS
        if (indicadores.includes('PIVOT')) {
            const ultimo = data.data[data.data.length-1];
                
            if (ultimo.PIVOT_PP !== undefined && ultimo.PIVOT_PP !== null && !isNaN(ultimo.PIVOT_PP)) {
        
                console.log('✅ PIVOT POINTS - Dibujando niveles:');
                console.log('  PP:', ultimo.PIVOT_PP);
                console.log('  R1:', ultimo.PIVOT_R1);
                console.log('  S1:', ultimo.PIVOT_S1);
        
                // Obtener rango del gráfico para debug
                const maxPrecio = Math.max(...data.data.map(d => d.High));
                const minPrecio = Math.min(...data.data.map(d => d.Low));
                console.log('  Rango gráfico:', minPrecio.toFixed(2), '→', maxPrecio.toFixed(2));
        
                const pivots = [
                    { nivel: ultimo.PIVOT_R3, nombre: 'R3', color: '#b91c1c', width: 2.0, dash: 'dash' },
                    { nivel: ultimo.PIVOT_R2, nombre: 'R2', color: '#dc2626', width: 2.0, dash: 'dash' },
                    { nivel: ultimo.PIVOT_R1, nombre: 'R1', color: '#ef4444', width: 2.0, dash: 'dot' },
                    { nivel: ultimo.PIVOT_PP, nombre: 'PP', color: '#ca8a04', width: 2.5, dash: 'solid' },
                    { nivel: ultimo.PIVOT_S1, nombre: 'S1', color: '#16a34a', width: 2.0, dash: 'dot' },
                    { nivel: ultimo.PIVOT_S2, nombre: 'S2', color: '#22c55e', width: 2.0, dash: 'dash' },
                    { nivel: ultimo.PIVOT_S3, nombre: 'S3', color: '#4ade80', width: 2.0, dash: 'dash' }
                ];

                pivots.forEach(pivot => {
                    if (pivot.nivel && !isNaN(pivot.nivel) && pivot.nivel > 0) {
        
                        // Verificar si el nivel está dentro del rango visible
                        const dentroRango = pivot.nivel >= minPrecio * 0.8 && pivot.nivel <= maxPrecio * 1.2;

                        shapes.push({
                            type: 'line',
                            xref: 'paper',
                            yref: 'y',
                            x0: 0,
                            x1: 1,
                            y0: pivot.nivel,
                            y1: pivot.nivel,
                            line: {
                                color: pivot.color,
                                width: pivot.width,
                                dash: pivot.dash
                            },
                            layer: 'above'  // Sobre las velas para mejor visibilidad
                        });

                        annotations.push({
                            x: 0.01,
                            y: pivot.nivel,
                            xref: 'paper',
                            yref: 'y',
                            text: `${pivot.nombre}  ${pivot.nivel.toFixed(2)}€`,
                            showarrow: false,
                            xanchor: 'left',
                            bgcolor: 'rgba(255,255,255,0.9)',
                           font: { color: pivot.color, size: 10, weight: 'bold' },
                            borderpad: 3,
                            bordercolor: pivot.color,
                            borderwidth: 1,
                            opacity: 0.95
                        });
                    }
                });
                console.log(`📊 Shapes añadidas: ${shapes.length}`);
                console.log(`📝 Annotations añadidas: ${annotations.length}`);
        
                // 🚨🚨🚨 LÍNEA CRÍTICA AÑADIDA 🚨🚨🚨
                // Forzar actualización de shapes y annotations en el gráfico
                setTimeout(() => {
                    Plotly.relayout('grafico', {
                        shapes: shapes,
                        annotations: annotations
                    });
                    console.log('🔄 Shapes y annotations actualizadas en Plotly');
                        }, 500);

                }
            }

        // ===========================
        // CALCULAR DOMINIOS DE PANELES
        // ===========================
        const tieneRSI = indicadores.includes('RSI');
        const tieneMACD = indicadores.includes('MACD');
        const tieneVolumen = indicadores.includes('VOLUMEN');
        const tieneOBV = indicadores.includes('OBV');
        const tieneMFI = indicadores.includes('MFI');
        const tieneADX = indicadores.includes('ADX');

        const GAP = 0.01;
        const pVolumen = tieneVolumen ? 0.16 : 0;
        const pMACD = tieneMACD ? 0.11 : 0;
        const pOBV = tieneOBV ? 0.11 : 0;
        const pRSI = tieneRSI ? 0.11 : 0;
        const pMFI = tieneMFI ? 0.11 : 0;
        const pADX = tieneADX ? 0.11 : 0;

        const pPrecio = 1 - pVolumen - pOBV - pMACD - pRSI - pMFI - pADX
            - (tieneVolumen && (tieneOBV || tieneMACD || tieneRSI || tieneMFI || tieneADX) ? GAP : 0)
            - (tieneOBV ? GAP : 0)
            - (tieneMACD ? GAP : 0)
            - (tieneRSI ? GAP : 0)
            - (tieneMFI ? GAP : 0)
            - (tieneADX ? GAP : 0);

        let cursor = 0.03;
        const domVolumen = tieneVolumen ? [cursor, cursor += pVolumen] : null;
        if (tieneVolumen) cursor += GAP;
        const domOBV = tieneOBV ? [cursor, cursor += pOBV] : null;
        if (tieneOBV) cursor += GAP;
        const domMACD = tieneMACD ? [cursor, cursor += pMACD] : null;
        if (tieneMACD) cursor += GAP;
        const domRSI = tieneRSI ? [cursor, cursor += pRSI] : null;
        if (tieneRSI) cursor += GAP;
        const domMFI = tieneMFI ? [cursor, cursor += pMFI] : null;
        if (tieneMFI) cursor += GAP;
        const domADX = tieneADX ? [cursor, cursor += pADX] : null;
        if (tieneADX) cursor += GAP;
        const domPrecio = [cursor, 1]; 
        
        // ===========================
        // RSI
        // ===========================
        if (indicadores.includes('RSI') && data.data[0].RSI !== undefined) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.RSI),
                type: 'scatter',
                mode: 'lines',
                name: 'RSI',
                line: { color: '#9333ea', width: 2 },
                xaxis: 'x',
                yaxis: 'y2'
            });

            traces.push({
                x: fechas,
                y: Array(fechas.length).fill(70),
                type: 'scatter',
                mode: 'lines',
                name: 'Sobrecompra',
                line: { color: '#ef4444', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: 'y2',
                showlegend: false
            });

            traces.push({
                x: fechas,
                y: Array(fechas.length).fill(30),
                type: 'scatter',
                mode: 'lines',
                name: 'Sobreventa',
                line: { color: '#22c55e', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: 'y2',
                showlegend: false
            });
        }
        // ===========================
        // ADX
        // ===========================
        if (indicadores.includes('ADX') && data.data[0].ADX !== undefined) {

            // ADX siempre usa su propio panel (yaxis6)
            const yaxisName = 'y6';

            // Línea ADX
            traces.push({
                x: fechas,
                y: data.data.map(d => d.ADX),
                type: 'scatter',
                mode: 'lines',
                name: 'ADX',
                line: { color: '#eab308', width: 2 },
                xaxis: 'x',
                yaxis: yaxisName,
                hovertemplate: 'ADX: %{y:.2f}<extra></extra>'
            });

            // Línea +DI
            traces.push({
                x: fechas,
                y: data.data.map(d => d.DI_POS),
                type: 'scatter',
                mode: 'lines',
                name: '+DI',
                line: { color: '#22c55e', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisName,
                hovertemplate: '+DI: %{y:.2f}<extra></extra>'
            });

            // Línea -DI
            traces.push({
                x: fechas,
                y: data.data.map(d => d.DI_NEG),
                type: 'scatter',
                mode: 'lines',
                name: '-DI',
                line: { color: '#ef4444', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisName,
                hovertemplate: '-DI: %{y:.2f}<extra></extra>'
            });

            // Zona ADX > 25 (tendencia fuerte)
            shapes.push({
                type: 'rect',
                xref: 'paper',
                yref: yaxisName,
                x0: 0, x1: 1,
                y0: 25, y1: 100,
                fillcolor: 'rgba(234, 179, 8, 0.05)',
                line: { width: 0 },
                layer: 'below'
            });
        }

        // ===========================
        // MACD
        // ===========================
        if (indicadores.includes('MACD') && data.data[0].MACD !== undefined) {
            const yaxisName = tieneRSI ? 'y3' : 'y2';

            traces.push({
                x: fechas,
                y: data.data.map(d => d.MACD),
                type: 'scatter',
                mode: 'lines',
                name: 'MACD',
                line: { color: '#3b82f6', width: 2 },
                xaxis: 'x',
                yaxis: yaxisName
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.MACD_SEÑAL),
                type: 'scatter',
                mode: 'lines',
                name: 'Señal',
                line: { color: '#f59e0b', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisName
            });

            traces.push({
                x: fechas,
                y: data.data.map(d => d.MACD_HIST),
                type: 'bar',
                name: 'Histograma',
                marker: {
                    color: data.data.map(d => d.MACD_HIST >= 0 ? '#22c55e' : '#ef4444')
                },
                xaxis: 'x',
                yaxis: yaxisName
            });
        }

        // ===========================
        // OBV
        // ===========================
        if (indicadores.includes('OBV') && data.data[0].OBV !== undefined) {
            let yaxisName = 'y2';
            if (tieneRSI && tieneMACD) {
                yaxisName = 'y4';
            } else if (tieneRSI || tieneMACD) {
                yaxisName = 'y3';
            }

            traces.push({
                x: fechas,
                y: data.data.map(d => d.OBV),
                type: 'scatter',
                mode: 'lines',
                name: 'OBV',
                line: { color: '#3b82f6', width: 2 },
                xaxis: 'x',
                yaxis: yaxisName,
                hovertemplate: '<b>OBV</b><br>%{y:,.0f}<extra></extra>'
            });
        }

        // VOLUMEN
        if (indicadores.includes('VOLUMEN')) {
            traces.push({
                x: fechas,
                y: data.data.map(d => d.Volume ? d.Volume / 1000000 : 0),
                type: 'bar',
                name: 'Volumen (M)',
                yaxis: 'y5',
                marker: {
                    color: data.data.map((d, i) => {
                        if (i === 0) return '#94a3b8';
                        return d.Close > data.data[i - 1].Close ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)';
                    })
                },
                hovertemplate: '%{y:.2f}M<extra></extra>'
            });
        }

        // ===========================
        // LAYOUT
        // ===========================
        const layout = {
            template: 'plotly_white',
            paper_bgcolor: '#f8fafc',
            plot_bgcolor: '#f1f5f9',
            font: { color: '#334155', size: 11, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
            margin: { l: 60, r: 30, t: 20, b: 15 },
            hovermode: 'x unified',
            dragmode: 'pan',
            showlegend: true,
            legend: {
                orientation: 'h',
                yanchor: 'bottom',
                y: 1.02,
                xanchor: 'left',
                x: 0,
                font: { size: 10 }
            },
            xaxis: {
                type: 'date',
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                rangeslider: { visible: false },
                showspikes: true,
                spikemode: 'across',
                spikesnap: 'cursor',
                spikecolor: '#64748b',
                spikethickness: 1,
                fixedrange: false,
                rangebreaks: [
                    { bounds: ['sat', 'mon'] }
                ],
                hoverformat: '%a %d %b %Y'
            }
        };

        // Panel de precio
        layout.yaxis = {
            domain: domPrecio,
            gridcolor: '#cbd5e1',
            linecolor: '#94a3b8',
            title: { text: 'Precio (€)', font: { size: 11 } },
            fixedrange: false
        };

        // Panel RSI
        if (tieneRSI) {
            layout.yaxis2 = {
                domain: domRSI,
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                title: { text: 'RSI', font: { size: 11 } },
                range: [0, 100]
            };
        }

        // Panel ADX
        if (tieneADX) {
            layout.yaxis6 = {
                domain: domADX,
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                title: { text: 'ADX', font: { size: 11 } },
                fixedrange: false
            };
        }

        // Panel MACD
        if (tieneMACD) {
            const yaxisKey = tieneRSI ? 'yaxis3' : 'yaxis2';
            layout[yaxisKey] = {
                domain: domMACD,
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                title: { text: 'MACD', font: { size: 11 } }
            };
        }
         
        // Panel OBV
        if (tieneOBV) {
            let yaxisKey;
            if (tieneRSI && tieneMACD) {
                yaxisKey = 'yaxis4';
            } else if (tieneRSI || tieneMACD) {
                yaxisKey = 'yaxis3';
            } else {
                yaxisKey = 'yaxis2';
            }

            layout[yaxisKey] = {
                domain: domOBV,
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                title: { text: '📊 OBV', font: { size: 11 } },
                showgrid: true,
                tickfont: { size: 9 },
                hoverformat: ',.0f'
            };
        }

        // Panel MFI
        if (tieneMFI && mfiYAxis) {
            layout[mfiYAxis] = {
                domain: domMFI,
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                title: { text: 'MFI', font: { size: 11 } },
                range: [0, 100]
            };
        }

        // Panel VOLUMEN
        if (tieneVolumen) {
            layout.yaxis5 = {
                domain: domVolumen,
                gridcolor: '#cbd5e1',
                linecolor: '#94a3b8',
                title: { text: 'Volumen (M)', font: { size: 11 } },
                showgrid: false
            };
        }

        layout.newshape = {
            line: { color: '#3b82f6', width: 2, dash: 'solid' },
            fillcolor: 'rgba(59, 130, 246, 0.1)',
            opacity: 0.8,
            layer: 'above'
        };
        layout.modebar = {
            orientation: 'v',
            bgcolor: 'rgba(255,255,255,0.8)'
        };

        // ✅ CRÍTICO: Pasar shapes y annotations al layout
        layout.shapes = shapes;
        layout.annotations = annotations;

        // Configuración de la barra de herramientas
        const config = {
            displaylogo: false,
            responsive: true,
            displayModeBar: true,
            scrollZoom: true,
            modeBarButtonsToAdd: [
                'drawline',
                'drawrect',
                'drawopenpath',
                'eraseshape'
            ],
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            toImageButtonOptions: {
                format: 'png',
                filename: 'grafico_tecnico',
                height: 1080,
                width: 1920,
                scale: 2
            },
            editable: true
        };

        Plotly.newPlot('grafico', traces, layout, config);

        if (indicadores.includes('SR')) {
            this.anadirNivelesSR(data.soportes, data.resistencias);
        }

        if (indicadores.includes('FIBO') && data.fibonacci) {
            this.dibujarFibonacci(data.fibonacci);
        }

        if (data.divergencias && data.divergencias.length > 0) {
            this.dibujarDivergencias(data.divergencias, data.data, indicadores);
        }

        if (data.patrones_chartistas && data.patrones_chartistas.length > 0) {
            this.dibujarPatronesChartistas(data.patrones_chartistas);
        }
    }

    /**
     * Dibuja niveles de Fibonacci Retracement
     */
    dibujarFibonacci(fibo) {
        if (!fibo || !fibo.niveles) return;

        const shapes = [];
        const annotations = [];

        const COLORES = {
            '0%': '#3b82f6',
            '38.2%': '#10b981',
            '50%': '#3b82f6',
            '61.8%': '#8b5cf6',
            '100%': '#3b82f6'
        };

        fibo.niveles.forEach(nivel => {
            const color = COLORES[nivel.nombre] || '#94a3b8';
            const ancho = nivel.importancia === 'clave' ? 2 : 1;
            let dash = 'solid';

            if (nivel.nombre === '0%' || nivel.nombre === '100%') {
                dash = 'dash';
            } else if (nivel.nombre === '50%') {
                dash = 'dash';
            } else if (nivel.importancia === 'clave') {
                dash = 'solid';
            } else if (nivel.importancia === 'medio') {
                dash = 'dash';
            } else {
                dash = 'dot';
            }

            shapes.push({
                type: 'line',
                xref: 'paper',
                yref: 'y',
                x0: 0,
                y0: nivel.precio,
                x1: 1,
                y1: nivel.precio,
                line: { color, width: ancho, dash }
            });

            annotations.push({
                x: 1,
                y: nivel.precio,
                xref: 'paper',
                yref: 'y',
                text: `${nivel.nombre} · ${nivel.precio.toFixed(2)}€`,
                showarrow: false,
                xanchor: 'left',
                font: { size: 9, color },
                bgcolor: 'rgba(255,255,255,0.8)',
                borderpad: 2
            });
        });

        const layoutActual = document.getElementById('grafico')._fullLayout || {};
        const shapesExistentes = layoutActual.shapes || [];
        const annsExistentes = layoutActual.annotations || [];

        Plotly.relayout('grafico', {
            shapes: [...shapesExistentes, ...shapes],
            annotations: [...annsExistentes, ...annotations]
        });
    }

    /**
     * Dibuja líneas de divergencia
     */
    dibujarDivergencias(divergencias, datos, indicadores) {
        if (!divergencias || divergencias.length === 0) return;

        const shapes = [];
        const annotations = [];

        const layoutActual = document.getElementById('grafico')._fullLayout || {};
        const shapesExistentes = (layoutActual.shapes || []).filter(s => 
            !s.line || s.line.dash !== 'dot'
        );

        divergencias.forEach((div, idx) => {
            if (div.indicador === 'RSI' && !indicadores.includes('RSI')) return;
            if (div.indicador === 'MACD' && !indicadores.includes('MACD')) return;
            if (div.indicador === 'OBV' && !indicadores.includes('OBV')) return;

            const color = div.tipo === 'alcista' ? '#22c55e' : '#ef4444';
            const dash = 'dot';

            shapes.push({
                type: 'line',
                xref: 'x', yref: 'y',
                x0: div.fecha1, y0: div.precio1,
                x1: div.fecha2, y1: div.precio2,
                line: { color, width: 2, dash }
            });

            let yaxisInd = 'y2';
            if (div.indicador === 'RSI') {
                yaxisInd = 'y2';
            } else if (div.indicador === 'MACD') {
                yaxisInd = indicadores.includes('RSI') ? 'y3' : 'y2';
            } else if (div.indicador === 'OBV') {
                let yaxisOBV = 'y2';
                if (indicadores.includes('RSI') && indicadores.includes('MACD')) {
                    yaxisOBV = 'y4';
                } else if (indicadores.includes('RSI') || indicadores.includes('MACD')) {
                    yaxisOBV = 'y3';
                }
                yaxisInd = yaxisOBV;
            }

            shapes.push({
                type: 'line',
                xref: 'x', yref: yaxisInd,
                x0: div.fecha1, y0: div.ind1,
                x1: div.fecha2, y1: div.ind2,
                line: { color, width: 2, dash }
            });

            const emoji = div.tipo === 'alcista' ? '▲' : '▼';
            annotations.push({
                x: div.fecha2,
                y: div.precio2,
                xref: 'x', yref: 'y',
                text: `${emoji} Div ${div.indicador}`,
                showarrow: true,
                arrowhead: 2,
                arrowsize: 1,
                arrowcolor: color,
                ax: 0,
                ay: div.tipo === 'alcista' ? 30 : -30,
                font: { size: 9, color },
                bgcolor: 'rgba(255,255,255,0.85)',
                bordercolor: color,
                borderwidth: 1,
                borderpad: 2
            });
        });

        const annsExistentes = (layoutActual.annotations || []).filter(a =>
            !a.text || !a.text.includes('Div ')
        );

        Plotly.relayout('grafico', {
            shapes: [...shapesExistentes, ...shapes],
            annotations: [...annsExistentes, ...annotations]
        });
    }

    /**
     * Dibujar patrones chartistas
     */
    dibujarPatronesChartistas(patrones) {
        if (!patrones || patrones.length === 0) return;

        const shapes = [];
        const annotations = [];

        const layoutActual = document.getElementById('grafico')._fullLayout || {};
        const shapesExistentes = (layoutActual.shapes || []).filter(s =>
            !(s.name && s.name.startsWith('patron_'))
        );

        patrones.forEach(patron => {
            const color = patron.direccion === 'alcista' ? '#10b981' : '#ef4444';
            const colorNeck = patron.confirmado ? color : '#94a3b8';

            if (patron.tipo === 'doble_techo' || patron.tipo === 'doble_suelo') {
                shapes.push({
                    type: 'line',
                    xref: 'x', yref: 'y',
                    x0: patron.fecha1,
                    y0: patron.precio1,
                    x1: patron.fecha2,
                    y1: patron.precio2,
                    line: {
                        color: color,
                        width: 3,
                        dash: 'dot'
                    },
                    name: 'patron_' + patron.tipo + '_resistencia'
                });

                shapes.push({
                    type: 'circle',
                    xref: 'x', yref: 'y',
                    x0: patron.fecha1, y0: patron.precio1 * 0.995,
                    x1: patron.fecha1, y1: patron.precio1 * 1.005,
                    line: { color, width: 3 },
                    fillcolor: color,
                    opacity: 0.5,
                    name: 'patron_' + patron.tipo
                });

                shapes.push({
                    type: 'circle',
                    xref: 'x', yref: 'y',
                    x0: patron.fecha2, y0: patron.precio2 * 0.995,
                    x1: patron.fecha2, y1: patron.precio2 * 1.005,
                    line: { color, width: 3 },
                    fillcolor: color,
                    opacity: 0.5,
                    name: 'patron_' + patron.tipo
                });

                shapes.push({
                    type: 'line',
                    xref: 'x', yref: 'y',
                    x0: patron.fecha1,
                    y0: patron.neckline,
                    x1: patron.fecha2,
                    y1: patron.neckline,
                    line: {
                        color: colorNeck,
                        width: 2,
                        dash: patron.confirmado ? 'solid' : 'dot'
                    },
                    name: 'patron_' + patron.tipo + '_neckline'
                });

                const emoji = patron.direccion === 'alcista' ? '📈' : '📉';
                const label = patron.tipo === 'doble_techo' ? 'Doble Techo' : 'Doble Suelo';
                const estado = patron.confirmado ? ' ✓ CONFIRMADO' : ' ⚠️ En formación';

                annotations.push({
                    x: patron.fecha2,
                    y: patron.tipo === 'doble_techo' ? patron.precio2 * 1.02 : patron.precio2 * 0.98,
                    xref: 'x', yref: 'y',
                    text: `${emoji} ${label}${estado}`,
                    showarrow: true,
                    arrowhead: 2,
                    arrowsize: 1,
                    arrowcolor: color,
                    ax: 40,
                    ay: patron.direccion === 'alcista' ? 30 : -30,
                    font: { size: 11, color, weight: 'bold' },
                    bgcolor: 'rgba(255,255,255,0.95)',
                    bordercolor: color,
                    borderwidth: 2,
                    borderpad: 4
                });

            } else if (patron.tipo === 'hch' || patron.tipo === 'hch_invertido') {
                [
                    { fecha: patron.fecha_h1, precio: patron.hombro1 },
                    { fecha: patron.fecha_c, precio: patron.cabeza },
                    { fecha: patron.fecha_h2, precio: patron.hombro2 }
                ].forEach(punto => {
                    shapes.push({
                        type: 'circle',
                        xref: 'x', yref: 'y',
                        x0: punto.fecha, y0: punto.precio * 0.998,
                        x1: punto.fecha, y1: punto.precio * 1.002,
                        line: { color, width: 2 },
                        fillcolor: color,
                        opacity: 0.3,
                        name: 'patron_hch'
                    });
                });

                shapes.push({
                    type: 'line',
                    xref: 'x', yref: 'y',
                    x0: patron.fecha_h1,
                    y0: patron.neckline,
                    x1: patron.fecha_h2,
                    y1: patron.neckline,
                    line: {
                        color: colorNeck,
                        width: 2,
                        dash: patron.confirmado ? 'solid' : 'dot'
                    },
                    name: 'patron_hch'
                });

                const emoji = patron.direccion === 'alcista' ? '📈' : '📉';
                const label = patron.tipo === 'hch' ? 'HCH' : 'HCH Inv';
                annotations.push({
                    x: patron.fecha_h2,
                    y: patron.hombro2,
                    xref: 'x', yref: 'y',
                    text: `${emoji} ${label}${patron.confirmado ? ' ✓' : ''}`,
                    showarrow: true,
                    arrowhead: 2,
                    arrowsize: 1,
                    arrowcolor: color,
                    ax: 40,
                    ay: patron.direccion === 'alcista' ? 30 : -30,
                    font: { size: 10, color, weight: 'bold' },
                    bgcolor: 'rgba(255,255,255,0.9)',
                    bordercolor: color,
                    borderwidth: 2,
                    borderpad: 3
                });
            }
        });

        const annsExistentes = (layoutActual.annotations || []).filter(a =>
            !a.text || (!a.text.includes('Doble') && !a.text.includes('HCH'))
        );

        Plotly.relayout('grafico', {
            shapes: [...shapesExistentes, ...shapes],
            annotations: [...annsExistentes, ...annotations]
        });
    }

    /**
     * Añadir líneas de soporte y resistencia
     */
    anadirNivelesSR(soportes, resistencias) {
        if (!soportes && !resistencias) return;

        const grafico = document.getElementById('grafico');
        if (!grafico || !grafico.layout) {
            console.warn('Gráfico no disponible para añadir S/R');
            return;
        }

        // CRÍTICO: Obtener shapes existentes para NO borrarlas
        const shapesExistentes = grafico.layout.shapes || [];
        const newShapes = [];

        // Añadir soportes (líneas verdes punteadas)
        if (soportes && soportes.length > 0) {
            soportes.forEach(s => {
                newShapes.push({
                    type: 'line',
                    xref: 'paper',
                    yref: 'y',
                    x0: 0,
                    y0: s.precio,
                    x1: 1,
                    y1: s.precio,
                    line: {
                        color: '#22c55e',
                        width: 1.5,
                        dash: 'dot'
                    },
                    layer: 'below',
                    name: 'soporte_' + s.precio
                });
            });
        }

        // Añadir resistencias (líneas rojas punteadas)
        if (resistencias && resistencias.length > 0) {
            resistencias.forEach(r => {
                newShapes.push({
                    type: 'line',
                    xref: 'paper',
                    yref: 'y',
                    x0: 0,
                    y0: r.precio,
                    x1: 1,
                    y1: r.precio,
                    line: {
                        color: '#ef4444',
                        width: 1.5,
                        dash: 'dot'
                    },
                    layer: 'below',
                    name: 'resistencia_' + r.precio
                });
            });
        }

        // SOLUCIÓN: Combinar shapes existentes + nuevas S/R
        if (newShapes.length > 0) {
            console.log(`Añadiendo ${newShapes.length} líneas S/R al gráfico`);
            Plotly.relayout('grafico', { 
                shapes: [...shapesExistentes, ...newShapes] 
            });
        }
    }

    /**
     * Actualizar paneles laterales
     */
    actualizarPaneles(data, indicadores = []) {
        if (!data.data || data.data.length === 0) {
            console.warn('No hay datos para actualizar paneles');
            return;
        }

        const ultimo = data.data[data.data.length - 1];

        const panelVela = document.getElementById('ultima-vela');
        if (panelVela) {
            const atrPct = ultimo.ATR && ultimo.Close
                ? ((ultimo.ATR / ultimo.Close) * 100).toFixed(2) + '%'
                : '--';
            const atrValor = ultimo.ATR ? this.formatearPrecio(ultimo.ATR) : '--';
            panelVela.innerHTML = `
                <p><span>Apertura:</span> <strong>${this.formatearPrecio(ultimo.Open)}</strong></p>
                <p><span>Máximo:</span> <strong>${this.formatearPrecio(ultimo.High)}</strong></p>
                <p><span>Mínimo:</span> <strong>${this.formatearPrecio(ultimo.Low)}</strong></p>
                <p><span>Cierre:</span> <strong>${this.formatearPrecio(ultimo.Close)}</strong></p>
                <p><span>Volumen:</span> <strong>${this.formatearVolumen(ultimo.Volume)}</strong></p>
                <p><span>ATR (14):</span> <strong>${atrValor}</strong></p>
                <p><span>ATR %:</span> <strong>${atrPct}</strong></p>
            `;
        }

        const panelSoportes = document.getElementById('soportes');
        if (panelSoportes) {
            if (data.soportes && data.soportes.length > 0) {
                panelSoportes.innerHTML = data.soportes
                    .sort((a, b) => b.precio - a.precio)
                    .map(s => {
                        const distancia = s.distancia_pct ? `↓${s.distancia_pct}%` : '';
                        return `
                        <div class="nivel-precio soporte">
                            <div style="display: flex; flex-direction: column; gap: 2px;">
                                <span class="precio">${this.formatearPrecio(s.precio)}</span>
                                ${distancia ? `<span style="font-size: 10px; color: #16a34a;">${distancia}</span>` : ''}
                            </div>
                            <span class="fuerza">${s.toques || Math.round(s.fuerza || 1)} toques</span>
                        </div>
                    `}).join('');
            } else {
                panelSoportes.innerHTML = '<p style="color: #94a3b8;">No detectados debajo del precio actual</p>';
            }
        }

        const panelResistencias = document.getElementById('resistencias');
        if (panelResistencias) {
            if (data.resistencias && data.resistencias.length > 0) {
                panelResistencias.innerHTML = data.resistencias
                    .sort((a, b) => a.precio - b.precio)
                    .map(r => {
                        const distancia = r.distancia_pct ? `↑${r.distancia_pct}%` : '';
                        return `
                        <div class="nivel-precio resistencia">
                            <div style="display: flex; flex-direction: column; gap: 2px;">
                                <span class="precio">${this.formatearPrecio(r.precio)}</span>
                                ${distancia ? `<span style="font-size: 10px; color: #dc2626;">${distancia}</span>` : ''}
                            </div>
                            <span class="fuerza">${r.toques || Math.round(r.fuerza || 1)} toques</span>
                        </div>
                    `}).join('');
            } else {
                panelResistencias.innerHTML = '<p style="color: #94a3b8;">No detectadas encima del precio actual</p>';
            }
        }

        const panelPatrones = document.getElementById('patrones');
        if (panelPatrones) {
            if (data.patrones && data.patrones.length > 0) {
                const patronesRecientes = data.patrones.slice(0, 5);
                panelPatrones.innerHTML = patronesRecientes.map(p => {
                    const clasePatron = p.tipo === 'alcista' ? 'patron-alcista' :
                        p.tipo === 'bajista' ? 'patron-bajista' : 'patron-neutral';
                    const emoji = p.tipo === 'alcista' ? '📈' : p.tipo === 'bajista' ? '📉' : '⚖️';
                    return `
                        <div class="patron-vela ${clasePatron}">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <strong style="font-size: 11px;">${emoji} ${p.nombre}</strong>
                                <span style="font-size: 10px; opacity: 0.7;">${Math.round(p.confianza * 100)}%</span>
                            </div>
                            <div style="font-size: 10px; opacity: 0.8;">${p.descripcion}</div>
                            ${p.fecha ? `<div style="font-size: 9px; opacity: 0.6; margin-top: 2px;">${p.fecha}</div>` : ''}
                        </div>
                    `;
                }).join('');
            } else {
                panelPatrones.innerHTML = '<p style="color: #94a3b8;">No detectados recientemente</p>';
            }
        }

        if (data.resumen_tecnico) {
            actualizarResumenTecnico(data.resumen_tecnico);
            actualizarDesglose(data.resumen_tecnico);
        }

        const panelDivergencias = document.getElementById('divergencias');
        if (panelDivergencias) {
            if (data.divergencias && data.divergencias.length > 0) {
                const divsFiltradas = data.divergencias.filter(div => {
                    if (div.indicador === 'RSI' && !indicadores.includes('RSI')) return false;
                    if (div.indicador === 'MACD' && !indicadores.includes('MACD')) return false;
                    return true;
                });

                if (divsFiltradas.length > 0) {
                    panelDivergencias.innerHTML = divsFiltradas.map(div => {
                        const clase = div.tipo === 'alcista' ? 'patron-alcista' : 'patron-bajista';
                        const emoji = div.tipo === 'alcista' ? '📈' : '📉';
                        const badgeC = div.tipo === 'alcista'
                            ? 'background:#dcfce7;color:#15803d;border:1px solid #86efac;'
                            : 'background:#fee2e2;color:#b91c1c;border:1px solid #fca5a5;';
                        return `
                        <div class="patron-vela ${clase}" style="margin-bottom:6px;">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
                                <strong style="font-size:11px;">${emoji} Div. ${div.tipo.charAt(0).toUpperCase() + div.tipo.slice(1)} · ${div.indicador}</strong>
                                <span style="font-size:10px;padding:1px 5px;border-radius:4px;${badgeC}">${div.señal}</span>
                            </div>
                            <div style="font-size:10px;opacity:0.85;">${div.descripcion}</div>
                            <div style="font-size:9px;opacity:0.6;margin-top:2px;">${div.fecha1} → ${div.fecha2}</div>
                        </div>
                    `;
                    }).join('');
                } else {
                    panelDivergencias.innerHTML = '<p style="color:#94a3b8;font-size:0.85em;">No detectadas recientemente</p>';
                }
            } else {
                panelDivergencias.innerHTML = '<p style="color:#94a3b8;font-size:0.85em;">No detectadas recientemente</p>';
            }
        }

        const panelFibo = document.getElementById('fibonacci');
        if (panelFibo) {
            if (indicadores.includes('FIBO') && data.fibonacci && data.fibonacci.niveles) {
                const fibo = data.fibonacci;
                const dirIcon = fibo.direccion === 'bajista' ? '↘' : '↗';
                const dirColor = fibo.direccion === 'bajista' ? '#ef4444' : '#22c55e';
                const COLORES = {
                    '0%': '#8b5cf6', '38.2%': '#10b981',
                    '50%': '#3b82f6', '61.8%': '#8b5cf6', '100%': '#8b5cf6'
                };

                panelFibo.innerHTML = `
                    <div style="font-size:10px;color:#64748b;margin-bottom:6px;">
                        Impulso ${dirIcon} ${fibo.punto_inicio}€ → ${fibo.punto_final}€
                        <span style="color:${dirColor};font-weight:600;"> (${fibo.swing_pct}%)</span>
                    </div>
                    <div style="font-size:9px;color:#94a3b8;margin-bottom:8px;">
                        ${fibo.direccion === 'alcista'
                        ? '0% = mínimo, buscar entrada en retroceso'
                        : '0% = máximo, buscar rebote en retroceso'}
                    </div>
                    ${fibo.niveles.map(n => {
                            const color = COLORES[n.nombre] || '#94a3b8';
                            const bgColor = n.cerca ? `${color}18` : 'transparent';
                            const borde = n.cerca ? `1px solid ${color}44` : '1px solid transparent';
                            const bold = n.importancia === 'clave' ? 'font-weight:600;' : '';
                            const dist = n.distancia_pct >= 0
                                ? `<span style="color:#16a34a;font-size:9px;">+${n.distancia_pct}%</span>`
                                : `<span style="color:#dc2626;font-size:9px;">${n.distancia_pct}%</span>`;
                            return `
                            <div style="display:flex;justify-content:space-between;align-items:center;
                                        padding:3px 6px;border-radius:4px;margin-bottom:2px;
                                        background:${bgColor};border:${borde};">
                                <span style="color:${color};font-size:10px;${bold}">${n.nombre}</span>
                                <span style="font-size:11px;${bold}">${n.precio.toFixed(2)}€</span>
                                ${dist}
                            </div>`;
                        }).join('')}
                `;
            } else {
                panelFibo.innerHTML = '<p style="color:#94a3b8;font-size:0.85em;">Activa el checkbox Fibonacci</p>';
            }
        }

        const panelChartistas = document.getElementById('patrones_chartistas');
        if (panelChartistas) {
            if (data.patrones_chartistas && data.patrones_chartistas.length > 0) {
                panelChartistas.innerHTML = data.patrones_chartistas.map(p => {
                    const color = p.direccion === 'alcista' ? '#10b981' : '#ef4444';
                    const emoji = p.direccion === 'alcista' ? '📈' : '📉';
                    const badge = p.confirmado
                        ? '<span style="font-size:9px;color:#10b981;margin-left:4px;">✓ Confirmado</span>'
                        : '<span style="font-size:9px;color:#f59e0b;margin-left:4px;">⏱ En formación</span>';

                    let titulo = '';
                    let detalles = '';

                    if (p.tipo === 'doble_techo') {
                        titulo = '🔴 Doble Techo';
                        detalles = `
                            <div style="font-size:10px;margin-top:4px;line-height:1.4;">
                                <div>Techos: ${p.precio1}€ · ${p.precio2}€</div>
                                <div>Neckline: <strong>${p.neckline}€</strong></div>
                                <div>Objetivo: ${p.objetivo}€</div>
                            </div>`;
                    } else if (p.tipo === 'doble_suelo') {
                        titulo = '🟢 Doble Suelo';
                        detalles = `
                            <div style="font-size:10px;margin-top:4px;line-height:1.4;">
                                <div>Suelos: ${p.precio1}€ · ${p.precio2}€</div>
                                <div>Neckline: <strong>${p.neckline}€</strong></div>
                                <div>Objetivo: ${p.objetivo}€</div>
                            </div>`;
                    } else if (p.tipo === 'hch') {
                        titulo = '🔴 Hombro-Cabeza-Hombro';
                        detalles = `
                            <div style="font-size:10px;margin-top:4px;line-height:1.4;">
                                <div>H1: ${p.hombro1}€ · C: ${p.cabeza}€ · H2: ${p.hombro2}€</div>
                                <div>Neckline: <strong>${p.neckline}€</strong></div>
                                <div>Objetivo: ${p.objetivo}€</div>
                            </div>`;
                    } else if (p.tipo === 'hch_invertido') {
                        titulo = '🟢 HCH Invertido';
                        detalles = `
                            <div style="font-size:10px;margin-top:4px;line-height:1.4;">
                                <div>H1: ${p.hombro1}€ · C: ${p.cabeza}€ · H2: ${p.hombro2}€</div>
                                <div>Neckline: <strong>${p.neckline}€</strong></div>
                                <div>Objetivo: ${p.objetivo}€</div>
                            </div>`;
                    }

                    return `
                        <div style="padding:8px;margin-bottom:8px;border-left:3px solid ${color};background:${color}10;border-radius:4px;">
                            <div style="font-weight:600;font-size:11px;color:${color};margin-bottom:2px;">
                                ${titulo}${badge}
                            </div>
                            ${detalles}
                            <div style="font-size:9px;color:#64748b;margin-top:4px;font-style:italic;">
                                ${p.descripcion}
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                panelChartistas.innerHTML = '<p style="color:#94a3b8;font-size:0.85em;">No detectados en ventana de 100 velas</p>';
            }
        }
    }

    /**
     * Formatear precio con 2 decimales y símbolo €
     */
    formatearPrecio(valor) {
        if (valor === null || valor === undefined) return '--';
        return `${Number(valor).toFixed(2)} €`;
    }

    /**
     * Formatear volumen en millones
     */
    formatearVolumen(valor) {
        if (valor === null || valor === undefined) return '--';
        return `${(valor / 1000000).toFixed(2)}M`;
    }
}

// ============================================================================
// FIN DE LA CLASE - FUNCIONES GLOBALES
// ============================================================================

// ===========================
// INICIALIZACIÓN
// ===========================
const grafico = new GraficoIndicadores();

document.addEventListener('DOMContentLoaded', () => {
    grafico.cargar();
});

// ============================================================================
// FUNCIONES AUXILIARES PARA GAUGES
// ============================================================================

function dibujarGauge(svgId, puntuacion) {
    const svg = document.getElementById(svgId);
    if (!svg) return;

    svg.innerHTML = '';

    const cx = 100;
    const cy = 100;
    const radius = 70;
    const strokeWidth = 20;

    const arcoBg = describeArc(cx, cy, radius, 180, 0);
    const pathBg = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    pathBg.setAttribute('d', arcoBg);
    pathBg.setAttribute('fill', 'none');
    pathBg.setAttribute('stroke', '#e2e8f0');
    pathBg.setAttribute('stroke-width', strokeWidth);
    pathBg.setAttribute('stroke-linecap', 'round');
    svg.appendChild(pathBg);

    let color, anguloFinal;

    if (puntuacion >= 0.5) {
        color = '#22c55e';
        anguloFinal = 180 - (puntuacion * 90);
    } else if (puntuacion >= 0.2) {
        color = '#86efac';
        anguloFinal = 180 - (puntuacion * 90);
    } else if (puntuacion >= -0.2) {
        color = '#cbd5e1';
        anguloFinal = 180 - (puntuacion * 90);
    } else if (puntuacion >= -0.5) {
        color = '#fca5a5';
        anguloFinal = 180 - (puntuacion * 90);
    } else {
        color = '#ef4444';
        anguloFinal = 180 - (puntuacion * 90);
    }

    const arcoProgreso = describeArc(cx, cy, radius, 180, anguloFinal);
    const pathProgreso = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    pathProgreso.setAttribute('d', arcoProgreso);
    pathProgreso.setAttribute('fill', 'none');
    pathProgreso.setAttribute('stroke', color);
    pathProgreso.setAttribute('stroke-width', strokeWidth);
    pathProgreso.setAttribute('stroke-linecap', 'round');
    svg.appendChild(pathProgreso);

    const markerX = cx + radius * Math.cos((anguloFinal * Math.PI) / 180);
    const markerY = cy - radius * Math.sin((anguloFinal * Math.PI) / 180);

    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    marker.setAttribute('cx', markerX);
    marker.setAttribute('cy', markerY);
    marker.setAttribute('r', 8);
    marker.setAttribute('fill', color);
    marker.setAttribute('stroke', '#ffffff');
    marker.setAttribute('stroke-width', 3);
    svg.appendChild(marker);
}

function describeArc(x, y, radius, startAngle, endAngle) {
    const start = polarToCartesian(x, y, radius, endAngle);
    const end = polarToCartesian(x, y, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

    return [
        'M', start.x, start.y,
        'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y
    ].join(' ');
}

function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
    const angleInRadians = (angleInDegrees * Math.PI) / 180.0;
    return {
        x: centerX + (radius * Math.cos(angleInRadians)),
        y: centerY - (radius * Math.sin(angleInRadians))
    };
}

function actualizarResumenTecnico(resumen) {
    if (!resumen) {
        console.warn('No hay resumen técnico disponible');
        return;
    }

    if (resumen.indicadores) {
        const ind = resumen.indicadores;
        dibujarGauge('gauge-indicadores', ind.puntuacion);

        const labelInd = document.getElementById('label-indicadores');
        if (labelInd) {
            const texto = ind.puntuacion >= 0.5 ? 'Compra fuerte' :
                ind.puntuacion >= 0.2 ? 'Compra' :
                    ind.puntuacion >= -0.2 ? 'Neutral' :
                        ind.puntuacion >= -0.5 ? 'Venta' : 'Venta fuerte';

            const saldo = ind.compras - ind.ventas;
            const signo = saldo > 0 ? '+' : '';
            labelInd.querySelector('.gauge-value').textContent = `${signo}${saldo}`;
            labelInd.querySelector('.gauge-text').textContent = texto;
        }

        const detalleInd = document.getElementById('detalle-indicadores');
        if (detalleInd) {
            detalleInd.innerHTML = `
                <span class="compra">${ind.compras} Compra</span>
                <span class="venta">${ind.ventas} Venta</span>
                <span class="neutral">${ind.neutrales} Neutral</span>
            `;
        }
    }

    dibujarGauge('gauge-resumen', resumen.puntuacion_global);

    const labelResumen = document.getElementById('label-resumen');
    if (labelResumen) {
        const puntuacionReal = resumen.puntuacion || 0;
        const contexto = resumen.contexto_mm200 || '';
        const contextoFavorable = resumen.contexto_favorable;

        labelResumen.querySelector('.gauge-value').textContent = resumen.recomendacion;

        const checkMark = contextoFavorable ? '✓' : '⚠️';
        labelResumen.querySelector('.gauge-text').textContent = `${contexto} ${checkMark}`;
    }

    const recomendacionFinal = document.getElementById('recomendacion-final');
    if (recomendacionFinal) {
        const puntosCompra = resumen.puntos_compra || 0;
        const puntosVenta = resumen.puntos_venta || 0;
        const puntuacionReal = resumen.puntuacion || 0;
        const nivelConfianza = resumen.nivel_confianza || 'bajo';
        const proximidad = resumen.proximidad || null;
        const warnings = resumen.warnings || [];

        let confianzaTexto = 'Baja';
        let confianzaColor = '#94a3b8';
        if (nivelConfianza === 'muy_alto') {
            confianzaTexto = 'Muy Alta';
            confianzaColor = '#22c55e';
        } else if (nivelConfianza === 'alto') {
            confianzaTexto = 'Alta';
            confianzaColor = '#22c55e';
        } else if (nivelConfianza === 'medio') {
            confianzaTexto = 'Media';
            confianzaColor = '#f59e0b';
        } else if (nivelConfianza === 'medio_bajo') {
            confianzaTexto = 'Media-Baja';
            confianzaColor = '#f59e0b';
        }

        let html = `
            <strong>Resumen:</strong> 
            <span class="recomendacion-badge ${resumen.color}">${resumen.recomendacion}</span>
            <div style="margin-top: 8px; font-size: 0.80em; line-height: 1.6;">
                <div style="color: #64748b;">
                    <strong>Puntuación:</strong> 
                    <span style="color: ${puntuacionReal >= 0 ? '#22c55e' : '#ef4444'}; font-weight: 600;">
                        ${puntuacionReal > 0 ? '+' : ''}${puntuacionReal.toFixed(1)}
                    </span>
                    <span style="margin-left: 12px;">
                        <strong>Confianza:</strong> 
                        <span style="color: ${confianzaColor}; font-weight: 600;">${confianzaTexto}</span>
                    </span>
                </div>
        `;

        if (proximidad) {
            html += `
                <div style="color: #64748b; margin-top: 4px; font-size: 0.95em;">
                    ${proximidad}
                </div>
            `;
        }

        if (warnings.length > 0) {
            html += `<div style="margin-top: 8px; padding: 6px 8px; background-color: #fef3c7; border-left: 3px solid #f59e0b; border-radius: 4px;">`;
            warnings.forEach(warning => {
                html += `<div style="color: #92400e; font-size: 0.85em; margin: 2px 0;">⚠️ ${warning}</div>`;
            });
            html += `</div>`;
        }

        html += `
                <div style="color: #94a3b8; margin-top: 6px; font-size: 0.85em; opacity: 0.7;">
                    (${puntosCompra.toFixed(1)} compra / ${puntosVenta.toFixed(1)} venta)
                </div>
            </div>
        `;

        recomendacionFinal.innerHTML = html;
    }

    if (resumen.medias_moviles) {
        const mm = resumen.medias_moviles;
        dibujarGauge('gauge-medias', mm.puntuacion);

        const labelMm = document.getElementById('label-medias');
        if (labelMm) {
            const texto = mm.puntuacion >= 0.5 ? 'Compra fuerte' :
                mm.puntuacion >= 0.2 ? 'Compra' :
                    mm.puntuacion >= -0.2 ? 'Neutral' :
                        mm.puntuacion >= -0.5 ? 'Venta' : 'Venta fuerte';

            const saldo = mm.compras - mm.ventas;
            const signo = saldo > 0 ? '+' : '';
            labelMm.querySelector('.gauge-value').textContent = `${signo}${saldo}`;
            labelMm.querySelector('.gauge-text').textContent = texto;
        }

        const detalleMm = document.getElementById('detalle-medias');
        if (detalleMm) {
            detalleMm.innerHTML = `
                <span class="compra">${mm.compras} Compra</span>
                <span class="venta">${mm.ventas} Venta</span>
                <span class="neutral">${mm.neutrales} Neutral</span>
            `;
        }
    }

    if (resumen.gauge_volumen !== undefined) {
        const volumen = resumen.gauge_volumen;
        const ratio = resumen.ratio_volumen || 1.0;

        dibujarGauge('gauge-volumen', volumen / 100);

        const labelVolumen = document.getElementById('label-volumen');
        if (labelVolumen) {
            let texto = '';
            let color = '';

            if (volumen >= 70) {
                texto = 'Muy Alto';
                color = '#10b981';
            } else if (volumen >= 40) {
                texto = 'Alto';
                color = '#059669';
            } else if (volumen >= 10) {
                texto = 'Normal Alto';
                color = '#84cc16';
            } else if (volumen >= -10) {
                texto = 'Normal';
                color = '#94a3b8';
            } else if (volumen >= -40) {
                texto = 'Normal Bajo';
                color = '#fbbf24';
            } else if (volumen >= -70) {
                texto = 'Bajo';
                color = '#fb923c';
            } else {
                texto = 'Muy Bajo';
                color = '#ef4444';
            }

            const valueSpan = labelVolumen.querySelector('.gauge-value');
            valueSpan.textContent = Math.round(volumen);
            valueSpan.style.color = color;
            labelVolumen.querySelector('.gauge-text').textContent = texto;
        }

        const detalleVolumen = document.getElementById('detalle-volumen');
        if (detalleVolumen) {
            detalleVolumen.innerHTML = `
                <span class="ratio-volumen">${ratio.toFixed(2)}x promedio</span>
            `;
        }
    }

    if (resumen.gauge_momentum !== undefined) {
        const momentum = resumen.gauge_momentum;

        dibujarGauge('gauge-momentum', momentum / 100);

        const labelMomentum = document.getElementById('label-momentum');
        if (labelMomentum) {
            let texto = '';
            let color = '';

            if (momentum >= 60) {
                texto = 'Muy Alcista';
                color = '#10b981';
            } else if (momentum >= 30) {
                texto = 'Alcista';
                color = '#059669';
            } else if (momentum >= -30) {
                texto = 'Neutral';
                color = '#94a3b8';
            } else if (momentum >= -60) {
                texto = 'Bajista';
                color = '#f59e0b';
            } else {
                texto = 'Muy Bajista';
                color = '#ef4444';
            }

            const valueSpan = labelMomentum.querySelector('.gauge-value');
            valueSpan.textContent = Math.round(momentum);
            valueSpan.style.color = color;
            labelMomentum.querySelector('.gauge-text').textContent = texto;
        }

        const detalleMomentum = document.getElementById('detalle-momentum');
        if (detalleMomentum) {
            detalleMomentum.innerHTML = `
                <span class="momentum-info" style="font-size: 0.8em; color: #64748b;">
                    RSI (40%) + MACD (30%) + Tend (30%)
                </span>
            `;
        }
    }
}

function toggleDesglose() {
    const content = document.getElementById('desglose-content');
    const icon = document.getElementById('desglose-toggle');

    if (content.classList.contains('open')) {
        content.classList.remove('open');
        icon.classList.remove('rotated');
    } else {
        content.classList.add('open');
        icon.classList.add('rotated');
    }
}

function actualizarDesglose(resumen) {
    if (!resumen) {
        console.warn('No hay resumen técnico para desglose');
        return;
    }

    if (resumen.indicadores) {
        const ind = resumen.indicadores;

        actualizarListaSeñales(
            'ind-compra-lista',
            'ind-compra-count',
            ind.desglose_compra || [],
            'compra'
        );

        actualizarListaSeñales(
            'ind-venta-lista',
            'ind-venta-count',
            ind.desglose_venta || [],
            'venta'
        );

        actualizarListaSeñales(
            'ind-neutral-lista',
            'ind-neutral-count',
            ind.desglose_neutral || [],
            'neutral'
        );
    }

    if (resumen.medias_moviles) {
        const mm = resumen.medias_moviles;

        actualizarListaSeñales(
            'mm-compra-lista',
            'mm-compra-count',
            mm.desglose_compra || [],
            'compra'
        );

        actualizarListaSeñales(
            'mm-venta-lista',
            'mm-venta-count',
            mm.desglose_venta || [],
            'venta'
        );

        actualizarListaSeñales(
            'mm-neutral-lista',
            'mm-neutral-count',
            mm.desglose_neutral || [],
            'neutral'
        );
    }
}

function actualizarListaSeñales(listaId, countId, señales, tipo) {
    const lista = document.getElementById(listaId);
    const count = document.getElementById(countId);

    if (!lista || !count) return;

    count.textContent = señales.length;

    if (señales.length === 0) {
        lista.innerHTML = '<li class="vacio">Ninguna</li>';
        return;
    }

    lista.innerHTML = señales.map(s => {
        const indicador = s.indicador;
        const peso = s.peso.toFixed(1);
        const nombre = formatearNombreIndicador(indicador, tipo);

        return `
            <li class="${tipo}-item">
                <strong>${indicador}</strong>
                ${nombre ? `: ${nombre}` : ''}
                <span style="float: right; color: #94a3b8; font-size: 0.75rem;">
                    Peso ${peso}
                </span>
            </li>
        `;
    }).join('');
}

function formatearNombreIndicador(indicador, tipo) {
    const descripciones = {
        'RSI': {
            'compra': 'Sobreventa',
            'venta': 'Sobrecompra',
            'neutral': 'Zona neutral'
        },
        'MACD': {
            'compra': 'Cruce alcista',
            'venta': 'Cruce bajista',
            'neutral': 'Sin cruce claro'
        },
        'Estocástico': {
            'compra': 'Cruce alcista',
            'venta': 'Cruce bajista',
            'neutral': 'Zona media'
        },
        'Momentum': {
            'compra': 'Impulso alcista',
            'venta': 'Impulso bajista',
            'neutral': 'Sin impulso'
        },
        'DI±': {
            'compra': 'DI+ dominante',
            'venta': 'DI- dominante',
            'neutral': 'Equilibrados'
        },
        'MM20': {
            'compra': 'Precio por encima',
            'venta': 'Precio por debajo',
            'neutral': 'Precio en la media'
        },
        'MM50': {
            'compra': 'Precio por encima',
            'venta': 'Precio por debajo',
            'neutral': 'Precio en la media'
        },
        'MM200': {
            'compra': 'Precio por encima',
            'venta': 'Precio por debajo',
            'neutral': 'Sobreextendido'
        },
        'Alineación MM': {
            'compra': 'Alcista perfecta',
            'venta': 'Bajista perfecta',
            'neutral': 'Medias juntas'
        }
    };

    if (descripciones[indicador] && descripciones[indicador][tipo]) {
        return descripciones[indicador][tipo];
    }

    return '';
}

// Inicializar panel cerrado
document.addEventListener('DOMContentLoaded', () => {
    const content = document.getElementById('desglose-content');
    if (content) {
        content.classList.remove('open');
    }
});