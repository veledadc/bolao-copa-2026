"""
Gerenciamento incremental de estado do modelo.

Separa duas operações de custo radicalmente diferente:

  build_state(df)       → O(n_historico)  — rode uma vez, salva em JSON
  apply_result(state)   → O(1)            — rode a cada novo placar cadastrado

O estado persistido em data/state.json contém:
  - elos          : rating atual de cada seleção
  - form          : últimos 10 resultados competitivos por seleção
  - copa_history  : estatísticas históricas de Copa por seleção
  - state_hash    : MD5 dos elos — invalida cache de simulação automaticamente
  - meta          : timestamps e contagens para auditoria
"""

import json
import os
import hashlib
from datetime import datetime

import pandas as pd

from config import DATA_DIR

_STATE_FILE = os.path.join(DATA_DIR, 'state.json')


# ── Persistência ─────────────────────────────────────────────────────────────

def load_state() -> dict | None:
    """Carrega estado do disco. Retorna None se inexistente."""
    if not os.path.exists(_STATE_FILE):
        return None
    with open(_STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_state(state: dict) -> None:
    """Persiste estado no disco."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str, ensure_ascii=False)


def state_file_mtime() -> float:
    """mtime de state.json, ou 0 se ainda não existir.

    Usado como chave de cache do Streamlit: quando um processo externo
    (ex.: o sync diário de resultados) regrava state.json, o mtime muda e
    invalida o cache em memória de uma sessão já aberta no navegador.
    """
    return os.path.getmtime(_STATE_FILE) if os.path.exists(_STATE_FILE) else 0.0


def _hash_elos(elos: dict) -> str:
    raw = json.dumps(sorted(elos.items()), ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Construção inicial do estado (batch) ─────────────────────────────────────

def build_state(df: pd.DataFrame) -> dict:
    """
    Computa o estado completo a partir do DataFrame histórico.
    Operação lenta (O(n)) — executar uma vez e persistir.
    """
    from src.elo import calculate_elo_ratings
    from src.features import calculate_recent_form, calculate_copa_history

    elos         = calculate_elo_ratings(df)
    form         = calculate_recent_form(df)
    copa_history = calculate_copa_history(df)

    state = {
        'elos':         elos,
        'form':         form,
        'copa_history': copa_history,
        'meta': {
            'n_matches':      len(df),
            'last_rebuilt':   str(datetime.now()),
            'last_updated':   str(datetime.now()),
            'n_manual':       0,
        },
        'state_hash': _hash_elos(elos),
    }
    return state


def build_default_state() -> dict:
    """
    Estado de demonstração usando ratings padrão do config.
    Usado quando não há dados históricos baixados.
    """
    from config import DEFAULT_ELO_RATINGS, COPA_TITLES

    copa_history = {
        'Brazil':    {'win_rate': 0.670, 'goal_ratio': 1.97, 'matches': 114, 'wins': 76, 'draws': 20, 'losses': 18, 'goals_for': 229, 'goals_against': 102, 'titles': 5,  'experience_tier': 'elite'},
        'Germany':   {'win_rate': 0.636, 'goal_ratio': 2.23, 'matches': 109, 'wins': 69, 'draws': 21, 'losses': 19, 'goals_for': 227, 'goals_against': 125, 'titles': 4,  'experience_tier': 'elite'},
        'Italy':     {'win_rate': 0.620, 'goal_ratio': 2.20, 'matches': 83,  'wins': 51, 'draws': 21, 'losses': 11, 'goals_for': 129, 'goals_against': 77,  'titles': 4,  'experience_tier': 'elite'},
        'Argentina': {'win_rate': 0.623, 'goal_ratio': 1.98, 'matches': 87,  'wins': 54, 'draws': 17, 'losses': 16, 'goals_for': 145, 'goals_against': 97,  'titles': 3,  'experience_tier': 'elite'},
        'France':    {'win_rate': 0.560, 'goal_ratio': 1.71, 'matches': 75,  'wins': 42, 'draws': 18, 'losses': 15, 'goals_for': 141, 'goals_against': 79,  'titles': 2,  'experience_tier': 'elite'},
        'England':   {'win_rate': 0.520, 'goal_ratio': 1.72, 'matches': 69,  'wins': 36, 'draws': 20, 'losses': 13, 'goals_for': 100, 'goals_against': 68,  'titles': 1,  'experience_tier': 'elite'},
        'Spain':     {'win_rate': 0.561, 'goal_ratio': 1.98, 'matches': 66,  'wins': 37, 'draws': 12, 'losses': 17, 'goals_for': 110, 'goals_against': 73,  'titles': 1,  'experience_tier': 'elite'},
        'Uruguay':   {'win_rate': 0.520, 'goal_ratio': 1.64, 'matches': 56,  'wins': 29, 'draws': 15, 'losses': 12, 'goals_for': 95,  'goals_against': 70,  'titles': 2,  'experience_tier': 'elite'},
        'Portugal':  {'win_rate': 0.490, 'goal_ratio': 1.52, 'matches': 37,  'wins': 18, 'draws': 8,  'losses': 11, 'goals_for': 67,  'goals_against': 52,  'titles': 0,  'experience_tier': 'experienced'},
        'Netherlands':{'win_rate':0.530, 'goal_ratio': 1.93, 'matches': 50,  'wins': 26, 'draws': 10, 'losses': 14, 'goals_for': 88,  'goals_against': 59,  'titles': 0,  'experience_tier': 'elite'},
        'Croatia':   {'win_rate': 0.500, 'goal_ratio': 1.62, 'matches': 28,  'wins': 14, 'draws': 6,  'losses': 8,  'goals_for': 43,  'goals_against': 36,  'titles': 0,  'experience_tier': 'experienced'},
        'Belgium':   {'win_rate': 0.470, 'goal_ratio': 1.68, 'matches': 47,  'wins': 22, 'draws': 11, 'losses': 14, 'goals_for': 81,  'goals_against': 64,  'titles': 0,  'experience_tier': 'elite'},
        'Colombia':  {'win_rate': 0.440, 'goal_ratio': 1.58, 'matches': 27,  'wins': 12, 'draws': 5,  'losses': 10, 'goals_for': 44,  'goals_against': 36,  'titles': 0,  'experience_tier': 'experienced'},
        'Mexico':    {'win_rate': 0.430, 'goal_ratio': 1.35, 'matches': 58,  'wins': 25, 'draws': 11, 'losses': 22, 'goals_for': 81,  'goals_against': 98,  'titles': 0,  'experience_tier': 'elite'},
        'USA':       {'win_rate': 0.380, 'goal_ratio': 1.21, 'matches': 37,  'wins': 14, 'draws': 7,  'losses': 16, 'goals_for': 55,  'goals_against': 69,  'titles': 0,  'experience_tier': 'experienced'},
        'Japan':     {'win_rate': 0.360, 'goal_ratio': 1.14, 'matches': 25,  'wins': 9,  'draws': 5,  'losses': 11, 'goals_for': 30,  'goals_against': 36,  'titles': 0,  'experience_tier': 'experienced'},
        'Morocco':   {'win_rate': 0.370, 'goal_ratio': 1.22, 'matches': 22,  'wins': 8,  'draws': 6,  'losses': 8,  'goals_for': 24,  'goals_against': 26,  'titles': 0,  'experience_tier': 'experienced'},
        'South Korea':{'win_rate':0.330, 'goal_ratio': 1.08, 'matches': 35,  'wins': 11, 'draws': 9,  'losses': 15, 'goals_for': 50,  'goals_against': 70,  'titles': 0,  'experience_tier': 'experienced'},
        'Switzerland':{'win_rate':0.400, 'goal_ratio': 1.31, 'matches': 30,  'wins': 12, 'draws': 7,  'losses': 11, 'goals_for': 50,  'goals_against': 54,  'titles': 0,  'experience_tier': 'experienced'},
        'Ecuador':   {'win_rate': 0.340, 'goal_ratio': 1.19, 'matches': 12,  'wins': 4,  'draws': 3,  'losses': 5,  'goals_for': 14,  'goals_against': 17,  'titles': 0,  'experience_tier': 'moderate'},
        'Australia': {'win_rate': 0.360, 'goal_ratio': 1.19, 'matches': 14,  'wins': 5,  'draws': 3,  'losses': 6,  'goals_for': 20,  'goals_against': 25,  'titles': 0,  'experience_tier': 'moderate'},
        'Senegal':   {'win_rate': 0.370, 'goal_ratio': 1.26, 'matches': 11,  'wins': 4,  'draws': 4,  'losses': 3,  'goals_for': 13,  'goals_against': 11,  'titles': 0,  'experience_tier': 'moderate'},
        'Ghana':     {'win_rate': 0.360, 'goal_ratio': 1.22, 'matches': 14,  'wins': 5,  'draws': 2,  'losses': 7,  'goals_for': 18,  'goals_against': 24,  'titles': 0,  'experience_tier': 'moderate'},
        'Iran':      {'win_rate': 0.230, 'goal_ratio': 0.76, 'matches': 18,  'wins': 4,  'draws': 3,  'losses': 11, 'goals_for': 16,  'goals_against': 36,  'titles': 0,  'experience_tier': 'moderate'},
        'Saudi Arabia':{'win_rate':0.230,'goal_ratio': 0.82, 'matches': 17,  'wins': 4,  'draws': 2,  'losses': 11, 'goals_for': 16,  'goals_against': 36,  'titles': 0,  'experience_tier': 'moderate'},
    }

    state = {
        'elos':         dict(DEFAULT_ELO_RATINGS),
        'form':         {},
        'copa_history': copa_history,
        'meta': {
            'n_matches':    0,
            'last_rebuilt': str(datetime.now()),
            'last_updated': str(datetime.now()),
            'n_manual':     0,
            'mode':         'demo',
        },
        'state_hash': _hash_elos(dict(DEFAULT_ELO_RATINGS)),
    }
    return state


# ── Atualização incremental (O(1)) ───────────────────────────────────────────

def apply_result(
    state: dict,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    tournament: str,
    neutral: bool = True,
) -> dict:
    """
    Aplica um único resultado ao estado sem reprocessar o histórico.

    Atualiza:
      1. Elo dos dois times (δ = K × (resultado - esperado))
      2. Forma recente (apenas partidas competitivas)
      3. Histórico de Copa (se for jogo de Copa do Mundo)
      4. state_hash (invalida cache de simulação automaticamente)
    """
    from src.elo import update_elo

    elos         = state['elos']
    form         = state.get('form', {})
    copa_history = state.get('copa_history', {})

    # 1. Atualiza Elo
    old_h = elos.get(home, 1500)
    old_a = elos.get(away, 1500)
    new_h, new_a = update_elo(old_h, old_a, home_score, away_score,
                               tournament, neutral)
    elos[home] = new_h
    elos[away] = new_a

    # 2. Atualiza forma (ignora amistosos de baixo peso)
    t_lower = tournament.lower()
    is_competitive = ('friendly' not in t_lower and 'amistoso' not in t_lower)

    if is_competitive:
        hr = 'W' if home_score > away_score else ('D' if home_score == away_score else 'L')
        ar = 'L' if home_score > away_score else ('D' if home_score == away_score else 'W')

        form.setdefault(home, []).append(hr)
        form.setdefault(away, []).append(ar)
        form[home] = form[home][-10:]
        form[away] = form[away][-10:]

    # 3. Atualiza histórico de Copa
    if 'world cup' in t_lower and 'qualif' not in t_lower:
        for team, gf, ga in [(home, home_score, away_score),
                              (away, away_score, home_score)]:
            h = copa_history.setdefault(team, {
                'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                'goals_for': 0, 'goals_against': 0,
                'win_rate': 0.0, 'goal_ratio': 1.0, 'titles': 0,
                'experience_tier': 'limited',
            })
            h['matches']       += 1
            h['goals_for']     += gf
            h['goals_against'] += ga
            if gf > ga:    h['wins']   += 1
            elif gf == ga: h['draws']  += 1
            else:          h['losses'] += 1
            m = h['matches']
            h['win_rate']   = round(h['wins'] / m, 4)
            h['goal_ratio'] = round(h['goals_for'] / max(h['goals_against'], 1), 3)
            h['experience_tier'] = (
                'elite' if m >= 50 else 'experienced' if m >= 25
                else 'moderate' if m >= 10 else 'limited'
            )

    # 4. Atualiza meta e hash
    state['elos']         = elos
    state['form']         = form
    state['copa_history'] = copa_history
    state['state_hash']   = _hash_elos(elos)
    meta = state.setdefault('meta', {})
    meta['last_updated'] = str(datetime.now())
    meta['n_manual'] = meta.get('n_manual', 0) + 1

    return state


# ── Helper para Streamlit ─────────────────────────────────────────────────────

def get_or_build_state(force_rebuild: bool = False) -> dict:
    """
    Carrega o estado do disco ou reconstrói se necessário.

    Fluxo:
      1. Se state.json existe e não forçar rebuild → carrega (rápido)
      2. Se há dados históricos (results.csv) → reconstrói e salva
      3. Caso contrário → usa estado de demonstração (ratings padrão)
    """
    from config import HISTORICAL_RESULTS_FILE
    from src.data_loader import get_all_results

    if not force_rebuild:
        state = load_state()
        if state is not None:
            return state

    if os.path.exists(HISTORICAL_RESULTS_FILE):
        df    = get_all_results()
        state = build_state(df)
    else:
        state = build_default_state()

    save_state(state)
    return state
