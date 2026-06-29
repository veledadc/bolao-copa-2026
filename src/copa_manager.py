"""
Copa 2026 match-state manager.

Two layers of match results:
  official  → data/copa_official.json  (locked forever, persisted)
  simulated → st.session_state['copa_sim']  (ephemeral, session only)
"""

from __future__ import annotations
import json, os
from datetime import datetime

OFFICIAL_FILE = os.path.join('data', 'copa_official.json')

# ── Country flags ────────────────────────────────────────────────────────────
TEAM_FLAGS: dict[str, str] = {
    'Mexico': '🇲🇽', 'South Africa': '🇿🇦', 'South Korea': '🇰🇷', 'Czechia': '🇨🇿',
    'Canada': '🇨🇦', 'Switzerland': '🇨🇭', 'Qatar': '🇶🇦', 'Bosnia Herzegovina': '🇧🇦',
    'Brazil': '🇧🇷', 'Morocco': '🇲🇦', 'Haiti': '🇭🇹', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
    'USA': '🇺🇸', 'Paraguay': '🇵🇾', 'Australia': '🇦🇺', 'Turkey': '🇹🇷',
    'Germany': '🇩🇪', 'Curacao': '🇨🇼', 'Ivory Coast': '🇨🇮', 'Ecuador': '🇪🇨',
    'Netherlands': '🇳🇱', 'Japan': '🇯🇵', 'Sweden': '🇸🇪', 'Tunisia': '🇹🇳',
    'Belgium': '🇧🇪', 'Egypt': '🇪🇬', 'Iran': '🇮🇷', 'New Zealand': '🇳🇿',
    'Spain': '🇪🇸', 'Cape Verde': '🇨🇻', 'Saudi Arabia': '🇸🇦', 'Uruguay': '🇺🇾',
    'France': '🇫🇷', 'Senegal': '🇸🇳', 'Iraq': '🇮🇶', 'Norway': '🇳🇴',
    'Argentina': '🇦🇷', 'Algeria': '🇩🇿', 'Austria': '🇦🇹', 'Jordan': '🇯🇴',
    'Portugal': '🇵🇹', 'DR Congo': '🇨🇩', 'Uzbekistan': '🇺🇿', 'Colombia': '🇨🇴',
    'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Croatia': '🇭🇷', 'Ghana': '🇬🇭', 'Panama': '🇵🇦',
}

# ── Group stage schedule ─────────────────────────────────────────────────────

_MD_DATES = {
    1: {'A': '2026-06-11', 'B': '2026-06-12', 'C': '2026-06-11', 'D': '2026-06-12',
        'E': '2026-06-13', 'F': '2026-06-14', 'G': '2026-06-13', 'H': '2026-06-14',
        'I': '2026-06-15', 'J': '2026-06-16', 'K': '2026-06-15', 'L': '2026-06-16'},
    2: {'A': '2026-06-19', 'B': '2026-06-20', 'C': '2026-06-19', 'D': '2026-06-20',
        'E': '2026-06-21', 'F': '2026-06-22', 'G': '2026-06-21', 'H': '2026-06-22',
        'I': '2026-06-23', 'J': '2026-06-24', 'K': '2026-06-23', 'L': '2026-06-24'},
    3: {'A': '2026-06-27', 'B': '2026-06-28', 'C': '2026-06-27', 'D': '2026-06-28',
        'E': '2026-06-29', 'F': '2026-06-30', 'G': '2026-06-29', 'H': '2026-06-30',
        'I': '2026-07-01', 'J': '2026-07-02', 'K': '2026-07-01', 'L': '2026-07-02'},
}

_GROUP_VENUES: dict[str, list] = {
    'A': [('Estadio Azteca', 'Mexico City', 'México'),   ('Estadio BBVA', 'Monterrey', 'México')],
    'B': [('BC Place', 'Vancouver', 'Canadá'),           ('BMO Field', 'Toronto', 'Canadá')],
    'C': [('AT&T Stadium', 'Dallas', 'EUA'),             ('NRG Stadium', 'Houston', 'EUA')],
    'D': [('SoFi Stadium', 'Los Angeles', 'EUA'),        ("Levi's Stadium", 'São Francisco', 'EUA')],
    'E': [('Mercedes-Benz Stadium', 'Atlanta', 'EUA'),   ('Hard Rock Stadium', 'Miami', 'EUA')],
    'F': [('MetLife Stadium', 'Nova York', 'EUA'),       ('Gillette Stadium', 'Boston', 'EUA')],
    'G': [('Soldier Field', 'Chicago', 'EUA'),           ('Arrowhead Stadium', 'Kansas City', 'EUA')],
    'H': [('Lincoln Financial Field', 'Filadélfia','EUA'),('AT&T Stadium', 'Dallas', 'EUA')],
    'I': [('Estadio Akron', 'Guadalajara', 'México'),    ('Estadio Azteca', 'Mexico City', 'México')],
    'J': [("Levi's Stadium", 'São Francisco', 'EUA'),    ('SoFi Stadium', 'Los Angeles', 'EUA')],
    'K': [('Gillette Stadium', 'Boston', 'EUA'),         ('MetLife Stadium', 'Nova York', 'EUA')],
    'L': [('NRG Stadium', 'Houston', 'EUA'),             ('Hard Rock Stadium', 'Miami', 'EUA')],
}

# MD1/2: pairs (i,j) of team indices; MD3: simultaneous last two matches
_MATCH_PAIRS: dict[int, list] = {1: [(0,1),(2,3)], 2: [(0,2),(1,3)], 3: [(0,3),(1,2)]}
_TIMES: dict[tuple, str] = {
    (1,0):'16:00',(1,1):'22:00',
    (2,0):'16:00',(2,1):'22:00',
    (3,0):'16:00',(3,1):'16:00',  # simultaneous in MD3
}


def generate_schedule() -> list[dict]:
    """Return list of 72 group stage match dicts."""
    from config import COPA_2026_GROUPS
    schedule: list[dict] = []
    match_num = 1
    for grp, teams in COPA_2026_GROUPS.items():
        for md in (1, 2, 3):
            base_date = _MD_DATES[md][grp]
            venues    = _GROUP_VENUES[grp]
            for pair_idx, (i, j) in enumerate(_MATCH_PAIRS[md]):
                stad, city, country = venues[pair_idx % len(venues)]
                schedule.append({
                    'id':       f'G_{grp}_MD{md}_{pair_idx+1}',
                    'num':      match_num,
                    'phase':    'group',
                    'group':    grp,
                    'matchday': md,
                    'date':     base_date,
                    'time_brt': _TIMES.get((md, pair_idx), '19:00'),
                    'home':     teams[i],
                    'away':     teams[j],
                    'stadium':  stad,
                    'city':     city,
                    'country':  country,
                })
                match_num += 1
    return schedule


# ── Knockout schedule ────────────────────────────────────────────────────────
# Each tuple: (id, phase, date, time_brt, slot_home, slot_away, stadium, city, country)
# IDs usam a numeração oficial FIFA das partidas (Match 73-104). Horários
# convertidos de ET para BRT (ET+1h, já que o Brasil não observa horário de
# verão). Estrutura, datas e locais conferidos cruzando a tabela oficial da
# FIFA (Wikipedia: 2026 FIFA World Cup knockout stage) com a cobertura da
# Fox Sports e worldcupwiki.com em 29/06/2026 — três fontes independentes.
_KO_ROWS = [
    # Rodada de 32 (Match 73-88) — 28/Jun a 03/Jul
    ('M73','r32','28/Jun','16:00','2A','2B','SoFi Stadium','Los Angeles','EUA'),
    ('M76','r32','29/Jun','14:00','1C','2F','NRG Stadium','Houston','EUA'),
    ('M74','r32','29/Jun','17:30','1E','3D','Gillette Stadium','Boston','EUA'),
    ('M75','r32','29/Jun','22:00','1F','2C','Estadio BBVA','Monterrey','México'),
    ('M78','r32','30/Jun','14:00','2E','2I','AT&T Stadium','Dallas','EUA'),
    ('M77','r32','30/Jun','18:00','1I','3F','MetLife Stadium','Nova York','EUA'),
    ('M79','r32','30/Jun','22:00','1A','3E','Estadio Azteca','Mexico City','México'),
    ('M80','r32','01/Jul','13:00','1L','3K','Mercedes-Benz Stadium','Atlanta','EUA'),
    ('M82','r32','01/Jul','17:00','1G','3I','Lumen Field','Seattle','EUA'),
    ('M81','r32','01/Jul','21:00','1D','3B',"Levi's Stadium",'São Francisco','EUA'),
    ('M84','r32','02/Jul','16:00','1H','2J','SoFi Stadium','Los Angeles','EUA'),
    ('M83','r32','02/Jul','20:00','2K','2L','BMO Field','Toronto','Canadá'),
    ('M85','r32','03/Jul','00:00','1B','3J','BC Place','Vancouver','Canadá'),
    ('M88','r32','03/Jul','15:00','2D','2G','AT&T Stadium','Dallas','EUA'),
    ('M86','r32','03/Jul','19:00','1J','2H','Hard Rock Stadium','Miami','EUA'),
    ('M87','r32','03/Jul','22:30','1K','3L','Arrowhead Stadium','Kansas City','EUA'),
    # Oitavas de Final (Match 89-96) — 04 a 07/Jul
    ('M90','r16','04/Jul','14:00','W_M73','W_M75','NRG Stadium','Houston','EUA'),
    ('M89','r16','04/Jul','18:00','W_M74','W_M77','Lincoln Financial Field','Filadélfia','EUA'),
    ('M91','r16','05/Jul','17:00','W_M76','W_M78','MetLife Stadium','Nova York','EUA'),
    ('M92','r16','05/Jul','21:00','W_M79','W_M80','Estadio Azteca','Mexico City','México'),
    ('M93','r16','06/Jul','16:00','W_M83','W_M84','AT&T Stadium','Dallas','EUA'),
    ('M94','r16','06/Jul','21:00','W_M81','W_M82','Lumen Field','Seattle','EUA'),
    ('M95','r16','07/Jul','13:00','W_M86','W_M88','Mercedes-Benz Stadium','Atlanta','EUA'),
    ('M96','r16','07/Jul','17:00','W_M85','W_M87','BC Place','Vancouver','Canadá'),
    # Quartas de Final (Match 97-100) — 09 a 11/Jul
    ('M97', 'qf','09/Jul','17:00','W_M89','W_M90','Gillette Stadium','Boston','EUA'),
    ('M98', 'qf','10/Jul','16:00','W_M93','W_M94','SoFi Stadium','Los Angeles','EUA'),
    ('M99', 'qf','11/Jul','18:00','W_M91','W_M92','Hard Rock Stadium','Miami','EUA'),
    ('M100','qf','11/Jul','22:00','W_M95','W_M96','Arrowhead Stadium','Kansas City','EUA'),
    # Semifinais (Match 101-102) — 14 e 15/Jul
    ('M101','sf','14/Jul','16:00','W_M97','W_M98','AT&T Stadium','Dallas','EUA'),
    ('M102','sf','15/Jul','16:00','W_M99','W_M100','Mercedes-Benz Stadium','Atlanta','EUA'),
    # Disputa de 3º Lugar (Match 103) — 18/Jul
    ('M103','tp','18/Jul','18:00','L_M101','L_M102','Hard Rock Stadium','Miami','EUA'),
    # Final (Match 104) — 19/Jul
    ('M104','final','19/Jul','16:00','W_M101','W_M102','MetLife Stadium','Nova York','EUA'),
]


def generate_knockout_schedule() -> list[dict]:
    """Return list of knockout match dicts with slot labels."""
    matches = []
    for row in _KO_ROWS:
        mid, phase, dt, t, sh, sa, stad, city, country = row
        matches.append({
            'id': mid, 'phase': phase, 'date': dt, 'time_brt': t,
            'slot_home': sh, 'slot_away': sa,
            'stadium': stad, 'city': city, 'country': country,
            'home': None, 'away': None,
        })
    return matches


# ── Official results persistence ──────────────────────────────────────────────

def load_official() -> dict:
    if not os.path.exists(OFFICIAL_FILE):
        return {}
    with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_official_result(match_id: str, home_score: int, away_score: int,
                         home: str | None = None, away: str | None = None) -> None:
    official = load_official()
    if match_id in official and official[match_id].get('locked'):
        raise ValueError(f'{match_id} already locked')
    entry = {
        'home_score': int(home_score),
        'away_score': int(away_score),
        'locked': True,
        'recorded_at': datetime.now().isoformat(),
    }
    if home:
        entry['home'] = home
    if away:
        entry['away'] = away
    official[match_id] = entry
    os.makedirs('data', exist_ok=True)
    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(official, f, indent=2)


def update_official_result(match_id: str, home_score: int, away_score: int) -> None:
    """Overwrite a previously locked result (used by the edit panel)."""
    official = load_official()
    existing = official.get(match_id, {})
    existing.update({
        'home_score': int(home_score),
        'away_score': int(away_score),
        'locked': True,
        'updated_at': datetime.now().isoformat(),
    })
    official[match_id] = existing
    os.makedirs('data', exist_ok=True)
    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(official, f, indent=2)


def delete_official_result(match_id: str) -> None:
    """Remove a recorded result entirely (used by the edit panel)."""
    official = load_official()
    official.pop(match_id, None)
    os.makedirs('data', exist_ok=True)
    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(official, f, indent=2)


def rebuild_elo_from_officials() -> dict:
    """
    Rebuild ELO state from historical data + manual results, then re-apply
    all Copa 2026 official results in recorded order.
    Returns the new state (also saves it to disk).
    """
    from src import state_manager as sm

    base_state = sm.get_or_build_state(force_rebuild=True)

    official = load_official()
    if not official:
        return base_state

    schedule = generate_schedule()
    id_to_teams: dict[str, tuple[str, str]] = {}
    for m in schedule:
        id_to_teams[m['id']] = (m['home'], m['away'])

    # Sort by recorded_at so we re-apply in original order
    sorted_items = sorted(
        official.items(),
        key=lambda kv: kv[1].get('recorded_at', ''),
    )

    state = base_state
    for mid, res in sorted_items:
        # Try team names stored in the record first, then schedule lookup
        home = res.get('home') or id_to_teams.get(mid, (None, None))[0]
        away = res.get('away') or id_to_teams.get(mid, (None, None))[1]
        if home and away:
            state = sm.apply_result(
                state, home, away,
                int(res['home_score']), int(res['away_score']),
                'FIFA World Cup', neutral=True,
            )

    sm.save_state(state)
    return state


# ── Group standings computation ───────────────────────────────────────────────

def compute_group_standings(schedule: list, official: dict, simulated: dict) -> dict:
    """
    Returns dict per group with sorted standings and match details.
    """
    from config import COPA_2026_GROUPS
    standings: dict = {}
    for grp, teams in COPA_2026_GROUPS.items():
        standings[grp] = {
            'teams': list(teams),
            'points': {t: 0 for t in teams},
            'gd':     {t: 0 for t in teams},
            'gf':     {t: 0 for t in teams},
            'played': {t: 0 for t in teams},
            'sorted': list(teams),
            'matches': [],
        }

    for m in schedule:
        if m['phase'] != 'group':
            continue
        grp = m['group']
        mid = m['id']
        home, away = m['home'], m['away']
        s = standings[grp]

        result = official.get(mid) or simulated.get(mid)
        if result:
            hs, as_ = int(result['home_score']), int(result['away_score'])
            status  = 'official' if mid in official else 'simulated'
            if hs > as_:
                s['points'][home] += 3
            elif hs == as_:
                s['points'][home] += 1
                s['points'][away] += 1
            else:
                s['points'][away] += 3
            s['gd'][home] += hs - as_;  s['gd'][away] += as_ - hs
            s['gf'][home] += hs;        s['gf'][away] += as_
            s['played'][home] += 1;     s['played'][away] += 1
            s['matches'].append({**m, 'hs': hs, 'as': as_, 'status': status})
        else:
            s['matches'].append({**m, 'hs': None, 'as': None, 'status': 'pending'})

    for grp in standings:
        s = standings[grp]
        s['sorted'] = sorted(
            s['teams'],
            key=lambda t: (s['points'][t], s['gd'][t], s['gf'][t]),
            reverse=True,
        )
    return standings


# ── Best thirds and bracket resolution ───────────────────────────────────────

def get_best_thirds(standings: dict, n: int = 8) -> list[dict]:
    thirds = []
    for grp, s in standings.items():
        if len(s['sorted']) >= 3:
            t = s['sorted'][2]
            thirds.append({'team': t, 'group': grp,
                           'pts': s['points'][t], 'gd': s['gd'][t], 'gf': s['gf'][t]})
    thirds.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)
    return thirds[:n]


def resolve_bracket_slots(standings: dict) -> dict[str, str | None]:
    """Map slot keys like '1A', '2B', '3rd_1' to actual team names (or None)."""
    slots: dict[str, str | None] = {}
    thirds = get_best_thirds(standings, 8)

    for grp, s in standings.items():
        st = s['sorted']
        if len(st) >= 1: slots[f'1{grp}'] = st[0]
        if len(st) >= 2: slots[f'2{grp}'] = st[1]
        if len(st) >= 3: slots[f'3{grp}'] = st[2]

    for i, entry in enumerate(thirds):
        slots[f'3rd_{i+1}'] = entry['team']

    return slots


def resolve_knockout_teams(
    ko_schedule: list[dict],
    bracket_slots: dict,
    ko_official: dict,
    ko_simulated: dict,
) -> list[dict]:
    """
    Fill home/away team names into knockout matches.

    Uses multi-pass propagation: each pass uses newly decided results to fill
    slots for subsequent rounds, handling up to 6 rounds (R32→Final).
    """
    # Start: resolve only direct group-stage slots
    resolved = []
    for m in ko_schedule:
        mc = dict(m)
        mc['home'] = bracket_slots.get(m['slot_home'])
        mc['away'] = bracket_slots.get(m['slot_away'])
        resolved.append(mc)

    # Iterative propagation: run enough passes for R32→R16→QF→SF→3P→F
    for _ in range(8):
        winners: dict[str, str] = {}
        losers:  dict[str, str] = {}
        for m in resolved:
            mid = m['id']
            res = ko_official.get(mid) or ko_simulated.get(mid)
            if res and m.get('home') and m.get('away'):
                hs, as_ = int(res['home_score']), int(res['away_score'])
                if hs > as_:
                    winners[f'W_{mid}'] = m['home']
                    losers [f'L_{mid}'] = m['away']
                else:
                    winners[f'W_{mid}'] = m['away']
                    losers [f'L_{mid}'] = m['home']

        new_resolved = []
        for m in resolved:
            mc = dict(m)
            if not mc.get('home'):
                mc['home'] = (bracket_slots.get(m['slot_home'])
                              or winners.get(m['slot_home'])
                              or losers.get(m['slot_home']))
            if not mc.get('away'):
                mc['away'] = (bracket_slots.get(m['slot_away'])
                              or winners.get(m['slot_away'])
                              or losers.get(m['slot_away']))
            new_resolved.append(mc)
        resolved = new_resolved

    return resolved


# ── Match simulation ──────────────────────────────────────────────────────────

def simulate_match_score(
    home: str, away: str,
    elos: dict,
    form: dict | None = None,
    copa_history: dict | None = None,
) -> tuple[int, int]:
    """Return (home_goals, away_goals) for a simulated match."""
    import numpy as np
    from src.elo import win_probability

    form         = form         or {}
    copa_history = copa_history or {}

    ea = elos.get(home, 1500)
    eb = elos.get(away, 1500)

    prob_a = win_probability(ea, eb, neutral=True)
    draw_p = max(0.08, 0.26 - abs(prob_a - 0.5) * 0.45)
    win_ap = (1.0 - draw_p) * prob_a

    r = np.random.random()
    if r < win_ap:
        ga = max(1, np.random.poisson(1.7))
        gb = max(0, min(ga - 1, np.random.poisson(0.7)))
    elif r < win_ap + draw_p:
        ga = np.random.poisson(1.1)
        gb = ga
    else:
        gb = max(1, np.random.poisson(1.7))
        ga = max(0, min(gb - 1, np.random.poisson(0.7)))

    return int(ga), int(gb)


def simulate_all_pending(
    schedule: list[dict],
    official: dict,
    simulated: dict,
    elos: dict,
) -> dict:
    """Simulate every pending group match and return updated simulated dict."""
    new_sim = dict(simulated)
    for m in schedule:
        if m['phase'] != 'group':
            continue
        mid = m['id']
        if mid not in official and mid not in new_sim:
            ga, gb = simulate_match_score(m['home'], m['away'], elos)
            new_sim[mid] = {'home_score': ga, 'away_score': gb}
    return new_sim


def simulate_all_knockout_pending(
    ko_schedule: list[dict],
    ko_official: dict,
    ko_simulated: dict,
    elos: dict,
) -> dict:
    """Simulate every pending knockout match (only if both teams are known)."""
    new_sim = dict(ko_simulated)
    for m in ko_schedule:
        mid = m['id']
        if mid in ko_official or mid in new_sim:
            continue
        if m.get('home') and m.get('away'):
            ga, gb = simulate_match_score(m['home'], m['away'], elos)
            new_sim[mid] = {'home_score': ga, 'away_score': gb}
    return new_sim


# ── TV channels (Brazil) ─────────────────────────────────────────────────────

_BIG_TEAMS = {
    'Brazil','Argentina','France','England','Germany','Spain','Portugal',
    'Netherlands','Uruguay','Belgium','Croatia','Colombia','Mexico','USA',
}

TV_INFO = {
    'TV Globo':  {'css': 'tv-globo',   'url': 'https://globoplay.globo.com'},
    'SporTV':    {'css': 'tv-sportv',  'url': 'https://globoplay.globo.com/sportv'},
    'CazéTV':    {'css': 'tv-cazé',    'url': 'https://www.youtube.com/@CazéTV'},
    'Globoplay': {'css': 'tv-globoplay','url': 'https://globoplay.globo.com'},
    'FIFA+':     {'css': 'tv-fifaplus', 'url': 'https://www.fifa.com/fifaplus'},
}


def get_tv_channels(home: str | None, away: str | None, phase: str) -> list[str]:
    if not home or not away:
        return ['Globoplay']
    channels: list[str] = []
    if 'Brazil' in (home, away) or phase in ('sf', 'final'):
        channels.append('TV Globo')
    if home in _BIG_TEAMS or away in _BIG_TEAMS or phase in ('qf', 'sf', 'final'):
        channels.append('SporTV')
    if phase in ('group', 'r32') and 'Brazil' not in (home, away):
        channels.append('CazéTV')
    channels.append('Globoplay')
    return list(dict.fromkeys(channels))


def tv_html(home: str | None, away: str | None, phase: str) -> str:
    """Return HTML string of clickable TV chip badges."""
    channels = get_tv_channels(home, away, phase)
    parts = []
    for c in channels:
        info = TV_INFO.get(c, {'css': '', 'url': '#'})
        parts.append(
            f'<a href="{info["url"]}" target="_blank" style="text-decoration:none">'
            f'<span class="tv-chip {info["css"]}">{c}</span></a>'
        )
    return ' '.join(parts)
