/* ═══════════════════════════════════════════════════════════
   GRÁFICO PROFESIONAL - JavaScript Core
   ═══════════════════════════════════════════════════════════ */

class GraficoPro {
    constructor() {
        this.ticker = TICKER_ACTUAL;
        this.timeframe = '1d';
        this.chartType = 'candlestick';
        this.yAxisType = 'linear';  // 'linear' o 'log'
        this.pivotTipo = 'semanal';  // 'diario' o 'semanal' (POR DEFECTO: semanal)
        this.data = null;
        this.layout = null;
        this.config = null;
        this.indicadoresActivos = new Set();  // Indicadores activados
        
        // Herramientas de dibujo
        this.herramientaActiva = null;  // 'tendencia', 'canal', 'horizontal', null
        this.dibujos = [];  // Array de objetos dibujados
        this.puntosTemporal = [];  // Puntos temporales para dibujo en progreso
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.cargarDatos();
    }
    
    /* ═══ EVENT LISTENERS ═══ */
    setupEventListeners() {
        // Selector ticker
        document.getElementById('ticker-select').addEventListener('change', (e) => {
            this.ticker = e.target.value;
            this.cargarDatos();
        });
        
        // Timeframe buttons
        document.querySelectorAll('.btn-tf').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.btn-tf').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.timeframe = e.target.dataset.tf;
                this.cargarDatos();
            });
        });
        
        // Tipo gráfico buttons
        document.querySelectorAll('.btn-tipo').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.btn-tipo').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.chartType = e.target.dataset.tipo;
                this.actualizarTipoGrafico();
            });
        });
        
        // Escala (Linear/Log) buttons
        document.querySelectorAll('.btn-escala').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.btn-escala').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.yAxisType = e.target.dataset.escala;
                this.cargarDatos();  // Recargar con nueva escala
            });
        });
        
        // Desplegable de indicadores (personalizado con checkboxes)
        const btnIndicators = document.getElementById('btn-indicators');
        const indicatorsMenu = document.getElementById('indicators-menu');
        
        if (btnIndicators && indicatorsMenu) {
            // Toggle menú
            btnIndicators.addEventListener('click', (e) => {
                e.stopPropagation();
                btnIndicators.classList.toggle('open');
                indicatorsMenu.classList.toggle('show');
            });
            
            // Cerrar al hacer clic fuera
            document.addEventListener('click', (e) => {
                if (!btnIndicators.contains(e.target) && !indicatorsMenu.contains(e.target)) {
                    btnIndicators.classList.remove('open');
                    indicatorsMenu.classList.remove('show');
                }
            });
            
            // Checkboxes
            document.querySelectorAll('.indicator-check').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const indicator = e.target.value;
                    
                    if (e.target.checked) {
                        this.indicadoresActivos.add(indicator);
                    } else {
                        this.indicadoresActivos.delete(indicator);
                    }
                    
                    // Actualizar texto del botón
                    const count = this.indicadoresActivos.size;
                    if (count === 0) {
                        btnIndicators.childNodes[0].textContent = 'Seleccionar... ';
                    } else {
                        btnIndicators.childNodes[0].textContent = `${count} seleccionado${count > 1 ? 's' : ''} `;
                    }
                    
                    console.log('📊 Indicadores activos:', Array.from(this.indicadoresActivos));
                    this.actualizarGrafico();
                });
            });
        }
        
        // Herramientas de dibujo
        document.querySelectorAll('.btn-dibujo').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const herramienta = e.target.dataset.herramienta;
                
                if (herramienta === 'borrar') {
                    this.borrarDibujos();
                    return;
                }
                
                const graficoDiv = document.getElementById('grafico-pro');
                
                // Activar/desactivar herramienta
                if (this.herramientaActiva === herramienta) {
                    // Desactivar si ya estaba activa
                    this.herramientaActiva = null;
                    document.querySelectorAll('.btn-dibujo').forEach(b => b.classList.remove('active'));
                    this.puntosTemporal = [];
                    if (graficoDiv) graficoDiv.style.cursor = 'default';
                } else {
                    // Activar nueva herramienta
                    this.herramientaActiva = herramienta;
                    this.puntosTemporal = [];
                    document.querySelectorAll('.btn-dibujo').forEach(b => b.classList.remove('active'));
                    e.target.classList.add('active');
                    if (graficoDiv) graficoDiv.style.cursor = 'crosshair';
                }
                
                console.log('✏️ Herramienta activa:', this.herramientaActiva);
            });
        });
        
        // Botón Pan (Mano)
        document.getElementById('btn-pan').addEventListener('click', (e) => {
            const btnPan = e.currentTarget;  // ✅ currentTarget siempre es el botón, no el emoji
            const graficoDiv = document.getElementById('grafico-pro');
            
            if (btnPan.classList.contains('active')) {
                // Desactivar Pan → volver a Zoom
                btnPan.classList.remove('active');
                btnPan.style.background = '';
                btnPan.style.color = '';
                btnPan.style.borderColor = '';
                Plotly.relayout('grafico-pro', { dragmode: 'zoom' });
                if (graficoDiv) graficoDiv.style.cursor = 'default';
                console.log('🔍 Modo Zoom activado');
            } else {
                // Activar Pan
                this.desactivarHerramienta();  // Desactivar otras herramientas
                btnPan.classList.add('active');
                btnPan.style.background = '#3b82f6';
                btnPan.style.color = '#ffffff';
                btnPan.style.borderColor = '#2563eb';
                Plotly.relayout('grafico-pro', { dragmode: 'pan' });
                if (graficoDiv) graficoDiv.style.cursor = 'grab';
                console.log('✋ Modo Pan activado');
            }
        });
        
        // Refresh
        document.getElementById('btn-refresh').addEventListener('click', () => {
            this.cargarDatos();
        });
        
        // Screenshot
        document.getElementById('btn-screenshot').addEventListener('click', () => {
            this.tomarCaptura();
        });
        
        // Fullscreen
        document.getElementById('btn-fullscreen').addEventListener('click', () => {
            this.toggleFullscreen();
        });
    }
    
    /* ═══ CARGA DE DATOS ═══ */
    async cargarDatos() {
        this.mostrarLoading(true);
        
        try {
            const url = `${API_BASE}/data/${this.ticker}?tf=${this.timeframe}&period=2y`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error('Error cargando datos');
            }
            
            const data = await response.json();
            this.data = data;
            
            // Cargar indicadores si están activos
            if (this.indicadoresActivos.has('RSI') || this.indicadoresActivos.has('MACD')) {
                await this.cargarIndicadores();
            }
            
            // Cargar S/R si está activo
            if (this.indicadoresActivos.has('SR')) {
                await this.cargarSoportesResistencias();
            }

        // Mostrar/ocultar selector de tipo de pivot
        const pivotCheck = document.querySelector('input[value="PIVOT"]');
        const pivotSelector = document.getElementById('pivot-selector');
        
        if (pivotCheck && pivotSelector) {
            pivotCheck.addEventListener('change', () => {
                pivotSelector.style.display = pivotCheck.checked ? 'flex' : 'none';
            });
        }
        
        // Cambiar tipo de pivot
        document.querySelectorAll('input[name="pivot-tipo"]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (this.indicadoresActivos.has('PIVOT')) {
                    this.pivotTipo = radio.value;  // 'diario' o 'semanal'
                    this.crearGrafico();  // Redibujar con nuevos pivots
                }
            });
        });
        
            
            this.cargarDibujos();  // Cargar dibujos guardados para este ticker
            this.crearGrafico();
            this.setupHoverInfo();
            
        } catch (error) {
            console.error('Error:', error);
            alert('Error cargando datos: ' + error.message);
        } finally {
            this.mostrarLoading(false);
        }
    }
    
    async cargarIndicadores() {
        try {
            const indicators = [];
            if (this.indicadoresActivos.has('RSI')) indicators.push('rsi');
            if (this.indicadoresActivos.has('MACD')) indicators.push('macd');
            
            if (indicators.length === 0) return;
            
            console.log('📊 Cargando indicadores:', indicators);
            
            const url = `${API_BASE}/indicadores/${this.ticker}?indicators=${indicators.join(',')}&tf=${this.timeframe}`;
            console.log('🔗 URL:', url);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                console.error('❌ Error HTTP cargando indicadores:', response.status);
                return;
            }
            
            const data = await response.json();
            this.indicadores = data;
            console.log('✅ Indicadores cargados:', data);
            
        } catch (error) {
            console.error('❌ Error cargando indicadores:', error);
        }
    }
    
    async cargarSoportesResistencias() {
        try {
            console.log('📊 Cargando S/R...');
            
            const url = `${API_BASE}/soportes-resistencias/${this.ticker}?tf=${this.timeframe}`;
            console.log('🔗 URL:', url);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                console.error('❌ Error HTTP cargando S/R:', response.status);
                return;
            }
            
            const data = await response.json();
            this.soportesResistencias = data;
            console.log('✅ S/R cargados:', data);
            
        } catch (error) {
            console.error('❌ Error cargando S/R:', error);
        }
    }
    
    calcularMM(datos, periodo) {
        const result = [];
        for (let i = 0; i < datos.length; i++) {
            if (i < periodo - 1) {
                result.push(null);
            } else {
                const sum = datos.slice(i - periodo + 1, i + 1).reduce((a, b) => a + b, 0);
                result.push(sum / periodo);
            }
        }
        return result;
    }
    
    calcularStd(datos, periodo) {
        const result = [];
        const mm = this.calcularMM(datos, periodo);
        
        for (let i = 0; i < datos.length; i++) {
            if (i < periodo - 1 || !mm[i]) {
                result.push(null);
            } else {
                const slice = datos.slice(i - periodo + 1, i + 1);
                const mean = mm[i];
                const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / periodo;
                result.push(Math.sqrt(variance));
            }
        }
        return result;
    }
    
    calcularVWAP(high, low, close, volume) {
        const vwap = [];
        let cumVolPrice = 0;
        let cumVol = 0;
        
        for (let i = 0; i < close.length; i++) {
            const typical = (high[i] + low[i] + close[i]) / 3;
            cumVolPrice += typical * volume[i];
            cumVol += volume[i];
            vwap.push(cumVol > 0 ? cumVolPrice / cumVol : null);
        }
        return vwap;
    }
    
    calcularStochastic(high, low, close, periodo = 14) {
        const k = [];
        for (let i = 0; i < close.length; i++) {
            if (i < periodo - 1) {
                k.push(null);
            } else {
                const slice_high = high.slice(i - periodo + 1, i + 1);
                const slice_low = low.slice(i - periodo + 1, i + 1);
                const highest = Math.max(...slice_high);
                const lowest = Math.min(...slice_low);
                const range = highest - lowest;
                k.push(range > 0 ? ((close[i] - lowest) / range) * 100 : 50);
            }
        }
        
        // %D = MM3 de %K
        const d = this.calcularMM(k, 3);
        return { k, d };
    }
    
    calcularADX(high, low, close, periodo = 14) {
        const tr = [];
        const plusDM = [];
        const minusDM = [];
        
        // Calcular TR, +DM, -DM
        for (let i = 0; i < close.length; i++) {
            if (i === 0) {
                tr.push(high[i] - low[i]);
                plusDM.push(0);
                minusDM.push(0);
            } else {
                // True Range
                const hl = high[i] - low[i];
                const hc = Math.abs(high[i] - close[i-1]);
                const lc = Math.abs(low[i] - close[i-1]);
                tr.push(Math.max(hl, hc, lc));
                
                // Directional Movement
                const upMove = high[i] - high[i-1];
                const downMove = low[i-1] - low[i];
                
                if (upMove > downMove && upMove > 0) {
                    plusDM.push(upMove);
                } else {
                    plusDM.push(0);
                }
                
                if (downMove > upMove && downMove > 0) {
                    minusDM.push(downMove);
                } else {
                    minusDM.push(0);
                }
            }
        }
        
        // Calcular smoothed TR, +DM, -DM
        const atr = [];
        const smoothPlusDM = [];
        const smoothMinusDM = [];
        
        let sumTR = 0, sumPlusDM = 0, sumMinusDM = 0;
        
        for (let i = 0; i < close.length; i++) {
            if (i < periodo) {
                sumTR += tr[i];
                sumPlusDM += plusDM[i];
                sumMinusDM += minusDM[i];
                
                if (i === periodo - 1) {
                    atr.push(sumTR / periodo);
                    smoothPlusDM.push(sumPlusDM / periodo);
                    smoothMinusDM.push(sumMinusDM / periodo);
                } else {
                    atr.push(null);
                    smoothPlusDM.push(null);
                    smoothMinusDM.push(null);
                }
            } else {
                const prevATR = atr[i-1];
                const prevPlusDM = smoothPlusDM[i-1];
                const prevMinusDM = smoothMinusDM[i-1];
                
                atr.push((prevATR * (periodo - 1) + tr[i]) / periodo);
                smoothPlusDM.push((prevPlusDM * (periodo - 1) + plusDM[i]) / periodo);
                smoothMinusDM.push((prevMinusDM * (periodo - 1) + minusDM[i]) / periodo);
            }
        }
        
        // Calcular +DI, -DI
        const plusDI = [];
        const minusDI = [];
        const dx = [];
        
        for (let i = 0; i < close.length; i++) {
            if (atr[i] && atr[i] > 0) {
                plusDI.push((smoothPlusDM[i] / atr[i]) * 100);
                minusDI.push((smoothMinusDM[i] / atr[i]) * 100);
                
                const diSum = plusDI[i] + minusDI[i];
                const diDiff = Math.abs(plusDI[i] - minusDI[i]);
                dx.push(diSum > 0 ? (diDiff / diSum) * 100 : 0);
            } else {
                plusDI.push(null);
                minusDI.push(null);
                dx.push(null);
            }
        }
        
        // Calcular ADX (media móvil de DX)
        const adx = this.calcularMM(dx, periodo);
        
        return { adx, plusDI, minusDI };
    }
    
    detectarDivergencias(prices, indicator, ventana = 8) {
        const divergencias = [];
        
        // Encontrar picos locales en precio
        const picosPrecio = [];
        const vallesPrecio = [];
        
        for (let i = ventana; i < prices.length - ventana; i++) {
            let esPico = true;
            let esValle = true;
            
            for (let j = 1; j <= ventana; j++) {
                if (prices[i] <= prices[i - j] || prices[i] <= prices[i + j]) {
                    esPico = false;
                }
                if (prices[i] >= prices[i - j] || prices[i] >= prices[i + j]) {
                    esValle = false;
                }
            }
            
            if (esPico) picosPrecio.push(i);
            if (esValle) vallesPrecio.push(i);
        }
        
        // Buscar divergencias alcistas (precio baja, indicador sube)
        for (let i = 1; i < vallesPrecio.length; i++) {
            const idx1 = vallesPrecio[i - 1];
            const idx2 = vallesPrecio[i];
            
            // Filtro 1: Distancia mínima entre valles (al menos 10 velas)
            if (idx2 - idx1 < 10) continue;
            
            // Filtro 2: Distancia máxima (no más de 100 velas)
            if (idx2 - idx1 > 100) continue;
            
            if (indicator[idx1] && indicator[idx2]) {
                const precioDiff = ((prices[idx1] - prices[idx2]) / prices[idx1]) * 100;
                const indDiff = ((indicator[idx2] - indicator[idx1]) / indicator[idx1]) * 100;
                
                // Filtro 3: Divergencia significativa (precio baja >2%, RSI sube >5%)
                if (precioDiff > 2 && indDiff > 5) {
                    divergencias.push({
                        tipo: 'alcista',
                        inicio: idx1,
                        fin: idx2,
                        precio1: prices[idx1],
                        precio2: prices[idx2],
                        ind1: indicator[idx1],
                        ind2: indicator[idx2]
                    });
                }
            }
        }
        
        // Buscar divergencias bajistas (precio sube, indicador baja)
        for (let i = 1; i < picosPrecio.length; i++) {
            const idx1 = picosPrecio[i - 1];
            const idx2 = picosPrecio[i];
            
            // Filtro 1: Distancia mínima entre picos
            if (idx2 - idx1 < 10) continue;
            
            // Filtro 2: Distancia máxima
            if (idx2 - idx1 > 100) continue;
            
            if (indicator[idx1] && indicator[idx2]) {
                const precioDiff = ((prices[idx2] - prices[idx1]) / prices[idx1]) * 100;
                const indDiff = ((indicator[idx1] - indicator[idx2]) / indicator[idx1]) * 100;
                
                // Filtro 3: Divergencia significativa (precio sube >2%, RSI baja >5%)
                if (precioDiff > 2 && indDiff > 5) {
                    divergencias.push({
                        tipo: 'bajista',
                        inicio: idx1,
                        fin: idx2,
                        precio1: prices[idx1],
                        precio2: prices[idx2],
                        ind1: indicator[idx1],
                        ind2: indicator[idx2]
                    });
                }
            }
        }
        
        return divergencias;
    }
    
    detectarPatronesVelas() {
        const patrones = [];
        const { open, high, low, close } = this.data;
        
        // Calcular promedio de rangos (últimas 20 velas)
        let sumRanges = 0;
        const periodAvg = Math.min(20, close.length);
        for (let j = close.length - periodAvg; j < close.length; j++) {
            sumRanges += high[j] - low[j];
        }
        const avgRange = sumRanges / periodAvg;
        
        for (let i = 2; i < close.length; i++) {
            const prev2 = { o: open[i-2], h: high[i-2], l: low[i-2], c: close[i-2] };
            const prev = { o: open[i-1], h: high[i-1], l: low[i-1], c: close[i-1] };
            const curr = { o: open[i], h: high[i], l: low[i], c: close[i] };
            
            const body = Math.abs(curr.c - curr.o);
            const currBody = body;  // Alias para consistencia
            const upperShadow = curr.h - Math.max(curr.o, curr.c);
            const lowerShadow = Math.min(curr.o, curr.c) - curr.l;
            const range = curr.h - curr.l;
            
            // MARTILLO (Bullish reversal - posible pullback terminado)
            if (curr.c > curr.o && // Vela verde
                lowerShadow > body * 2 && // Sombra inferior > 2x cuerpo
                upperShadow < body * 0.3 && // Sombra superior pequeña
                prev.c < prev.o) { // Vela anterior roja
                patrones.push({ idx: i, tipo: 'martillo', señal: 'alcista' });
            }
            
            // SHOOTING STAR (Bearish reversal - posible breakout fallido)
            if (curr.c < curr.o && // Vela roja
                upperShadow > body * 2 && // Sombra superior > 2x cuerpo
                lowerShadow < body * 0.3 && // Sombra inferior pequeña
                prev.c > prev.o) { // Vela anterior verde
                patrones.push({ idx: i, tipo: 'shooting_star', señal: 'bajista' });
            }
            
            // ENVOLVENTE ALCISTA (Bullish engulfing - breakout alcista)
            if (prev.c < prev.o && // Vela anterior roja
                curr.c > curr.o && // Vela actual verde
                curr.o < prev.c && // Abre por debajo del cierre anterior
                curr.c > prev.o) { // Cierra por encima de la apertura anterior
                patrones.push({ idx: i, tipo: 'envolvente_alcista', señal: 'alcista' });
            }
            
            // ENVOLVENTE BAJISTA (Bearish engulfing - breakout bajista)
            if (prev.c > prev.o && // Vela anterior verde
                curr.c < curr.o && // Vela actual roja
                curr.o > prev.c && // Abre por encima del cierre anterior
                curr.c < prev.o) { // Cierra por debajo de la apertura anterior
                patrones.push({ idx: i, tipo: 'envolvente_bajista', señal: 'bajista' });
            }
            
            // DOJI (Indecisión - posible reversión)
            if (body < range * 0.1) { // Cuerpo muy pequeño
                patrones.push({ idx: i, tipo: 'doji', señal: 'neutral' });
            }
            
            // VELA DE MOMENTUM (Breakout confirmado)
            const prevBody = Math.abs(prev.c - prev.o);
            if (body > prevBody * 1.5 && body > range * 0.7) {
                const señal = curr.c > curr.o ? 'alcista' : 'bajista';
                patrones.push({ idx: i, tipo: 'momentum', señal });
            }
            
            // ESTRELLA DE LA MAÑANA (Morning Star - reversión alcista fuerte)
            const prev2Body = Math.abs(prev2.c - prev2.o);
            const prevRange = prev.h - prev.l;
            if (i >= 2 &&
                prev2.c < prev2.o && // Vela 1: roja
                prev2Body > avgRange * 0.8 && // Vela 1: cuerpo GRANDE (>80% del promedio)
                Math.abs(prev.c - prev.o) < avgRange * 0.2 && // Vela 2: MUY pequeña (<20% del promedio)
                prev.h < prev2.c && // Vela 2: GAP DOWN (máximo de vela 2 < cierre de vela 1)
                curr.c > curr.o && // Vela 3: verde
                currBody > avgRange * 0.6 && // Vela 3: cuerpo grande
                curr.c > prev2.c + (prev2.o - prev2.c) * 0.5) { // Vela 3 cierra dentro del 50% superior de vela 1
                patrones.push({ idx: i, tipo: 'estrella_mañana', señal: 'alcista' });
            }
            
            // ESTRELLA DE LA TARDE (Evening Star - reversión bajista fuerte)
            if (i >= 2 &&
                prev2.c > prev2.o && // Vela 1: verde
                prev2Body > avgRange * 0.8 && // Vela 1: cuerpo GRANDE (>80% del promedio)
                Math.abs(prev.c - prev.o) < avgRange * 0.2 && // Vela 2: MUY pequeña (<20% del promedio)
                prev.l > prev2.c && // Vela 2: GAP UP (mínimo de vela 2 > cierre de vela 1)
                curr.c < curr.o && // Vela 3: roja
                currBody > avgRange * 0.6 && // Vela 3: cuerpo grande
                curr.c < prev2.c - (prev2.c - prev2.o) * 0.5) { // Vela 3 cierra dentro del 50% inferior de vela 1
                patrones.push({ idx: i, tipo: 'estrella_tarde', señal: 'bajista' });
            }
            
            // TRES SOLDADOS BLANCOS (Three White Soldiers - tendencia alcista fuerte)
            if (i >= 2 &&
                prev2.c > prev2.o && curr.c > curr.o && prev.c > prev.o && // 3 velas verdes
                curr.c > prev.c && prev.c > prev2.c && // Cierres ascendentes
                curr.o > prev.o && prev.o > prev2.o && // Aperturas ascendentes
                curr.o < prev.c && prev.o < prev2.c) { // Cada vela abre dentro del cuerpo anterior
                patrones.push({ idx: i, tipo: 'tres_soldados', señal: 'alcista' });
            }
            
            // TRES CUERVOS NEGROS (Three Black Crows - tendencia bajista fuerte)
            if (i >= 2 &&
                prev2.c < prev2.o && curr.c < curr.o && prev.c < prev.o && // 3 velas rojas
                curr.c < prev.c && prev.c < prev2.c && // Cierres descendentes
                curr.o < prev.o && prev.o < prev2.o && // Aperturas descendentes
                curr.o > prev.c && prev.o > prev2.c) { // Cada vela abre dentro del cuerpo anterior
                patrones.push({ idx: i, tipo: 'tres_cuervos', señal: 'bajista' });
            }
        }
        
        return patrones;
    }
    detectarPatronesChartistas() {
        const patrones = [];
        const { high, low, close, dates } = this.data;
        const n = close.length;
        
        if (n < 50) return patrones;  // Necesitamos historia suficiente
        
        // Buscar máximos y mínimos locales significativos
        const pivots = this.encontrarPivots(high, low, 5);
        
        if (pivots.highs.length < 3 || pivots.lows.length < 3) return patrones;
        
        // Analizar últimos 60-100 períodos para patrones
        const ventanaAnalisis = Math.min(100, n);
        const desde = n - ventanaAnalisis;
        
        // ═══════════════════════════════════════════════════════
        // HOMBRO-CABEZA-HOMBRO (HCH)
        // ═══════════════════════════════════════════════════════
        const hch = this.detectarHCH(pivots.highs, pivots.lows, desde);
        if (hch) patrones.push(hch);
        
        // ═══════════════════════════════════════════════════════
        // HCH INVERTIDO
        // ═══════════════════════════════════════════════════════
        const hchInv = this.detectarHCHInvertido(pivots.highs, pivots.lows, desde);
        if (hchInv) patrones.push(hchInv);
        
        // ═══════════════════════════════════════════════════════
        // DOBLE TECHO
        // ═══════════════════════════════════════════════════════
        const dobleTecho = this.detectarDobleTecho(pivots.highs, desde);
        if (dobleTecho) patrones.push(dobleTecho);
        
        // ═══════════════════════════════════════════════════════
        // DOBLE SUELO
        // ═══════════════════════════════════════════════════════
        const dobleSuelo = this.detectarDobleSuelo(pivots.lows, desde);
        if (dobleSuelo) patrones.push(dobleSuelo);
        
        // ═══════════════════════════════════════════════════════
        // TRIÁNGULOS
        // ═══════════════════════════════════════════════════════
        const triangulo = this.detectarTriangulos(pivots, high, low, desde);
        if (triangulo) patrones.push(triangulo);
        
        // ═══════════════════════════════════════════════════════
        // BANDERAS
        // ═══════════════════════════════════════════════════════
        const bandera = this.detectarBanderas(high, low, close, desde);
        if (bandera) patrones.push(bandera);
        
        return patrones;
    }
    
    encontrarPivots(high, low, ventana) {
        const highs = [];
        const lows = [];
        
        for (let i = ventana; i < high.length - ventana; i++) {
            // Pivot High (máximo local)
            let esMaximo = true;
            for (let j = i - ventana; j <= i + ventana; j++) {
                if (j !== i && high[j] >= high[i]) {
                    esMaximo = false;
                    break;
                }
            }
            if (esMaximo) {
                highs.push({ idx: i, precio: high[i] });
            }
            
            // Pivot Low (mínimo local)
            let esMinimo = true;
            for (let j = i - ventana; j <= i + ventana; j++) {
                if (j !== i && low[j] <= low[i]) {
                    esMinimo = false;
                    break;
                }
            }
            if (esMinimo) {
                lows.push({ idx: i, precio: low[i] });
            }
        }
        
        return { highs, lows };
    }
    
    detectarHCH(highs, lows, desde) {
        // Buscar 3 máximos: HI - Cabeza - HD
        for (let i = highs.length - 1; i >= 2; i--) {
            const hd = highs[i];  // Hombro derecho (más reciente)
            const cabeza = highs[i-1];
            const hi = highs[i-2];  // Hombro izquierdo
            
            if (hi.idx < desde) continue;
            
            // Validaciones HCH:
            // 1. Cabeza más alta que hombros
            if (cabeza.precio <= hi.precio || cabeza.precio <= hd.precio) continue;
            
            // 2. Hombros a altura similar (±5%)
            const difHombros = Math.abs(hi.precio - hd.precio) / hi.precio;
            if (difHombros > 0.05) continue;
            
            // 3. Buscar línea de cuello (mínimos entre los máximos)
            const minEntreHiCabeza = this.encontrarMinimoEntre(lows, hi.idx, cabeza.idx);
            const minEntreCabezaHd = this.encontrarMinimoEntre(lows, cabeza.idx, hd.idx);
            
            if (!minEntreHiCabeza || !minEntreCabezaHd) continue;
            
            // Línea de cuello debe ser aproximadamente horizontal (±3%)
            const difCuello = Math.abs(minEntreHiCabeza.precio - minEntreCabezaHd.precio) / minEntreHiCabeza.precio;
            if (difCuello > 0.03) continue;
            
            return {
                tipo: 'hch',
                señal: 'bajista',
                puntos: [hi, cabeza, hd],
                cuello: (minEntreHiCabeza.precio + minEntreCabezaHd.precio) / 2,
                inicio: hi.idx,
                fin: hd.idx
            };
        }
        return null;
    }
    
    detectarHCHInvertido(highs, lows, desde) {
        // Buscar 3 mínimos: HI - Cabeza - HD
        for (let i = lows.length - 1; i >= 2; i--) {
            const hd = lows[i];
            const cabeza = lows[i-1];
            const hi = lows[i-2];
            
            if (hi.idx < desde) continue;
            
            // Cabeza más baja que hombros
            if (cabeza.precio >= hi.precio || cabeza.precio >= hd.precio) continue;
            
            // Hombros a altura similar
            const difHombros = Math.abs(hi.precio - hd.precio) / hi.precio;
            if (difHombros > 0.05) continue;
            
            // Línea de cuello
            const maxEntreHiCabeza = this.encontrarMaximoEntre(highs, hi.idx, cabeza.idx);
            const maxEntreCabezaHd = this.encontrarMaximoEntre(highs, cabeza.idx, hd.idx);
            
            if (!maxEntreHiCabeza || !maxEntreCabezaHd) continue;
            
            const difCuello = Math.abs(maxEntreHiCabeza.precio - maxEntreCabezaHd.precio) / maxEntreHiCabeza.precio;
            if (difCuello > 0.03) continue;
            
            return {
                tipo: 'hch_invertido',
                señal: 'alcista',
                puntos: [hi, cabeza, hd],
                cuello: (maxEntreHiCabeza.precio + maxEntreCabezaHd.precio) / 2,
                inicio: hi.idx,
                fin: hd.idx
            };
        }
        return null;
    }
    
    detectarDobleTecho(highs, desde) {
        for (let i = highs.length - 1; i >= 1; i--) {
            const techo2 = highs[i];
            const techo1 = highs[i-1];
            
            if (techo1.idx < desde) continue;
            
            // Techos a altura similar (±2%)
            const dif = Math.abs(techo1.precio - techo2.precio) / techo1.precio;
            if (dif > 0.02) continue;
            
            // Separación razonable (15-50 velas) - más estricto
            const separacion = techo2.idx - techo1.idx;
            if (separacion < 15 || separacion > 50) continue;
            
            // NUEVO: Validar que hay un valle significativo entre ambos techos
            // (debe bajar al menos 3% desde el primer techo)
            let huboValle = false;
            let minEntreTechos = techo1.precio;
            
            for (let j = techo1.idx + 1; j < techo2.idx; j++) {
                if (this.data.low[j] < minEntreTechos) {
                    minEntreTechos = this.data.low[j];
                }
            }
            
            const bajadaEntreTechos = (techo1.precio - minEntreTechos) / techo1.precio;
            if (bajadaEntreTechos < 0.03) continue;  // Debe bajar al menos 3%
            
            return {
                tipo: 'doble_techo',
                señal: 'bajista',
                puntos: [techo1, techo2],
                inicio: techo1.idx,
                fin: techo2.idx
            };
        }
        return null;
    }
    
    detectarDobleSuelo(lows, desde) {
        for (let i = lows.length - 1; i >= 1; i--) {
            const suelo2 = lows[i];
            const suelo1 = lows[i-1];
            
            if (suelo1.idx < desde) continue;
            
            // Suelos a altura similar (±2%)
            const dif = Math.abs(suelo1.precio - suelo2.precio) / suelo1.precio;
            if (dif > 0.02) continue;
            
            // Separación razonable (15-50 velas) - más estricto
            const separacion = suelo2.idx - suelo1.idx;
            if (separacion < 15 || separacion > 50) continue;
            
            // NUEVO: Validar que hay un pico significativo entre ambos suelos
            // (debe subir al menos 3% desde el primer suelo)
            let maxEntreSuelos = suelo1.precio;
            
            for (let j = suelo1.idx + 1; j < suelo2.idx; j++) {
                if (this.data.high[j] > maxEntreSuelos) {
                    maxEntreSuelos = this.data.high[j];
                }
            }
            
            const subidaEntreSuelos = (maxEntreSuelos - suelo1.precio) / suelo1.precio;
            if (subidaEntreSuelos < 0.03) continue;  // Debe subir al menos 3%
            
            return {
                tipo: 'doble_suelo',
                señal: 'alcista',
                puntos: [suelo1, suelo2],
                inicio: suelo1.idx,
                fin: suelo2.idx
            };
        }
        return null;
    }
    
    detectarTriangulos(pivots, high, low, desde) {
        const { highs, lows } = pivots;
        
        // Necesitamos al menos 3 pivots de cada tipo para un triángulo válido
        if (highs.length < 3 || lows.length < 3) return null;
        
        // Analizar últimos 3 pivots de cada tipo
        const ultimosHighs = highs.slice(-3);
        const ultimosLows = lows.slice(-3);
        
        // Validar que todos estén en la ventana de análisis
        if (ultimosHighs[0].idx < desde || ultimosLows[0].idx < desde) return null;
        
        // ══════════════════════════════════════════════════════════
        // TRIÁNGULO ASCENDENTE: resistencia horizontal + soporte ascendente
        // ══════════════════════════════════════════════════════════
        
        // 1. Resistencia horizontal: los 3 máximos deben estar al mismo nivel (±1.5%)
        const maxPrecios = ultimosHighs.map(h => h.precio);
        const avgHigh = maxPrecios.reduce((sum, p) => sum + p, 0) / maxPrecios.length;
        const desviacionHighs = maxPrecios.map(p => Math.abs(p - avgHigh) / avgHigh);
        const resistenciaHorizontal = desviacionHighs.every(d => d < 0.015);
        
        // 2. Soporte ascendente: cada mínimo más alto que el anterior
        const soporteAscendente = (
            ultimosLows.length >= 3 &&
            ultimosLows[1].precio > ultimosLows[0].precio &&
            ultimosLows[2].precio > ultimosLows[1].precio
        );
        
        // 3. Compresión: el rango se está estrechando
        const rangoInicial = ultimosHighs[0].precio - ultimosLows[0].precio;
        const rangoFinal = ultimosHighs[ultimosHighs.length-1].precio - ultimosLows[ultimosLows.length-1].precio;
        const hayCompresion = rangoFinal < rangoInicial * 0.7;  // Rango final <70% del inicial
        
        if (resistenciaHorizontal && soporteAscendente && hayCompresion) {
            return {
                tipo: 'triangulo_ascendente',
                señal: 'alcista',
                resistencia: avgHigh,
                inicio: Math.min(ultimosHighs[0].idx, ultimosLows[0].idx),
                fin: Math.max(ultimosHighs[ultimosHighs.length-1].idx, ultimosLows[ultimosLows.length-1].idx)
            };
        }
        
        // ══════════════════════════════════════════════════════════
        // TRIÁNGULO DESCENDENTE: soporte horizontal + resistencia descendente
        // ══════════════════════════════════════════════════════════
        
        // 1. Soporte horizontal: los 3 mínimos deben estar al mismo nivel (±1.5%)
        const minPrecios = ultimosLows.map(l => l.precio);
        const avgLow = minPrecios.reduce((sum, p) => sum + p, 0) / minPrecios.length;
        const desviacionLows = minPrecios.map(p => Math.abs(p - avgLow) / avgLow);
        const soporteHorizontal = desviacionLows.every(d => d < 0.015);
        
        // 2. Resistencia descendente: cada máximo más bajo que el anterior
        const resistenciaDescendente = (
            ultimosHighs.length >= 3 &&
            ultimosHighs[1].precio < ultimosHighs[0].precio &&
            ultimosHighs[2].precio < ultimosHighs[1].precio
        );
        
        // 3. Compresión: el rango se está estrechando
        const hayCompresion2 = rangoFinal < rangoInicial * 0.7;
        
        if (soporteHorizontal && resistenciaDescendente && hayCompresion2) {
            return {
                tipo: 'triangulo_descendente',
                señal: 'bajista',
                soporte: avgLow,
                inicio: Math.min(ultimosHighs[0].idx, ultimosLows[0].idx),
                fin: Math.max(ultimosHighs[ultimosHighs.length-1].idx, ultimosLows[ultimosLows.length-1].idx)
            };
        }
        
        return null;
    }
    
    detectarBanderas(high, low, close, desde) {
        // DESACTIVADO TEMPORALMENTE
        // Las banderas son muy difíciles de detectar automáticamente de forma fiable
        // Requieren análisis visual humano para confirmar el patrón
        // 
        // Problemas con detección automática:
        // - Falsos positivos frecuentes
        // - Difícil distinguir bandera de consolidación normal
        // - Patrón muy subjetivo (forma rectangular no siempre clara)
        //
        // TODO: Implementar detección manual con clicks del usuario
        
        return null;
    }
    
    encontrarMinimoEntre(lows, idx1, idx2) {
        let minimo = null;
        for (const low of lows) {
            if (low.idx > idx1 && low.idx < idx2) {
                if (!minimo || low.precio < minimo.precio) {
                    minimo = low;
                }
            }
        }
        return minimo;
    }
    
    encontrarMaximoEntre(highs, idx1, idx2) {
        let maximo = null;
        for (const high of highs) {
            if (high.idx > idx1 && high.idx < idx2) {
                if (!maximo || high.precio > maximo.precio) {
                    maximo = high;
                }
            }
        }
        return maximo;
    }
    
    
    /* ═══ CREAR GRÁFICO ═══ */
    crearGrafico() {
        // ✅ RECORTAR DATOS A ÚLTIMAS 260 SESIONES (aprox 1 año)
        // Mantener los 2 años descargados solo para cálculo de MM200, pero visualizar solo 1 año
        const numSesionesVisibles = 260;
        const totalSesiones = this.data.dates.length;
        
// ELIMINADO:         if (totalSesiones > numSesionesVisibles) {
// ELIMINADO:             const inicio = totalSesiones - numSesionesVisibles;
// ELIMINADO:             console.log(`📊 Recortando datos: ${totalSesiones} → ${numSesionesVisibles} sesiones (desde índice ${inicio})`);
// ELIMINADO:             
// ELIMINADO:             // Recortar todos los arrays de datos
// ELIMINADO:             this.data = {
// ELIMINADO:                 dates: this.data.dates.slice(inicio),
// ELIMINADO:                 open: this.data.open.slice(inicio),
// ELIMINADO:                 high: this.data.high.slice(inicio),
// ELIMINADO:                 low: this.data.low.slice(inicio),
// ELIMINADO:                 close: this.data.close.slice(inicio),
// ELIMINADO:                 volume: this.data.volume.slice(inicio),
// ELIMINADO:                 // Medias móviles ya calculadas con todos los datos
// ELIMINADO:                 mm20: this.data.mm20 ? this.data.mm20.slice(inicio) : null,
// ELIMINADO:                 mm50: this.data.mm50 ? this.data.mm50.slice(inicio) : null,
// ELIMINADO:                 mm200: this.data.mm200 ? this.data.mm200.slice(inicio) : null
// ELIMINADO:             };
// ELIMINADO:         }
        
        // ✅ VALIDACIÓN CRÍTICA: Escala logarítmica requiere valores > 0
        if (this.yAxisType === 'log' && this.data) {
            const minValido = 0.01;
            let datosCorregidos = 0;
            
            ['open', 'high', 'low', 'close'].forEach(campo => {
                if (this.data[campo]) {
                    this.data[campo] = this.data[campo].map(val => {
                        if (val <= 0 || !isFinite(val)) {
                            datosCorregidos++;
                            return minValido;
                        }
                        return val;
                    });
                }
            });
            
            if (datosCorregidos > 0) {
                console.warn(`⚠️ ${datosCorregidos} valores corregidos para escala log`);
            }
        }
        
        const traces = [];
        
        // Trace principal (velas o línea)
        if (this.chartType === 'candlestick') {
            traces.push({
                type: 'candlestick',
                x: this.data.dates,
                open: this.data.open,
                high: this.data.high,
                low: this.data.low,
                close: this.data.close,
                name: this.ticker,
                increasing: { line: { color: '#10b981' } },
                decreasing: { line: { color: '#ef4444' } },
                xaxis: 'x',
                yaxis: 'y',
                hoverinfo: 'x',  // ✅ Permitir hover pero solo en X
                hovertemplate: '<extra></extra>'  // ✅ Tooltip vacío (solo dispara evento)
            });
        } else {
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: this.data.close,
                name: this.ticker,
                line: { color: '#2a5298', width: 2 },
                xaxis: 'x',
                yaxis: 'y',
                hoverinfo: 'x',
                hovertemplate: '<extra></extra>'
            });
        }
        
        // Volumen
        // ═══ VOLUMEN (con detección de outliers) ═══
        // Los outliers (volumen > 3x media) están cappeados a 2.5x
        // y se marcan en rojo intenso para distinguirlos
        let volColors;
        
        if (this.data.volume_colors && this.data.volume_colors.length > 0) {
            // Usar colores del backend (marcan outliers en rojo)
            volColors = this.data.volume_colors;
        } else {
            // Fallback: colores tradicionales verde/rojo
            volColors = this.data.close.map((close, i) => {
                if (i === 0) return 'rgba(100, 181, 246, 0.6)';
                return close >= this.data.close[i-1] 
                    ? 'rgba(16, 185, 129, 0.6)'   // verde
                    : 'rgba(239, 68, 68, 0.6)';   // rojo
            });
        }
        
        traces.push({
            type: 'bar',
            x: this.data.dates,
            y: this.data.volume,
            name: 'Volumen',
            marker: { color: volColors },
            xaxis: 'x',
            yaxis: 'y2',
            hovertemplate: 'Vol: %{y:,.0f}<extra></extra>'
        });
        
        // ═══ VWAP (Volume Weighted Average Price) ═══
        if (this.indicadoresActivos.has('VWAP')) {
            const volumeReal = this.data.volume_real || this.data.volume;
            const vwap = this.calcularVWAP(this.data.high, this.data.low, this.data.close, volumeReal);
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: vwap,
                name: 'VWAP',
                line: { color: '#f59e0b', width: 2, dash: 'dot' },
                xaxis: 'x',
                yaxis: 'y',  // Mismo eje que precio
                hovertemplate: 'VWAP: %{y:.2f}<extra></extra>'
            });
        }

        // ═══ FIBONACCI ═══
        if (this.indicadoresActivos.has('FIBO') && this.data.fibonacci) {
            const fib = this.data.fibonacci;
            const niveles = fib.niveles;
            
            // Colores para cada nivel
            const coloresFibo = {
                '0.0': '#ef4444',
                '23.6': '#f59e0b',
                '38.2': '#10b981',
                '50.0': '#3b82f6',
                '61.8': '#8b5cf6',
                '78.6': '#ec4899',
                '100.0': '#ef4444'
            };
            
            // Dibujar cada nivel
            Object.entries(niveles).forEach(([nivel, precio]) => {
                traces.push({
                    type: 'scatter',
                    mode: 'lines',
                    x: this.data.dates,
                    y: Array(this.data.dates.length).fill(precio),
                    name: `Fib ${nivel}%`,
                    line: { color: coloresFibo[nivel], width: 1, dash: 'dot' },
                    xaxis: 'x',
                    yaxis: 'y',
                    hovertemplate: `Fibonacci ${nivel}%: ${precio.toFixed(2)}<extra></extra>`
                });
            });
        }
        
        // ═══ PIVOT POINTS ═══
        if (this.indicadoresActivos.has('PIVOT') && this.data.pivots) {
            // Por defecto usar pivots diarios (luego añadiremos selector)
            const pivots = this.data.pivots[this.pivotTipo];
            
            if (pivots) {
                // Pivot Point central
                traces.push({
                    type: 'scatter',
                    mode: 'lines',
                    x: this.data.dates,
                    y: Array(this.data.dates.length).fill(pivots.PP),
                    name: 'PP',
                    line: { color: '#6366f1', width: 2, dash: 'solid' },
                    xaxis: 'x',
                    yaxis: 'y',
                    hovertemplate: `PP: ${pivots.PP}<extra></extra>`
                });
                
                // Resistencias
                ['R1', 'R2', 'R3'].forEach((nivel, idx) => {
                    traces.push({
                        type: 'scatter',
                        mode: 'lines',
                        x: this.data.dates,
                        y: Array(this.data.dates.length).fill(pivots[nivel]),
                        name: nivel,
                        line: { color: '#ef4444', width: 1, dash: 'dash' },
                        xaxis: 'x',
                        yaxis: 'y',
                        hovertemplate: `${nivel}: ${pivots[nivel]}<extra></extra>`
                    });
                });
                
                // Soportes
                ['S1', 'S2', 'S3'].forEach((nivel, idx) => {
                    traces.push({
                        type: 'scatter',
                        mode: 'lines',
                        x: this.data.dates,
                        y: Array(this.data.dates.length).fill(pivots[nivel]),
                        name: nivel,
                        line: { color: '#10b981', width: 1, dash: 'dash' },
                        xaxis: 'x',
                        yaxis: 'y',
                        hovertemplate: `${nivel}: ${pivots[nivel]}<extra></extra>`
                    });
                });
            }
        }
        
        
        // ═══ MEDIAS MÓVILES ═══
        if (this.indicadoresActivos.has('MM')) {
            // MM20
            const mm20 = this.calcularMM(this.data.close, 20);
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: mm20,
                name: 'MM20',
                line: { color: '#3b82f6', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'MM20: %{y:.2f}<extra></extra>'
            });
            
            // MM50
            const mm50 = this.calcularMM(this.data.close, 50);
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: mm50,
                name: 'MM50',
                line: { color: '#f59e0b', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'MM50: %{y:.2f}<extra></extra>'
            });
            
            // MM200
            const mm200 = this.calcularMM(this.data.close, 200);
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: mm200,
                name: 'MM200',
                line: { color: '#ef4444', width: 2 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'MM200: %{y:.2f}<extra></extra>'
            });
        }
        
        // ═══ BOLLINGER BANDS ═══
        if (this.indicadoresActivos.has('BB')) {
            const periodo = 20;
            const desv = 2;
            const mm = this.calcularMM(this.data.close, periodo);
            const std = this.calcularStd(this.data.close, periodo);
            
            const upper = mm.map((m, i) => m ? m + (std[i] * desv) : null);
            const lower = mm.map((m, i) => m ? m - (std[i] * desv) : null);
            
            // Banda superior
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: upper,
                name: 'BB Superior',
                line: { color: '#94a3b8', width: 1, dash: 'dot' },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'BB Superior: %{y:.2f}<extra></extra>'
            });
            
            // Banda media (MM20)
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: mm,
                name: 'BB Media',
                line: { color: '#64748b', width: 1 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'BB Media: %{y:.2f}<extra></extra>'
            });
            
            // Banda inferior
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: lower,
                name: 'BB Inferior',
                line: { color: '#94a3b8', width: 1, dash: 'dot' },
                xaxis: 'x',
                yaxis: 'y',
                fill: 'tonexty',
                fillcolor: 'rgba(148, 163, 184, 0.1)',
                hovertemplate: 'BB Inferior: %{y:.2f}<extra></extra>'
            });
        }
        
        // ═══ SOPORTES Y RESISTENCIAS ═══
        const shapes = [];
        const annotations = [];  // ✅ Para las etiquetas de precio
        
        // Aplicar dibujos del usuario PRIMERO (para que estén debajo de S/R automáticos)
        this.aplicarDibujos(shapes);
        
        if (this.indicadoresActivos.has('SR') && this.soportesResistencias) {
            console.log('🎨 Dibujando S/R:', this.soportesResistencias);
            
            // ✅ FILTRAR S/R FUERA DE RANGO para evitar aplanar el gráfico
            // Calcular rango de precios visible con un margen del 20%
            const preciosVisibles = [...this.data.high, ...this.data.low];
            const minPrecio = Math.min(...preciosVisibles);
            const maxPrecio = Math.max(...preciosVisibles);
            const margen = (maxPrecio - minPrecio) * 0.2; // 20% de margen
            const limiteInferior = minPrecio - margen;
            const limiteSuperior = maxPrecio + margen;
            
            console.log(`📊 Rango precios: ${minPrecio.toFixed(2)} - ${maxPrecio.toFixed(2)} (con margen: ${limiteInferior.toFixed(2)} - ${limiteSuperior.toFixed(2)})`);
            
            // Soportes (verdes) - TODAS discontinuas
            if (this.soportesResistencias.soportes) {
                const soportesFiltrados = this.soportesResistencias.soportes.filter(s => 
                    s.precio >= limiteInferior && s.precio <= limiteSuperior
                );
                console.log(`  📗 Soportes: ${this.soportesResistencias.soportes.length} totales → ${soportesFiltrados.length} en rango`);
                
                soportesFiltrados.forEach((s, idx) => {
                    shapes.push({
                        type: 'line',
                        xref: 'paper',
                        x0: 0,
                        x1: 1,
                        yref: 'y',
                        y0: s.precio,
                        y1: s.precio,
                        line: {
                            color: '#10b981',
                            width: s.fuerza === 'FUERTE' ? 2 : 1,
                            dash: 'dash'  // ← SIEMPRE discontinua
                        }
                    });
                    
                    // ✅ Añadir etiqueta con precio
                    annotations.push({
                        xref: 'paper',
                        yref: 'y',
                        x: 0.02,  // 2% desde la izquierda
                        y: s.precio,
                        xanchor: 'left',
                        yanchor: 'middle',
                        text: `${s.precio.toFixed(2)} €`,
                        showarrow: false,
                        font: {
                            size: 10,
                            color: '#10b981',
                            family: 'monospace'
                        },
                        bgcolor: 'rgba(255, 255, 255, 0.9)',
                        bordercolor: '#10b981',
                        borderwidth: 1,
                        borderpad: 3
                    });
                });
            }
            
            // Resistencias (rojas) - TODAS discontinuas
            if (this.soportesResistencias.resistencias) {
                const resistenciasFiltradas = this.soportesResistencias.resistencias.filter(r => 
                    r.precio >= limiteInferior && r.precio <= limiteSuperior
                );
                console.log(`  📕 Resistencias: ${this.soportesResistencias.resistencias.length} totales → ${resistenciasFiltradas.length} en rango`);
                
                resistenciasFiltradas.forEach((r, idx) => {
                    shapes.push({
                        type: 'line',
                        xref: 'paper',
                        x0: 0,
                        x1: 1,
                        yref: 'y',
                        y0: r.precio,
                        y1: r.precio,
                        line: {
                            color: '#ef4444',
                            width: r.fuerza === 'FUERTE' ? 2 : 1,
                            dash: 'dash'  // ← SIEMPRE discontinua
                        }
                    });
                    
                    // ✅ Añadir etiqueta con precio
                    annotations.push({
                        xref: 'paper',
                        yref: 'y',
                        x: 0.02,  // 2% desde la izquierda
                        y: r.precio,
                        xanchor: 'left',
                        yanchor: 'middle',
                        text: `${r.precio.toFixed(2)} €`,
                        showarrow: false,
                        font: {
                            size: 10,
                            color: '#ef4444',
                            family: 'monospace'
                        },
                        bgcolor: 'rgba(255, 255, 255, 0.9)',
                        bordercolor: '#ef4444',
                        borderwidth: 1,
                        borderpad: 3
                    });
                });
            }
            
            console.log('✅ Total shapes S/R:', shapes.length);
        } else if (this.indicadoresActivos.has('SR')) {
            console.warn('⚠️ S/R activado pero no hay datos:', this.soportesResistencias);
        }
        
        // ═══ ANOTACIONES FIBONACCI (LADO IZQUIERDO) ═══
        if (this.indicadoresActivos.has('FIBO') && this.data.fibonacci) {
            // Labels de Fibonacci desactivados (causaban problemas de posicionamiento)
            // Los niveles ya son visibles en las líneas horizontales
        }
        
        // ═══ ANOTACIONES PIVOT POINTS ═══
        if (this.indicadoresActivos.has('PIVOT') && this.data.pivots) {
            // Labels de Pivot Points desactivados (causaban problemas de posicionamiento)
            // Los niveles ya son visibles en las líneas horizontales
        }
        
        // Layout
        // Calcular domains dinámicamente según indicadores activos
        let numPaneles = 1;  // Principal siempre
        let tieneRSI = this.indicadoresActivos.has('RSI');
        let tieneMACD = this.indicadoresActivos.has('MACD');
        let tieneADX = this.indicadoresActivos.has('ADX');
        let tieneSTOCH = this.indicadoresActivos.has('STOCH');
        
        if (tieneRSI) numPaneles++;
        if (tieneMACD) numPaneles++;
        if (tieneADX) numPaneles++;
        if (tieneSTOCH) numPaneles++;
        
        // Distribuir espacio vertical dinámicamente
        let altoPrincipal = 0.70;
        let altoVolumen = 0.15;
        let altoIndicador = 0.15;
        
        if (numPaneles === 2) {
            altoPrincipal = 0.60;
            altoVolumen = 0.15;
            altoIndicador = 0.20;
        } else if (numPaneles === 3) {
            altoPrincipal = 0.50;
            altoVolumen = 0.15;
            altoIndicador = 0.15;
        } else if (numPaneles >= 4) {
            altoPrincipal = 0.40;
            altoVolumen = 0.12;
            altoIndicador = 0.12;
        }
        
        let yInicio = 0;
        let domainVolumen = [yInicio, yInicio + altoVolumen];
        yInicio += altoVolumen + 0.02;
        
        let domainRSI, domainMACD, domainADX, domainSTOCH;
        if (tieneRSI) {
            domainRSI = [yInicio, yInicio + altoIndicador];
            yInicio += altoIndicador + 0.02;
        }
        if (tieneMACD) {
            domainMACD = [yInicio, yInicio + altoIndicador];
            yInicio += altoIndicador + 0.02;
        }
        if (tieneADX) {
            domainADX = [yInicio, yInicio + altoIndicador];
            yInicio += altoIndicador + 0.02;
        }
        if (tieneSTOCH) {
            domainSTOCH = [yInicio, yInicio + altoIndicador];
            yInicio += altoIndicador + 0.02;
        }
        
        let domainPrincipal = [yInicio, 1];
        
        this.layout = {
            title: {
                text: `${this.ticker.replace('.MC', '')} - ${this.getNombreTimeframe()}`,
                font: { size: 20, color: '#2c3e50', family: 'Arial, sans-serif' }
            },
            paper_bgcolor: '#ffffff',
            plot_bgcolor: '#fafafa',
            font: { family: 'Arial, sans-serif', size: 12, color: '#2c3e50' },
            margin: { l: 60, r: 40, t: 60, b: 40 },
            hovermode: 'closest',  // Cambiar de 'x unified' a 'closest'
            dragmode: 'zoom',  // ✅ Zoom de caja por defecto; botón derecho para pan
            showlegend: false,
            
            xaxis: {
                type: 'category',
                gridcolor: '#e5e7eb',
                showgrid: true,
                rangeslider: { visible: false },
                fixedrange: false,
                tickmode: 'auto',
                nticks: 10,  // Máximo 10 etiquetas en eje X
                tickangle: -45,
                tickfont: { size: 9 }
            },
            
            yaxis: {
                title: '',  // Sin título
                type: this.yAxisType,     // ✅ 'linear' o 'log'
                gridcolor: '#e5e7eb',
                showgrid: false,          // ✅ NO líneas horizontales completas
                nticks: 20,               // ✅ ~20 niveles de precio
                tickformat: '.2f',        // ✅ 2 decimales (ej: 4.50)
                side: 'right',            // ✅ Etiquetas en lado DERECHO
                ticks: 'outside',         // ✅ Marcas fuera del gráfico
                ticklen: 5,               // ✅ Longitud de las marcas (5px)
                tickwidth: 1,             // ✅ Grosor de las marcas
                tickcolor: '#9ca3af',     // ✅ Color gris de las marcas
                domain: domainPrincipal,
                fixedrange: false
                // ✅ Dejar que Plotly maneje autorange por defecto
            },
            
            yaxis2: {
                title: 'Volumen',
                gridcolor: '#e5e7eb',
                showgrid: false,
                domain: domainVolumen,
                fixedrange: false,
                side: 'left'
            },
            
            yaxis3: {
                title: 'OBV',
                gridcolor: '#e5e7eb',
                showgrid: false,
                domain: domainVolumen,  // Mismo dominio que volumen
                fixedrange: false,
                side: 'right',
                overlaying: 'y2'  // Superpuesto a y2
            },
            
            shapes: shapes,          // ✅ Líneas S/R
            annotations: annotations  // ✅ Etiquetas con precios
        };
        
        // ═══ AÑADIR EJES PARA RSI Y MACD ═══
        if (tieneRSI) {
            this.layout.yaxis4 = {
                title: 'RSI',
                gridcolor: '#e5e7eb',
                showgrid: true,
                domain: domainRSI,
                range: [0, 100],
                fixedrange: false
            };
        }
        
        if (tieneMACD) {
            const yaxisKey = tieneRSI ? 'yaxis5' : 'yaxis4';
            this.layout[yaxisKey] = {
                title: 'MACD',
                gridcolor: '#e5e7eb',
                showgrid: true,
                domain: domainMACD,
                fixedrange: false
            };
        }
        
        if (tieneADX) {
            let yaxisKey = 'yaxis4';
            if (tieneRSI) yaxisKey = 'yaxis5';
            if (tieneRSI && tieneMACD) yaxisKey = 'yaxis6';
            
            this.layout[yaxisKey] = {
                title: 'ADX',
                gridcolor: '#e5e7eb',
                showgrid: true,
                domain: domainADX,
                range: [0, 100],
                fixedrange: false
            };
        }
        
        if (tieneSTOCH) {
            let yaxisKey = 'yaxis4';
            if (tieneRSI) yaxisKey = 'yaxis5';
            if (tieneRSI && tieneMACD) yaxisKey = 'yaxis6';
            if (tieneRSI && tieneMACD && tieneADX) yaxisKey = 'yaxis7';
            
            this.layout[yaxisKey] = {
                title: 'Stochastic',
                gridcolor: '#e5e7eb',
                showgrid: true,
                domain: domainSTOCH,
                range: [0, 100],
                fixedrange: false
            };
        }
        
        // ═══ RSI ═══
        if (this.indicadoresActivos.has('RSI') && this.indicadores && this.indicadores.rsi) {
            console.log('🎨 Dibujando RSI, datos:', this.indicadores.rsi.length, 'puntos');
            
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.indicadores.dates,
                y: this.indicadores.rsi,
                name: 'RSI',
                line: { color: '#8b5cf6', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y4',  // Actualizado de y3 a y4
                hovertemplate: 'RSI: %{y:.1f}<extra></extra>'
            });
            
            // Líneas de referencia 30 y 70
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.indicadores.dates,
                y: Array(this.indicadores.dates.length).fill(70),
                name: 'Sobrecompra',
                line: { color: '#ef4444', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: 'y4',  // Actualizado
                showlegend: false,
                hoverinfo: 'skip'
            });
            
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.indicadores.dates,
                y: Array(this.indicadores.dates.length).fill(30),
                name: 'Sobreventa',
                line: { color: '#10b981', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: 'y4',  // Actualizado
                showlegend: false,
                hoverinfo: 'skip'
            });
        }
        
        // ═══ DIVERGENCIAS RSI ═══
        if (this.indicadoresActivos.has('DIVERG') && 
            this.indicadoresActivos.has('RSI') && 
            this.indicadores && this.indicadores.rsi) {
            
            const divergencias = this.detectarDivergencias(this.data.close, this.indicadores.rsi, 5);
            
            divergencias.forEach(div => {
                const color = div.tipo === 'alcista' ? '#10b981' : '#ef4444';
                const dashStyle = div.tipo === 'alcista' ? 'solid' : 'dot';
                
                // Línea en el gráfico de precio
                shapes.push({
                    type: 'line',
                    x0: this.data.dates[div.inicio],
                    y0: div.precio1,
                    x1: this.data.dates[div.fin],
                    y1: div.precio2,
                    line: { color: color, width: 2, dash: dashStyle },
                    xref: 'x',
                    yref: 'y'
                });
                
                // Línea en el panel RSI
                shapes.push({
                    type: 'line',
                    x0: this.data.dates[div.inicio],
                    y0: div.ind1,
                    x1: this.data.dates[div.fin],
                    y1: div.ind2,
                    line: { color: color, width: 2, dash: dashStyle },
                    xref: 'x',
                    yref: 'y4'
                });
                
                // Etiqueta
                annotations.push({
                    x: this.data.dates[div.fin],
                    y: div.precio2,
                    text: div.tipo === 'alcista' ? '⬆ DIV' : '⬇ DIV',
                    showarrow: true,
                    arrowhead: 2,
                    arrowcolor: color,
                    ax: 0,
                    ay: div.tipo === 'alcista' ? -30 : 30,
                    font: { size: 10, color: color },
                    xref: 'x',
                    yref: 'y'
                });
            });
        }
        
        // ═══ MACD ═══
        if (this.indicadoresActivos.has('MACD') && this.indicadores && this.indicadores.macd) {
            console.log('🎨 Dibujando MACD, datos:', this.indicadores.macd.macd.length, 'puntos');
            
            const yaxisKey = this.indicadoresActivos.has('RSI') ? 'y5' : 'y4';  // Actualizado
            
            // MACD Line
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.indicadores.dates,
                y: this.indicadores.macd.macd,
                name: 'MACD',
                line: { color: '#3b82f6', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisKey,
                hovertemplate: 'MACD: %{y:.3f}<extra></extra>'
            });
            
            // Signal Line
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.indicadores.dates,
                y: this.indicadores.macd.signal,
                name: 'Signal',
                line: { color: '#f59e0b', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisKey,
                hovertemplate: 'Signal: %{y:.3f}<extra></extra>'
            });
            
            // Histogram
            const histColors = this.indicadores.macd.histogram.map(h => h >= 0 ? '#10b981' : '#ef4444');
            traces.push({
                type: 'bar',
                x: this.indicadores.dates,
                y: this.indicadores.macd.histogram,
                name: 'Histogram',
                marker: { color: histColors, opacity: 0.5 },
                xaxis: 'x',
                yaxis: yaxisKey,
                hovertemplate: 'Hist: %{y:.3f}<extra></extra>'
            });
        }
        
        // ═══ ADX ═══
        if (this.indicadoresActivos.has('ADX')) {
            const adxData = this.calcularADX(this.data.high, this.data.low, this.data.close, 14);
            
            // Determinar eje Y
            let yaxisADX = 'y4';
            if (tieneRSI) yaxisADX = 'y5';
            if (tieneRSI && tieneMACD) yaxisADX = 'y6';
            
            // ADX Line (solo la línea morada)
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: adxData.adx,
                name: 'ADX',
                line: { color: '#8b5cf6', width: 2 },
                xaxis: 'x',
                yaxis: yaxisADX,
                hovertemplate: 'ADX: %{y:.1f}<extra></extra>'
            });
            
            // Línea 25 (nivel de fuerza)
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: Array(this.data.dates.length).fill(25),
                line: { color: '#94a3b8', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: yaxisADX,
                showlegend: false,
                hoverinfo: 'skip'
            });
        }
        
        // ═══ STOCHASTIC ═══
        if (this.indicadoresActivos.has('STOCH')) {
            const stoch = this.calcularStochastic(this.data.high, this.data.low, this.data.close, 14);
            
            // Determinar eje Y (depende de cuántos indicadores hay antes)
            let yaxisStoch = 'y4';
            if (tieneRSI) yaxisStoch = 'y5';
            if (tieneRSI && tieneMACD) yaxisStoch = 'y6';
            if (tieneRSI && tieneMACD && tieneADX) yaxisStoch = 'y7';
            
            // %K Line
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: stoch.k,
                name: '%K',
                line: { color: '#3b82f6', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisStoch,
                hovertemplate: '%K: %{y:.1f}<extra></extra>'
            });
            
            // %D Line
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: stoch.d,
                name: '%D',
                line: { color: '#f59e0b', width: 1.5 },
                xaxis: 'x',
                yaxis: yaxisStoch,
                hovertemplate: '%D: %{y:.1f}<extra></extra>'
            });
            
            // Líneas 80 y 20
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: Array(this.data.dates.length).fill(80),
                line: { color: '#ef4444', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: yaxisStoch,
                showlegend: false,
                hoverinfo: 'skip'
            });
            
            traces.push({
                type: 'scatter',
                mode: 'lines',
                x: this.data.dates,
                y: Array(this.data.dates.length).fill(20),
                line: { color: '#10b981', width: 1, dash: 'dash' },
                xaxis: 'x',
                yaxis: yaxisStoch,
                showlegend: false,
                hoverinfo: 'skip'
            });
        }
        
        // ═══ PATRONES DE VELAS ═══
        if (this.indicadoresActivos.has('VELAS')) {
            const patrones = this.detectarPatronesVelas();
            
            patrones.forEach(patron => {
                const idx = patron.idx;
                const precio = this.data.high[idx];
                
                // Validación para escala logarítmica
                if (this.yAxisType === 'log' && precio <= 0) {
                    console.warn('⚠️ Patrón ignorado en escala log (precio <= 0):', patron);
                    return;
                }
                
                let simbolo = '';
                let color = '#64748b';
                
                switch(patron.tipo) {
                    case 'martillo':
                        simbolo = '🔨';
                        color = '#10b981';
                        break;
                    case 'shooting_star':
                        simbolo = '⭐';
                        color = '#ef4444';
                        break;
                    case 'envolvente_alcista':
                        simbolo = '🟢';
                        color = '#10b981';
                        break;
                    case 'envolvente_bajista':
                        simbolo = '🔴';
                        color = '#ef4444';
                        break;
                    case 'estrella_mañana':
                        simbolo = '🌅';
                        color = '#10b981';
                        break;
                    case 'estrella_tarde':
                        simbolo = '🌆';
                        color = '#ef4444';
                        break;
                    case 'tres_soldados':
                        simbolo = '⬆⬆⬆';
                        color = '#10b981';
                        break;
                    case 'tres_cuervos':
                        simbolo = '⬇⬇⬇';
                        color = '#ef4444';
                        break;
                    case 'doji':
                        simbolo = '✖';
                        color = '#f59e0b';
                        break;
                    case 'momentum':
                        simbolo = patron.señal === 'alcista' ? '⬆' : '⬇';
                        color = patron.señal === 'alcista' ? '#10b981' : '#ef4444';
                        break;
                }
                
                annotations.push({
                    x: this.data.dates[idx],
                    y: precio,
                    text: simbolo,
                    showarrow: false,
                    font: { size: 16, color: color },
                    xref: 'x',
                    yref: 'y',
                    yshift: 10
                });
            });
        }
        
        // ═══ PATRONES CHARTISTAS ═══
        if (this.indicadoresActivos.has('CHARTISTAS')) {
            const patronesChart = this.detectarPatronesChartistas();
            
            patronesChart.forEach(patron => {
                const color = patron.señal === 'alcista' ? '#10b981' : '#ef4444';
                
                switch(patron.tipo) {
                    case 'hch':
                    case 'hch_invertido':
                        // Dibujar líneas conectando TODOS los puntos (HI -> Cabeza -> HD)
                        const [hi, cabeza, hd] = patron.puntos;
                        
                        // Línea HI -> Cabeza
                        shapes.push({
                            type: 'line',
                            x0: this.data.dates[hi.idx],
                            y0: hi.precio,
                            x1: this.data.dates[cabeza.idx],
                            y1: cabeza.precio,
                            line: { color: color, width: 2, dash: 'solid' }
                        });
                        
                        // Línea Cabeza -> HD
                        shapes.push({
                            type: 'line',
                            x0: this.data.dates[cabeza.idx],
                            y0: cabeza.precio,
                            x1: this.data.dates[hd.idx],
                            y1: hd.precio,
                            line: { color: color, width: 2, dash: 'solid' }
                        });
                        
                        // Línea de cuello (neckline)
                        shapes.push({
                            type: 'line',
                            x0: this.data.dates[patron.inicio],
                            y0: patron.cuello,
                            x1: this.data.dates[patron.fin],
                            y1: patron.cuello,
                            line: { color: color, width: 2, dash: 'dash' }
                        });
                        
                        // Label del patrón CON NECKLINE (en la cabeza)
                        annotations.push({
                            x: this.data.dates[cabeza.idx],
                            y: cabeza.precio,
                            text: patron.tipo === 'hch' ? 
                                `HCH 👤 (${patron.cuello.toFixed(2)}€)` : 
                                `HCH-i 👤 (${patron.cuello.toFixed(2)}€)`,
                            showarrow: true,
                            arrowhead: 2,
                            arrowcolor: color,
                            font: { size: 11, color: color, weight: 'bold' },
                            bgcolor: 'rgba(255,255,255,0.9)',
                            bordercolor: color,
                            borderwidth: 1,
                            yshift: patron.tipo === 'hch' ? 15 : -15
                        });
                        
                        break;
                        
                    case 'doble_techo':
                    case 'doble_suelo':
                        // Precio del nivel (promedio de ambos puntos)
                        const precio = (patron.puntos[0].precio + patron.puntos[1].precio) / 2;
                        
                        // Línea horizontal conectando los dos puntos
                        shapes.push({
                            type: 'line',
                            x0: this.data.dates[patron.puntos[0].idx],
                            y0: precio,
                            x1: this.data.dates[patron.puntos[1].idx],
                            y1: precio,
                            line: { color: color, width: 2, dash: 'dot' }
                        });
                        
                        // Círculos en cada punto del doble
                        patron.puntos.forEach(punto => {
                            shapes.push({
                                type: 'circle',
                                x0: this.data.dates[punto.idx],
                                y0: punto.precio - 0.3,
                                x1: this.data.dates[punto.idx],
                                y1: punto.precio + 0.3,
                                line: { color: color, width: 2 },
                                fillcolor: 'transparent'
                            });
                        });
                        
                        // Label del patrón CON PRECIO (centro)
                        const centroDobleTecho = Math.floor((patron.puntos[0].idx + patron.puntos[1].idx) / 2);
                        annotations.push({
                            x: this.data.dates[centroDobleTecho],
                            y: precio,
                            text: patron.tipo === 'doble_techo' ? 
                                `Doble Techo ⚠️ ${precio.toFixed(2)}€` : 
                                `Doble Suelo ⚠️ ${precio.toFixed(2)}€`,
                            showarrow: true,
                            arrowhead: 2,
                            arrowcolor: color,
                            font: { size: 11, color: color, weight: 'bold' },
                            bgcolor: 'rgba(255,255,255,0.9)',
                            bordercolor: color,
                            borderwidth: 1,
                            yshift: patron.tipo === 'doble_techo' ? 15 : -15
                        });
                        
                        break;
                        
                    case 'triangulo_ascendente':
                        // Resistencia horizontal
                        shapes.push({
                            type: 'line',
                            x0: this.data.dates[patron.inicio],
                            y0: patron.resistencia,
                            x1: this.data.dates[patron.fin],
                            y1: patron.resistencia,
                            line: { color: '#ef4444', width: 2, dash: 'solid' }
                        });
                        
                        annotations.push({
                            x: this.data.dates[patron.fin],
                            y: patron.resistencia,
                            text: 'Triángulo Ascendente 📈',
                            showarrow: false,
                            font: { size: 10, color: '#10b981' },
                            bgcolor: 'rgba(255,255,255,0.9)',
                            bordercolor: '#10b981',
                            borderwidth: 1
                        });
                        break;
                        
                    case 'triangulo_descendente':
                        // Soporte horizontal
                        shapes.push({
                            type: 'line',
                            x0: this.data.dates[patron.inicio],
                            y0: patron.soporte,
                            x1: this.data.dates[patron.fin],
                            y1: patron.soporte,
                            line: { color: '#10b981', width: 2, dash: 'solid' }
                        });
                        
                        annotations.push({
                            x: this.data.dates[patron.fin],
                            y: patron.soporte,
                            text: 'Triángulo Descendente 📉',
                            showarrow: false,
                            font: { size: 10, color: '#ef4444' },
                            bgcolor: 'rgba(255,255,255,0.9)',
                            bordercolor: '#ef4444',
                            borderwidth: 1
                        });
                        break;
                        
                    case 'bandera_alcista':
                    case 'bandera_bajista':
                        // Rectángulo para la bandera
                        shapes.push({
                            type: 'rect',
                            x0: this.data.dates[patron.bandera.inicio],
                            y0: Math.min(this.data.high[patron.bandera.inicio], this.data.high[patron.bandera.fin]),
                            x1: this.data.dates[patron.bandera.fin],
                            y1: Math.max(this.data.high[patron.bandera.inicio], this.data.high[patron.bandera.fin]),
                            line: { color: color, width: 2, dash: 'dot' },
                            fillcolor: 'transparent'
                        });
                        
                        annotations.push({
                            x: this.data.dates[patron.bandera.fin],
                            y: this.data.high[patron.bandera.fin],
                            text: patron.tipo === 'bandera_alcista' ? 'Bandera 🚩↗' : 'Bandera 🚩↘',
                            showarrow: true,
                            arrowhead: 2,
                            arrowcolor: color,
                            font: { size: 10, color: color },
                            bgcolor: 'rgba(255,255,255,0.9)',
                            bordercolor: color,
                            borderwidth: 1
                        });
                        break;
                }
            });
        }
        
        
        // Config
        this.config = {
            displayModeBar: true,
            displaylogo: false,
            responsive: true,
            scrollZoom: true,
            modeBarButtonsToAdd: [
                'drawline',
                'drawopenpath',
                'drawclosedpath',
                'drawcircle',
                'drawrect',
                'eraseshape'
            ],
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            toImageButtonOptions: {
                format: 'png',
                filename: `${this.ticker}_grafico`,
                height: 1080,
                width: 1920,
                scale: 1
            },
            edits: {
                shapePosition: true  // ✅ Permite mover y redimensionar shapes
            }
        };
        
        // Debug: Verificar datos antes de renderizar
        console.log('📊 Renderizando gráfico:', {
            traces: traces.length,
            yAxisType: this.yAxisType,
            patrones: this.indicadoresActivos.has('VELAS'),
            annotations: annotations.length
        });
        
        // ✅ Renderizar con protección de errores
        try {
            Plotly.newPlot('grafico-pro', traces, this.layout, this.config);
            
            // Mantener cursor default (flecha)
            const graficoDiv = document.getElementById('grafico-pro');
            graficoDiv.on('plotly_hover', () => {
                graficoDiv.style.cursor = 'default';
            });
            graficoDiv.on('plotly_unhover', () => {
                graficoDiv.style.cursor = 'default';
            });
            
            // Event listener para herramientas de dibujo
            // Remover handler anterior si existe para evitar duplicados
            if (this._capturarClickHandler) {
                graficoDiv.removeEventListener('click', this._capturarClickHandler);
                this._capturarClickHandler = null;
            }

            const capturarClick = (event) => {
                if (!this.herramientaActiva) return;

                // Obtener el layout completo de Plotly
                const fullLayout = graficoDiv._fullLayout;
                if (!fullLayout) {
                    console.error('❌ _fullLayout no disponible');
                    return;
                }

                const xaxis = fullLayout.xaxis;
                const yaxis = fullLayout.yaxis;

                if (!xaxis || !yaxis) {
                    console.error('❌ Axes no definidos');
                    return;
                }

                // Coordenadas relativas al div del gráfico
                const bounds = graficoDiv.getBoundingClientRect();
                const xPixel = event.clientX - bounds.left;
                const yPixel = event.clientY - bounds.top;

                // Restar márgenes del plot para obtener coordenadas relativas AL ÁREA DE DATOS
                const marginL = fullLayout._size.l;
                const marginT = fullLayout._size.t;
                const xRelativo = xPixel - marginL;
                const yRelativo = yPixel - marginT;

                // Ignorar clicks fuera del área de datos
                const plotW = fullLayout._size.w;
                const plotH = fullLayout._size.h;
                if (xRelativo < 0 || xRelativo > plotW || yRelativo < 0 || yRelativo > plotH) return;

                // p2d convierte píxeles-relativos-al-plot a coordenadas de datos
                const xRaw  = xaxis.p2d(xRelativo);
                const yData = yaxis.p2d(yRelativo);

                // Para ejes categóricos, p2d puede devolver:
                // - Un string (la categoría directamente) → usar tal cual
                // - Un número (índice) → convertir a fecha
                let xFecha;
                if (typeof xRaw === 'string') {
                    xFecha = xRaw;
                } else {
                    const idx = Math.max(0, Math.min(this.data.dates.length - 1, Math.round(xRaw)));
                    xFecha = this.data.dates[idx];
                }

                if (!xFecha) {
                    console.error('❌ No se pudo obtener fecha. xRaw:', xRaw, 'tipo:', typeof xRaw);
                    return;
                }

                console.log(`🖱️ Click capturado → fecha: ${xFecha}, precio: ${yData.toFixed(2)}`);

                this.manejarClickDibujo({
                    points: [{ x: xFecha, y: yData }]
                });
            };

            graficoDiv.addEventListener('click', capturarClick);
            this._capturarClickHandler = capturarClick;
            
            // Event listener para capturar ediciones de shapes
            graficoDiv.on('plotly_relayout', (eventData) => {
                // Cuando el usuario edita una shape, Plotly emite plotly_relayout con las nuevas coordenadas
                if (eventData && eventData.shapes) {
                    console.log('📝 Shapes editadas, actualizando localStorage...');
                    this.sincronizarDibujosDesdeGrafico(eventData.shapes);
                }
            });
        } catch (error) {
            console.error('❌ Error renderizando gráfico:', error);
            console.error('Layout:', this.layout);
            console.error('Traces:', traces);
            alert('Error al renderizar el gráfico. Revisa la consola para más detalles.');
        }
    }
    
    /* ═══ HOVER INFO PERSONALIZADO ═══ */
    setupHoverInfo() {
        const graficoDiv = document.getElementById('grafico-pro');
        const tooltip = document.getElementById('custom-tooltip');
        
        console.log('🎯 Configurando hover info...');
        
        graficoDiv.on('plotly_hover', async (eventData) => {
            console.log('🖱️ Hover detectado:', eventData);
            
            const point = eventData.points[0];
            if (!point) {
                console.log('⚠️ No hay punto');
                return;
            }
            
            if (point.data.type === 'bar') {
                console.log('⚠️ Es volumen, ignorar');
                return;
            }
            
            const dateStr = point.x;
            console.log('📅 Fecha:', dateStr);
            
            const pointIndex = this.data.dates.indexOf(dateStr);
            
            if (pointIndex === -1) {
                console.log('⚠️ Fecha no encontrada en datos');
                return;
            }
            
            // ✅ Convertir fecha de dd.mm.yy a YYYY-MM-DD para la API
            const dateForAPI = this.convertirFechaParaAPI(dateStr);
            console.log('📅 Fecha para API:', dateForAPI);
            
            // Obtener info completa de la vela desde la API
            try {
                console.log('🔄 Fetching vela info...');
                const response = await fetch(
                    `${API_BASE}/vela-info/${this.ticker}?date=${dateForAPI}&tf=${this.timeframe}`
                );
                
                if (!response.ok) {
                    console.error('❌ Error HTTP:', response.status);
                    return;
                }
                
                const info = await response.json();
                console.log('✅ Info recibida:', info);
                
                this.mostrarTooltip(info, eventData.event.clientX, eventData.event.clientY);
                
            } catch (error) {
                console.error('❌ Error obteniendo info de vela:', error);
            }
        });
        
        graficoDiv.on('plotly_unhover', () => {
            console.log('👋 Unhover');
            tooltip.style.display = 'none';
        });
    }
    
    mostrarTooltip(info, mouseX, mouseY) {
        console.log('📋 Mostrando tooltip en', mouseX, mouseY);
        const tooltip = document.getElementById('custom-tooltip');
        
        // Rellenar datos
        document.getElementById('tooltip-date').textContent = info.fecha;
        document.getElementById('tooltip-weekday').textContent = this.traducirDia(info.dia_semana);
        document.getElementById('tooltip-open').textContent = info.open.toFixed(2) + ' €';
        document.getElementById('tooltip-high').textContent = info.high.toFixed(2) + ' €';
        document.getElementById('tooltip-low').textContent = info.low.toFixed(2) + ' €';
        document.getElementById('tooltip-close').textContent = info.close.toFixed(2) + ' €';
        
        // Variación con color
        const varElem = document.getElementById('tooltip-var');
        const varSign = info.variacion_pct >= 0 ? '+' : '';
        varElem.textContent = `${varSign}${info.variacion_pct.toFixed(2)}% (${varSign}${info.variacion_abs.toFixed(2)} €)`;
        varElem.className = info.variacion_pct >= 0 ? 'var-positive' : 'var-negative';
        
        // Volumen
        document.getElementById('tooltip-vol').textContent = this.formatearVolumen(info.volume);
        
        // ATR y RSI
        document.getElementById('tooltip-atr').textContent = info.atr ? info.atr.toFixed(2) + ' €' : 'N/A';
        document.getElementById('tooltip-rsi').textContent = info.rsi ? info.rsi.toFixed(1) : 'N/A';
        
        // Posicionar tooltip inteligentemente para evitar que se salga de la pantalla
        tooltip.style.display = 'block';
        
        const tooltipWidth = 280;  // Ancho aproximado del tooltip
        const screenWidth = window.innerWidth;
        
        let tooltipX;
        if (mouseX - tooltipWidth < 0) {
            // Si se sale por la izquierda, ponerlo a la derecha del cursor
            tooltipX = mouseX + 15;
        } else if (mouseX + tooltipWidth > screenWidth) {
            // Si se sale por la derecha, ponerlo a la izquierda
            tooltipX = mouseX - tooltipWidth - 15;
        } else {
            // Suficiente espacio, ponerlo a la izquierda (preferido)
            tooltipX = mouseX - tooltipWidth - 15;
        }
        
        tooltip.style.left = tooltipX + 'px';
        tooltip.style.top = (mouseY - 100) + 'px';
        
        console.log('✅ Tooltip mostrado en X:', tooltipX);
    }
    
    /* ═══ UTILIDADES ═══ */
    convertirFechaParaAPI(fechaDDMMYY) {
        // Convertir dd.mm.yy a YYYY-MM-DD
        // Ejemplo: "24.06.24" -> "2024-06-24"
        const partes = fechaDDMMYY.split('.');
        if (partes.length !== 3) return fechaDDMMYY;  // Fallback
        
        const dia = partes[0].padStart(2, '0');
        const mes = partes[1].padStart(2, '0');
        let año = partes[2];
        
        // Convertir año de 2 dígitos a 4
        if (año.length === 2) {
            const añoActual = new Date().getFullYear();
            const prefijo = Math.floor(añoActual / 100);
            año = prefijo + año;
        }
        
        return `${año}-${mes}-${dia}`;
    }
    
    async actualizarGrafico() {
        if (!this.data) return;
        
        console.log('🔄 Actualizando gráfico con indicadores:', Array.from(this.indicadoresActivos));
        
        // Cargar indicadores si están activos
        if (this.indicadoresActivos.has('RSI') || this.indicadoresActivos.has('MACD')) {
            await this.cargarIndicadores();
        }
        
        // Cargar S/R si está activo
        if (this.indicadoresActivos.has('SR')) {
            await this.cargarSoportesResistencias();
        }
        
        this.crearGrafico();
        this.setupHoverInfo();
    }
    
    actualizarTipoGrafico() {
        if (!this.data) return;
        this.crearGrafico();
        this.setupHoverInfo();
    }
    
    getNombreTimeframe() {
        const nombres = {
            '1d': 'Diario',
            '1wk': 'Semanal',
            '1mo': 'Mensual'
        };
        return nombres[this.timeframe] || 'Diario';
    }
    
    traducirDia(dia) {
        const dias = {
            'Monday': 'Lunes',
            'Tuesday': 'Martes',
            'Wednesday': 'Miércoles',
            'Thursday': 'Jueves',
            'Friday': 'Viernes',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        };
        return dias[dia] || dia;
    }
    
    formatearVolumen(vol) {
        if (vol >= 1000000) {
            return (vol / 1000000).toFixed(2) + 'M';
        } else if (vol >= 1000) {
            return (vol / 1000).toFixed(1) + 'K';
        }
        return vol.toLocaleString();
    }
    
    mostrarLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }
    
    tomarCaptura() {
        Plotly.downloadImage('grafico-pro', {
            format: 'png',
            width: 1920,
            height: 1080,
            filename: `${this.ticker}_${new Date().toISOString().split('T')[0]}`
        });
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    /* ═══════════════════════════════════════════════
       HERRAMIENTAS DE DIBUJO
       ═══════════════════════════════════════════════ */
    
    manejarClickDibujo(data) {
        if (!data.points || data.points.length === 0) return;

        const point = data.points[0];
        const punto = { x: point.x, y: point.y };

        this.puntosTemporal.push(punto);
        console.log(`📌 [${this.herramientaActiva}] Punto ${this.puntosTemporal.length}:`, punto);
        
        switch(this.herramientaActiva) {
            case 'tendencia':
                if (this.puntosTemporal.length === 2) {
                    this.crearLineaTendencia(this.puntosTemporal[0], this.puntosTemporal[1]);
                    this.puntosTemporal = [];
                    this.desactivarHerramienta();
                }
                break;
                
            case 'canal':
                console.log('📐 Modo canal...');
                if (this.puntosTemporal.length === 1) {
                    console.log('⏳ Punto 1 capturado. Click en punto 2 (fin línea base)');
                } else if (this.puntosTemporal.length === 2) {
                    console.log('⏳ Línea base definida. Click en punto 3 (posición paralela)');
                } else if (this.puntosTemporal.length === 3) {
                    console.log('✅ 3 puntos capturados, creando canal');
                    this.crearCanal(
                        this.puntosTemporal[0],
                        this.puntosTemporal[1],
                        this.puntosTemporal[2]
                    );
                    this.puntosTemporal = [];
                    this.desactivarHerramienta();
                }
                break;
                
            case 'horizontal':
                this.crearLineaHorizontal(this.puntosTemporal[0]);
                this.puntosTemporal = [];
                this.desactivarHerramienta();
                break;

            default:
                console.warn('❌ Herramienta no reconocida:', this.herramientaActiva);
        }
    }
    
    crearLineaTendencia(p1, p2) {
        const dibujo = {
            tipo: 'tendencia',
            puntos: [p1, p2],
            color: '#6366f1',
            width: 2
        };

        this.dibujos.push(dibujo);
        this.guardarDibujos();
        this.actualizarDibujosEnGrafico();
        console.log('✅ Línea de tendencia creada:', p1.x, '→', p2.x);
    }
    
    crearCanal(p1, p2, p3) {
        // Calcular índices para la pendiente
        const x1_idx = this.data.dates.indexOf(p1.x);
        const x2_idx = this.data.dates.indexOf(p2.x);
        const x3_idx = this.data.dates.indexOf(p3.x);

        if (x1_idx === -1 || x2_idx === -1 || x3_idx === -1) {
            console.error('❌ Índice de fecha no encontrado en datos');
            return;
        }

        // Pendiente de la línea base (precio por unidad de índice)
        const dx = x2_idx - x1_idx;
        if (dx === 0) return;
        const pendiente = (p2.y - p1.y) / dx;

        // La paralela pasa por p3: calcular su punto inicial
        // Proyectar p3 de vuelta al índice x1_idx y x2_idx
        const offsetDesdeP1 = p3.y - (p1.y + pendiente * (x3_idx - x1_idx));
        const y_linea2_inicio = p1.y + offsetDesdeP1;
        const y_linea2_fin    = p2.y + offsetDesdeP1;

        const dibujo = {
            tipo: 'canal',
            linea1: [p1, p2],
            linea2: [
                { x: p1.x, y: y_linea2_inicio },
                { x: p2.x, y: y_linea2_fin }
            ],
            color: '#8b5cf6',
            width: 2
        };

        this.dibujos.push(dibujo);
        this.guardarDibujos();
        this.actualizarDibujosEnGrafico();

        console.log('✅ Canal creado con paralela manual:', dibujo);
    }
    
    crearLineaHorizontal(punto) {
        const dibujo = {
            tipo: 'horizontal',
            precio: punto.y,
            color: '#10b981',
            width: 2
        };
        
        this.dibujos.push(dibujo);
        this.guardarDibujos();
        this.actualizarDibujosEnGrafico();
        
        console.log('✅ Línea horizontal creada:', dibujo);
    }
    
    borrarDibujos() {
        const graficoDiv = document.getElementById('grafico-pro');
        if (!graficoDiv || !graficoDiv.layout) {
            alert('Gráfico no disponible');
            return;
        }
        
        const currentShapes = graficoDiv.layout.shapes || [];
        
        // Shapes del SISTEMA tienen nombres específicos (soporte_, resistencia_, patron_, etc.)
        const shapesDelSistema = currentShapes.filter(shape => {
            return shape.name && (
                shape.name.startsWith('soporte_') ||
                shape.name.startsWith('resistencia_') ||
                shape.name.startsWith('patron_') ||
                shape.name.startsWith('fibonacci_') ||
                shape.name.startsWith('divergencia_')
            );
        });
        
        // Shapes del USUARIO = personalizadas (_esUsuario) + Plotly (sin nombre del sistema)
        const shapesUsuario = currentShapes.filter(shape => {
            // Si tiene marca _esUsuario → es del usuario
            if (shape._esUsuario) return true;
            
            // Si NO tiene nombre del sistema → es del usuario (dibujada con Plotly)
            if (!shape.name) return true;
            if (!shape.name.startsWith('soporte_') && 
                !shape.name.startsWith('resistencia_') &&
                !shape.name.startsWith('patron_') &&
                !shape.name.startsWith('fibonacci_') &&
                !shape.name.startsWith('divergencia_')) {
                return true;
            }
            
            return false;
        });
        
        const totalUsuario = shapesUsuario.length + this.dibujos.length;
        
        if (totalUsuario === 0) {
            alert('No hay dibujos para borrar');
            return;
        }
        
        if (confirm(`¿Borrar todos los dibujos (${totalUsuario})?`)) {
            // Borrar dibujos personalizados
            this.dibujos = [];
            this.guardarDibujos();
            
            // Mantener solo shapes del sistema
            Plotly.relayout('grafico-pro', { shapes: shapesDelSistema });
            
            console.log(`🗑️ Dibujos borrados. Sistema: ${shapesDelSistema.length}, Usuario borrado: ${shapesUsuario.length}`);
        }
    }
    
    desactivarHerramienta() {
        this.herramientaActiva = null;
        document.querySelectorAll('.btn-dibujo').forEach(b => b.classList.remove('active'));
        
        // Desactivar Pan si estaba activo
        const btnPan = document.getElementById('btn-pan');
        if (btnPan && btnPan.classList.contains('active')) {
            btnPan.classList.remove('active');
            btnPan.style.background = '';
            btnPan.style.color = '';
            btnPan.style.borderColor = '';
            Plotly.relayout('grafico-pro', { dragmode: 'zoom' });
        }
        
        // Restaurar cursor normal
        const graficoDiv = document.getElementById('grafico-pro');
        if (graficoDiv) {
            graficoDiv.style.cursor = 'default';
        }
    }
    
    guardarDibujos() {
        // Guardar en localStorage por ticker
        const key = `dibujos_${this.ticker}`;
        localStorage.setItem(key, JSON.stringify(this.dibujos));
    }
    
    cargarDibujos() {
        // Cargar desde localStorage por ticker
        const key = `dibujos_${this.ticker}`;
        const guardados = localStorage.getItem(key);
        
        if (guardados) {
            try {
                this.dibujos = JSON.parse(guardados);
                console.log('📂 Dibujos cargados:', this.dibujos.length);
            } catch (e) {
                console.error('❌ Error cargando dibujos:', e);
                this.dibujos = [];
            }
        } else {
            this.dibujos = [];
        }
    }
    
    actualizarDibujosEnGrafico() {
        // Actualiza solo las shapes sin redibujar el gráfico completo
        // Esto preserva el zoom y la posición actual
        const graficoDiv = document.getElementById('grafico-pro');
        if (!graficoDiv || !graficoDiv.layout || !graficoDiv.data) {
            console.warn('⚠️ Gráfico no está listo, usando actualizarGrafico() completo');
            this.actualizarGrafico();
            return;
        }
        
        // Obtener shapes existentes del layout actual
        const currentLayout = graficoDiv.layout;
        const shapesExistentes = currentLayout.shapes || [];
        
        // Filtrar SOLO las shapes que NO son dibujos del usuario
        // Las shapes de dibujos tienen la propiedad _esUsuario: true
        const shapesBase = shapesExistentes.filter(shape => !shape._esUsuario);
        
        // Regenerar shapes de dibujos con marca identificadora y editables
        const shapesDibujos = [];
        this.dibujos.forEach((dibujo) => {
            switch(dibujo.tipo) {
                case 'tendencia':
                    shapesDibujos.push({
                        type: 'line',
                        x0: dibujo.puntos[0].x,
                        y0: dibujo.puntos[0].y,
                        x1: dibujo.puntos[1].x,
                        y1: dibujo.puntos[1].y,
                        line: {
                            color: dibujo.color,
                            width: dibujo.width,
                            dash: 'solid'
                        },
                        editable: true,
                        _esUsuario: true
                    });
                    break;
                    
                case 'canal':
                    shapesDibujos.push({
                        type: 'line',
                        x0: dibujo.linea1[0].x,
                        y0: dibujo.linea1[0].y,
                        x1: dibujo.linea1[1].x,
                        y1: dibujo.linea1[1].y,
                        line: { color: dibujo.color, width: dibujo.width, dash: 'solid' },
                        editable: true,
                        _esUsuario: true
                    });
                    shapesDibujos.push({
                        type: 'line',
                        x0: dibujo.linea2[0].x,
                        y0: dibujo.linea2[0].y,
                        x1: dibujo.linea2[1].x,
                        y1: dibujo.linea2[1].y,
                        line: { color: dibujo.color, width: dibujo.width, dash: 'solid' },
                        editable: true,
                        _esUsuario: true
                    });
                    break;
                    
                case 'horizontal':
                    shapesDibujos.push({
                        type: 'line',
                        xref: 'paper',
                        x0: 0,
                        x1: 1,
                        y0: dibujo.precio,
                        y1: dibujo.precio,
                        line: { color: dibujo.color, width: dibujo.width, dash: 'dash' },
                        editable: true,
                        _esUsuario: true
                    });
                    break;
            }
        });
        
        // Actualizar solo las shapes, preservando el zoom
        Plotly.relayout('grafico-pro', {
            shapes: [...shapesBase, ...shapesDibujos]
        });
        
        console.log(`✅ Dibujos actualizados: ${shapesDibujos.length} shapes, ${shapesBase.length} base (zoom preservado)`);
    }
    
    sincronizarDibujosDesdeGrafico(shapes) {
        // Extrae solo las shapes de usuario (_esUsuario: true) y actualiza this.dibujos
        const shapesUsuario = shapes.filter(shape => shape._esUsuario);
        
        // Reconstruir el array de dibujos desde las shapes editadas
        this.dibujos = [];
        
        let i = 0;
        while (i < shapesUsuario.length) {
            const shape = shapesUsuario[i];
            
            // Detectar si es canal (2 líneas consecutivas del mismo color)
            if (i < shapesUsuario.length - 1) {
                const nextShape = shapesUsuario[i + 1];
                if (shape.line.color === nextShape.line.color && 
                    shape.line.dash === nextShape.line.dash &&
                    shape.line.color === '#8b5cf6') {  // Color del canal
                    // Es un canal
                    this.dibujos.push({
                        tipo: 'canal',
                        linea1: [
                            { x: shape.x0, y: shape.y0 },
                            { x: shape.x1, y: shape.y1 }
                        ],
                        linea2: [
                            { x: nextShape.x0, y: nextShape.y0 },
                            { x: nextShape.x1, y: nextShape.y1 }
                        ],
                        color: shape.line.color,
                        width: shape.line.width
                    });
                    i += 2;  // Saltar la siguiente shape (ya procesada)
                    continue;
                }
            }
            
            // Línea horizontal (xref: 'paper')
            if (shape.xref === 'paper') {
                this.dibujos.push({
                    tipo: 'horizontal',
                    precio: shape.y0,
                    color: shape.line.color,
                    width: shape.line.width
                });
            } else {
                // Línea de tendencia normal
                this.dibujos.push({
                    tipo: 'tendencia',
                    puntos: [
                        { x: shape.x0, y: shape.y0 },
                        { x: shape.x1, y: shape.y1 }
                    ],
                    color: shape.line.color,
                    width: shape.line.width
                });
            }
            
            i++;
        }
        
        // Guardar en localStorage
        this.guardarDibujos();
        console.log(`✅ Dibujos sincronizados: ${this.dibujos.length}`);
    }
    
    aplicarDibujos(shapes) {
        console.log('🎨 aplicarDibujos llamado');
        console.log('  Dibujos totales:', this.dibujos.length);
        console.log('  Shapes antes:', shapes.length);
        
        // Añadir dibujos guardados como shapes de Plotly
        this.dibujos.forEach((dibujo, idx) => {
            console.log(`  Procesando dibujo ${idx}:`, dibujo.tipo);
            
            switch(dibujo.tipo) {
                case 'tendencia':
                    const shapeTendencia = {
                        type: 'line',
                        x0: dibujo.puntos[0].x,
                        y0: dibujo.puntos[0].y,
                        x1: dibujo.puntos[1].x,
                        y1: dibujo.puntos[1].y,
                        line: {
                            color: dibujo.color,
                            width: dibujo.width,
                            dash: 'solid'
                        },
                        editable: true,
                        _esUsuario: true
                    };
                    console.log('    Shape tendencia:', shapeTendencia);
                    shapes.push(shapeTendencia);
                    break;
                    
                case 'canal':
                    // Línea 1
                    shapes.push({
                        type: 'line',
                        x0: dibujo.linea1[0].x,
                        y0: dibujo.linea1[0].y,
                        x1: dibujo.linea1[1].x,
                        y1: dibujo.linea1[1].y,
                        line: {
                            color: dibujo.color,
                            width: dibujo.width,
                            dash: 'solid'
                        },
                        editable: true,
                        _esUsuario: true
                    });
                    // Línea 2 (paralela)
                    shapes.push({
                        type: 'line',
                        x0: dibujo.linea2[0].x,
                        y0: dibujo.linea2[0].y,
                        x1: dibujo.linea2[1].x,
                        y1: dibujo.linea2[1].y,
                        line: {
                            color: dibujo.color,
                            width: dibujo.width,
                            dash: 'solid'
                        },
                        editable: true,
                        _esUsuario: true
                    });
                    console.log('    Canal añadido (2 líneas)');
                    break;
                    
                case 'horizontal':
                    const shapeHorizontal = {
                        type: 'line',
                        xref: 'paper',
                        x0: 0,
                        x1: 1,
                        y0: dibujo.precio,
                        y1: dibujo.precio,
                        line: {
                            color: dibujo.color,
                            width: dibujo.width,
                            dash: 'dash'
                        },
                        editable: true,
                        _esUsuario: true
                    };
                    console.log('    Shape horizontal:', shapeHorizontal);
                    shapes.push(shapeHorizontal);
                    break;
            }
        });
        
        console.log('  Shapes después:', shapes.length);
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.graficoPro = new GraficoPro();
});


/* ═══════════════════════════════════════════════════════

/* ═══════════════════════════════════════════════════════
   GLOSARIO - ABRIR MODAL LOCAL
   ═══════════════════════════════════════════════════════ */

document.getElementById('btn-glosario').addEventListener('click', () => {
    abrirGlosario();
});
