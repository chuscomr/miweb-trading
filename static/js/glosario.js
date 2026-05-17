// ═══════════════════════════════════════════════════════════
// GLOSARIO DE INDICADORES TÉCNICOS
// ═══════════════════════════════════════════════════════════

const GLOSARIO = [
    // HERRAMIENTAS DEL GRÁFICO
    { cat: "🔧 Gráfico", badge: "LOG", nombre: "Escala Logarítmica",
      def: "En escala logarítmica, distancias iguales en el eje Y representan variaciones porcentuales iguales — no absolutas.",
      uso: "Imprescindible para analizar activos con grandes recorridos históricos (posicional 2+ años). Actívala con el botón Lin/Log." },

    // TENDENCIA
    { cat: "📈 Tendencia", badge: "MM20", nombre: "Media Móvil Simple 20",
      def: "Promedio del precio de cierre de las últimas 20 velas.",
      uso: "Si el precio está por encima de la MM20, hay tendencia alcista. Se usa como soporte o resistencia dinámica." },

    { cat: "📈 Tendencia", badge: "MM50", nombre: "Media Móvil Simple 50",
      def: "Promedio de los últimos 50 cierres. Refleja la tendencia a medio plazo.",
      uso: "El cruce de MM20 con MM50 (cruce dorado/muerte) es señal clásica de cambio de tendencia." },

    { cat: "📈 Tendencia", badge: "MM200", nombre: "Media Móvil Simple 200",
      def: "Promedio de los últimos 200 cierres. Define tendencia a largo plazo.",
      uso: "Precio sobre MM200 = mercado alcista. Precio bajo MM200 = bajista." },

    { cat: "📈 Tendencia", badge: "ADX", nombre: "Average Directional Index",
      def: "Mide la FUERZA de la tendencia en escala 0-100, sin indicar dirección.",
      uso: "ADX > 25 = tendencia fuerte. ADX < 20 = lateral." },

    // MOMENTUM
    { cat: "⚡ Momentum", badge: "RSI", nombre: "Relative Strength Index",
      def: "Oscilador 0-100 que mide velocidad y magnitud de movimientos.",
      uso: "RSI > 70 = sobrecompra. RSI < 30 = sobreventa. Buscar divergencias." },

    { cat: "⚡ Momentum", badge: "MACD", nombre: "Moving Average Convergence Divergence",
      def: "Diferencia entre EMA12 y EMA26 con su media de 9 períodos.",
      uso: "Cruce MACD sobre señal = compra. Las divergencias MACD/precio son muy fiables." },

    { cat: "⚡ Momentum", badge: "STOCH", nombre: "Stochastic",
      def: "Compara cierre con rango máx/mín de N períodos. Oscila 0-100.",
      uso: "%K > 80 sobrecompra, < 20 sobreventa. Cruce %K/%D en extremos da señales." },

    // VOLUMEN
    { cat: "📊 Volumen", badge: "VOL", nombre: "Volumen",
      def: "Número de acciones negociadas en cada vela.",
      uso: "Subida con volumen alto = tendencia confirmada. Subida con volumen bajo = sospechosa." },

    { cat: "📊 Volumen", badge: "VWAP", nombre: "Volume Weighted Average Price",
      def: "Precio promedio del día ponderado por volumen. Referencia institucional.",
      uso: "Precio sobre VWAP = sesgo alcista intradía. Actúa como soporte/resistencia dinámico." },

    // VOLATILIDAD
    { cat: "🌡️ Volatilidad", badge: "BB", nombre: "Bandas de Bollinger",
      def: "MM20 ± 2 desviaciones estándar. Se expanden con volatilidad.",
      uso: "Squeeze (bandas juntas) anticipa movimiento fuerte. Precio en banda = sobrecompra/sobreventa." },

    // NIVELES
    { cat: "🎯 Niveles", badge: "S/R", nombre: "Soportes y Resistencias",
      def: "Zonas donde el mercado ha rebotado (soporte) o rechazado (resistencia).",
      uso: "Comprar cerca de soporte con stop bajo él. Si soporte se rompe, se convierte en resistencia." },

    // PATRONES
    { cat: "🕯️ Patrones", badge: "DIV", nombre: "Divergencias",
      def: "Precio marca nuevo máximo/mínimo pero indicador no lo confirma.",
      uso: "Divergencia bajista: precio sube pero RSI baja. Divergencia alcista: precio baja pero RSI sube." },

    { cat: "🕯️ Patrones", badge: "VELAS", nombre: "Patrones de Velas Japonesas",
      def: "Formaciones de 1-3 velas que indican reversión o continuación.",
      uso: "Ver secciones detalladas abajo." },
];

function abrirGlosario() {
    const modal = document.getElementById('modalDefiniciones');
    modal.classList.add('abierto');
    document.getElementById('buscadorIndicador').value = '';
    renderizarGlosario(GLOSARIO);
}

function cerrarGlosario() {
    document.getElementById('modalDefiniciones').classList.remove('abierto');
}

function filtrarIndicadores(termino) {
    termino = termino.toLowerCase().trim();
    if (!termino) {
        renderizarGlosario(GLOSARIO);
        return;
    }
    const filtrados = GLOSARIO.filter(i =>
        i.nombre.toLowerCase().includes(termino) ||
        i.def.toLowerCase().includes(termino) ||
        i.uso.toLowerCase().includes(termino) ||
        i.badge.toLowerCase().includes(termino)
    );
    renderizarGlosario(filtrados);
}

function renderizarGlosario(lista) {
    const contenedor = document.getElementById('listaIndicadores');
    if (lista.length === 0) {
        contenedor.innerHTML = '<div class="sin-resultados">🔍 No se encontraron indicadores con ese término.</div>';
        return;
    }
    const categorias = [...new Set(lista.map(i => i.cat))];
    let html = '';
    categorias.forEach(cat => {
        html += `<div class="cat-separador"><h3>${cat}</h3></div>`;
        lista.filter(i => i.cat === cat).forEach(ind => {
            // Renderizado especial para patrones de velas
            if (ind.badge === 'VELAS') {
                html += renderizarPatronesVelas(ind);
            } else {
                html += `
                <div class="indicador-card">
                    <div class="ind-cabecera">
                        <span class="ind-badge">${ind.badge}</span>
                        <span class="ind-nombre">${ind.nombre}</span>
                    </div>
                    <p class="ind-definicion">${ind.def}</p>
                    <div class="ind-uso"><strong>💡 Cómo usarlo:</strong> ${ind.uso}</div>
                </div>`;
            }
        });
    });
    contenedor.innerHTML = html;
}

function renderizarPatronesVelas(ind) {
    return `
    <div class="indicador-card patrones-velas-card">
        <div class="ind-cabecera">
            <span class="ind-badge">${ind.badge}</span>
            <span class="ind-nombre">${ind.nombre}</span>
        </div>
        <p class="ind-definicion">Formaciones de 1-3 velas que indican reversión o continuación. El gráfico los marca automáticamente.</p>
        
        <div class="patron-seccion">
            <div class="patron-titulo">📈 REVERSIÓN ALCISTA (Fin de pullback)</div>
            <div class="patron-lista">
                <div class="patron-item"><span class="patron-icono">🔨</span><strong>Martillo</strong> — Sombra inferior larga (>2× cuerpo)</div>
                <div class="patron-item"><span class="patron-icono">🟢</span><strong>Envolvente Alcista</strong> — Vela verde envuelve roja</div>
                <div class="patron-item"><span class="patron-icono">🌅</span><strong>Estrella Mañana</strong> — 3 velas: roja + doji + verde</div>
            </div>
        </div>
        
        <div class="patron-seccion">
            <div class="patron-titulo">📉 REVERSIÓN BAJISTA (Fin de rally)</div>
            <div class="patron-lista">
                <div class="patron-item"><span class="patron-icono">⭐</span><strong>Estrella Fugaz</strong> — Sombra superior larga</div>
                <div class="patron-item"><span class="patron-icono">🔴</span><strong>Envolvente Bajista</strong> — Vela roja envuelve verde</div>
                <div class="patron-item"><span class="patron-icono">🌆</span><strong>Estrella Tarde</strong> — 3 velas: verde + doji + roja</div>
            </div>
        </div>
        
        <div class="patron-seccion">
            <div class="patron-titulo">🚀 CONTINUACIÓN ALCISTA</div>
            <div class="patron-lista">
                <div class="patron-item"><span class="patron-icono">⬆⬆⬆</span><strong>Tres Soldados Blancos</strong> — 3 verdes ascendentes</div>
                <div class="patron-item"><span class="patron-icono">⬆</span><strong>Vela Momentum</strong> — Vela verde muy grande</div>
            </div>
        </div>
        
        <div class="patron-seccion">
            <div class="patron-titulo">📊 CONTINUACIÓN BAJISTA</div>
            <div class="patron-lista">
                <div class="patron-item"><span class="patron-icono">⬇⬇⬇</span><strong>Tres Cuervos Negros</strong> — 3 rojas descendentes</div>
                <div class="patron-item"><span class="patron-icono">⬇</span><strong>Vela Momentum</strong> — Vela roja muy grande</div>
            </div>
        </div>
        
        <div class="patron-seccion">
            <div class="patron-titulo">⚖️ INDECISIÓN</div>
            <div class="patron-lista">
                <div class="patron-item"><span class="patron-icono">✖</span><strong>Doji</strong> — Cuerpo muy pequeño</div>
            </div>
        </div>
        
        <div class="patron-estrategia">
            <div class="estrategia-titulo">📈 ESTRATEGIA PULLBACK:</div>
            <div class="estrategia-desc">
                Busca: 🔨 + 🌅 + 🟢 en soporte/VWAP<br>
                <em>+ Confluencia con divergencia alcista RSI</em>
            </div>
        </div>
        
        <div class="patron-estrategia">
            <div class="estrategia-titulo">📊 ESTRATEGIA BREAKOUT:</div>
            <div class="estrategia-desc">
                Busca: ⬆⬆⬆ + 🟢 en resistencia + volumen alto<br>
                <em>+ Sin divergencia bajista</em>
            </div>
        </div>
    </div>`;
}

// Cerrar con ESC
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') cerrarGlosario();
});

// ═══════════════════════════════════════════════════════════
// DRAG & DROP DEL MODAL
// ═══════════════════════════════════════════════════════════

(function() {
    const overlay = document.getElementById('modalDefiniciones');
    const contenido = overlay?.querySelector('.modal-contenido');
    const header = overlay?.querySelector('.modal-header');
    
    if (!overlay || !header) return;
    
    let drag = false;
    let startX, startY;
    let initialLeft, initialTop;
    
    // Cursor de "grab"
    header.style.cursor = 'grab';
    
    header.addEventListener('mousedown', (e) => {
        // No hacer drag si se clickea un botón o input
        if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
        
        drag = true;
        header.style.cursor = 'grabbing';
        
        // Convertir de transform a posición fija
        const rect = overlay.getBoundingClientRect();
        overlay.style.left = rect.left + 'px';
        overlay.style.top = rect.top + 'px';
        overlay.style.transform = 'none';
        
        startX = e.clientX;
        startY = e.clientY;
        initialLeft = rect.left;
        initialTop = rect.top;
        
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!drag) return;
        
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        
        let newLeft = initialLeft + deltaX;
        let newTop = initialTop + deltaY;
        
        // Limitar a los bordes de la ventana
        const maxLeft = window.innerWidth - overlay.offsetWidth;
        const maxTop = window.innerHeight - overlay.offsetHeight;
        
        newLeft = Math.max(0, Math.min(newLeft, maxLeft));
        newTop = Math.max(0, Math.min(newTop, maxTop));
        
        overlay.style.left = newLeft + 'px';
        overlay.style.top = newTop + 'px';
    });
    
    document.addEventListener('mouseup', () => {
        if (drag) {
            drag = false;
            header.style.cursor = 'grab';
        }
    });
})();
