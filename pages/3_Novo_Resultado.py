"""Página 3 — Cadastrar Novo Resultado (com atualização incremental O(1))"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
from datetime import date

from config import COPA_2026_GROUPS, K_FACTORS
from src import data_loader, state_manager as sm
from src.features import form_summary, team_feature_summary
from src.styles import get_css

st.set_page_config(page_title='Novo Resultado · Bolão 2026', page_icon='➕',
                   layout='centered', initial_sidebar_state='expanded')
st.markdown(get_css(), unsafe_allow_html=True)
st.title('➕ Cadastrar Novo Resultado')
st.markdown(
    'Ao salvar, o **Elo**, a **forma recente** e o **histórico de Copa** '
    'são atualizados em tempo real sem reprocessar o histórico completo.'
)


@st.cache_data(show_spinner='Carregando estado...')
def _get_state():
    return sm.get_or_build_state()


state     = _get_state()
all_teams = sorted(set(
    t for teams in COPA_2026_GROUPS.values() for t in teams
))

tournament_options = list(K_FACTORS.keys())

# ── Formulário ────────────────────────────────────────────────────────────────
with st.form('form_resultado', clear_on_submit=True):
    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        match_date = st.date_input('Data', value=date.today())
    with c2:
        home_team  = st.selectbox('Mandante',  all_teams,
                                   index=all_teams.index('Brazil') if 'Brazil' in all_teams else 0)
    with c3:
        away_team  = st.selectbox('Visitante', all_teams,
                                   index=all_teams.index('Argentina') if 'Argentina' in all_teams else 1)

    c4, c5 = st.columns(2)
    with c4:
        home_score = st.number_input('Gols Mandante',  min_value=0, max_value=20, value=1)
    with c5:
        away_score = st.number_input('Gols Visitante', min_value=0, max_value=20, value=0)

    tournament = st.selectbox('Competição', tournament_options)
    neutral    = st.checkbox('Campo Neutro', value=True)

    submitted = st.form_submit_button('💾 Salvar e Atualizar Modelo', type='primary',
                                       use_container_width=True)

if submitted:
    if home_team == away_team:
        st.error('Mandante e visitante não podem ser o mesmo time.')
    else:
        # 1. Persiste no CSV
        data_loader.save_manual_result(
            match_date=match_date, home_team=home_team, away_team=away_team,
            home_score=int(home_score), away_score=int(away_score),
            tournament=tournament, neutral=neutral,
        )

        # 2. Atualização incremental do estado (O(1))
        current_state = sm.load_state() or sm.get_or_build_state()
        old_elo_h = round(current_state['elos'].get(home_team, 1500))
        old_elo_a = round(current_state['elos'].get(away_team, 1500))

        new_state = sm.apply_result(
            current_state, home_team, away_team,
            int(home_score), int(away_score),
            tournament, bool(neutral),
        )
        sm.save_state(new_state)

        # 3. Invalida caches de Streamlit
        _get_state.clear()
        st.session_state['state_dirty']  = True
        st.session_state['sim_probs']    = None
        st.session_state['simulation_results'] = None

        # 4. Feedback visual
        placar = f'{home_team} {int(home_score)} × {int(away_score)} {away_team}'
        new_elo_h = round(new_state['elos'].get(home_team, 1500))
        new_elo_a = round(new_state['elos'].get(away_team, 1500))

        st.success(f'✅ **{placar}** salvo! Elo atualizado sem reprocessar histórico.')

        col1, col2 = st.columns(2)
        with col1:
            st.metric(home_team, new_elo_h, delta=new_elo_h - old_elo_h)
        with col2:
            st.metric(away_team, new_elo_a, delta=new_elo_a - old_elo_a)

        st.info('Acesse **Simulação** ou **Campeões** para ver as probabilidades atualizadas.')

# ── Pré-visualização dos times selecionados ───────────────────────────────────
st.markdown('---')
st.subheader('📊 Comparativo dos Times Selecionados')

state_now = sm.load_state() or state
col_a, col_b = st.columns(2)

for col, team in [(col_a, home_team), (col_b, away_team)]:
    feat = team_feature_summary(team, state_now['elos'],
                                 state_now.get('form', {}),
                                 state_now.get('copa_history', {}))
    with col:
        st.markdown(f'**{team}**')
        st.metric('Elo Base',     feat['elo'])
        st.metric('Elo Efetivo',  feat['effective_elo'],
                  delta=feat['effective_elo'] - feat['elo'])
        st.metric('Forma L5',     feat['form_l5'] or '—')
        st.metric('Histórico Copa', f"{feat['copa_wr']}% ({feat['copa_matches']} j.)")

# ── Resultados manuais cadastrados ────────────────────────────────────────────
st.markdown('---')
st.subheader('📋 Resultados Manuais Cadastrados')

manual_df = data_loader.load_manual_results()
if manual_df.empty:
    st.info('Nenhum resultado manual cadastrado ainda.')
else:
    df_show = manual_df.copy()
    df_show['Placar'] = (df_show['home_team'] + ' ' + df_show['home_score'].astype(str)
                         + ' × ' + df_show['away_score'].astype(str) + ' ' + df_show['away_team'])
    st.dataframe(
        df_show[['date', 'Placar', 'tournament', 'neutral']].rename(
            columns={'date': 'Data', 'tournament': 'Competição', 'neutral': 'Neutro'}),
        use_container_width=True,
    )

    with st.expander('🗑️ Remover resultado manual'):
        idx = st.number_input('Índice (0-based)', 0, max(0, len(manual_df)-1), 0)
        if st.button('Remover', type='secondary'):
            data_loader.delete_manual_result(idx)
            _get_state.clear()
            st.session_state['state_dirty'] = True
            st.success('Removido. Recarregue a página.')
