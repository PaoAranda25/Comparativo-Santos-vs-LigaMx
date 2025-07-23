import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import openpyxl


# === Cargar archivo Excel
df = pd.read_excel("Matrix Jugadores AP25.xlsx",header=1)
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
for stat in estadisticas:
    df[f"{stat}_P90"] = df.apply(
        lambda row: row[stat] / (row["MINUTOS JUGADOS"] / 90)
        if pd.notna(row[stat]) and row["MINUTOS JUGADOS"] >= 1 else 0,
        axis=1
    )



# === Dividir Santos y resto del torneo
santos = df[df["EQUIPO"].str.contains("Santos Laguna", case=False, na=False)].copy()
print(santos)
santos.to_csv("SANTOS.csv", index=False, encoding="utf-8-sig")
resto = df.copy()
print(resto)
resto.to_csv("RESTO.csv", index=False, encoding="utf-8-sig")


# === Promedio por posición (resto del torneo)
p90_santos = santos.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].max().reset_index()
print(p90_santos)
p90_santos.to_csv("P90SANTOS.csv", index=False, encoding="utf-8-sig")

p90_resto = resto.groupby("POSICION")[[f"{e}_P90" for e in estadisticas]].mean().reset_index()
print(p90_resto)
p90_resto.to_csv("P90RESTO.csv", index=False, encoding="utf-8-sig")


# ========== STREAMLIT =========
# Mostrarlo arriba a la izquierda
st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>Comparativo CL25 vs AP24</h3>", unsafe_allow_html=True)


bd = pd.read_csv("SANTOS.csv")
bdap24 = pd.read_csv("RESTO.csv")
p90cl25 = pd.read_csv("P90SANTOS.csv")
p90ap24 = pd.read_csv("P90RESTO.csv")
categorias = pd.read_csv("categorias_por_posicion_y_grupo_utf8.csv")

categorias["Categoría"] = categorias["Categoría"].str.upper()


print( bd)



jugadores = bd["JUGADOR"].unique()


if len(jugadores) > 0:
    jugador = st.selectbox("Selecciona un jugador", jugadores, index=0)
    posicion = bd[bd["JUGADOR"] == jugador]["POSICION"].values[0]
    st.markdown(f"""
    <div style="font-size: 20px; color: #444; margin-top: -0.5rem;">
        <strong>Posición:</strong><br>{posicion}
    </div>
""", unsafe_allow_html=True)
else:
    st.warning("No hay jugadores disponibles para esta jornada.")
    st.stop() 


# Función de color
def obtener_color(valor):
    if valor == 0:
        return 'white'
    elif valor <= 30:
        return 'red'
    elif valor <= 50:
        return 'yellow'
    elif valor <= 75:
        return 'lightgreen'
    else:
        return 'green'

# Mostrar por grupo
grupos = ["Ofensivo", "Defensivo", "Posesión", "Conducción"]

for grupo in grupos:
    st.markdown(f"<h3 style='text-align: center; padding: 0.3em'>{grupo.upper()}</h3>", unsafe_allow_html=True)

    if grupo == "Ofensivo":
        st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los duelos No exitosos, entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
    elif grupo == "Defensivo":
        st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para los 1 vs 1 no exitosos entre más baja la barra, mejor promedio</em></p>", unsafe_allow_html=True)
    elif grupo == "Conducción":
        st.markdown("<p style='text-align: center; font-size: 13px'><em>*Para las categorías de conducción entre más abajo la barra mejor promedio</em></p>", unsafe_allow_html=True)

    # === Procesar categorías del grupo
    cat_grupo = categorias[
        (categorias["Posición"].str.upper() == posicion.upper()) &
        (categorias["Grupo"].str.upper() == grupo.upper())
    ]["Categoría"].tolist()

    # Convertir a mayúsculas y agregar _P90
    cat_grupo = [f"{cat.upper()}_P90" for cat in cat_grupo]

    # Verificar que existan en todos los DataFrames
    cat_grupo_existentes = [
        cat for cat in cat_grupo
        if cat in bd.columns and cat in p90ap24.columns and cat in p90cl25.columns
    ]

    cat_grupo_existentes = [cat for cat in cat_grupo if cat in bd.columns and cat in p90ap24.columns and cat in p90cl25.columns]


    if not cat_grupo_existentes:
        st.warning("Este jugador no tiene datos para este grupo de métricas.")
        continue

    # Datos jugador (Santos)
    df_izq = bd[bd["JUGADOR"] == jugador][cat_grupo_existentes].T.reset_index()
    df_izq.columns = ["Categoría", "Valor"]

    # Datos promedio por posición
    if posicion in p90ap24["POSICION"].values:
        df_der = p90ap24[p90ap24["POSICION"] == posicion][cat_grupo_existentes].T.reset_index()
        df_der.columns = ["Categoría", "Valor"]
    else:
        df_der = pd.DataFrame({"Categoría": cat_grupo_existentes, "Valor": [0]*len(cat_grupo_existentes)})

    # Gráfico
    fig = go.Figure()

for i, cat in enumerate(cat_grupo_existentes):
    real_val_jugador = float(df_izq.loc[df_izq["Categoría"] == cat, "Valor"].values[0])
    real_val_promedio = float(df_der.loc[df_der["Categoría"] == cat, "Valor"].values[0])

    val_jugador = (real_val_jugador / real_val_promedio) * 100 if real_val_promedio > 0 else 0
    val_promedio = 100

    fig.add_trace(go.Bar(
        y=[cat], x=[-val_jugador], orientation='h',
        marker_color=obtener_color(val_jugador), text=[f"{real_val_jugador:.0f}"],
        textposition="outside", showlegend=(i == 0), width=0.35, name="Jugador"
    ))

    fig.add_trace(go.Bar(
        y=[cat], x=[val_promedio], orientation='h',
        marker_color=obtener_color(val_promedio), text=[f"{real_val_promedio:.0f}"],
        textposition="outside", showlegend=(i == 0), width=0.35, name="Promedio posición"
    ))


    fig.add_annotation(x=-120, y=len(cat_grupo_existentes), text="P90", showarrow=False, font=dict(size=13,family="Arial Black"))
    fig.add_annotation(x=0, y=len(cat_grupo_existentes), text="Jugador     Jornada", showarrow=False, font=dict(size=13,family="Arial Black"))
    fig.add_annotation(x=120, y=len(cat_grupo_existentes), text="P90", showarrow=False, font=dict(size=13,family="Arial Black"))

    fig.update_layout(
        barmode='overlay',
        xaxis=dict(showticklabels=False, range=[-180, 180]),
        showlegend=False,
        height=400 + 15 * len(cat_grupo_existentes)
    )
    fig.add_shape(
        type="line", x0=0, x1=0,
        y0=-0.5, y1=len(cat_grupo_existentes) - 0.5,
        line=dict(color="white", width=4),
        xref="x", yref="y", layer="above"
    )

    st.plotly_chart(fig, use_container_width=True)
