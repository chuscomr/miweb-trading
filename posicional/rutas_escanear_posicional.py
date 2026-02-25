# ==========================================================
# AÑADIR AL FINAL DE posicional_bp.py (ANTES DEL print final)
# ==========================================================

# ==========================================================
# ESCÁNERES
# ==========================================================

@posicional_bp.route('/escanear/ibex')
def escanear_ibex():
    """Escáner IBEX 35 - Señales de compra posicionales"""
    try:
        print("\n🔍 Ejecutando escáner IBEX 35...")
        
        resultados = []
        
        for ticker in IBEX_35:
            try:
                # Obtener datos semanales
                df, validacion = obtener_datos_semanales(ticker, validar=False)
                
                if df is None or len(df) < 50:
                    continue
                
                # Analizar
                precios = df['Close'].tolist()
                volumenes = df['Volume'].tolist() if 'Volume' in df.columns else None
                analisis = evaluar_entrada_posicional(precios, volumenes, df=df)
                
                # Guardar resultado
                resultados.append({
                    "ticker": ticker,
                    "nombre": ticker.replace(".MC", ""),
                    "precio": float(df['Close'].iloc[-1]),
                    "decision": analisis.get("decision", "ESPERAR"),
                    "motivo": ", ".join(analisis.get("motivos", [])),
                    "entrada": analisis.get("entrada", 0),
                    "stop": analisis.get("stop", 0),
                    "riesgo_pct": analisis.get("riesgo_pct", 0)
                })
                
            except Exception as e:
                print(f"⚠️ Error en {ticker}: {e}")
                continue
        
        # Separar por decisión
        compras = [r for r in resultados if r['decision'] == 'COMPRA']
        esperas = [r for r in resultados if r['decision'] != 'COMPRA']
        
        print(f"✅ Escáner completado: {len(compras)} señales de compra")
        
        return render_template('escanear_posicional.html',
                             titulo="Escáner IBEX 35",
                             universo="IBEX 35",
                             total=len(IBEX_35),
                             analizados=len(resultados),
                             compras=compras,
                             esperas=esperas,
                             sistema="posicional")
    
    except Exception as e:
        print(f"❌ Error en escáner IBEX: {e}")
        import traceback
        traceback.print_exc()
        return render_template('escanear_posicional.html',
                             error=str(e),
                             sistema="posicional")

@posicional_bp.route('/escanear/continuo')
def escanear_continuo():
    """Escáner Mercado Continuo - Señales de compra posicionales"""
    try:
        print("\n🔍 Ejecutando escáner Mercado Continuo...")
        
        resultados = []
        
        for ticker in MERCADO_CONTINUO:
            try:
                # Obtener datos semanales
                df, validacion = obtener_datos_semanales(ticker, validar=False)
                
                if df is None or len(df) < 50:
                    continue
                
                # Analizar
                precios = df['Close'].tolist()
                volumenes = df['Volume'].tolist() if 'Volume' in df.columns else None
                analisis = evaluar_entrada_posicional(precios, volumenes, df=df)
                
                # Guardar resultado
                resultados.append({
                    "ticker": ticker,
                    "nombre": ticker.replace(".MC", ""),
                    "precio": float(df['Close'].iloc[-1]),
                    "decision": analisis.get("decision", "ESPERAR"),
                    "motivo": ", ".join(analisis.get("motivos", [])),
                    "entrada": analisis.get("entrada", 0),
                    "stop": analisis.get("stop", 0),
                    "riesgo_pct": analisis.get("riesgo_pct", 0)
                })
                
            except Exception as e:
                print(f"⚠️ Error en {ticker}: {e}")
                continue
        
        # Separar por decisión
        compras = [r for r in resultados if r['decision'] == 'COMPRA']
        esperas = [r for r in resultados if r['decision'] != 'COMPRA']
        
        print(f"✅ Escáner completado: {len(compras)} señales de compra")
        
        return render_template('escanear_posicional.html',
                             titulo="Escáner Mercado Continuo",
                             universo="Mercado Continuo",
                             total=len(MERCADO_CONTINUO),
                             analizados=len(resultados),
                             compras=compras,
                             esperas=esperas,
                             sistema="posicional")
    
    except Exception as e:
        print(f"❌ Error en escáner Continuo: {e}")
        import traceback
        traceback.print_exc()
        return render_template('escanear_posicional.html',
                             error=str(e),
                             sistema="posicional")
