import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import openpyxl


# ========== STREAMLIT =========
# Mostrarlo arriba a la izquierda
st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>Comparativa estadística Santos vs Liga Mx</h3>", unsafe_allow_html=True)
analisis = st.selectbox("Selecciona un análisis:", ["Jornada", "Torneo", "Actual vs Anterior", "Leagues Cup"])

# ======== LEAGUES CUP (estilo "comparativo" con barras P90 absolutas) ========
if analisis == "Leagues Cup":
    # 1) Cargar Excel de LC y Torneo Anterior
    df = pd.read_excel("Matrix Jugadores Leaguescup.xlsx", header=1)
    df_anterior = pd.read_excel("Matrix Jugadores Torneo Anterior.xlsx", header=1)

    # Normaliza encabezados
    for d in (df, df_anterior):
        d.columns = d.columns.str.upper().str.strip()
        if "POSICIÓN" in d.columns:  # por si viene con acento
            d.rename(columns={"POSICIÓN": "POSICION"}, inplace=True)

    # 2) Lista de métricas para P90
    estadisticas = [
        "CENTROS TOTALES","CENTROS TOTALES GANADOS POR UN COMPAÑERO",
        "1 VS 1 OFENSIVOS TOTALES","1 VS 1 EXITOSOS OFENSIVOS","1VS1 NO EXITOSO OFENSIVO",
        "PARTICIPACIÓN EN GOL","ASISTENCIAS",
        "TIROS A GOL","TIROS A GOL CON DESTINO A PORTERÍA",
        "BALONES RECUPERADOS 1/4 DE CANCHA","BALONES RECUPERADOS 2/4 DE CANCHA",
        "BALONES RECUPERADOS 3/4 DE CANCHA","BALONES RECUPERADOS 4/4 DE CANCHA",
        "1 VS 1 DEFENSIVOS TOTALES","1 VS 1 EXITOSOS DEFENSIVOS","1VS1 NO EXITOSO DEFENSIVO",
        "TOTAL PASES ACERTADOS","PASES ACERTADOS CANCHA PROPIA 1/4","PASES ACERTADOS CANCHA PROPIA 2/4",
        "PASES ACERTADOS CANCHA RIVAL 3/4","PASES ACERTADOS CANCHA RIVAL 4/4",
        "BALONES PERDIDOS 1/4 DE CANCHA","BALONES PERDIDOS 2/4 DE CANCHA",
        "BALONES PERDIDOS 3/4 DE CANCHA","BALONES PERDIDOS 4/4 DE CANCHA"
    ]

    # 3) Calcular P90 (≥45 min)
    def calc_p90(row, stat):
        mins = pd.to_numeric(row.get("MINUTOS JUGADOS", 0), errors="coerce")
        val  = pd.to_numeric(row.get(stat, 0), errors="coerce")
        if pd.notna(val) and pd.notna(mins) and mins >= 1 and mins > 0:
            return float(val) / (mins / 90.0)
        return 0.0

    for stat in estadisticas:
        df[f"{stat}_P90"] = df.apply(lambda r, s=stat: calc_p90(r, s), axis=1)
        df_anterior[f"{stat}_P90"] = df_anterior.apply(lambda r, s=stat: calc_p90(r, s), axis=1)

    # 4) Tablas base (actual LC y torneo anterior)
    bd = df.copy()
    bdap24 = df_anterior.copy()

    
    bd.to_csv("ACTUAL.csv", index=False, encoding="utf-8-sig")
    bdap24.to_csv("ANTERIOR.csv", index=False, encoding="utf-8-sig")

    # 5) Promedios P90 por POSICION (LC y TA) — max por posición (como usas en otros comparativos)
    p90_actual   = bd.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()
    p90_anterior = bdap24.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()

        
    p90_actual.to_csv("P90ACTUAL.csv", index=False, encoding="utf-8-sig")
    p90_anterior.to_csv("P90ANTERIOR.csv", index=False, encoding="utf-8-sig")

    # 6) Cargar catálogo de categorías
    categorias = pd.read_csv("categorias_por_posicion_y_grupo_utf8.csv", encoding="utf-8-sig")
    # normaliza para coincidir


    categorias.columns = (
        categorias.columns
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.upper()
    )

    for col in ["POSICION", "GRUPO", "CATEGORIA"]:
        if col in categorias.columns:
            categorias[col] = categorias[col].astype(str).str.strip().str.upper()

    
    # 7) Filtrar Santos
    bd_filtrada = bd[bd["EQUIPO"].astype(str).str.contains("SANTOS LAGUNA", case=False, na=False)].copy()

    # 8) Selección de jugador
    jugadores = bd_filtrada["JUGADOR"].dropna().unique()
    if len(jugadores) == 0:
        st.warning("No hay jugadores disponibles para Leagues Cup.")
        st.stop()

    jugador = st.selectbox("Selecciona un jugador", sorted(jugadores), index=0)
    posicion = bd_filtrada.loc[bd_filtrada["JUGADOR"] == jugador, "POSICION"].iloc[0]

    st.markdown(f"""
        <div style="font-size: 20px; color: #444; margin-top: -0.5rem;">
            <strong>Posición:</strong><br>{posicion}
        </div>
    """, unsafe_allow_html=True)

    # 9) Funciones auxiliares
    def obtener_color(valor):
        if valor == 0: return 'white'
        elif valor <= 30: return 'red'
        elif valor <= 50: return 'yellow'
        elif valor <= 75: return 'lightgreen'
        else: return 'green'

    # helper: devuelve qué nombre de columna usar para una categoría (prioriza *_P90)
    def col_p90(cat):
        c1 = f"{cat}_P90"
        if c1 in bd.columns:      return c1
        if cat in bd.columns:     return cat      # por si ya viene como _P90 en categorías
        return None

    # 10) Graficar por grupo (barras con P90 absolutos LC vs TA)
    grupos = ["Ofensivo", "Defensivo", "Posesión", "Conducción"]

    for grupo in grupos:
        st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>{grupo.upper()}</h3>", unsafe_allow_html=True)
        if grupo == "Ofensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los duelos No exitosos, entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Defensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los 1 vs 1 no exitosos entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Conducción":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para las categorías de conducción entre más abajo la barra mejor promedio</em></p>", unsafe_allow_html=True)

        # categorías del grupo/posición y columnas existentes
        cats = categorias[(categorias["POSICION"] == posicion.upper()) & (categorias["GRUPO"] == grupo.upper())]["CATEGORIA"].tolist()
        cols = [col_p90(cat) for cat in cats]
        cols = [c for c in cols if c is not None]  # filtra solo las que existen

        if not cols:
            st.warning("Este jugador no tiene datos P90 para este grupo de métricas.")
            continue

        # valores del jugador LC (actual)
        df_izq = bd_filtrada[bd_filtrada["JUGADOR"] == jugador][cols].T.reset_index()
        df_izq.columns = ["Col", "Valor"]
        df_izq["Categoría"] = df_izq["Col"].str.replace("_P90", "", regex=False)

        # valores del MISMO jugador en TA (si no existe la col en TA, da 0)
        if "JUGADOR" in bdap24.columns and jugador in bdap24["JUGADOR"].values:
            # Asegura que las mismas columnas existan en TA (si no, fill 0)
            cols_ta = [c if c in bdap24.columns else c for c in cols]
            df_der = bdap24[bdap24["JUGADOR"] == jugador][cols_ta].T.reset_index()
            df_der.columns = ["Col", "Valor"]
            df_der["Categoría"] = df_der["Col"].str.replace("_P90", "", regex=False)
        else:
            df_der = pd.DataFrame({"Col": cols, "Valor": [0.0]*len(cols)})
            df_der["Categoría"] = df_der["Col"].str.replace("_P90", "", regex=False)

        # Promedios por POSICION (LC/TA)
        # usaremos las mismas columnas que graficamos
        fig = go.Figure()
        for i, c in enumerate(cols):
            cat = c.replace("_P90", "")

            # P90 del jugador (LC y TA)
            v_lc = float(pd.to_numeric(df_izq.loc[df_izq["Col"] == c, "Valor"], errors="coerce").fillna(0).values[0])
            v_ta = float(pd.to_numeric(df_der.loc[df_der["Col"] == c, "Valor"], errors="coerce").fillna(0).values[0])

            # P90 de referencia por POSICION (los que muestras a los lados)
            prom_lc = float(pd.to_numeric(p90_actual.loc[p90_actual["POSICION"] == posicion, c], errors="coerce").fillna(0).values[0]) if c in p90_actual.columns else 0.0
            prom_ta = float(pd.to_numeric(p90_anterior.loc[p90_anterior["POSICION"] == posicion, c], errors="coerce").fillna(0).values[0]) if c in p90_anterior.columns else 0.0

            # Referencia = máximo P90 del renglón (lo que será 100%)
            ref = max(prom_lc, prom_ta)
            pct_lc = (v_lc / ref * 100.0) if ref > 0 else 0.0
            pct_ta = (v_ta / ref * 100.0) if ref > 0 else 0.0

            # Barras en porcentaje (izq = LC, der = TA)
            fig.add_trace(go.Bar(
                y=[cat], x=[-pct_lc], orientation='h',
                marker_color=obtener_color(pct_lc), text=[f"{pct_lc:.0f}%"],
                textposition="outside", showlegend=(i == 0), width=0.35, name="LC"
            ))
            fig.add_trace(go.Bar(
                y=[cat], x=[ pct_ta], orientation='h',
                marker_color=obtener_color(pct_ta), text=[f"{pct_ta:.0f}%"],
                textposition="outside", showlegend=(i == 0), width=0.35, name="TA"
            ))

            # Sigue mostrando los P90 de referencia a los lados
        # TEXTO EXTRA: columnas de referencia
            # P90JUG (más alejado)
        # Nuevo orden de columnas de texto
            # P90 (promedio LC) → izquierda extrema
            fig.add_trace(go.Scatter(x=[-280], y=[cat], mode="text", text=[f"{prom_lc:.2f}"],
                                    textposition="middle right", showlegend=False))
            # P90JUG LC → antes del centro
            fig.add_trace(go.Scatter(x=[-200], y=[cat], mode="text", text=[f"{v_lc:.2f}"],
                                    textposition="middle right", showlegend=False))
            # P90JUG TA → después del centro
            fig.add_trace(go.Scatter(x=[200], y=[cat], mode="text", text=[f"{v_ta:.2f}"],
                                    textposition="middle left", showlegend=False))
            # P90 (promedio TA) → derecha extrema
            fig.add_trace(go.Scatter(x=[280], y=[cat], mode="text", text=[f"{prom_ta:.2f}"],
                                    textposition="middle left", showlegend=False))

        # Encabezados/estilo como tus comparativos
        fig.add_annotation(x=-280, y=len(cols), text="P90", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=-170, y=len(cols), text="P90JUG", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=0,     y=len(cols), text="AP25   |   CL25", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=170,  y=len(cols), text="P90JUG", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=280,  y=len(cols), text="P90", showarrow=False, font=dict(size=13,family="Arial Black"))

        fig.update_layout(
            barmode='overlay',
            xaxis=dict(showticklabels=False, range=[-300, 300]),  # ampliado
            showlegend=False,
            height=400 + 15 * len(cols)
        )


        fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=len(cols) - 0.5,
                      line=dict(color="white", width=4), xref="x", yref="y", layer="above")

        st.plotly_chart(fig, use_container_width=True)

elif analisis == "Actual vs Anterior":
        # 1) Cargar Excel de LC y Torneo Anterior
    df = pd.read_excel("Matrix Jugadores Torneo.xlsx", header=1)
    df_anterior = pd.read_excel("Matrix Jugadores Torneo Anterior.xlsx", header=1)

    # Normaliza encabezados
    for d in (df, df_anterior):
        d.columns = d.columns.str.upper().str.strip()
        if "POSICIÓN" in d.columns:  # por si viene con acento
            d.rename(columns={"POSICIÓN": "POSICION"}, inplace=True)

    # 2) Lista de métricas para P90
    estadisticas = [
        "CENTROS TOTALES","CENTROS TOTALES GANADOS POR UN COMPAÑERO",
        "1 VS 1 OFENSIVOS TOTALES","1 VS 1 EXITOSOS OFENSIVOS","1VS1 NO EXITOSO OFENSIVO",
        "PARTICIPACIÓN EN GOL","ASISTENCIAS",
        "TIROS A GOL","TIROS A GOL CON DESTINO A PORTERÍA",
        "BALONES RECUPERADOS 1/4 DE CANCHA","BALONES RECUPERADOS 2/4 DE CANCHA",
        "BALONES RECUPERADOS 3/4 DE CANCHA","BALONES RECUPERADOS 4/4 DE CANCHA",
        "1 VS 1 DEFENSIVOS TOTALES","1 VS 1 EXITOSOS DEFENSIVOS","1VS1 NO EXITOSO DEFENSIVO",
        "TOTAL PASES ACERTADOS","PASES ACERTADOS CANCHA PROPIA 1/4","PASES ACERTADOS CANCHA PROPIA 2/4",
        "PASES ACERTADOS CANCHA RIVAL 3/4","PASES ACERTADOS CANCHA RIVAL 4/4",
        "BALONES PERDIDOS 1/4 DE CANCHA","BALONES PERDIDOS 2/4 DE CANCHA",
        "BALONES PERDIDOS 3/4 DE CANCHA","BALONES PERDIDOS 4/4 DE CANCHA"
    ]

    # 3) Calcular P90 (≥45 min)
    def calc_p90(row, stat):
        mins = pd.to_numeric(row.get("MINUTOS JUGADOS", 0), errors="coerce")
        val  = pd.to_numeric(row.get(stat, 0), errors="coerce")
        if pd.notna(val) and pd.notna(mins) and mins >= 1 and mins > 0:
            return float(val) / (mins / 90.0)
        return 0.0

    for stat in estadisticas:
        df[f"{stat}_P90"] = df.apply(lambda r, s=stat: calc_p90(r, s), axis=1)
        df_anterior[f"{stat}_P90"] = df_anterior.apply(lambda r, s=stat: calc_p90(r, s), axis=1)

    # 4) Tablas base (actual LC y torneo anterior)
    bd = df.copy()
    bdap24 = df_anterior.copy()

    
    bd.to_csv("ACTUAL.csv", index=False, encoding="utf-8-sig")
    bdap24.to_csv("ANTERIOR.csv", index=False, encoding="utf-8-sig")

    # 5) Promedios P90 por POSICION (LC y TA) — max por posición (como usas en otros comparativos)
    p90_actual   = bd.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()
    p90_anterior = bdap24.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()

        
    p90_actual.to_csv("P90ACTUAL.csv", index=False, encoding="utf-8-sig")
    p90_anterior.to_csv("P90ANTERIOR.csv", index=False, encoding="utf-8-sig")

    # 6) Cargar catálogo de categorías
    categorias = pd.read_csv("categorias_por_posicion_y_grupo_utf8.csv", encoding="utf-8-sig")
    # normaliza para coincidir


    categorias.columns = (
        categorias.columns
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.upper()
    )

    for col in ["POSICION", "GRUPO", "CATEGORIA"]:
        if col in categorias.columns:
            categorias[col] = categorias[col].astype(str).str.strip().str.upper()

    
    # 7) Filtrar Santos
    bd_filtrada = bd[bd["EQUIPO"].astype(str).str.contains("SANTOS LAGUNA", case=False, na=False)].copy()

    # 8) Selección de jugador
    jugadores = bd_filtrada["JUGADOR"].dropna().unique()
    if len(jugadores) == 0:
        st.warning("No hay jugadores disponibles para Leagues Cup.")
        st.stop()

    jugador = st.selectbox("Selecciona un jugador", sorted(jugadores), index=0)
    posicion = bd_filtrada.loc[bd_filtrada["JUGADOR"] == jugador, "POSICION"].iloc[0]

    st.markdown(f"""
        <div style="font-size: 20px; color: #444; margin-top: -0.5rem;">
            <strong>Posición:</strong><br>{posicion}
        </div>
    """, unsafe_allow_html=True)

    # 9) Funciones auxiliares
    def obtener_color(valor):
        if valor == 0: return 'white'
        elif valor <= 30: return 'red'
        elif valor <= 50: return 'yellow'
        elif valor <= 75: return 'lightgreen'
        else: return 'green'

    # helper: devuelve qué nombre de columna usar para una categoría (prioriza *_P90)
    def col_p90(cat):
        c1 = f"{cat}_P90"
        if c1 in bd.columns:      return c1
        if cat in bd.columns:     return cat      # por si ya viene como _P90 en categorías
        return None

    # 10) Graficar por grupo (barras con P90 absolutos LC vs TA)
    grupos = ["Ofensivo", "Defensivo", "Posesión", "Conducción"]

    for grupo in grupos:
        st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>{grupo.upper()}</h3>", unsafe_allow_html=True)
        if grupo == "Ofensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los duelos No exitosos, entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Defensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los 1 vs 1 no exitosos entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Conducción":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para las categorías de conducción entre más abajo la barra mejor promedio</em></p>", unsafe_allow_html=True)

        # categorías del grupo/posición y columnas existentes
        cats = categorias[(categorias["POSICION"] == posicion.upper()) & (categorias["GRUPO"] == grupo.upper())]["CATEGORIA"].tolist()
        cols = [col_p90(cat) for cat in cats]
        cols = [c for c in cols if c is not None]  # filtra solo las que existen

        if not cols:
            st.warning("Este jugador no tiene datos P90 para este grupo de métricas.")
            continue

        # valores del jugador LC (actual)
        df_izq = bd_filtrada[bd_filtrada["JUGADOR"] == jugador][cols].T.reset_index()
        df_izq.columns = ["Col", "Valor"]
        df_izq["Categoría"] = df_izq["Col"].str.replace("_P90", "", regex=False)

        # valores del MISMO jugador en TA (si no existe la col en TA, da 0)
        if "JUGADOR" in bdap24.columns and jugador in bdap24["JUGADOR"].values:
            # Asegura que las mismas columnas existan en TA (si no, fill 0)
            cols_ta = [c if c in bdap24.columns else c for c in cols]
            df_der = bdap24[bdap24["JUGADOR"] == jugador][cols_ta].T.reset_index()
            df_der.columns = ["Col", "Valor"]
            df_der["Categoría"] = df_der["Col"].str.replace("_P90", "", regex=False)
        else:
            df_der = pd.DataFrame({"Col": cols, "Valor": [0.0]*len(cols)})
            df_der["Categoría"] = df_der["Col"].str.replace("_P90", "", regex=False)

        # Promedios por POSICION (LC/TA)
        # usaremos las mismas columnas que graficamos
        fig = go.Figure()
        for i, c in enumerate(cols):
            cat = c.replace("_P90", "")

            # P90 del jugador (LC y TA)
            v_lc = float(pd.to_numeric(df_izq.loc[df_izq["Col"] == c, "Valor"], errors="coerce").fillna(0).values[0])
            v_ta = float(pd.to_numeric(df_der.loc[df_der["Col"] == c, "Valor"], errors="coerce").fillna(0).values[0])

            # P90 de referencia por POSICION (los que muestras a los lados)
            prom_lc = float(pd.to_numeric(p90_actual.loc[p90_actual["POSICION"] == posicion, c], errors="coerce").fillna(0).values[0]) if c in p90_actual.columns else 0.0
            prom_ta = float(pd.to_numeric(p90_anterior.loc[p90_anterior["POSICION"] == posicion, c], errors="coerce").fillna(0).values[0]) if c in p90_anterior.columns else 0.0

            # Referencia = máximo P90 del renglón (lo que será 100%)
            ref = max(prom_lc, prom_ta)
            pct_lc = (v_lc / ref * 100.0) if ref > 0 else 0.0
            pct_ta = (v_ta / ref * 100.0) if ref > 0 else 0.0

            # Barras en porcentaje (izq = LC, der = TA)
            fig.add_trace(go.Bar(
                y=[cat], x=[-pct_lc], orientation='h',
                marker_color=obtener_color(pct_lc), text=[f"{pct_lc:.0f}%"],
                textposition="outside", showlegend=(i == 0), width=0.35, name="LC"
            ))
            fig.add_trace(go.Bar(
                y=[cat], x=[ pct_ta], orientation='h',
                marker_color=obtener_color(pct_ta), text=[f"{pct_ta:.0f}%"],
                textposition="outside", showlegend=(i == 0), width=0.35, name="TA"
            ))

            # Sigue mostrando los P90 de referencia a los lados
        # TEXTO EXTRA: columnas de referencia
            # P90JUG (más alejado)
        # Nuevo orden de columnas de texto
            # P90 (promedio LC) → izquierda extrema
            fig.add_trace(go.Scatter(x=[-280], y=[cat], mode="text", text=[f"{prom_lc:.2f}"],
                                    textposition="middle right", showlegend=False))
            # P90JUG LC → antes del centro
            fig.add_trace(go.Scatter(x=[-200], y=[cat], mode="text", text=[f"{v_lc:.2f}"],
                                    textposition="middle right", showlegend=False))
            # P90JUG TA → después del centro
            fig.add_trace(go.Scatter(x=[200], y=[cat], mode="text", text=[f"{v_ta:.2f}"],
                                    textposition="middle left", showlegend=False))
            # P90 (promedio TA) → derecha extrema
            fig.add_trace(go.Scatter(x=[280], y=[cat], mode="text", text=[f"{prom_ta:.2f}"],
                                    textposition="middle left", showlegend=False))

        # Encabezados/estilo como tus comparativos
        fig.add_annotation(x=-280, y=len(cols), text="P90", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=-170, y=len(cols), text="P90JUG", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=0,     y=len(cols), text="AP25   |   CL25", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=170,  y=len(cols), text="P90JUG", showarrow=False, font=dict(size=13,family="Arial Black"))
        fig.add_annotation(x=280,  y=len(cols), text="P90", showarrow=False, font=dict(size=13,family="Arial Black"))

        fig.update_layout(
            barmode='overlay',
            xaxis=dict(showticklabels=False, range=[-300, 300]),  # ampliado
            showlegend=False,
            height=400 + 15 * len(cols)
        )


        fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=len(cols) - 0.5,
                      line=dict(color="white", width=4), xref="x", yref="y", layer="above")

        st.plotly_chart(fig, use_container_width=True)

elif analisis == "Jornada":
    # === Cargar archivo Excel
    df = pd.read_excel("Matrix Jugadores Jornada.xlsx",header=1)
    df.columns = df.columns.str.upper()

    
    # === Lista de métricas a convertir a P90
    estadisticas = [
        "CENTROS TOTALES",
        "CENTROS TOTALES GANADOS POR UN COMPAÑERO",
        "1 VS 1 OFENSIVOS TOTALES",
        "1 VS 1 EXITOSOS OFENSIVOS",
        "1VS1 NO EXITOSO OFENSIVO",
        "PARTICIPACIÓN EN GOL",
        "ASISTENCIAS",
        "TIROS A GOL",
        "TIROS A GOL CON DESTINO A PORTERÍA",
        "BALONES RECUPERADOS 1/4 DE CANCHA",
        "BALONES RECUPERADOS 2/4 DE CANCHA",
        "BALONES RECUPERADOS 3/4 DE CANCHA",
        "BALONES RECUPERADOS 4/4 DE CANCHA",
        "1 VS 1 DEFENSIVOS TOTALES",
        "1 VS 1 EXITOSOS DEFENSIVOS",
        "1VS1 NO EXITOSO DEFENSIVO",
        "TOTAL PASES ACERTADOS",
        "PASES ACERTADOS CANCHA PROPIA 1/4",
        "PASES ACERTADOS CANCHA PROPIA 2/4",
        "PASES ACERTADOS CANCHA RIVAL 3/4",
        "PASES ACERTADOS CANCHA RIVAL 4/4",
        "BALONES PERDIDOS 1/4 DE CANCHA",
        "BALONES PERDIDOS 2/4 DE CANCHA",
        "BALONES PERDIDOS 3/4 DE CANCHA",
        "BALONES PERDIDOS 4/4 DE CANCHA"
    ]

    # === Calcular P90 si jugó al menos 45 minutos
    def calc_p90(row, stat):
            mins = pd.to_numeric(row.get("MINUTOS JUGADOS", 0), errors="coerce")
            val  = pd.to_numeric(row.get(stat, 0), errors="coerce")
            if pd.notna(val) and pd.notna(mins) and mins >= 1 and mins > 0:
                return float(val) / (mins / 90.0)
            return 0.0

    for stat in estadisticas:
        df[f"{stat}_P90"] = df.apply(lambda r, s=stat: calc_p90(r, s), axis=1)

    bd = df.copy()
    bd.to_csv("JORNADA.csv", index=False, encoding="utf-8-sig")

    # 5) Promedios P90 por POSICION (LC y TA) — max por posición (como usas en otros comparativos)
    p90_actual   = bd.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()
    p90_actual.to_csv("P90JORNADA.csv", index=False, encoding="utf-8-sig")

    categorias = pd.read_csv("categorias_por_posicion_y_grupo_utf8.csv")

    categorias["Categoría"] = categorias["Categoría"].str.upper()


    categorias.columns = (
        categorias.columns
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.upper()
    )

    for col in ["POSICION", "GRUPO", "CATEGORIA"]:
        if col in categorias.columns:
            categorias[col] = categorias[col].astype(str).str.strip().str.upper()


    
    # 7) Filtrar Santos
    bd_filtrada = bd[bd["EQUIPO"].astype(str).str.contains("SANTOS LAGUNA", case=False, na=False)].copy()

    jugadores = bd_filtrada["JUGADOR"].dropna().unique()
    if len(jugadores) == 0:
        st.warning("No hay jugadores disponibles para Leagues Cup.")
        st.stop()

    jugador = st.selectbox("Selecciona un jugador", sorted(jugadores), index=0)
    posicion = bd_filtrada.loc[bd_filtrada["JUGADOR"] == jugador, "POSICION"].iloc[0]

    st.markdown(f"""
        <div style="font-size: 20px; color: #444; margin-top: -0.5rem;">
            <strong>Posición:</strong><br>{posicion}
        </div>
    """, unsafe_allow_html=True)

    # 9) Funciones auxiliares
    def obtener_color(valor):
        if valor == 0: return 'white'
        elif valor <= 30: return 'red'
        elif valor <= 50: return 'yellow'
        elif valor <= 75: return 'lightgreen'
        else: return 'green'

    # ===== Graficar por grupo (Jornada/Torneo): P90 – P90JUG – JORNADA/AP25 =====

    # Helper: usar *_P90 si existe
    def col_p90(cat):
        c1 = f"{cat}_P90"
        if c1 in bd.columns:  # jugador tiene esa métrica en P90
            return c1
        if cat in bd.columns: # por si ya viene con _P90 en categorias
            return cat
        return None

    grupos = ["Ofensivo", "Defensivo", "Posesión", "Conducción"]
    etiqueta_barra = "JORNADA" if analisis == "Jornada" else "TORNEO"

    for grupo in grupos:
        st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>{grupo.upper()}</h3>", unsafe_allow_html=True)
        if grupo == "Ofensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los duelos No exitosos, entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Defensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los 1 vs 1 no exitosos entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Conducción":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para las categorías de conducción entre más abajo la barra mejor promedio</em></p>", unsafe_allow_html=True)

        # Categorías del grupo/posición y columnas existentes
        cats = categorias[
            (categorias["POSICION"] == str(posicion).upper()) &
            (categorias["GRUPO"]    == grupo.upper())
        ]["CATEGORIA"].tolist()

        cols = [col_p90(cat) for cat in cats]
        cols = [c for c in cols if c is not None]
        if not cols:
            st.warning("Este jugador no tiene datos P90 para este grupo de métricas.")
            continue

        # Valores del jugador (Jornada/Torneo) solo para esas columnas
        df_izq = bd_filtrada[bd_filtrada["JUGADOR"] == jugador][cols].T.reset_index()
        df_izq.columns = ["Col", "Valor"]
        df_izq["Categoria"] = df_izq["Col"].str.replace("_P90", "", regex=False)

        # Figura
        fig = go.Figure()

        for i, c in enumerate(cols):
            cat = c.replace("_P90", "")

            # P90JUG (jugador) y P90 (referencia por posición)
            v_jug = float(pd.to_numeric(df_izq.loc[df_izq["Col"] == c, "Valor"], errors="coerce").fillna(0).values[0])
            ref   = float(pd.to_numeric(p90_actual.loc[p90_actual["POSICION"] == posicion, c], errors="coerce").fillna(0).values[0]) if c in p90_actual.columns else 0.0

            # % del jugador respecto al P90 de referencia
            pct = (v_jug / ref * 100.0) if ref > 0 else 0.0

            # Barra en porcentaje (al centro, hacia la izquierda)
            fig.add_trace(go.Bar(
                y=[cat], x=[-pct], orientation='h',
                marker_color=obtener_color(pct), text=[f"{pct:.0f}%"],
                textposition="outside", showlegend=(i == 0), width=0.35, name=etiqueta_barra
            ))

            # Textos: P90 (izquierda extrema) y P90JUG (antes del centro)
            fig.add_trace(go.Scatter(
                x=[-180], y=[cat], mode="text", text=[f"{ref:.2f}"],
                textposition="middle right", showlegend=False
            ))
            fig.add_trace(go.Scatter(
                x=[-150], y=[cat], mode="text", text=[f"{v_jug:.2f}"],
                textposition="middle right", showlegend=False
            ))

        # Encabezados (P90 – P90JUG – JORNADA/AP25)
        fig.add_annotation(x=-180, y=len(cols), text="P90", showarrow=False, font=dict(size=13, family="Arial Black"))
        fig.add_annotation(x=-145, y=len(cols), text="P90JUG", showarrow=False, font=dict(size=13, family="Arial Black"))
        fig.add_annotation(x=0,     y=len(cols), text=etiqueta_barra, showarrow=False, font=dict(size=13, family="Arial Black"))

        fig.update_layout(
            barmode='overlay',
            xaxis=dict(showticklabels=False, range=[-200, 40]),
            showlegend=False,
            height=400 + 15 * len(cols)
        )
        fig.add_shape(
            type="line", x0=0, x1=0, y0=-0.5, y1=len(cols) - 0.5,
            line=dict(color="white", width=4), xref="x", yref="y", layer="above"
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    df = pd.read_excel("Matrix Jugadores Torneo.xlsx",header=1)
    df.columns = df.columns.str.upper()

    # === Lista de métricas a convertir a P90
    estadisticas = [
        "CENTROS TOTALES",
        "CENTROS TOTALES GANADOS POR UN COMPAÑERO",
        "1 VS 1 OFENSIVOS TOTALES",
        "1 VS 1 EXITOSOS OFENSIVOS",
        "1VS1 NO EXITOSO OFENSIVO",
        "PARTICIPACIÓN EN GOL",
        "ASISTENCIAS",
        "TIROS A GOL",
        "TIROS A GOL CON DESTINO A PORTERÍA",
        "BALONES RECUPERADOS 1/4 DE CANCHA",
        "BALONES RECUPERADOS 2/4 DE CANCHA",
        "BALONES RECUPERADOS 3/4 DE CANCHA",
        "BALONES RECUPERADOS 4/4 DE CANCHA",
        "1 VS 1 DEFENSIVOS TOTALES",
        "1 VS 1 EXITOSOS DEFENSIVOS",
        "1VS1 NO EXITOSO DEFENSIVO",
        "TOTAL PASES ACERTADOS",
        "PASES ACERTADOS CANCHA PROPIA 1/4",
        "PASES ACERTADOS CANCHA PROPIA 2/4",
        "PASES ACERTADOS CANCHA RIVAL 3/4",
        "PASES ACERTADOS CANCHA RIVAL 4/4",
        "BALONES PERDIDOS 1/4 DE CANCHA",
        "BALONES PERDIDOS 2/4 DE CANCHA",
        "BALONES PERDIDOS 3/4 DE CANCHA",
        "BALONES PERDIDOS 4/4 DE CANCHA"
    ]

    # === Calcular P90 si jugó al menos 45 minutos
    def calc_p90(row, stat):
            mins = pd.to_numeric(row.get("MINUTOS JUGADOS", 0), errors="coerce")
            val  = pd.to_numeric(row.get(stat, 0), errors="coerce")
            if pd.notna(val) and pd.notna(mins) and mins >= 1 and mins > 0:
                return float(val) / (mins / 90.0)
            return 0.0

    for stat in estadisticas:
        df[f"{stat}_P90"] = df.apply(lambda r, s=stat: calc_p90(r, s), axis=1)

    bd = df.copy()
    bd.to_csv("TORNEO.csv", index=False, encoding="utf-8-sig")

    # 5) Promedios P90 por POSICION (LC y TA) — max por posición (como usas en otros comparativos)
    p90_actual   = bd.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()
    p90_actual.to_csv("P90TORNEO.csv", index=False, encoding="utf-8-sig")

    categorias = pd.read_csv("categorias_por_posicion_y_grupo_utf8.csv")

    categorias["Categoría"] = categorias["Categoría"].str.upper()


    categorias.columns = (
        categorias.columns
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.upper()
    )

    for col in ["POSICION", "GRUPO", "CATEGORIA"]:
        if col in categorias.columns:
            categorias[col] = categorias[col].astype(str).str.strip().str.upper()



    # 7) Filtrar Santos
    bd_filtrada = bd[bd["EQUIPO"].astype(str).str.contains("SANTOS LAGUNA", case=False, na=False)].copy()

    jugadores = bd_filtrada["JUGADOR"].dropna().unique()
    if len(jugadores) == 0:
        st.warning("No hay jugadores disponibles para Leagues Cup.")
        st.stop()

    jugador = st.selectbox("Selecciona un jugador", sorted(jugadores), index=0)
    posicion = bd_filtrada.loc[bd_filtrada["JUGADOR"] == jugador, "POSICION"].iloc[0]

    st.markdown(f"""
        <div style="font-size: 20px; color: #444; margin-top: -0.5rem;">
            <strong>Posición:</strong><br>{posicion}
        </div>
    """, unsafe_allow_html=True)

    # 9) Funciones auxiliares
    def obtener_color(valor):
        if valor == 0: return 'white'
        elif valor <= 30: return 'red'
        elif valor <= 50: return 'yellow'
        elif valor <= 75: return 'lightgreen'
        else: return 'green'

    # ===== Graficar por grupo (Jornada/Torneo): P90 – P90JUG – JORNADA/AP25 =====

    # Helper: usar *_P90 si existe
    def col_p90(cat):
        c1 = f"{cat}_P90"
        if c1 in bd.columns:  # jugador tiene esa métrica en P90
            return c1
        if cat in bd.columns: # por si ya viene con _P90 en categorias
            return cat
        return None

    grupos = ["Ofensivo", "Defensivo", "Posesión", "Conducción"]
    etiqueta_barra = "JORNADA" if analisis == "Jornada" else "TORNEO"

    for grupo in grupos:
        st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>{grupo.upper()}</h3>", unsafe_allow_html=True)
        if grupo == "Ofensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los duelos No exitosos, entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Defensivo":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los 1 vs 1 no exitosos entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
        if grupo == "Conducción":
            st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para las categorías de conducción entre más abajo la barra mejor promedio</em></p>", unsafe_allow_html=True)

        # Categorías del grupo/posición y columnas existentes
        cats = categorias[
            (categorias["POSICION"] == str(posicion).upper()) &
            (categorias["GRUPO"]    == grupo.upper())
        ]["CATEGORIA"].tolist()

        cols = [col_p90(cat) for cat in cats]
        cols = [c for c in cols if c is not None]
        if not cols:
            st.warning("Este jugador no tiene datos P90 para este grupo de métricas.")
            continue

        # Valores del jugador (Jornada/Torneo) solo para esas columnas
        df_izq = bd_filtrada[bd_filtrada["JUGADOR"] == jugador][cols].T.reset_index()
        df_izq.columns = ["Col", "Valor"]
        df_izq["Categoria"] = df_izq["Col"].str.replace("_P90", "", regex=False)

        # Figura
        fig = go.Figure()

        for i, c in enumerate(cols):
            cat = c.replace("_P90", "")

            # P90JUG (jugador) y P90 (referencia por posición)
            v_jug = float(pd.to_numeric(df_izq.loc[df_izq["Col"] == c, "Valor"], errors="coerce").fillna(0).values[0])
            ref   = float(pd.to_numeric(p90_actual.loc[p90_actual["POSICION"] == posicion, c], errors="coerce").fillna(0).values[0]) if c in p90_actual.columns else 0.0

            # % del jugador respecto al P90 de referencia
            pct = (v_jug / ref * 100.0) if ref > 0 else 0.0

            # Barra en porcentaje (al centro, hacia la izquierda)
            fig.add_trace(go.Bar(
                y=[cat], x=[-pct], orientation='h',
                marker_color=obtener_color(pct), text=[f"{pct:.0f}%"],
                textposition="outside", showlegend=(i == 0), width=0.35, name=etiqueta_barra
            ))

            # Textos: P90 (izquierda extrema) y P90JUG (antes del centro)
            fig.add_trace(go.Scatter(
                x=[-180], y=[cat], mode="text", text=[f"{ref:.2f}"],
                textposition="middle right", showlegend=False
            ))
            fig.add_trace(go.Scatter(
                x=[-150], y=[cat], mode="text", text=[f"{v_jug:.2f}"],
                textposition="middle right", showlegend=False
            ))

        # Encabezados (P90 – P90JUG – JORNADA/AP25)
        fig.add_annotation(x=-180, y=len(cols), text="P90", showarrow=False, font=dict(size=13, family="Arial Black"))
        fig.add_annotation(x=-145, y=len(cols), text="P90JUG", showarrow=False, font=dict(size=13, family="Arial Black"))
        fig.add_annotation(x=0,     y=len(cols), text=etiqueta_barra, showarrow=False, font=dict(size=13, family="Arial Black"))

        fig.update_layout(
            barmode='overlay',
            xaxis=dict(showticklabels=False, range=[-200, 40]),
            showlegend=False,
            height=400 + 15 * len(cols)
        )
        fig.add_shape(
            type="line", x0=0, x1=0, y0=-0.5, y1=len(cols) - 0.5,
            line=dict(color="white", width=4), xref="x", yref="y", layer="above"
        )

        st.plotly_chart(fig, use_container_width=True)

