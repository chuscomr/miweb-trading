/**
 * alertas_panel.js — MiWeb Swing Trading
 * Integración del panel de alertas en la página de swing/indicadores.
 *
 * USO: incluir en swing.html antes del cierre de </body>:
 *   <script src="{{ url_for('static', filename='js/alertas_panel.js') }}"></script>
 *
 * Requiere que en swing.html exista:
 *   <div id="panel-alertas"></div>
 *   <div id="alertas-ia-box"></div>  (opcional)
 */

// ─────────────────────────────────────────────
// COLORES Y CONFIGURACIÓN
// ─────────────────────────────────────────────
const SEVERIDAD_CONFIG = {
    ALTA:  { color: '#e74c3c', bg: '#fdf0ef', borde: '#e74c3c', badge: '#e74c3c' },
    MEDIA: { color: '#f39c12', bg: '#fef9ee', borde: '#f39c12', badge: '#f39c12' },
    BAJA:  { color: '#3498db', bg: '#eef6fd', borde: '#3498db', badge: '#3498db' },
};

const RECOMENDACION_TEXTO = {
    ENTRAR_LARGO:       '↑ Entrar largo',
    ENTRAR_CORTO:       '↓ Entrar corto',
    ESPERAR:            '⏳ Esperar',
    REDUCIR_POSICION:   '⬇ Reducir posición',
    CERRAR_POSICION:    '✖ Cerrar posición',
    AJUSTAR_STOP:       '🛡 Ajustar stop',
};

// ─────────────────────────────────────────────
// FUNCIÓN PRINCIPAL — llamar al cambiar ticker
// ─────────────────────────────────────────────

/**
 * Carga y renderiza las alertas para un ticker dado.
 * Llama a esta función desde tu evento de cambio de ticker.
 *
 * Ejemplo de uso en tu código existente:
 *   document.getElementById('ticker-select').addEventListener('change', function() {
 *       cargarAlertas(this.value, { usarIA: true, sistema: 'swing' });
 *   });
 */
async function cargarAlertas(ticker, opciones = {}) {
    const {
        usarIA   = false,     // true → llama a Haiku (coste mínimo)
        sistema  = 'swing',   // swing / medio / posicional
        panelId  = 'panel-alertas',
        iaBoxId  = 'alertas-ia-box',
    } = opciones;

    const panel = document.getElementById(panelId);
    if (!panel) return;

    // Estado de carga
    panel.innerHTML = _renderCargando(ticker);

    try {
        const url = `/api/alertas/${encodeURIComponent(ticker)}?ia=${usarIA ? 1 : 0}&sistema=${sistema}`;
        const res  = await fetch(url);

        if (!res.ok) {
            panel.innerHTML = _renderError(`Error ${res.status} obteniendo alertas`);
            return;
        }

        const data = await res.json();

        // Renderizar alertas
        panel.innerHTML = _renderAlertas(data);

        // Renderizar análisis IA si existe
        const iaBox = document.getElementById(iaBoxId);
        if (iaBox) {
            iaBox.innerHTML = data.analisis_ia
                ? _renderAnalisisIA(data.analisis_ia, ticker)
                : '';
            iaBox.style.display = data.analisis_ia ? 'block' : 'none';
        }

    } catch (err) {
        panel.innerHTML = _renderError(err.message);
    }
}


// ─────────────────────────────────────────────
// RENDERERS HTML
// ─────────────────────────────────────────────

function _renderAlertas(data) {
    if (data.total === 0) {
        return `
            <div class="alertas-vacio">
                <span style="font-size:1.4em">✅</span>
                <p style="margin:6px 0 0; color:#666; font-size:.85em">
                    Sin alertas activas para <strong>${data.ticker}</strong>
                </p>
            </div>`;
    }

    const header = `
        <div class="alertas-header">
            <span class="alertas-titulo">⚡ Alertas activas</span>
            <span class="alertas-badge">${data.total}</span>
        </div>`;

    const items = data.alertas.map(a => _renderAlertaItem(a)).join('');
    return header + `<div class="alertas-lista">${items}</div>`;
}

function _renderAlertaItem(alerta) {
    const cfg = SEVERIDAD_CONFIG[alerta.severidad] || SEVERIDAD_CONFIG.BAJA;
    return `
        <div class="alerta-item" style="
            border-left: 4px solid ${cfg.borde};
            background: ${cfg.bg};
            border-radius: 4px;
            padding: 10px 12px;
            margin-bottom: 8px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-weight:600; font-size:.88em; color:#2c3e50;">
                    ${alerta.icono} ${alerta.titulo}
                </span>
                <span style="
                    background:${cfg.badge}; color:#fff;
                    font-size:.7em; padding:2px 7px;
                    border-radius:10px; font-weight:600;
                ">${alerta.severidad}</span>
            </div>
            <p style="margin:0 0 6px; font-size:.8em; color:#555; line-height:1.4;">
                ${alerta.detalle}
            </p>
            <p style="margin:0; font-size:.78em; color:${cfg.color}; font-weight:500;">
                💡 ${alerta.accion}
            </p>
        </div>`;
}

function _renderAnalisisIA(ia, ticker) {
    const recTexto = RECOMENDACION_TEXTO[ia.recomendacion] || ia.recomendacion;
    const sesgColor = {
        ALCISTA: '#27ae60', BAJISTA: '#e74c3c', NEUTRO: '#7f8c8d'
    }[ia.sesgo] || '#7f8c8d';

    return `
        <div class="alertas-ia" style="
            background: #f0f4ff;
            border: 1px solid #bdc3e6;
            border-radius: 6px;
            padding: 12px;
            margin-top: 12px;
        ">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="font-size:.8em; font-weight:700; color:#4a5568;">
                    🤖 Análisis IA — ${ticker}
                </span>
                <span style="font-size:.75em; color:#888;">
                    Confianza: <strong>${ia.confianza}</strong>
                </span>
            </div>
            <p style="margin:0 0 8px; font-size:.82em; color:#333; line-height:1.5;">
                ${ia.interpretacion}
            </p>
            <div style="display:flex; gap:10px; align-items:center;">
                <span style="
                    background:#4a5568; color:#fff;
                    padding:4px 12px; border-radius:4px;
                    font-size:.8em; font-weight:600;
                ">${recTexto}</span>
                <span style="
                    color:${sesgColor}; font-size:.8em;
                    font-weight:600;
                ">● ${ia.sesgo}</span>
                <span style="font-size:.78em; color:#666; flex:1;">
                    ${ia.razon}
                </span>
            </div>
        </div>`;
}

function _renderCargando(ticker) {
    return `
        <div style="text-align:center; padding:16px; color:#888; font-size:.85em;">
            <div class="spinner-mini"></div>
            Analizando ${ticker}...
        </div>`;
}

function _renderError(msg) {
    return `
        <div style="color:#e74c3c; font-size:.82em; padding:10px;">
            ⚠️ ${msg}
        </div>`;
}


// ─────────────────────────────────────────────
// CSS — inyectar estilos una sola vez
// ─────────────────────────────────────────────
(function injectStyles() {
    if (document.getElementById('alertas-styles')) return;
    const style = document.createElement('style');
    style.id = 'alertas-styles';
    style.textContent = `
        #panel-alertas {
            font-family: inherit;
        }
        .alertas-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .alertas-titulo {
            font-weight: 700;
            font-size: .9em;
            color: #2c3e50;
        }
        .alertas-badge {
            background: #e74c3c;
            color: #fff;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: .75em;
            font-weight: 700;
        }
        .alertas-vacio {
            text-align: center;
            padding: 20px 10px;
        }
        .spinner-mini {
            width: 20px;
            height: 20px;
            border: 2px solid #ddd;
            border-top-color: #3498db;
            border-radius: 50%;
            animation: spin .7s linear infinite;
            margin: 0 auto 8px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    `;
    document.head.appendChild(style);
})();
