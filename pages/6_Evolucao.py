"""
Página 6 — Evolução do Elo e das Probabilidades
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import plotly.express as px

from config import COPA_2026_GROUPS, DEFAULT_ELO_RATINGS
from src import data_loader, elo as elo_mod
from src.styles import get_css

st.set_page_config(page_title='Evolução · Bolão 2026', page_icon='📈',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown(get_css(), unsafe_allow_html=True)
st.title('📈 Evolução do Elo Rating')

df_all = data_loader.get_all_results()

if df_all.empty:
    st.warning(
        'Sem dados históricos para traçar evolução. '
        'Execute `python scripts/download_data.py` para baixar o histórico.'
    )
    st.stop()

# ------------------------------------------------------------------
all_copa_teams = sorted({t for teams in COPA_2026_GROUPS.values() for t in teams})

selected_teams = st.multiselect(
    'Selecione seleções',
    all_copa_teams,
    default=['Brazil', 'Argentina', 'France', 'Germany', 'England'],
)

if not selected_teams:
    st.info('Selecione ao menos uma seleção.')
    st.stop()

col1, col2 = st.columns(2)
with col1:
    year_start = st.slider('A partir de', 1990, 2020, 2000)
with col2:
    smoothing = st.slider('Suavização (nº de jogos)', 0, 20, 5)

# ------------------------------------------------------------------
@st.cache_data(show_spinner='Calculando histórico de Elo...')
def get_history(teams_key: str, year: int):
    teams = list(teams_key.split('|'))
    df = data_loader.get_all_results()
    df = df[df['date'].dt.year >= year]
    return elo_mod.calculate_elo_history(df, teams=teams)


teams_key = '|'.join(sorted(selected_teams))
df_hist = get_history(teams_key, year_start)

if df_hist.empty:
    st.warning('Sem dados para os filtros selecionados.')
    st.stop()

# Suavização com rolling average
if smoothing > 1:
    df_hist = (
        df_hist
        .sort_values(['team', 'date'])
        .assign(elo=lambda d: d.groupby('team')['elo']
                .transform(lambda x: x.rolling(smoothing, min_periods=1).mean()))
    )

# ------------------------------------------------------------------
tab1, tab2 = st.tabs(['📈 Linha do Tempo', '📊 Variação Anual'])

with tab1:
    fig = px.line(
        df_hist,
        x='date',
        y='elo',
        color='team',
        title='Evolução do Elo Rating ao longo do tempo',
        labels={'date': 'Data', 'elo': 'Elo Rating', 'team': 'Seleção'},
        height=500,
    )
    fig.add_hline(y=1500, line_dash='dash', line_color='lightgray',
                  annotation_text='Média (1500)')
    fig.update_layout(hovermode='x unified', legend_title='Seleção')
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    df_annual = (
        df_hist
        .assign(year=df_hist['date'].dt.year)
        .groupby(['team', 'year'])['elo']
        .last()
        .reset_index()
    )

    fig2 = px.line(
        df_annual,
        x='year',
        y='elo',
        color='team',
        markers=True,
        title='Elo ao Final de Cada Ano',
        labels={'year': 'Ano', 'elo': 'Elo Rating', 'team': 'Seleção'},
        height=450,
    )
    fig2.add_hline(y=1500, line_dash='dash', line_color='lightgray')
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# Últimos jogos de cada seleção
# ------------------------------------------------------------------
st.markdown('---')
st.subheader('🔍 Últimos Jogos')

sel_detail = st.selectbox('Seleção', selected_teams)
df_team = df_all[
    (df_all['home_team'] == sel_detail) | (df_all['away_team'] == sel_detail)
].sort_values('date', ascending=False).head(20)

df_show = df_team.copy()
df_show['Placar'] = (
    df_show['home_team'] + ' ' +
    df_show['home_score'].astype(str) + ' x ' +
    df_show['away_score'].astype(str) + ' ' +
    df_show['away_team']
)
st.dataframe(
    df_show[['date', 'Placar', 'tournament']].rename(
        columns={'date': 'Data', 'tournament': 'Competição'}
    ),
    use_container_width=True,
)
