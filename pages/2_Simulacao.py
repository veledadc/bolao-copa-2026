"""Página 2 — Simulação Monte Carlo"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import plotly.express as px

from config import COPA_2026_GROUPS, DEFAULT_N_SIMULATIONS, N_BEST_THIRDS
from src import state_manager as sm, monte_carlo as mc
from src import copa_manager as cm
from src.styles import get_css
from src.sidebar import render_sidebar

st.set_page_config(page_title='Simulação MC · Copa 2026', page_icon='🎲', layout='wide')
st.markdown(get_css(), unsafe_allow_html=True)
render_sidebar()


@st.cache_data(show_spinner=False)
def _get_state(_mtime: float):
    return sm.get_or_build_state()

@st.cache_data(show_spinner='Simulando...')
def _run_mc(state_hash: str, n_sims: int):
    state = sm.load_state() or sm.build_default_state()
    return mc.run_simulations(
        COPA_2026_GROUPS, state['elos'], n_sims,
        form=state.get('form', {}), copa_history=state.get('copa_history', {}),
    )


state = _get_state(sm.state_file_mtime())
st.markdown('<h1 style="font-size:1.8rem">🎲 Simulação Monte Carlo</h1>', unsafe_allow_html=True)
st.markdown(
    '<div class="stage-label">Probabilidades calculadas via '
    'Elo + Forma + Histórico Copa</div><br>',
    unsafe_allow_html=True,
)

# Tab: single tournament vs MC
tab1, tab2 = st.tabs(['🎯 Sortear 1 Copa', '📊 Monte Carlo'])

# ── Tab 1: single simulation ──────────────────────────────────────────────────
with tab1:
    st.markdown('Clique para simular **um torneio completo** do zero.')

    if st.button('🎲 Sortear Nova Copa', type='primary'):
        import numpy as np
        np.random.seed(None)
        elos = state['elos']
        form = state.get('form', {})
        copa = state.get('copa_history', {})
        group_res = mc.simulate_group_stage(COPA_2026_GROUPS, elos, form, copa)
        advancing = mc.get_advancing_teams(group_res, N_BEST_THIRDS)
        knockout  = mc.simulate_knockout_stage(advancing, elos, form, copa)
        champion  = next((t for t, s in knockout.items() if 'Campeão' in s), None)
        finalists = [t for t, s in knockout.items() if 'Final' in s or 'Campeão' in s]
        semis     = [t for t, s in knockout.items() if 'Semifinal' in s]
        st.session_state['single_sim'] = {
            'group_res': group_res, 'advancing': advancing,
            'knockout': knockout, 'champion': champion,
            'finalists': finalists, 'semis': semis,
        }

    if st.session_state.get('single_sim'):
        sim   = st.session_state['single_sim']
        champ = sim['champion']
        elos  = state['elos']

        if champ:
            st.success(f'🏆 **Campeão: {champ}** — Elo {round(elos.get(champ, 1500))}')

        finalist_other = [t for t in sim['finalists'] if t != champ]
        semi_others    = [t for t in sim['semis'] if t not in sim['finalists']]

        cols   = st.columns(4)
        labels = ['🥇 Campeão', '🥈 Vice', '🥉 3°/4°', '🥉 3°/4°']
        teams_ = ([champ] + finalist_other + semi_others)[:4]
        for col, lbl, tm in zip(cols, labels, teams_):
            with col:
                st.metric(lbl, tm or '—',
                          delta=f'Elo {round(elos.get(tm, 0))}' if tm else '')

        st.markdown('---')
        st.subheader('Fase de Grupos')
        gcols = st.columns(3)
        for i, (gname, gdata) in enumerate(sim['group_res'].items()):
            with gcols[i % 3]:
                rows = []
                for pos, team in enumerate(gdata['standings'], 1):
                    adv = '✅' if team in sim['advancing'] else '❌'
                    rows.append({
                        '#': pos,
                        'Seleção': f'{adv} {team}',
                        'Pts': gdata['points'][team],
                        'SG':  gdata['goal_diff'][team],
                        'GP':  gdata['goals_for'][team],
                    })
                st.markdown(f'<div class="group-pill">GRUPO {gname}</div>',
                            unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(rows).set_index('#'),
                             use_container_width=True, hide_index=False, height=172)

# ── Tab 2: Monte Carlo ────────────────────────────────────────────────────────
with tab2:
    c_a, c_b = st.columns([1, 3])
    with c_a:
        n_sims = st.number_input('Simulações', 1_000, 50_000, DEFAULT_N_SIMULATIONS, 1_000)
        run_mc = st.button('▶ Rodar Monte Carlo', type='primary', use_container_width=True)

    if run_mc:
        _run_mc.clear()

    probs = None
    if run_mc or st.session_state.get('ran_mc_v2', False):
        with st.spinner(f'Simulando {n_sims:,} torneios...'):
            probs = _run_mc(state['state_hash'], int(n_sims))
        st.session_state['ran_mc_v2'] = True
        if run_mc:
            st.success(f'{n_sims:,} simulações concluídas!')

    if probs:
        df_mc = pd.DataFrame([
            {
                'Seleção':        t,
                'Campeão (%)':    round(v['campeao']   * 100, 1),
                'Final (%)':      round(v['final']      * 100, 1),
                'Semifinal (%)':  round(v['semifinal']  * 100, 1),
                'Quartas (%)':    round(v['quartas']    * 100, 1),
                'Oitavas (%)':    round(v['oitavas']    * 100, 1),
            }
            for t, v in sorted(probs.items(), key=lambda x: x[1]['campeao'], reverse=True)
        ])
        fig = px.bar(
            df_mc.head(20), x='Seleção', y='Campeão (%)',
            color='Campeão (%)', color_continuous_scale=['#1a3a6a','#0055e5','#c9a902'],
            text='Campeão (%)',
            title='Top 20 Favoritos ao Título (%)', height=440,
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#d8e2ef', title_font_color='#c9a902',
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_mc.set_index('Seleção'), use_container_width=True, height=520)
    else:
        st.info('Clique em **Rodar Monte Carlo** para gerar probabilidades.')
