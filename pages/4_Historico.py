"""
Página 4 — Histórico de Partidas
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd

from src import data_loader
from src.styles import get_css

st.set_page_config(page_title='Histórico · Bolão 2026', page_icon='📋',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown(get_css(), unsafe_allow_html=True)
st.title('📋 Histórico de Partidas')


@st.cache_data(show_spinner='Carregando partidas...')
def load():
    return data_loader.get_all_results()


df = load()

if df.empty:
    st.warning(
        'Nenhum dado histórico encontrado. Execute `python scripts/download_data.py` '
        'para baixar o histórico completo.'
    )
    st.stop()

# ------------------------------------------------------------------
# Filtros
# ------------------------------------------------------------------
st.sidebar.header('Filtros')

all_teams = sorted(set(df['home_team'].tolist() + df['away_team'].tolist()))
selected_team = st.sidebar.selectbox('Seleção', ['Todas'] + all_teams)

year_min = int(df['date'].dt.year.min())
year_max = int(df['date'].dt.year.max())
year_range = st.sidebar.slider('Período', year_min, year_max, (max(year_min, 2010), year_max))

tournaments = sorted(df['tournament'].dropna().unique().tolist())
selected_tournament = st.sidebar.selectbox('Competição', ['Todas'] + tournaments)

# ------------------------------------------------------------------
# Filtragem
# ------------------------------------------------------------------
mask = (
    (df['date'].dt.year >= year_range[0]) &
    (df['date'].dt.year <= year_range[1])
)

if selected_team != 'Todas':
    mask &= (df['home_team'] == selected_team) | (df['away_team'] == selected_team)

if selected_tournament != 'Todas':
    mask &= df['tournament'] == selected_tournament

df_filtered = df[mask].copy()
df_filtered = df_filtered.sort_values('date', ascending=False).reset_index(drop=True)

st.markdown(f'**{len(df_filtered):,} partidas** encontradas.')

# ------------------------------------------------------------------
# Tabela
# ------------------------------------------------------------------
df_show = df_filtered.copy()
df_show['Placar'] = (
    df_show['home_team'] + ' ' +
    df_show['home_score'].astype(str) + ' x ' +
    df_show['away_score'].astype(str) + ' ' +
    df_show['away_team']
)
df_show = df_show[['date', 'Placar', 'tournament', 'neutral', 'city', 'country']].rename(columns={
    'date': 'Data',
    'tournament': 'Competição',
    'neutral': 'Neutro',
    'city': 'Cidade',
    'country': 'País',
})

PAGE_SIZE = 100
total_pages = max(1, (len(df_show) - 1) // PAGE_SIZE + 1)
page = st.number_input('Página', 1, total_pages, 1)
start = (page - 1) * PAGE_SIZE
end = start + PAGE_SIZE

st.dataframe(df_show.iloc[start:end], use_container_width=True, height=550)
st.caption(f'Página {page} de {total_pages} | {len(df_show):,} resultados')

# ------------------------------------------------------------------
# Stats rápidas
# ------------------------------------------------------------------
if selected_team != 'Todas' and not df_filtered.empty:
    st.markdown('---')
    st.subheader(f'📊 Estatísticas — {selected_team}')

    home_mask = df_filtered['home_team'] == selected_team
    away_mask = df_filtered['away_team'] == selected_team

    df_home = df_filtered[home_mask]
    df_away = df_filtered[away_mask]

    w = ((df_home['home_score'] > df_home['away_score']).sum() +
         (df_away['away_score'] > df_away['home_score']).sum())
    d = ((df_home['home_score'] == df_home['away_score']).sum() +
         (df_away['away_score'] == df_away['home_score']).sum())
    l = len(df_filtered) - w - d

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Jogos', len(df_filtered))
    c2.metric('Vitórias', w)
    c3.metric('Empates', d)
    c4.metric('Derrotas', l)
