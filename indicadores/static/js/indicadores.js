// static/js/indicadores.js
const UI = {
    // Inicializar botones de indicadores
    initBotonesIndicadores: function() {
        document.querySelectorAll('.btn-indicador').forEach(btn => {
            btn.addEventListener('click', function() {
                this.classList.toggle('active');
            });
        });
    },

    // Obtener indicadores seleccionados
    getIndicadoresSeleccionados: function() {
        const indicadores = [];
        document.querySelectorAll('.btn-indicador.active').forEach(btn => {
            indicadores.push(btn.dataset.ind);
        });
        return indicadores;
    },

    // Mostrar loading
    mostrarCargando: function(mostrar) {
        const btn = document.querySelector('.btn-aplicar');
        if (mostrar) {
            btn.innerHTML = '<span class="material-icons">hourglass_empty</span> Analizando...';
            btn.disabled = true;
        } else {
            btn.innerHTML = '<span class="material-icons">refresh</span> Generar Análisis';
            btn.disabled = false;
        }
    },

    // Exportar gráfico
    exportarGrafico: function() {
        Plotly.downloadImage('grafico', {
            format: 'png',
            width: 1600,
            height: 900,
            filename: 'analisis_indicadores'
        });
    },

    // Guardar configuración
    guardarConfiguracion: function() {
        const config = {
            ticker: document.getElementById('ticker').value,
            tf: document.getElementById('tf').value,
            indicadores: this.getIndicadoresSeleccionados()
        };
        localStorage.setItem('config_indicadores', JSON.stringify(config));
        
        // Feedback visual
        const btn = document.querySelector('[onclick="UI.guardarConfiguracion()"]');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<span class="material-icons">check</span>';
        setTimeout(() => btn.innerHTML = originalHTML, 2000);
    },

    // Cargar configuración
    cargarConfiguracion: function() {
        const guardada = localStorage.getItem('config_indicadores');
        if (guardada) {
            const config = JSON.parse(guardada);
            document.getElementById('ticker').value = config.ticker;
            document.getElementById('tf').value = config.tf;
            
            // Limpiar selección actual
            document.querySelectorAll('.btn-indicador').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Activar guardados
            config.indicadores.forEach(ind => {
                const btn = document.querySelector(`[data-ind="${ind}"]`);
                if (btn) btn.classList.add('active');
            });
            
            return true;
        }
        return false;
    },

    // Actualizar indicadores activos en sidebar
    actualizarIndicadoresActivos: function(indicadores) {
        const container = document.getElementById('indicadores-activos');
        if (!container) return;
        
        if (indicadores.length === 0) {
            container.innerHTML = '<span class="badge-indicador">Ninguno</span>';
            return;
        }
        
        container.innerHTML = indicadores.map(ind => {
            const nombres = {
                'MM20': 'MM20', 'MM50': 'MM50', 'MM200': 'MM200',
                'RSI': 'RSI', 'MACD': 'MACD', 'BB': 'Bollinger',
                'ATR': 'ATR', 'SR': 'S/R'
            };
            return `<span class="badge-indicador">${nombres[ind] || ind}</span>`;
        }).join('');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    UI.initBotonesIndicadores();

    if (!UI.cargarConfiguracion()) {
        const defecto = ['MM20', 'RSI', 'SR'];
        defecto.forEach(ind => {
            const btn = document.querySelector(`[data-ind="${ind}"]`);
            if (btn) btn.classList.add('active');
        });
    }
});
    
    