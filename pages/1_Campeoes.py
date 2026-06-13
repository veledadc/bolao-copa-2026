"""Página 1 — Probabilidades de Título por fase"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import COPA_2026_GROUPS, DEFAULT_N_SIMULATIONS, TEAM_CONFEDERATION, CONFEDERATION_COLORS
from src import state_manager as sm, monte_carlo as mc
from src.features import team_feature_summary
from src.styles import get_css

st.set_page_config(page_title='Probabilidades · Copa 2026', page_icon='🏆', layout='wide')
st.markdown(get_css(), unsafe_allow_html=True)
st.markdown('<h1 style="font-size:1.8rem">🏆 Probabilidades por Fase</h1>', unsafe_allow_html=True)


@st.cache_data(show_spinner='Simulando torneios...')
def _run_sim(state_hash: str, n_sims: int):
    state = sm.load_state() or sm.build_default_state()
    return mc.run_simulations(
        COPA_2026_GROUPS, state['elos'], n_sims,
        form=state.get('form', {}),
        copa_history=state.get('copa_history', {}),
    )


# Sidebar
with st.sidebar:
    n_sims  = st.slider('Simulações', 1_000, 20_000, DEFAULT_N_SIMULATIONS, 1_000)
    run_btn = st.button('▶ Rodar Simulação', type='primary', use_container_width=True)

state = sm.load_state() or sm.build_default_state()
if run_btn:
    _run_sim.clear()

with st.spinner(f'Executando {n_sims:,} simulações...'):
    probs = _run_sim(state['state_hash'], n_sims)

# ── Tabela mestre ─────────────────────────────────────────────────────────────
rows = []
for team, vals in probs.items():
    feat = team_feature_summary(team, state['elos'], state.get('form', {}),
                                 state.get('copa_history', {}))
    conf = TEAM_CONFEDERATION.get(team, 'Other')
    rows.append({
        'Seleção':        team,
        'Conf.':          conf,
        'Elo Efetivo':    feat['effective_elo'],
        'Forma (L5)':     feat['form_l5'],
        'Campeão':        vals['campeao'],
        'Final':          vals['final'],
        'Semifinal':      vals['semifinal'],
        'Quartas':        vals['quartas'],
        'Oitavas':        vals['oitavas'],
        'Rodada de 32':   vals.get('rodada32', vals.get('grupo', 0)),
    })

df = (pd.DataFrame(rows)
      .sort_values('Campeão', ascending=False)
      .reset_index(drop=True))
df.index += 1

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(['📊 Gráfico', '📋 Tabela', '🌍 Confederações', '⚡ Força Real'])

# ── Tab 1: Gráfico ────────────────────────────────────────────────────────────
with tab1:
    top_n  = st.slider('Top N times', 5, 48, 20, key='top_n')
    df_plt = df.head(top_n).copy()
    stages = ['Campeão', 'Final', 'Semifinal', 'Quartas', 'Oitavas']
    colors = ['#FFD700', '#C0C0C0', '#CD7F32', '#4472C4', '#70AD47']

    fig = go.Figure()
    for stage, color in zip(stages, colors):
        fig.add_trace(go.Bar(
            name=stage, y=df_plt['Seleção'],
            x=df_plt[stage] * 100,
            orientation='h', marker_color=color,
            text=[f'{v*100:.1f}%' for v in df_plt[stage]],
            textposition='inside',
        ))
    fig.update_layout(
        barmode='group',
        title='Probabilidade de Alcançar Cada Fase (%)',
        xaxis_title='Probabilidade (%)',
        yaxis={'categoryorder': 'array',
               'categoryarray': df_plt['Seleção'].tolist()[::-1]},
        height=max(420, top_n * 28),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Tabela ─────────────────────────────────────────────────────────────
with tab2:
    search = st.text_input('🔍 Filtrar seleção')
    df_tbl = df if not search else df[df['Seleção'].str.contains(search, case=False)]
    df_show = df_tbl.copy()
    for col in ['Campeão', 'Final', 'Semifinal', 'Quartas', 'Oitavas', 'Rodada de 32']:
        df_show[col] = df_show[col].apply(lambda x: f'{x*100:.1f}%')
    st.dataframe(df_show, use_container_width=True, height=580)

# ── Tab 3: Confederações ──────────────────────────────────────────────────────
with tab3:
    conf_sel = st.selectbox('Confederação', ['Todas'] + sorted(df['Conf.'].unique()))
    df_c = df if conf_sel == 'Todas' else df[df['Conf.'] == conf_sel]
    fig2 = px.treemap(
        df_c, path=['Conf.', 'Seleção'],
        values=df_c['Campeão'] * 100,
        color='Campeão', color_continuous_scale='RdYlGn',
        title='Probabilidade de Título por Confederação (%)',
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Tab 4: Força Real (Elo Efetivo) ───────────────────────────────────────────
with tab4:
    st.markdown('**Elo Efetivo** = Elo base + bônus de Forma Recente + bônus de Histórico Copa.')
    df_eff = df[['Seleção', 'Conf.', 'Elo Efetivo', 'Forma (L5)']].copy()

    all_elos  = {t: state['elos'].get(t, 1500) for t in df['Seleção']}
    df_eff['Elo Base']     = df_eff['Seleção'].map(all_elos)
    df_eff['Δ Efetivo']    = df_eff['Elo Efetivo'] - df_eff['Elo Base']
    df_eff = df_eff.sort_values('Elo Efetivo', ascending=False).reset_index(drop=True)
    df_eff.index += 1

    fig3 = px.scatter(
        df_eff, x='Elo Base', y='Elo Efetivo',
        color='Conf.', color_discrete_map=CONFEDERATION_COLORS,
        text='Seleção', hover_data=['Forma (L5)', 'Δ Efetivo'],
        title='Elo Base vs Elo Efetivo (forma + Copa history)',
        height=500,
    )
    fig3.add_shape(type='line', x0=1400, y0=1400, x1=2100, y1=2100,
                   line=dict(dash='dash', color='lightgray'))
    fig3.update_traces(textposition='top center', textfont_size=9)
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(df_eff, use_container_width=True, height=400)
