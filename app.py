"""
Bolão Copa do Mundo 2026 — Principal
"""
import sys, os, json, hashlib, copy
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date as _date, timedelta
from urllib.parse import quote

from config import COPA_2026_GROUPS, DEFAULT_N_SIMULATIONS, N_BEST_THIRDS
from src import state_manager as sm, monte_carlo as mc
from src import copa_manager as cm
from src.styles import get_css

st.set_page_config(
    page_title='Copa 2026 Predictor',
    page_icon='⚽',
    layout='wide',
    initial_sidebar_state='expanded',
)
st.markdown(get_css(), unsafe_allow_html=True)

# ── Cached helpers ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_state():
    return sm.get_or_build_state()

@st.cache_data(show_spinner=False)
def _run_sim(cache_key: str, n_sims: int, adj_elos_json: str = ''):
    """Run Monte Carlo. adj_elos_json overrides base Elo ratings when provided."""
    state = sm.load_state() or sm.build_default_state()
    elos  = dict(json.loads(adj_elos_json)) if adj_elos_json else state['elos']
    return mc.run_simulations(
        COPA_2026_GROUPS, elos, n_simulations=n_sims,
        form=state.get('form', {}), copa_history=state.get('copa_history', {}),
    )

def _get_state():
    if st.session_state.get('state_dirty', False):
        _load_state.clear()
        _run_sim.clear()
        st.session_state['state_dirty'] = False
    return _load_state()

def _compute_adjusted_elos(base_state: dict, copa_sim: dict, copa_ko_sim: dict,
                            schedule: list, ko_resolved: list) -> dict:
    """Apply simulated match results as temporary Elo adjustments (read-only on base_state)."""
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


def _get_eliminated_teams(schedule: list, official: dict, copa_sim: dict,
                           standings: dict, ko_resolved: list,
                           ko_official: dict, ko_sim_now: dict) -> set:
    """
    Return set of teams definitively eliminated from the tournament.
    - Group stage: 4th place in any fully-played group; 3rds outside best-8 when all groups done.
    - Knockout: loser of each decided match (except 3rd-place match).
    """
    eliminated: set = set()
    thirds: list = []

    for grp, teams_list in COPA_2026_GROUPS.items():
        grp_matches = [m for m in schedule if m['group'] == grp]
        n_done = sum(1 for m in grp_matches if official.get(m['id']) or copa_sim.get(m['id']))
        if n_done == len(grp_matches):          # all 6 group matches played
            s = standings[grp]
            if len(s['sorted']) >= 4:
                eliminated.add(s['sorted'][3])  # 4th place always out
            if len(s['sorted']) >= 3:
                t3 = s['sorted'][2]
                thirds.append({'team': t3,
                               'pts': s['points'][t3], 'gd': s['gd'][t3], 'gf': s['gf'][t3]})

    # If ALL groups are done, we know exactly which 3rds miss out
    all_groups_done = all(
        sum(1 for m in schedule if m['group'] == grp and (official.get(m['id']) or copa_sim.get(m['id'])))
        == sum(1 for m in schedule if m['group'] == grp)
        for grp in COPA_2026_GROUPS
    )
    if all_groups_done and len(thirds) == len(COPA_2026_GROUPS):
        thirds_sorted = sorted(thirds, key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)
        for entry in thirds_sorted[8:]:         # 3rds beyond position 8 go home
            eliminated.add(entry['team'])

    # Knockout: loser of each decided match is eliminated
    for m in ko_resolved:
        mid = m['id']
        res = ko_official.get(mid) or ko_sim_now.get(mid)
        if res and m.get('home') and m.get('away') and m['phase'] != 'tp':
            hs, as_ = int(res['home_score']), int(res['away_score'])
            eliminated.add(m['away'] if hs > as_ else m['home'])

    return eliminated


def _apply_eliminations(probs: dict, eliminated: set) -> dict:
    """
    Zero out campeão probabilities for eliminated teams and renormalize
    remaining alive teams so their relative chances are meaningful.
    """
    if not eliminated:
        return probs
    alive_sum = sum(v['campeao'] for t, v in probs.items() if t not in eliminated)
    if alive_sum <= 0:
        return probs
    factor = 1.0 / alive_sum    # renorm factor so alive probs sum to ~1
    result = {}
    for team, vals in probs.items():
        if team in eliminated:
            result[team] = {k: 0.0 for k in vals}
        else:
            result[team] = {**vals, 'campeao': round(vals['campeao'] * factor, 4)}
    return result

# ── Calendar URL helper ────────────────────────────────────────────────────────

_MONTH_NUM = {'Jun': 6, 'Jul': 7, 'Ago': 8}

def _gcal_url(home: str, away: str, date: str, time_brt: str,
              stadium: str, city: str, extra: str = '') -> str:
    """Return Google Calendar add-event URL (BRT → UTC conversion)."""
    if '/' in date and len(date) <= 6:          # '04/Jul' KO format
        day_s, mon_s = date.split('/')
        d = _date(2026, _MONTH_NUM.get(mon_s, 7), int(day_s))
    else:                                        # '2026-06-11' group format
        d = _date.fromisoformat(date)
    h, mn = int(time_brt.split(':')[0]), int(time_brt.split(':')[1])
    h_utc = h + 3                                # BRT = UTC-3
    d0 = d
    if h_utc >= 24:
        h_utc -= 24; d0 = d + timedelta(days=1)
    h_end = h_utc + 2
    d1 = d0
    if h_end >= 24:
        h_end -= 24; d1 = d0 + timedelta(days=1)
    start = f"{d0.strftime('%Y%m%d')}T{h_utc:02d}{mn:02d}00Z"
    end   = f"{d1.strftime('%Y%m%d')}T{h_end:02d}{mn:02d}00Z"
    title = f"{home} vs {away} — Copa do Mundo 2026"
    if extra:
        title = f"{home} vs {away} — Copa 2026 {extra}"
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(title)}&dates={start}/{end}"
        f"&details={quote('Copa do Mundo FIFA 2026')}&location={quote(f'{stadium}, {city}')}"
    )

# ── Session state defaults ─────────────────────────────────────────────────────
if 'copa_sim'    not in st.session_state: st.session_state['copa_sim']    = {}
if 'copa_ko_sim' not in st.session_state: st.session_state['copa_ko_sim'] = {}

# ── Pre-load all shared objects ────────────────────────────────────────────────
state       = _get_state()
official    = cm.load_official()
copa_sim    = st.session_state['copa_sim']
copa_ko_sim = st.session_state['copa_ko_sim']
schedule    = cm.generate_schedule()
standings   = cm.compute_group_standings(schedule, official, copa_sim)
bracket_slots = cm.resolve_bracket_slots(standings)
ko_sched      = cm.generate_knockout_schedule()
ko_official   = {k: v for k, v in official.items() if not k.startswith('G_')}
ko_resolved   = cm.resolve_knockout_teams(ko_sched, bracket_slots, ko_official, copa_ko_sim)

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:.4rem 0 .8rem">'
        '<div style="font-size:1.25rem;font-weight:900;color:#c9a902;letter-spacing:-.02em">'
        '⚽ Copa 2026</div>'
        '<div style="font-size:.7rem;color:#3a5a78;text-transform:uppercase;'
        'letter-spacing:.08em;margin-top:2px">Predictor</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="font-size:.68rem;color:#2a4a68;text-transform:uppercase;'
                'letter-spacing:.1em;padding:.2rem 0 .3rem">Navegação principal</div>',
                unsafe_allow_html=True)
    st.page_link('app.py',                     label='🏠  Home')
    st.page_link('pages/4_Historico.py',        label='📜  Histórico de Resultados')
    st.page_link('pages/7_Documentacao.py',     label='📚  Documentação')
    st.page_link('pages/8_Cenarios_Finais.py',  label='🔮  Cenários das Finais')

    st.markdown('<div style="border-top:1px solid #0d2040;margin:.6rem 0 .5rem"></div>',
                unsafe_allow_html=True)
    st.markdown('<div style="font-size:.68rem;color:#2a4a68;text-transform:uppercase;'
                'letter-spacing:.1em;padding:.1rem 0 .3rem">Análises</div>',
                unsafe_allow_html=True)
    st.page_link('pages/1_Campeoes.py',         label='🏆  Probabilidades Detalhadas')
    st.page_link('pages/5_Ranking_Elo.py',       label='📊  Ranking Elo')
    st.page_link('pages/2_Simulacao.py',         label='🎲  Simulação Monte Carlo')
    st.page_link('pages/3_Novo_Resultado.py',    label='➕  Novo Resultado Histórico')

    st.markdown('<div style="border-top:1px solid #0d2040;margin:.6rem 0 .5rem"></div>',
                unsafe_allow_html=True)
    meta = state.get('meta', {})
    if meta.get('mode') == 'demo':
        st.warning('⚠️ Modo demo', icon='⚠️')
    else:
        st.success(f'✅ {meta.get("n_matches", 0):,} partidas históricas')
    if meta.get('n_manual'):
        st.info(f'📝 {meta["n_manual"]} resultado(s) manual(is)')

# ── Page header + inline nav ───────────────────────────────────────────────────
_NL = ('display:inline-flex;align-items:center;gap:.35rem;'
       'background:#0c1c2e;border:1px solid #1a3a6a;border-radius:8px;'
       'padding:.42rem .85rem;text-decoration:none!important;'
       'font-weight:600;font-size:.82rem;transition:all .15s;')
_NA = _NL + 'color:#c9a902!important;border-color:#c9a902;background:#0a1e30;'
_NN = _NL + 'color:#7a9ab8!important;'

st.markdown(
    '<h1 style="font-size:2.1rem;margin-bottom:.28rem">⚽ Copa do Mundo 2026</h1>'
    '<div class="stage-label">'
    '🇺🇸 EUA &nbsp;·&nbsp; 🇨🇦 CANADÁ &nbsp;·&nbsp; 🇲🇽 MÉXICO'
    ' &nbsp;|&nbsp; 11 JUN – 26 JUL 2026</div>'
    '<nav style="display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.85rem;margin-bottom:.2rem">'
    f'<a href="/"               target="_self" style="{_NA}">🏠 Home</a>'
    f'<a href="/Historico"      target="_self" style="{_NN}">📜 Histórico</a>'
    f'<a href="/Documentacao"   target="_self" style="{_NN}">📚 Documentação</a>'
    f'<a href="/Cenarios_Finais" target="_self" style="{_NN}">🔮 Cenários das Finais</a>'
    '</nav>',
    unsafe_allow_html=True,
)
st.markdown('<br>', unsafe_allow_html=True)

# ── Ceremonies ─────────────────────────────────────────────────────────────────
_TV_CHIPS_CEREMONY = (
    '<a href="https://globoplay.globo.com" target="_blank" style="text-decoration:none">'
    '<span class="tv-chip tv-globo">TV Globo</span></a>&nbsp;'
    '<a href="https://globoplay.globo.com" target="_blank" style="text-decoration:none">'
    '<span class="tv-chip tv-globoplay">Globoplay</span></a>'
)

with st.expander('🎭 Cerimônias de Abertura e Encerramento', expanded=False):
    cc1, cc2 = st.columns(2)
    with cc1:
        gcal_open = _gcal_url(
            'Cerimônia de Abertura', 'Copa do Mundo 2026',
            '2026-06-11', '14:00', 'Estadio Azteca', 'Mexico City',
        )
        st.markdown(
            f'<div style="padding:.6rem 0">'
            f'<div style="font-weight:700;font-size:1rem;margin-bottom:.4rem">🎉 Cerimônia de Abertura</div>'
            f'📅 11 de Junho de 2026<br>'
            f'⏰ 14:00 BRT · 🏟️ Estadio Azteca, Mexico City, México<br>'
            f'<div style="margin:.5rem 0">{_TV_CHIPS_CEREMONY}</div>'
            f'<a href="{gcal_open}" target="_blank" style="color:#4472c4;font-size:.8rem">'
            f'📆 Adicionar ao Google Calendário</a>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cc2:
        gcal_close = _gcal_url(
            'Cerimônia de Encerramento', 'Copa do Mundo 2026',
            '2026-07-26', '15:00', 'MetLife Stadium', 'East Rutherford / Nova York',
        )
        st.markdown(
            f'<div style="padding:.6rem 0">'
            f'<div style="font-weight:700;font-size:1rem;margin-bottom:.4rem">🏆 Cerimônia de Encerramento + Final</div>'
            f'📅 26 de Julho de 2026<br>'
            f'⏰ 15:00 BRT · 🏟️ MetLife Stadium, Nova York/NJ, EUA<br>'
            f'<div style="margin:.5rem 0">{_TV_CHIPS_CEREMONY}</div>'
            f'<a href="{gcal_close}" target="_blank" style="color:#4472c4;font-size:.8rem">'
            f'📆 Adicionar ao Google Calendário</a>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — FAVORITOS  (probabilidades dinâmicas)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">🏆 Favoritos ao Título</div>', unsafe_allow_html=True)

# Compute adjusted Elos incorporating simulated match results
adj_elos     = _compute_adjusted_elos(state, copa_sim, copa_ko_sim, schedule, ko_resolved)
_sim_content = json.dumps(sorted({**copa_sim, **copa_ko_sim}.items()), sort_keys=True)
_sim_hash    = hashlib.md5(_sim_content.encode()).hexdigest()[:8]
_cache_key   = f"{state['state_hash']}_{_sim_hash}"
_adj_elos_j  = json.dumps(sorted(adj_elos.items())) if (copa_sim or copa_ko_sim) else ''

with st.spinner('Calculando probabilidades...'):
    probs = _run_sim(_cache_key, DEFAULT_N_SIMULATIONS, _adj_elos_j)

# Apply eliminations: teams that lost or finished 4th get 0%; alive teams renormalized
eliminated    = _get_eliminated_teams(schedule, official, copa_sim, standings,
                                       ko_resolved, ko_official, copa_ko_sim)
probs         = _apply_eliminations(probs, eliminated)

n_sims_applied = len(copa_sim) + len(copa_ko_sim)
sorted_teams   = sorted(probs.items(), key=lambda x: x[1]['campeao'], reverse=True)

# Top-3 metrics
medals = ['🥇', '🥈', '🥉']
c1, c2, c3 = st.columns(3)
for col, medal, (team, vals) in zip([c1, c2, c3], medals, sorted_teams[:3]):
    with col:
        base_elo = state['elos'].get(team, 1500)
        cur_elo  = adj_elos.get(team, base_elo)
        delta    = f'Elo {round(cur_elo)}'
        if copa_sim or copa_ko_sim:
            diff = round(cur_elo - base_elo)
            delta = f'Elo {round(cur_elo)} ({diff:+d})'
        st.metric(label=f'{medal} {team}', value=f"{vals['campeao']*100:.1f}%", delta=delta)

if n_sims_applied > 0 or eliminated:
    parts = []
    if n_sims_applied:
        parts.append(f'⚡ {n_sims_applied} resultado(s) simulado(s) incorporado(s)')
    if eliminated:
        parts.append(f'🚫 {len(eliminated)} seleção(ões) eliminada(s) com prob. 0%')
    st.caption(' · '.join(parts) + ' · Grave resultados oficiais para atualização definitiva.')

st.markdown('<br>', unsafe_allow_html=True)

# Top-10 bar chart
df_chart = pd.DataFrame([
    {'Seleção': t, 'Campeão (%)': round(v['campeao'] * 100, 1)}
    for t, v in sorted_teams[:10]
])
fig = px.bar(
    df_chart, x='Campeão (%)', y='Seleção', orientation='h',
    color='Campeão (%)', color_continuous_scale=['#1a3a6a', '#0055e5', '#c9a902'],
    text='Campeão (%)', title='Top 10 Favoritos ao Título',
    height=390,
)
fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    coloraxis_showscale=False,
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font_color='#d8e2ef', title_font_color='#c9a902',
    margin=dict(l=10, r=90, t=50, b=10),
)
st.plotly_chart(fig, use_container_width=True)

with st.expander(f'📋 Ver todos os {len(sorted_teams)} times'):
    rows_all = []
    for rank, (team, vals) in enumerate(sorted_teams, 1):
        rows_all.append({
            '#': rank, 'Seleção': team,
            'Campeão':   f"{vals['campeao']*100:.1f}%",
            'Final':     f"{vals['final']*100:.1f}%",
            'Semifinal': f"{vals['semifinal']*100:.1f}%",
            'Quartas':   f"{vals['quartas']*100:.1f}%",
            'Oitavas':   f"{vals['oitavas']*100:.1f}%",
            'Elo atual': round(adj_elos.get(team, state['elos'].get(team, 1500))),
        })
    st.dataframe(pd.DataFrame(rows_all).set_index('#'), use_container_width=True, height=520)

st.caption(
    f'Baseado em {DEFAULT_N_SIMULATIONS:,} simulações Monte Carlo · Elo + Forma + Histórico Copa · '
    f'Fontes: EloRatings.net · FIFA.com · Copa história via Wikipedia'
)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS — match row rendering
# ═══════════════════════════════════════════════════════════════════════════════

def _sync_inputs_from(result_dict: dict):
    for mid, res in result_dict.items():
        st.session_state[f'hs_{mid}'] = int(res['home_score'])
        st.session_state[f'as_{mid}'] = int(res['away_score'])

def _clear_inputs(match_ids):
    for mid in match_ids:
        st.session_state.pop(f'hs_{mid}', None)
        st.session_state.pop(f'as_{mid}', None)
        st.session_state.pop(f'confirm_{mid}', None)


def _render_match(m: dict, off: dict, sim: dict, elos: dict):
    """Render one group-stage match row."""
    mid  = m['id']
    home = m['home']
    away = m['away']
    off_result  = off.get(mid)
    sim_result  = sim.get(mid)
    is_official = bool(off_result)

    # Initialize inputs from existing result (only when key not yet in session state)
    if f'hs_{mid}' not in st.session_state:
        if off_result:
            st.session_state[f'hs_{mid}'] = int(off_result['home_score'])
            st.session_state[f'as_{mid}'] = int(off_result['away_score'])
        elif sim_result:
            st.session_state[f'hs_{mid}'] = int(sim_result['home_score'])
            st.session_state[f'as_{mid}'] = int(sim_result['away_score'])

    gcal = _gcal_url(home, away, m['date'], m['time_brt'], m['stadium'], m['city'],
                     f"Grupo {m.get('group', '')}")
    meta_html = (
        f'<span style="font-size:.72rem;color:#3a5a78">'
        f'📅 {m["date"]} · ⏰ {m["time_brt"]} BRT · '
        f'🏟️ {m["stadium"]}, {m["city"]} · '
        f'{cm.tv_html(home, away, m["phase"])} · '
        f'<a href="{gcal}" target="_blank" style="color:#4472c4;text-decoration:none" '
        f'title="Adicionar ao Calendário">📆 cal</a>'
        f'</span>'
    )

    if is_official:
        hs, as_ = off_result['home_score'], off_result['away_score']
        c_h, c_hs, c_x, c_as, c_a, c_st = st.columns([3, 1, 0.4, 1, 3, 2])
        with c_h:
            st.markdown(
                f'<div style="text-align:right;font-weight:700;padding-top:.4rem">{home}</div>',
                unsafe_allow_html=True)
        with c_hs:
            st.markdown(
                f'<div style="text-align:center;font-size:1.3rem;font-weight:900;'
                f'color:#c9a902;padding-top:.2rem">{hs}</div>', unsafe_allow_html=True)
        with c_x:
            st.markdown(
                '<div style="text-align:center;padding-top:.45rem;color:#3a5a78">×</div>',
                unsafe_allow_html=True)
        with c_as:
            st.markdown(
                f'<div style="text-align:center;font-size:1.3rem;font-weight:900;'
                f'color:#c9a902;padding-top:.2rem">{as_}</div>', unsafe_allow_html=True)
        with c_a:
            st.markdown(
                f'<div style="font-weight:700;padding-top:.4rem">{away}</div>',
                unsafe_allow_html=True)
        with c_st:
            st.markdown(
                '<div style="text-align:center;padding-top:.5rem;font-size:.8rem;'
                'color:#00aa55">🔒 Oficial</div>', unsafe_allow_html=True)
        st.markdown(meta_html, unsafe_allow_html=True)
    else:
        status_icon = '🎲' if sim_result else '·'
        c_h, c_hs, c_x, c_as, c_a, c_sim, c_grv = st.columns([3, 1.1, 0.4, 1.1, 3, 1.6, 1.6])
        with c_h:
            st.markdown(
                f'<div style="text-align:right;font-weight:700;padding-top:.5rem">'
                f'{home} <span style="color:#3a5a78;font-size:.8rem">{status_icon}</span></div>',
                unsafe_allow_html=True)
        with c_hs:
            st.number_input('', 0, 20, key=f'hs_{mid}', label_visibility='collapsed')
        with c_x:
            st.markdown(
                '<div style="text-align:center;padding-top:.5rem;color:#3a5a78">×</div>',
                unsafe_allow_html=True)
        with c_as:
            st.number_input('', 0, 20, key=f'as_{mid}', label_visibility='collapsed')
        with c_a:
            st.markdown(
                f'<div style="font-weight:700;padding-top:.5rem">{away}</div>',
                unsafe_allow_html=True)
        with c_sim:
            if st.button('⚡ Sim', key=f'sim_{mid}', use_container_width=True,
                         help='Simular resultado aleatório'):
                ga, gb = cm.simulate_match_score(home, away, elos)
                sim[mid] = {'home_score': ga, 'away_score': gb}
                # Remove widget keys so init block re-reads from sim_result on rerun
                st.session_state.pop(f'hs_{mid}', None)
                st.session_state.pop(f'as_{mid}', None)
                st.rerun()
        with c_grv:
            if st.button('📝 Gravar', key=f'grv_{mid}', use_container_width=True,
                         help='Gravar placar oficial (irreversível)'):
                st.session_state[f'confirm_{mid}'] = {
                    'hs': int(st.session_state.get(f'hs_{mid}', 0)),
                    'as': int(st.session_state.get(f'as_{mid}', 0)),
                }

        st.markdown(meta_html, unsafe_allow_html=True)

        confirm = st.session_state.get(f'confirm_{mid}')
        if confirm:
            hs_c, as_c = confirm['hs'], confirm['as']
            st.warning(
                f'⚠️ **Gravar oficialmente: {home} {hs_c} × {as_c} {away}** '
                f'— esta ação **não pode ser desfeita**.', icon='🔒',
            )
            gc1, gc2 = st.columns(2)
            with gc1:
                if st.button('✅ Confirmar e Gravar', key=f'yes_{mid}',
                             type='secondary', use_container_width=True):
                    cm.save_official_result(mid, hs_c, as_c)
                    cur   = sm.load_state() or state
                    new_s = sm.apply_result(cur, home, away, hs_c, as_c,
                                            'FIFA World Cup', neutral=True)
                    sm.save_state(new_s)
                    _load_state.clear()
                    _run_sim.clear()
                    st.session_state['state_dirty'] = True
                    sim.pop(mid, None)
                    st.session_state.pop(f'confirm_{mid}', None)
                    st.session_state.pop(f'hs_{mid}', None)
                    st.session_state.pop(f'as_{mid}', None)
                    st.rerun()
            with gc2:
                if st.button('Cancelar', key=f'no_{mid}', use_container_width=True):
                    st.session_state.pop(f'confirm_{mid}', None)
                    st.rerun()

    st.markdown('<hr style="margin:.3rem 0;border-color:#0a1e30">', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# BOTÕES GLOBAIS DE SIMULAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<br>', unsafe_allow_html=True)
_g1, _g2, _g3 = st.columns([2, 2.2, 4])
with _g1:
    if st.button('⚡ Simular Tudo', type='primary', use_container_width=True,
                 help='Simula todos os jogos pendentes: grupos + todas as fases eliminatórias'):
        _new_sim = cm.simulate_all_pending(schedule, official, {}, state['elos'])
        _clear_inputs([m['id'] for m in schedule])
        _std_tmp = cm.compute_group_standings(schedule, official, _new_sim)
        _sl_tmp  = cm.resolve_bracket_slots(_std_tmp)
        _ko_off  = {k: v for k, v in official.items() if not k.startswith('G_')}
        _new_ko: dict = {}
        for _ in range(6):
            _rt   = cm.resolve_knockout_teams(ko_sched, _sl_tmp, _ko_off, _new_ko)
            _new_ko = cm.simulate_all_knockout_pending(_rt, _ko_off, _new_ko, state['elos'])
        _clear_inputs([m['id'] for m in ko_sched])
        st.session_state['copa_sim']    = _new_sim
        st.session_state['copa_ko_sim'] = _new_ko
        st.rerun()
with _g2:
    if st.button('🗑️ Limpar Tudo', use_container_width=True,
                 help='Remove todos os resultados simulados (grupos + eliminatórias)'):
        _clear_inputs([m['id'] for m in schedule])
        _clear_inputs([m['id'] for m in ko_sched])
        st.session_state['copa_sim']    = {}
        st.session_state['copa_ko_sim'] = {}
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — FASE DE GRUPOS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<br>', unsafe_allow_html=True)

n_played   = sum(1 for m in schedule if official.get(m['id']) or copa_sim.get(m['id']))
n_official = sum(1 for m in schedule if m['id'] in official)

with st.expander('📅 Fase de Grupos', expanded=True):
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 4])
    with ctrl1:
        if st.button('⚡ Simular Todos Pendentes', type='primary', use_container_width=True):
            new_sim = cm.simulate_all_pending(schedule, official, copa_sim, state['elos'])
            _clear_inputs([m['id'] for m in schedule])
            _sync_inputs_from(new_sim)
            st.session_state['copa_sim'] = new_sim
            st.rerun()
    with ctrl2:
        if st.button('🗑️ Limpar Simulações', use_container_width=True):
            _clear_inputs([m['id'] for m in schedule])
            st.session_state['copa_sim'] = {}
            st.rerun()
    with ctrl3:
        st.progress(
            n_played / len(schedule),
            text=(
                f'{n_played}/{len(schedule)} partidas com resultado '
                f'({n_official} 🔒 oficiais · {n_played - n_official} 🎲 simuladas)'
            ),
        )

    st.markdown('<br>', unsafe_allow_html=True)

    official_now = cm.load_official()
    sim_now      = st.session_state['copa_sim']
    standings    = cm.compute_group_standings(schedule, official_now, sim_now)
    groups_list  = list(COPA_2026_GROUPS.keys())

    for row_i in range(0, len(groups_list), 2):
        pair = groups_list[row_i:row_i + 2]
        cols = st.columns(len(pair))

        for ci, grp in enumerate(pair):
            s = standings[grp]
            # Count results in this group for expander label
            grp_matches = [m for m in schedule if m['group'] == grp]
            n_grp_done  = sum(1 for m in grp_matches if official_now.get(m['id']) or sim_now.get(m['id']))
            with cols[ci]:
                with st.expander(
                    f'Grupo {grp}  —  {n_grp_done}/{len(grp_matches)} jogos',
                    expanded=True,
                ):
                    stand_rows = []
                    for pos, team in enumerate(s['sorted'], 1):
                        stand_rows.append({
                            'P': pos, 'Seleção': team,
                            'J': s['played'][team], 'Pts': s['points'][team], 'SG': s['gd'][team],
                        })
                    st.dataframe(
                        pd.DataFrame(stand_rows).set_index('P'),
                        use_container_width=True, hide_index=False, height=168,
                    )
                    for md in [1, 2, 3]:
                        st.caption(f'Rodada {md}' + (' — simultâneos' if md == 3 else ''))
                        for m in (x for x in grp_matches if x['matchday'] == md):
                            _render_match(m, official_now, sim_now, state['elos'])

        if row_i + 2 < len(groups_list):
            st.markdown('---')


# ═══════════════════════════════════════════════════════════════════════════════
# KO BRACKET HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _slot_label(slot: str, br_slots: dict, ko_sched: list) -> str:
    if slot in br_slots and br_slots[slot]:
        return br_slots[slot]
    if slot.startswith('W_'):
        mid = slot[2:]
        m = next((x for x in ko_sched if x['id'] == mid), None)
        if m:
            h = br_slots.get(m['slot_home'], m['slot_home'])
            a = br_slots.get(m['slot_away'], m['slot_away'])
            return f'Venc. ({h} × {a})'
    if slot.startswith('L_'):
        mid = slot[2:]
        m = next((x for x in ko_sched if x['id'] == mid), None)
        if m:
            h = br_slots.get(m['slot_home'], m['slot_home'])
            a = br_slots.get(m['slot_away'], m['slot_away'])
            return f'Perd. ({h} × {a})'
    return slot


def _render_ko_match(m: dict, ko_off: dict, ko_sim: dict,
                     br_slots: dict, ko_sched: list, elos: dict):
    """Render one knockout match row."""
    mid       = m['id']
    home      = m.get('home')
    away      = m.get('away')
    home_lbl  = home or _slot_label(m['slot_home'], br_slots, ko_sched)
    away_lbl  = away or _slot_label(m['slot_away'], br_slots, ko_sched)
    off_result  = ko_off.get(mid)
    sim_result  = ko_sim.get(mid)
    is_official = bool(off_result)
    teams_known = bool(home and away)

    if f'hs_{mid}' not in st.session_state:
        if off_result:
            st.session_state[f'hs_{mid}'] = int(off_result['home_score'])
            st.session_state[f'as_{mid}'] = int(off_result['away_score'])
        elif sim_result:
            st.session_state[f'hs_{mid}'] = int(sim_result['home_score'])
            st.session_state[f'as_{mid}'] = int(sim_result['away_score'])

    gcal = _gcal_url(home_lbl, away_lbl, m['date'], m['time_brt'], m['stadium'], m['city'])
    meta_html = (
        f'<span style="font-size:.72rem;color:#3a5a78">'
        f'📅 {m["date"]} · ⏰ {m["time_brt"]} BRT · '
        f'🏟️ {m["stadium"]}, {m["city"]}'
        f'{" · " + cm.tv_html(home, away, m["phase"]) if teams_known else ""}'
        f' · <a href="{gcal}" target="_blank" style="color:#4472c4;text-decoration:none" '
        f'title="Adicionar ao Calendário">📆 cal</a>'
        f'</span>'
    )

    if is_official:
        hs, as_ = off_result['home_score'], off_result['away_score']
        c_h, c_hs, c_x, c_as, c_a, c_st = st.columns([3, 1, 0.4, 1, 3, 2])
        with c_h:
            st.markdown(
                f'<div style="text-align:right;font-weight:700;padding-top:.4rem">'
                f'{home_lbl}</div>', unsafe_allow_html=True)
        with c_hs:
            st.markdown(
                f'<div style="text-align:center;font-size:1.3rem;font-weight:900;'
                f'color:#c9a902;padding-top:.2rem">{hs}</div>', unsafe_allow_html=True)
        with c_x:
            st.markdown(
                '<div style="text-align:center;padding-top:.45rem;color:#3a5a78">×</div>',
                unsafe_allow_html=True)
        with c_as:
            st.markdown(
                f'<div style="text-align:center;font-size:1.3rem;font-weight:900;'
                f'color:#c9a902;padding-top:.2rem">{as_}</div>', unsafe_allow_html=True)
        with c_a:
            st.markdown(
                f'<div style="font-weight:700;padding-top:.4rem">{away_lbl}</div>',
                unsafe_allow_html=True)
        with c_st:
            st.markdown(
                '<div style="text-align:center;padding-top:.5rem;font-size:.8rem;'
                'color:#00aa55">🔒 Oficial</div>', unsafe_allow_html=True)
    else:
        c_h, c_hs, c_x, c_as, c_a, c_sim, c_grv = st.columns([3, 1.1, 0.4, 1.1, 3, 1.6, 1.6])
        with c_h:
            status_ico = '🎲' if sim_result else '·'
            style_h = ('text-align:right;font-weight:700;padding-top:.5rem'
                       if teams_known else
                       'text-align:right;font-style:italic;color:#3a5a78;padding-top:.5rem')
            st.markdown(
                f'<div style="{style_h}">{home_lbl} '
                f'<span style="color:#3a5a78;font-size:.8rem">{status_ico}</span></div>',
                unsafe_allow_html=True)
        with c_hs:
            if teams_known:
                st.number_input('', 0, 20, key=f'hs_{mid}', label_visibility='collapsed')
            else:
                st.markdown(
                    '<div style="padding-top:.5rem;color:#1a3050;text-align:center">—</div>',
                    unsafe_allow_html=True)
        with c_x:
            st.markdown(
                '<div style="text-align:center;padding-top:.5rem;color:#3a5a78">×</div>',
                unsafe_allow_html=True)
        with c_as:
            if teams_known:
                st.number_input('', 0, 20, key=f'as_{mid}', label_visibility='collapsed')
            else:
                st.markdown(
                    '<div style="padding-top:.5rem;color:#1a3050;text-align:center">—</div>',
                    unsafe_allow_html=True)
        with c_a:
            style_a = ('font-weight:700;padding-top:.5rem'
                       if teams_known else
                       'font-style:italic;color:#3a5a78;padding-top:.5rem')
            st.markdown(f'<div style="{style_a}">{away_lbl}</div>', unsafe_allow_html=True)
        with c_sim:
            if teams_known:
                if st.button('⚡ Sim', key=f'sim_{mid}', use_container_width=True):
                    ga, gb = cm.simulate_match_score(home, away, elos)
                    ko_sim[mid] = {'home_score': ga, 'away_score': gb}
                    st.session_state.pop(f'hs_{mid}', None)
                    st.session_state.pop(f'as_{mid}', None)
                    st.rerun()
        with c_grv:
            if teams_known:
                if st.button('📝 Gravar', key=f'grv_{mid}', use_container_width=True):
                    st.session_state[f'confirm_{mid}'] = {
                        'hs': int(st.session_state.get(f'hs_{mid}', 0)),
                        'as': int(st.session_state.get(f'as_{mid}', 0)),
                    }

    st.markdown(meta_html, unsafe_allow_html=True)

    confirm = st.session_state.get(f'confirm_{mid}')
    if confirm and teams_known and not is_official:
        hs_c, as_c = confirm['hs'], confirm['as']
        st.warning(
            f'⚠️ **Gravar: {home_lbl} {hs_c} × {as_c} {away_lbl}** — ação irreversível.',
            icon='🔒',
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button('✅ Confirmar', key=f'yes_{mid}', type='secondary',
                         use_container_width=True):
                cm.save_official_result(mid, hs_c, as_c)
                cur   = sm.load_state() or state
                new_s = sm.apply_result(cur, home, away, hs_c, as_c,
                                        'FIFA World Cup', neutral=True)
                sm.save_state(new_s)
                _load_state.clear()
                _run_sim.clear()
                st.session_state['state_dirty'] = True
                ko_sim.pop(mid, None)
                st.session_state.pop(f'confirm_{mid}', None)
                st.session_state.pop(f'hs_{mid}', None)
                st.session_state.pop(f'as_{mid}', None)
                st.rerun()
        with cc2:
            if st.button('Cancelar', key=f'no_{mid}', use_container_width=True):
                st.session_state.pop(f'confirm_{mid}', None)
                st.rerun()

    st.markdown('<hr style="margin:.3rem 0;border-color:#0a1e30">', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3-8 — FASES ELIMINATÓRIAS
# ═══════════════════════════════════════════════════════════════════════════════

official_now  = cm.load_official()
sim_now       = st.session_state['copa_sim']
ko_sim_now    = st.session_state['copa_ko_sim']
standings_now = cm.compute_group_standings(schedule, official_now, sim_now)
bracket_slots = cm.resolve_bracket_slots(standings_now)
ko_official   = {k: v for k, v in official_now.items() if not k.startswith('G_')}
ko_resolved   = cm.resolve_knockout_teams(ko_sched, bracket_slots, ko_official, ko_sim_now)

_PHASES = [
    ('r32',   '🗂️ Rodada de 32',     'Jul 4–11',  16),
    ('r16',   '⚔️ Oitavas de Final',  'Jul 13–16',  8),
    ('qf',    '🏟️ Quartas de Final',  'Jul 18–19',  4),
    ('sf',    '🌟 Semifinais',        'Jul 22–23',  2),
    ('tp',    '🥉 Disputa 3º Lugar',  'Jul 25',     1),
    ('final', '🏆 Final',             'Jul 26',     1),
]

for phase_key, phase_label, phase_dates, expected in _PHASES:
    phase_matches = [m for m in ko_resolved if m['phase'] == phase_key]
    if not phase_matches:
        continue

    n_ko_played = sum(
        1 for m in phase_matches
        if ko_official.get(m['id']) or ko_sim_now.get(m['id'])
    )

    with st.expander(
        f'{phase_label} — {phase_dates}  ({n_ko_played}/{expected} com resultado)',
        expanded=False,
    ):
        kc1, kc2, kc3 = st.columns([2, 2, 4])
        with kc1:
            if st.button(f'⚡ Simular Fase', key=f'simphase_{phase_key}',
                         type='primary', use_container_width=True):
                new_ko = dict(ko_sim_now)
                for _ in range(6):
                    res_tmp = cm.resolve_knockout_teams(ko_sched, bracket_slots,
                                                        ko_official, new_ko)
                    new_ko  = cm.simulate_all_knockout_pending(
                        res_tmp, ko_official, new_ko, state['elos'])
                st.session_state['copa_ko_sim'] = new_ko
                st.rerun()
        with kc2:
            if st.button('🗑️ Limpar Fase', key=f'clear_{phase_key}',
                         use_container_width=True,
                         help='Remove simulações desta fase'):
                _clr_ko = dict(ko_sim_now)
                for _pm in phase_matches:
                    _clr_ko.pop(_pm['id'], None)
                st.session_state['copa_ko_sim'] = _clr_ko
                st.rerun()

        n_grp_played = sum(
            1 for m in schedule
            if official_now.get(m['id']) or sim_now.get(m['id'])
        )
        if n_grp_played < len(schedule):
            st.info(
                f'ℹ️ {len(schedule) - n_grp_played} jogo(s) da fase de grupos sem resultado. '
                f'Use **"Simular Todos Pendentes"** acima para definir os classificados.'
            )

        st.markdown('<br>', unsafe_allow_html=True)

        for m in phase_matches:
            _render_ko_match(m, ko_official, ko_sim_now, bracket_slots, ko_sched, state['elos'])
