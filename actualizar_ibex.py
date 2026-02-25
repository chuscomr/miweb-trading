def actualizar_ibex():
    ahora = datetime.now(timezone.utc)

    meta = {
        "fecha": ahora.strftime("%d/%m/%Y"),
        "hora": ahora.strftime("%H:%M"),
        "timezone": "UTC",
        "mercado_abierto": en_horario_mercado() and es_dia_habil(),
        "fuente": "actualizar_ibex.py"
    }

    print(f">>> ACTUALIZANDO IBEX {meta['hora']} UTC <<<")

    datos_salida = {
        "__meta__": meta
    }

    for ticker in IBEX35:
        try:
            df = yf.download(
                ticker,
                period="60d",
                interval="1h",
                progress=False
            )

            if df.empty or "Close" not in df or "Volume" not in df:
                continue

            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            volume = df["Volume"]
            if hasattr(volume, "columns"):
                volume = volume.iloc[:, 0]

            precios = close.dropna().tolist()
            volumenes = volume.dropna().tolist()

            if len(precios) < 50 or len(volumenes) < 50:
                continue

            precio_actual = round(precios[-1], 2)
            hora_precio = meta["hora"]

            resultado = sistema_trading(precios, volumenes)

            mm20 = sum(precios[-20:]) / 20
            max20 = max(precios[-20:])
            min20 = min(precios[-20:])

            if resultado["decision"] == "COMPRA":
                entrada = round(max20 * 1.001, 2)
                stop = round(min20 * 0.995, 2)
                riesgo = round(entrada - stop, 2)
                objetivo = round(entrada + 2 * riesgo, 2)
                riesgo_pct = round(riesgo / entrada * 100, 2)
                rr = round((objetivo - entrada) / riesgo, 2)
            else:
                entrada = stop = objetivo = riesgo_pct = rr = None

            datos_salida[ticker] = {
                "decision": resultado["decision"],
                "motivos": resultado["motivos"],
                "precio": precio_actual,
                "hora": hora_precio,
                "max_reciente": max20,
                "min_reciente": min20,
                "mm20": mm20,
                "entrada": entrada,
                "stop": stop,
                "objetivo": objetivo,
                "riesgo_pct": riesgo_pct,
                "rr": rr
            }

        except Exception as e:
            print(f"Error en {ticker}: {e}")

    with open(RUTA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos_salida, f, indent=4, ensure_ascii=False)

    print(f">>> JSON actualizado ({len(datos_salida) - 1} valores) <<<")
