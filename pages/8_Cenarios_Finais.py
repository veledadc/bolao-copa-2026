"""
Cenários das Finais — 5 simulações detalhadas + análise de probabilidades
para Semifinais, Disputa de 3º e Final da Copa 2026.
"""
import sys, os, json, hashlib, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter, defaultdict

from config import COPA_2026_GROUPS, DEFAULT_N_SIMULATIONS, N_BEST_THIRDS
from src import state_manager as sm, monte_carlo as mc
from src import copa_manager as cm
from src.copa_manager import TEAM_FLAGS
from src.styles import get_css
from src.sidebar import render_sidebar

st.set_page_config(page_title='Cenários das Finais · Copa 2026', page_icon='🔮',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown(get_css(), unsafe_allow_html=True)
render_sidebar()

# ── Helpers ────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_state(_mtime: float):
    return sm.get_or_build_state()

@st.cache_data(show_spinner=False)
def _run_scenarios(cache_key: str, n_sims: int, adj_elos_json: str = '') -> list:
    state = sm.load_state() or sm.build_default_state()
    elos  = dict(json.loads(adj_elos_json)) if adj_elos_json else state['elos']
    return mc.run_bracket_scenarios(
        COPA_2026_GROUPS, elos, n_simulations=n_sims,
        form=state.get('form', {}), copa_history=state.get('copa_history', {}),
    )


def _match_key(a: str, b: str) -> str:
    return ' × '.join(sorted([a, b]))


def _unpack_score(score_data):
    """Unpack score tuple (3 or 5 elements) → (ga, gb, pens, pen_a, pen_b)."""
    if len(score_data) >= 5:
        return score_data[0], score_data[1], score_data[2], score_data[3], score_data[4]
    return score_data[0], score_data[1], score_data[2], 0, 0


def _best_score_for_pair(scens: list, match_f: str, score_f: str, pair_str: str):
    """Most common score for a specific pair in a single match (final or third)."""
    p1, p2 = pair_str.split(' × ')
    tally: Counter = Counter()
    total = 0
    for s in scens:
        score_data = s.get(score_f)
        if score_data is None:
            continue
        ta, tb, _ = s[match_f]
        if {ta, tb} != {p1, p2}:
            continue
        ga, gb, pens, pen_a, pen_b = _unpack_score(score_data)
        total += 1
        if ta == p1:
            key = (p1, ga, gb, pens, pen_a, pen_b, p2)
        else:
            key = (p1, gb, ga, pens, pen_b, pen_a, p2)
        tally[key] += 1
    if not tally:
        return None
    top, cnt = tally.most_common(1)[0]
    return top, cnt, total


def _best_score_for_sf_pair(scens: list, pair_str: str):
    """Most common score for a pair appearing in either SF1 or SF2."""
    p1, p2 = pair_str.split(' × ')
    tally: Counter = Counter()
    total = 0
    for s in scens:
        for mf, sf in (('sf1', 'sf1_score'), ('sf2', 'sf2_score')):
            score_data = s.get(sf)
            if score_data is None:
                continue
            ta, tb, _ = s[mf]
            if {ta, tb} != {p1, p2}:
                continue
            ga, gb, pens, pen_a, pen_b = _unpack_score(score_data)
            total += 1
            if ta == p1:
                key = (p1, ga, gb, pens, pen_a, pen_b, p2)
            else:
                key = (p1, gb, ga, pens, pen_b, pen_a, p2)
            tally[key] += 1
    if not tally:
        return None
    top, cnt = tally.most_common(1)[0]
    return top, cnt, total


def _score_badge(p1: str, ga: int, gb: int, pens: bool, pen_a: int, pen_b: int,
                 p2: str, cnt: int, tot: int) -> str:
    if pens and (pen_a or pen_b):
        pens_s = f' <span style="font-size:.7rem;color:#6b8aa8">({pen_a}–{pen_b} nos pênaltis)</span>'
    elif pens:
        pens_s = ' <span style="font-size:.7rem;color:#6b8aa8">(pênaltis)</span>'
    else:
        pens_s = ''
    pct = cnt / tot * 100 if tot > 0 else 0
    return (
        f'<div style="background:#060f1c;border-radius:6px;padding:.5rem;margin-top:.4rem">'
        f'<span style="color:#5a8aa8;font-size:.68rem">Placar mais provável</span><br>'
        f'<strong style="color:#d8e2ef;font-size:.88rem">'
        f'{p1} <span style="color:#c9a902">{ga} × {gb}</span> {p2}</strong>'
        f'{pens_s}<br>'
        f'<span style="color:#3a5a78;font-size:.68rem">({pct:.0f}% das ocorrências)</span>'
        f'</div>'
    )


def _elo_score_html(team_a: str, team_b: str, elos: dict) -> str:
    """ELO-derived most likely score (Poisson mode) — always returns a value."""
    from src.elo import win_probability
    ea = elos.get(team_a, 1500)
    eb = elos.get(team_b, 1500)
    prob_a  = win_probability(ea, eb, neutral=True)
    share_a = max(0.2, min(0.8, 0.5 + (prob_a - 0.5) * 0.6))
    ga = int(max(0.45, 2.3 * share_a))
    gb = int(max(0.45, 2.3 * (1.0 - share_a)))
    if ga == gb:
        winner = team_a if prob_a >= 0.5 else team_b
        # Typical WC penalty scoreline: 5-4 or 4-3
        pw, pl = (5, 4) if prob_a >= 0.5 else (5, 4)
        pen_a  = pw if winner == team_a else pl
        pen_b  = pl if winner == team_a else pw
        extra  = (
            f'<span style="font-size:.7rem;color:#6b8aa8">'
            f'({pen_a}–{pen_b} nos pênaltis → {winner})</span>'
        )
    else:
        extra = ''
    return (
        f'<div style="background:#060f1c;border-radius:6px;padding:.5rem;margin-top:.4rem">'
        f'<span style="color:#5a8aa8;font-size:.68rem">Placar mais provável (modelo)</span><br>'
        f'<strong style="color:#d8e2ef;font-size:.88rem">'
        f'{team_a} <span style="color:#c9a902">{ga} × {gb}</span> {team_b}</strong><br>'
        f'{extra}'
        f'</div>'
    )


def _badge_or_elo(score_res, pair_str: str, elos: dict) -> str:
    """Returns sim-based score badge if available, else ELO-derived fallback."""
    if score_res:
        return _score_badge(*score_res[0], score_res[1], score_res[2])
    a, b = pair_str.split(' × ')
    return _elo_score_html(a, b, elos)


def _score_html(team_a: str, ga: int, team_b: str, gb: int, pens: bool, winner: str,
                pen_a: int = 0, pen_b: int = 0) -> str:
    """Render a match row with score and winner indicator."""
    if pens and (pen_a or pen_b):
        pens_tag = (
            f'<span style="font-size:.58rem;color:#6b8aa8;margin-left:.2rem">'
            f'({pen_a}–{pen_b} p.)</span>'
        )
    elif pens:
        pens_tag = '<span style="font-size:.58rem;color:#6b8aa8;margin-left:.2rem">(pens.)</span>'
    else:
        pens_tag = ''
    winner_color = '#00cc66'
    loser_color  = '#4a6a84'
    ca = winner_color if winner == team_a else loser_color
    cb = winner_color if winner == team_b else loser_color
    return (
        f'<div style="display:flex;align-items:center;gap:.35rem;margin:.25rem 0;'
        f'background:#060f1c;border-radius:6px;padding:.3rem .5rem">'
        f'<span style="flex:1;text-align:right;font-weight:700;color:{ca};font-size:.8rem">{team_a}</span>'
        f'<span style="font-size:.9rem;font-weight:900;color:#c9a902;'
        f'background:#0a1825;padding:2px 8px;border-radius:4px;white-space:nowrap">'
        f'{ga} × {gb}{pens_tag}</span>'
        f'<span style="flex:1;font-weight:700;color:{cb};font-size:.8rem">{team_b}</span>'
        f'</div>'
    )


def _compute_adjusted_elos(base_state, copa_sim, copa_ko_sim, schedule, ko_resolved):
    if not copa_sim and not copa_ko_sim:
        return base_state['elos']
    s = copy.deepcopy(base_state)
    for m in schedule:
        mid = m['id']
        if mid in copa_sim and m.get('home') and m.get('away'):
            res = copa_sim[mid]
            sm.apply_result(s, m['home'], m['away'],
                            int(res['home_score']), int(res['away_score']),
                            'FIFA World Cup', neutral=True)
    for m in ko_resolved:
        mid = m['id']
        if mid in copa_ko_sim and m.get('home') and m.get('away'):
            res = copa_ko_sim[mid]
            sm.apply_result(s, m['home'], m['away'],
                            int(res['home_score']), int(res['away_score']),
                            'FIFA World Cup', neutral=True)
    return s['elos']


# ── Load state + compute cache key ─────────────────────────────────────────────
state       = _load_state(sm.state_file_mtime())
official    = cm.load_official()
copa_sim    = st.session_state.get('copa_sim', {})
copa_ko_sim = st.session_state.get('copa_ko_sim', {})
schedule    = cm.generate_schedule()
ko_sched    = cm.generate_knockout_schedule()
standings   = cm.compute_group_standings(schedule, official, copa_sim)
br_slots    = cm.resolve_bracket_slots(standings)
ko_official = {k: v for k, v in official.items() if not k.startswith('G_')}
ko_resolved = cm.resolve_knockout_teams(ko_sched, br_slots, ko_official, copa_ko_sim)

adj_elos    = _compute_adjusted_elos(state, copa_sim, copa_ko_sim, schedule, ko_resolved)
_sim_hash   = hashlib.md5(
    json.dumps(sorted({**copa_sim, **copa_ko_sim}.items()), sort_keys=True).encode()
).hexdigest()[:8]
_cache_key  = f"sc_v2_{state['state_hash']}_{_sim_hash}"
_adj_elos_j = json.dumps(sorted(adj_elos.items())) if (copa_sim or copa_ko_sim) else ''

N_SCENARIOS = 2000

# ── Header ─────────────────────────────────────────────────────────────────────
_NL = ('display:inline-flex;align-items:center;gap:.35rem;'
       'background:#0c1c2e;border:1px solid #1a3a6a;border-radius:8px;'
       'padding:.42rem .85rem;text-decoration:none!important;'
       'font-weight:600;font-size:.82rem;transition:all .15s;')
_NA = _NL + 'color:#c9a902!important;border-color:#c9a902;background:#0a1e30;'
_NN = _NL + 'color:#7a9ab8!important;'

st.markdown(
    '<h1 style="font-size:2rem;margin-bottom:.28rem">🔮 Cenários das Finais</h1>'
    '<div class="stage-label">Semifinais · Disputa 3º Lugar · Final · Análise de Probabilidades</div>'
    '<nav style="display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.85rem;margin-bottom:.2rem">'
    f'<a href="/"                target="_self" style="{_NN}">🏠 Home</a>'
    f'<a href="/Historico"       target="_self" style="{_NN}">📜 Histórico</a>'
    f'<a href="/Documentacao"    target="_self" style="{_NN}">📚 Documentação</a>'
    f'<a href="/Cenarios_Finais" target="_self" style="{_NA}">🔮 Cenários das Finais</a>'
    '</nav>',
    unsafe_allow_html=True,
)
st.markdown('<br>', unsafe_allow_html=True)

if copa_sim or copa_ko_sim:
    n_applied = len(copa_sim) + len(copa_ko_sim)
    st.info(f'⚡ {n_applied} resultado(s) simulado(s) incorporado(s) nas probabilidades abaixo.')

# ── Run scenarios ──────────────────────────────────────────────────────────────
with st.spinner(f'Rodando {N_SCENARIOS:,} cenários completos…'):
    scenarios = _run_scenarios(_cache_key, N_SCENARIOS, _adj_elos_j)

# Se o cache tem dados antigos (sem scores), limpa e re-executa
if scenarios and 'final_score' not in scenarios[0]:
    _run_scenarios.clear()
    with st.spinner('Atualizando cenários com placares…'):
        scenarios = _run_scenarios(_cache_key, N_SCENARIOS, _adj_elos_j)

# ── Pre-compute aggregates ─────────────────────────────────────────────────────
n = len(scenarios)

champion_counts    = Counter(s['champion']    for s in scenarios)
runner_up_counts   = Counter(s['runner_up']   for s in scenarios)
third_place_counts = Counter(s['third_place'] for s in scenarios)

final_pair_counts  = Counter(_match_key(s['final'][0], s['final'][1])  for s in scenarios)
sf_pair_counts     = Counter(
    _match_key(s['sf1'][0], s['sf1'][1]) for s in scenarios
) + Counter(
    _match_key(s['sf2'][0], s['sf2'][1]) for s in scenarios
)
tp_pair_counts     = Counter(_match_key(s['third'][0], s['third'][1])  for s in scenarios)

# SF qualification counts (how often each team reaches semis)
sf_team_counts = Counter(
    team
    for s in scenarios
    for team in [s['sf1'][0], s['sf1'][1], s['sf2'][0], s['sf2'][1]]
)

# ── Section: 5 example scenarios ───────────────────────────────────────────────
st.markdown('<div class="section-title">📋 5 Cenários Simulados</div>', unsafe_allow_html=True)
st.caption('Exemplos de desfechos sorteados das simulações — com placar de cada jogo.')

_sample_indices = [int(i * n / 5) for i in range(5)]
sample_scenarios = [scenarios[i] for i in _sample_indices]

sc_cols = st.columns(5)
for ci, sc in enumerate(sample_scenarios):
    sf1_a, sf1_b, sf1_w = sc['sf1']
    sf2_a, sf2_b, sf2_w = sc['sf2']
    fin_a, fin_b, champ = sc['final']
    tp_a,  tp_b,  third = sc['third']

    gs1a, gs1b, sp1, ps1a, ps1b = _unpack_score(sc.get('sf1_score',   (1, 0, False, 0, 0)))
    gs2a, gs2b, sp2, ps2a, ps2b = _unpack_score(sc.get('sf2_score',   (1, 0, False, 0, 0)))
    gfa,  gfb,  fp,  pfa,  pfb  = _unpack_score(sc.get('final_score', (1, 0, False, 0, 0)))
    gta,  gtb,  tp,  pta,  ptb  = _unpack_score(sc.get('third_score', (1, 0, False, 0, 0)))

    with sc_cols[ci]:
        fin_score_row = _score_html(fin_a, gfa, fin_b, gfb, fp,  champ, pfa,  pfb)
        sf1_score_row = _score_html(sf1_a, gs1a, sf1_b, gs1b, sp1, sf1_w, ps1a, ps1b)
        sf2_score_row = _score_html(sf2_a, gs2a, sf2_b, gs2b, sp2, sf2_w, ps2a, ps2b)
        tp_score_row  = _score_html(tp_a,  gta,  tp_b,  gtb,  tp,  third, pta,  ptb)

        st.markdown(
            f'<div style="background:#0d2137;border:1px solid #1a3a6a;border-radius:10px;'
            f'padding:.8rem .65rem;font-size:.78rem;line-height:1.7">'

            f'<div style="font-size:.9rem;font-weight:700;color:#c9a902;margin-bottom:.6rem;'
            f'text-align:center;border-bottom:1px solid #1a3a6a;padding-bottom:.5rem">'
            f'Cenário {ci + 1}</div>'

            # SF1
            f'<div style="color:#6b9ab8;font-size:.63rem;font-weight:800;'
            f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:.2rem">🌟 Semifinal 1</div>'
            f'{sf1_score_row}'

            f'<div style="border-top:1px solid #0d2040;margin:.4rem 0"></div>'

            # SF2
            f'<div style="color:#6b9ab8;font-size:.63rem;font-weight:800;'
            f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:.2rem">🌟 Semifinal 2</div>'
            f'{sf2_score_row}'

            f'<div style="border-top:1px solid #0d2040;margin:.4rem 0"></div>'

            # 3rd place
            f'<div style="color:#cd7f32;font-size:.63rem;font-weight:800;'
            f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:.2rem">🥉 Disputa 3º Lugar</div>'
            f'{tp_score_row}'
            f'<div style="color:#cd7f32;font-size:.7rem;text-align:center;margin-top:.15rem">'
            f'🥉 {third}</div>'

            f'<div style="border-top:2px solid #c9a902;margin:.5rem 0"></div>'

            # FINAL — destaque total
            f'<div style="background:linear-gradient(135deg,#1a1000,#241800);'
            f'border:2px solid #c9a902;border-radius:8px;padding:.55rem .5rem;margin:.1rem 0">'
            f'<div style="color:#c9a902;font-size:.63rem;font-weight:900;'
            f'text-transform:uppercase;letter-spacing:.1em;text-align:center;margin-bottom:.3rem">'
            f'🏆 Grande Final</div>'
            f'{fin_score_row}'
            f'<div style="text-align:center;margin-top:.4rem;'
            f'font-size:.95rem;font-weight:900;color:#c9a902;'
            f'text-shadow:0 0 12px rgba(201,169,2,.6)">'
            f'🏆 {champ}</div>'
            f'</div>'

            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown('<br>', unsafe_allow_html=True)

# ── Section: Key metrics ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Probabilidades de Confrontos</div>',
            unsafe_allow_html=True)

tab_final, tab_sf, tab_tp, tab_champ = st.tabs(
    ['🏆 Final', '🌟 Semifinais', '🥉 Disputa 3º Lugar', '👑 Campeão / Vice']
)

with tab_final:
    st.markdown('**Top 10 finais mais prováveis**')
    rows = [{'Confronto': pair, 'Probabilidade (%)': round(cnt / n * 100, 2)}
            for pair, cnt in final_pair_counts.most_common(10)]
    df_f = pd.DataFrame(rows)
    fig_f = px.bar(df_f, x='Probabilidade (%)', y='Confronto', orientation='h',
                   color='Probabilidade (%)',
                   color_continuous_scale=['#1a3a6a', '#0055e5', '#c9a902'],
                   text='Probabilidade (%)', height=400)
    fig_f.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_f.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        coloraxis_showscale=False,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color='#d8e2ef', margin=dict(l=10, r=90, t=20, b=10),
    )
    st.plotly_chart(fig_f, use_container_width=True)

    with st.expander('Ver tabela completa de finais'):
        all_rows = [{'Confronto': pair, 'Prob. (%)': f'{cnt/n*100:.2f}%', 'Ocorrências': cnt}
                    for pair, cnt in final_pair_counts.most_common()]
        st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)

with tab_sf:
    st.markdown('**Top 15 confrontos de semifinal mais prováveis**')
    st.caption('Cada semifinal é contada separadamente (total = 2× o nº de simulações).')
    rows_sf = [{'Confronto': pair, 'Probabilidade (%)': round(cnt / (2 * n) * 100, 2)}
               for pair, cnt in sf_pair_counts.most_common(15)]
    df_sf = pd.DataFrame(rows_sf)
    fig_sf = px.bar(df_sf, x='Probabilidade (%)', y='Confronto', orientation='h',
                    color='Probabilidade (%)',
                    color_continuous_scale=['#1a3a6a', '#0055e5', '#c9a902'],
                    text='Probabilidade (%)', height=500)
    fig_sf.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_sf.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        coloraxis_showscale=False,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color='#d8e2ef', margin=dict(l=10, r=90, t=20, b=10),
    )
    st.plotly_chart(fig_sf, use_container_width=True)

with tab_tp:
    st.markdown('**Top 10 confrontos mais prováveis na disputa pelo 3º lugar**')
    rows_tp = [{'Confronto': pair, 'Probabilidade (%)': round(cnt / n * 100, 2)}
               for pair, cnt in tp_pair_counts.most_common(10)]
    df_tp = pd.DataFrame(rows_tp)
    fig_tp = px.bar(df_tp, x='Probabilidade (%)', y='Confronto', orientation='h',
                    color='Probabilidade (%)',
                    color_continuous_scale=['#1a3a6a', '#cd7f32', '#c9a902'],
                    text='Probabilidade (%)', height=370)
    fig_tp.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_tp.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        coloraxis_showscale=False,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color='#d8e2ef', margin=dict(l=10, r=90, t=20, b=10),
    )
    st.plotly_chart(fig_tp, use_container_width=True)

with tab_champ:
    col_c, col_v = st.columns(2)
    with col_c:
        st.markdown('**🏆 Mais prováveis campeões**')
        rows_c = [{'Seleção': t, 'Prob. Campeão (%)': round(cnt / n * 100, 2)}
                  for t, cnt in champion_counts.most_common(12)]
        df_c = pd.DataFrame(rows_c)
        fig_c = px.bar(df_c, x='Prob. Campeão (%)', y='Seleção', orientation='h',
                       color='Prob. Campeão (%)',
                       color_continuous_scale=['#1a3a6a', '#0055e5', '#c9a902'],
                       text='Prob. Campeão (%)', height=420)
        fig_c.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_c.update_layout(
            yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#d8e2ef', margin=dict(l=10, r=70, t=20, b=10),
        )
        st.plotly_chart(fig_c, use_container_width=True)
    with col_v:
        st.markdown('**🥈 Mais prováveis vice-campeões**')
        rows_v = [{'Seleção': t, 'Prob. Final (%)': round(cnt / n * 100, 2)}
                  for t, cnt in runner_up_counts.most_common(12)]
        df_v = pd.DataFrame(rows_v)
        fig_v = px.bar(df_v, x='Prob. Final (%)', y='Seleção', orientation='h',
                       color='Prob. Final (%)',
                       color_continuous_scale=['#1a3a6a', '#4472c4', '#aaaaaa'],
                       text='Prob. Final (%)', height=420)
        fig_v.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_v.update_layout(
            yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#d8e2ef', margin=dict(l=10, r=70, t=20, b=10),
        )
        st.plotly_chart(fig_v, use_container_width=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Section: Analysis ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🧠 Análise dos Cenários</div>', unsafe_allow_html=True)

top_final      = final_pair_counts.most_common(1)[0]
top_sf_pairs   = sf_pair_counts.most_common(5)
top_third      = tp_pair_counts.most_common(1)[0]
top3_champs    = champion_counts.most_common(3)
top4_sf        = sf_team_counts.most_common(4)

an1, an2 = st.columns([1, 1])

with an1:
    st.markdown('#### 🏆 Desfecho mais provável')

    champ_name, champ_cnt = top3_champs[0]
    ru_name,    ru_cnt    = runner_up_counts.most_common(1)[0]
    third_name, third_cnt = third_place_counts.most_common(1)[0]
    fin_pair,   fin_cnt   = top_final
    tp_pair_top, tp_cnt   = top_third

    st.markdown(
        f'Com base em **{n:,} simulações**, o cenário mais frequente é:\n\n'
        f'- 🏆 **Campeão:** **{champ_name}** '
        f'— {champ_cnt/n*100:.1f}% das simulações\n'
        f'- 🥈 **Vice:** **{ru_name}** '
        f'— {ru_cnt/n*100:.1f}%\n'
        f'- 🥉 **3º lugar:** **{third_name}** '
        f'— {third_cnt/n*100:.1f}%\n\n'
        f'A **final mais provável** é **{fin_pair}** '
        f'({fin_cnt/n*100:.1f}% de chance de acontecer).\n\n'
        f'A **disputa pelo 3º lugar mais comum** é **{tp_pair_top}** '
        f'({tp_cnt/n*100:.1f}%).'
    )

with an2:
    st.markdown('#### 🌟 Os 4 semifinalistas mais frequentes')
    rows_semi = [{'Seleção': team, 'Chega às SF em': f'{cnt/n*100:.1f}% dos casos'}
                 for team, cnt in top4_sf]
    st.dataframe(pd.DataFrame(rows_semi), use_container_width=True, hide_index=True)

    st.markdown('#### 🎯 Top 5 confrontos de semifinal')
    for pair, cnt_p in top_sf_pairs:
        pct = cnt_p / (2 * n) * 100
        st.markdown(f'- **{pair}** — {pct:.1f}%')

st.markdown('<br>', unsafe_allow_html=True)

# Surprise teams
elo_vals = state['elos']
surprise = [
    (t, cnt)
    for t, cnt in champion_counts.most_common()
    if elo_vals.get(t, 1500) < 1750 and cnt / n > 0.01
][:3]

if surprise:
    st.markdown('#### ⚡ Surpresas com chances reais')
    for t, cnt in surprise:
        st.markdown(
            f'- **{t}** — aparece como campeão em **{cnt/n*100:.1f}%** '
            f'dos cenários (Elo base: {round(elo_vals.get(t, 1500))})'
        )

st.markdown('<br>', unsafe_allow_html=True)

# ── Section: Betting recommendations ──────────────────────────────────────────
st.markdown('<div class="section-title">🎰 Recomendações de Aposta</div>', unsafe_allow_html=True)
st.caption(
    'Baseado nas probabilidades do modelo — compare com as odds das casas de apostas. '
    'Se a odd oferecida for maior que a odd justa, há valor na aposta.'
)

# ── Pre-compute ALL betting card values outside columns ────────────────────────
top_champ_name, top_champ_cnt = top3_champs[0]
top_champ_pct  = top_champ_cnt / n * 100
champ_fair_odd = round(100 / top_champ_pct, 2) if top_champ_pct > 0 else 99.0

top_fin_pair, top_fin_cnt = top_final
top_fin_pct    = top_fin_cnt / n * 100
top_ru_name, top_ru_cnt = runner_up_counts.most_common(1)[0]
top_ru_pct     = top_ru_cnt / n * 100
ru_fair_odd    = round(100 / top_ru_pct, 2) if top_ru_pct > 0 else 99.0

top_sf1_pair, top_sf1_cnt = top_sf_pairs[0]
top_sf2_pair, top_sf2_cnt = top_sf_pairs[1] if len(top_sf_pairs) > 1 else top_sf_pairs[0]
top_sf1_pct    = top_sf1_cnt / (2 * n) * 100
top_sf2_pct    = top_sf2_cnt / (2 * n) * 100
sf1_name, sf1_cnt_t = top4_sf[0]
sf1_reach_pct  = sf1_cnt_t / n * 100
sf1_fair_odd   = round(100 / sf1_reach_pct, 2) if sf1_reach_pct > 0 else 99.0
sf2_name, sf2_cnt_t = top4_sf[1] if len(top4_sf) > 1 else top4_sf[0]
sf2_reach_pct  = sf2_cnt_t / n * 100
sf2_fair_odd   = round(100 / sf2_reach_pct, 2) if sf2_reach_pct > 0 else 99.0

tp_pair_name, tp_pair_cnt = top_third
tp_pair_pct    = tp_pair_cnt / n * 100
tp_winner_name, tp_winner_cnt = third_place_counts.most_common(1)[0]
tp_winner_pct  = tp_winner_cnt / n * 100
tp_fair_odd    = round(100 / tp_winner_pct, 2) if tp_winner_pct > 0 else 99.0
tp_ru_name, tp_ru_cnt = (third_place_counts.most_common(2)[1]
                          if len(third_place_counts) > 1 else (tp_winner_name, tp_winner_cnt))
tp_ru_pct  = tp_ru_cnt / n * 100
tp_ru_odd  = round(100 / tp_ru_pct, 2) if tp_ru_pct > 0 else 99.0

# Score badges: sim-based if available, else ELO-derived (always shows something)
_fin_score_res = _best_score_for_pair(scenarios, 'final', 'final_score', top_fin_pair)
_sf1_score_res = _best_score_for_sf_pair(scenarios, top_sf1_pair)
_tp_score_res  = _best_score_for_pair(scenarios, 'third', 'third_score', tp_pair_name)

_fin_badge = _badge_or_elo(_fin_score_res, top_fin_pair, adj_elos)
_sf1_badge = _badge_or_elo(_sf1_score_res, top_sf1_pair, adj_elos)
_tp_badge  = _badge_or_elo(_tp_score_res,  tp_pair_name, adj_elos)

bet1, bet2, bet3 = st.columns(3)

with bet1:
    st.markdown(
        f'<div style="background:#0a1e10;border:2px solid #00aa55;border-radius:10px;padding:1rem">'
        f'<div style="color:#00cc66;font-size:.8rem;font-weight:800;margin-bottom:.6rem">🏆 FINAL</div>'
        f'<div style="margin-bottom:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.72rem">Confronto mais provável</span><br>'
        f'<strong>{top_fin_pair}</strong>'
        f'<span style="color:#c9a902;margin-left:.4rem">({top_fin_pct:.1f}%)</span>'
        f'</div>'
        f'<div style="margin-bottom:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.72rem">Favorito para campeão</span><br>'
        f'<strong>{top_champ_name}</strong> — {top_champ_pct:.1f}%'
        f'</div>'
        f'<div style="background:#060f1c;border-radius:6px;padding:.5rem;margin-top:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.68rem">Odd justa (campeão)</span><br>'
        f'<strong style="font-size:1.1rem;color:#c9a902">{champ_fair_odd:.2f}</strong>'
        f'<span style="color:#4a6a84;font-size:.7rem"> — aposte se encontrar odd acima desta</span>'
        f'</div>'
        f'<div style="background:#060f1c;border-radius:6px;padding:.5rem;margin-top:.4rem">'
        f'<span style="color:#5a8aa8;font-size:.68rem">Odd justa (vice / finalista)</span><br>'
        f'<strong style="font-size:1.05rem;color:#7eaacc">{top_ru_name}: {ru_fair_odd:.2f}</strong>'
        f'</div>'
        + _fin_badge +
        f'</div>',
        unsafe_allow_html=True,
    )

with bet2:
    st.markdown(
        f'<div style="background:#0a1525;border:2px solid #2255cc;border-radius:10px;padding:1rem">'
        f'<div style="color:#5599ff;font-size:.8rem;font-weight:800;margin-bottom:.6rem">🌟 SEMIFINAIS</div>'
        f'<div style="margin-bottom:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.72rem">SF mais provável</span><br>'
        f'<strong>{top_sf1_pair}</strong>'
        f'<span style="color:#c9a902;margin-left:.4rem">({top_sf1_pct:.1f}%)</span>'
        f'</div>'
        f'<div style="margin-bottom:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.72rem">2ª SF mais provável</span><br>'
        f'<strong>{top_sf2_pair}</strong>'
        f'<span style="color:#c9a902;margin-left:.4rem">({top_sf2_pct:.1f}%)</span>'
        f'</div>'
        f'<div style="background:#060f1c;border-radius:6px;padding:.5rem;margin-top:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.68rem">Odd justa — chegar às SF</span><br>'
        f'<strong style="color:#c9a902">{sf1_name}</strong>: '
        f'<strong style="font-size:1.05rem;color:#c9a902">{sf1_fair_odd:.2f}</strong><br>'
        f'<strong style="color:#7eaacc">{sf2_name}</strong>: '
        f'<strong style="font-size:1.05rem;color:#7eaacc">{sf2_fair_odd:.2f}</strong>'
        f'</div>'
        + _sf1_badge +
        f'<div style="color:#3a5a78;font-size:.68rem;margin-top:.5rem">'
        f'💡 Aposte em "chegar às semifinais" se a odd '
        f'da casa for superior às odds justas acima.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with bet3:
    st.markdown(
        f'<div style="background:#1a0e00;border:2px solid #cd7f32;border-radius:10px;padding:1rem">'
        f'<div style="color:#cd7f32;font-size:.8rem;font-weight:800;margin-bottom:.6rem">🥉 DISPUTA 3º LUGAR</div>'
        f'<div style="margin-bottom:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.72rem">Confronto mais provável</span><br>'
        f'<strong>{tp_pair_name}</strong>'
        f'<span style="color:#c9a902;margin-left:.4rem">({tp_pair_pct:.1f}%)</span>'
        f'</div>'
        f'<div style="margin-bottom:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.72rem">Favorito para 3º lugar</span><br>'
        f'<strong>{tp_winner_name}</strong> — {tp_winner_pct:.1f}%'
        f'</div>'
        f'<div style="background:#060f1c;border-radius:6px;padding:.5rem;margin-top:.5rem">'
        f'<span style="color:#5a8aa8;font-size:.68rem">Odds justas (3º lugar)</span><br>'
        f'<strong style="color:#cd7f32">{tp_winner_name}</strong>: '
        f'<strong style="font-size:1.05rem;color:#cd7f32">{tp_fair_odd:.2f}</strong><br>'
        f'<strong style="color:#7eaacc">{tp_ru_name}</strong>: '
        f'<strong style="font-size:1.05rem;color:#7eaacc">{tp_ru_odd:.2f}</strong>'
        f'</div>'
        + _tp_badge +
        f'<div style="color:#3a5a78;font-size:.68rem;margin-top:.5rem">'
        f'💡 Disputa de 3º é rara nos bolões — pode ter bom valor '
        f'se o mercado subestimar o favorito.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<br>', unsafe_allow_html=True)
st.caption(
    f'Baseado em {n:,} simulações Monte Carlo · Elo + Forma + Histórico Copa · '
    f'Bracket gerado probabilisticamente (não reflete chaveamento oficial Copa 2026) · '
    f'Odds justas = 100 ÷ probabilidade (%) — não incluem margem da casa · '
    f'Fontes: EloRatings.net · FIFA.com'
)
