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
_KO_ROWS = [
    # Round of 32
    ('R32_01','r32','04/Jul','16:00','1A','2B','AT&T Stadium','Dallas','EUA'),
    ('R32_02','r32','04/Jul','22:00','1C','2D','MetLife Stadium','Nova York','EUA'),
    ('R32_03','r32','05/Jul','16:00','1E','2F','SoFi Stadium','Los Angeles','EUA'),
    ('R32_04','r32','05/Jul','22:00','1G','2H','Mercedes-Benz Stadium','Atlanta','EUA'),
    ('R32_05','r32','06/Jul','16:00','1I','2J',"Levi's Stadium",'São Francisco','EUA'),
    ('R32_06','r32','06/Jul','22:00','1K','2L','NRG Stadium','Houston','EUA'),
    ('R32_07','r32','07/Jul','16:00','1B','2A','BC Place','Vancouver','Canadá'),
    ('R32_08','r32','07/Jul','22:00','1D','2C','Estadio Azteca','Mexico City','México'),
    ('R32_09','r32','08/Jul','16:00','1F','2E','Gillette Stadium','Boston','EUA'),
    ('R32_10','r32','08/Jul','22:00','1H','2G','Arrowhead Stadium','Kansas City','EUA'),
    ('R32_11','r32','09/Jul','16:00','1J','2I','Estadio BBVA','Monterrey','México'),
    ('R32_12','r32','09/Jul','22:00','1L','2K','Hard Rock Stadium','Miami','EUA'),
    ('R32_13','r32','10/Jul','16:00','3rd_1','3rd_5','Lincoln Financial Field','Filadélfia','EUA'),
    ('R32_14','r32','10/Jul','22:00','3rd_2','3rd_6','Soldier Field','Chicago','EUA'),
    ('R32_15','r32','11/Jul','16:00','3rd_3','3rd_7','BMO Field','Toronto','Canadá'),
    ('R32_16','r32','11/Jul','22:00','3rd_4','3rd_8','SoFi Stadium','Los Angeles','EUA'),
    # Round of 16
    ('R16_01','r16','13/Jul','16:00','W_R32_01','W_R32_02','AT&T Stadium','Dallas','EUA'),
    ('R16_02','r16','13/Jul','22:00','W_R32_03','W_R32_04','MetLife Stadium','Nova York','EUA'),
    ('R16_03','r16','14/Jul','16:00','W_R32_05','W_R32_06',"Levi's Stadium",'São Francisco','EUA'),
    ('R16_04','r16','14/Jul','22:00','W_R32_07','W_R32_08','Estadio Azteca','Mexico City','México'),
    ('R16_05','r16','15/Jul','16:00','W_R32_09','W_R32_10','NRG Stadium','Houston','EUA'),
    ('R16_06','r16','15/Jul','22:00','W_R32_11','W_R32_12','Gillette Stadium','Boston','EUA'),
    ('R16_07','r16','16/Jul','16:00','W_R32_13','W_R32_14','SoFi Stadium','Los Angeles','EUA'),
    ('R16_08','r16','16/Jul','22:00','W_R32_15','W_R32_16','Mercedes-Benz Stadium','Atlanta','EUA'),
    # Quarterfinals
    ('QF_01','qf','18/Jul','16:00','W_R16_01','W_R16_02','MetLife Stadium','Nova York','EUA'),
    ('QF_02','qf','18/Jul','22:00','W_R16_03','W_R16_04','AT&T Stadium','Dallas','EUA'),
    ('QF_03','qf','19/Jul','16:00','W_R16_05','W_R16_06','SoFi Stadium','Los Angeles','EUA'),
    ('QF_04','qf','19/Jul','22:00','W_R16_07','W_R16_08','NRG Stadium','Houston','EUA'),
    # Semifinals
    ('SF_01','sf','22/Jul','22:00','W_QF_01','W_QF_02','MetLife Stadium','Nova York','EUA'),
    ('SF_02','sf','23/Jul','22:00','W_QF_03','W_QF_04','AT&T Stadium','Dallas','EUA'),
    # Third place
    ('TP',  'tp','25/Jul','16:00','L_SF_01','L_SF_02','Arrowhead Stadium','Kansas City','EUA'),
    # Final
    ('F', 'final','26/Jul','17:00','W_SF_01','W_SF_02','MetLife Stadium','Nova York','EUA'),
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


def save_official_result(match_id: str, home_score: int, away_score: int) -> None:
    official = load_official()
    if match_id in official and official[match_id].get('locked'):
        raise ValueError(f'{match_id} already locked')
    official[match_id] = {
        'home_score': int(home_score),
        'away_score': int(away_score),
        'locked': True,
        'recorded_at': datetime.now().isoformat(),
    }
    os.makedirs('data', exist_ok=True)
    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(official, f, indent=2)


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
