"""Página 5 — Ranking Elo com forma recente e histórico de Copa"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import plotly.express as px

from config import TEAM_CONFEDERATION, CONFEDERATION_COLORS
from src import state_manager as sm
from src.features import team_feature_summary
from src.elo import win_probability
from src.styles import get_css

st.set_page_config(page_title='Ranking Elo · Copa 2026', page_icon='📊', layout='wide')
st.markdown(get_css(), unsafe_allow_html=True)
st.markdown('<h1 style="font-size:1.8rem">📊 Ranking Elo das Seleções</h1>', unsafe_allow_html=True)
st.markdown(
    'Elo base + ajuste de **Forma Recente** (±30 pts) + **Histórico de Copa** (±12 pts) '
    '= **Elo Efetivo** usado nas simulações.'
)


@st.cache_data(show_spinner='Carregando estado...')
def _get_state():
    return sm.get_or_build_state()


state = _get_state()
elos  = state['elos']
form  = state.get('form', {})
copa  = state.get('copa_history', {})

# ── Constrói tabela de ranking ────────────────────────────────────────────────
rows = []
for team, elo in sorted(elos.items(), key=lambda x: x[1], reverse=True):
    feat = team_feature_summary(team, elos, form, copa)
    conf = TEAM_CONFEDERATION.get(team, 'Other')
    rows.append({
        'Seleção':       team,
        'Conf.':         conf,
        'Elo Base':      feat['elo'],
        'Forma (L5)':    feat['form_l5'] or '—',
        'Bônus Forma':   feat['form_bonus'],
        'Copa W%':       f"{feat['copa_wr']}%",
        'Bônus Copa':    feat['copa_bonus'],
        'Elo Efetivo':   feat['effective_elo'],
    })

df_rank = pd.DataFrame(rows).reset_index(drop=True)
df_rank.index += 1
df_rank['Tier'] = pd.cut(
    df_rank['Elo Efetivo'],
    bins=[0, 1550, 1650, 1750, 1850, 1950, 9999],
    labels=['★☆☆☆', '★★☆☆', '★★★☆', '★★★★', '★★★★+', '⭐ Elite'],
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(['📊 Gráfico', '📋 Tabela Completa', '🔍 Comparar'])

# ── Tab 1: Gráfico ────────────────────────────────────────────────────────────
with tab1:
    conf_opts = ['Todas'] + sorted(df_rank['Conf.'].unique().tolist())
    sel_conf  = st.selectbox('Confederação', conf_opts)
    df_plt    = df_rank if sel_conf == 'Todas' else df_rank[df_rank['Conf.'] == sel_conf]
    df_plt    = df_plt.head(30)

    fig = px.bar(
        df_plt, x='Elo Efetivo', y='Seleção',
        orientation='h',
        color='Conf.', color_discrete_map=CONFEDERATION_COLORS,
        text='Elo Efetivo',
        title=f'Elo Efetivo — {sel_conf}',
        height=max(420, len(df_plt) * 24),
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'},
                      margin=dict(l=10, r=90, t=40, b=10))
    fig.add_vline(x=1500, line_dash='dash', line_color='lightgray',
                  annotation_text='Base 1500')
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Tabela Completa ────────────────────────────────────────────────────
with tab2:
    search = st.text_input('🔍 Buscar seleção')
    df_tbl = df_rank if not search else df_rank[df_rank['Seleção'].str.contains(search, case=False)]
    st.dataframe(df_tbl, use_container_width=True, height=580)

# ── Tab 3: Comparador ─────────────────────────────────────────────────────────
with tab3:
    from config import COPA_2026_GROUPS as _GROUPS
    copa_teams = sorted({t for gp in _GROUPS.values() for t in gp})
    sel_teams  = st.multiselect(
        'Seleções para comparar', copa_teams,
        default=['Argentina', 'Brazil', 'France', 'England', 'Germany'],
    )

    if sel_teams:
        # Matriz de probabilidade de vitória
        st.subheader('Probabilidade de vitória (linha vence coluna)')
        mat = {}
        for ta in sel_teams:
            mat[ta] = {}
            for tb in sel_teams:
                if ta == tb:
                    mat[ta][tb] = '—'
                else:
                    ea = elos.get(ta, 1500)
                    eb = elos.get(tb, 1500)
                    p  = win_probability(ea, eb, neutral=True)
                    mat[ta][tb] = f'{p*100:.1f}%'
        st.dataframe(pd.DataFrame(mat).T, use_container_width=True)

        # Features dos times selecionados
        st.subheader('Features detalhadas')
        feat_rows = []
        for team in sel_teams:
            feat = team_feature_summary(team, elos, form, copa)
            feat_rows.append({'Seleção': team, **feat})
        st.dataframe(pd.DataFrame(feat_rows).set_index('Seleção'),
                     use_container_width=True)
