"""
Cálculo de features derivadas para o modelo de previsão.

Módulo responsável por:
- Forma recente ponderada por nível de torneio
- Histórico específico de Copa do Mundo
- Funções auxiliares de score e bônus de Elo
"""

import pandas as pd
from config import COPA_TITLES


# ── Pesos por tipo de torneio (forma recente) ────────────────────────────────

_TOURNAMENT_WEIGHTS: dict[str, float] = {
    'FIFA World Cup':                  1.00,
    'Copa América':                    0.90,
    'UEFA Euro':                       0.90,
    'UEFA European Championship':      0.90,
    'Africa Cup of Nations':           0.85,
    'AFC Asian Cup':                   0.85,
    'CONCACAF Gold Cup':               0.80,
    'OFC Nations Cup':                 0.75,
    'FIFA World Cup qualification':    0.80,
    'UEFA Nations League':             0.75,
    'FIFA Confederations Cup':         0.85,
    'Friendly':                        0.30,
}

_FRIENDLY_THRESHOLD = 0.40   # torneios com peso abaixo disso são ignorados na forma


def _tournament_weight(tournament: str) -> float:
    t = str(tournament)
    for key, w in _TOURNAMENT_WEIGHTS.items():
        if key.lower() in t.lower():
            return w
    return 0.55   # torneio desconhecido → peso moderado


# ── Forma Recente ────────────────────────────────────────────────────────────

def calculate_recent_form(df: pd.DataFrame, window: int = 10) -> dict:
    """
    Calcula a forma recente de cada seleção a partir do histórico.

    Inclui apenas partidas de torneios com peso ≥ _FRIENDLY_THRESHOLD
    (elimina amistosos de baixa relevância).

    Retorna
    -------
    dict: team → list de até `window` resultados ['W', 'D', 'L', ...]
          ordenados do mais antigo ao mais recente.
    """
    df = df.sort_values('date').reset_index(drop=True)
    form: dict[str, list] = {}

    for _, row in df.iterrows():
        tournament = str(row.get('tournament', 'Friendly'))
        if _tournament_weight(tournament) < _FRIENDLY_THRESHOLD:
            continue

        home = str(row['home_team'])
        away = str(row['away_team'])

        try:
            hs, as_ = int(row['home_score']), int(row['away_score'])
        except (ValueError, TypeError):
            continue

        home_r = 'W' if hs > as_ else ('D' if hs == as_ else 'L')
        away_r = 'L' if hs > as_ else ('D' if hs == as_ else 'W')

        form.setdefault(home, []).append(home_r)
        form.setdefault(away, []).append(away_r)

        form[home] = form[home][-window:]
        form[away] = form[away][-window:]

    return form


def form_score(results: list, last_n: int = 5) -> float:
    """
    Converte lista de resultados em score [0, 1].
    W=1.0, D=0.5, L=0.0. Retorna 0.5 (neutro) se lista vazia.
    """
    if not results:
        return 0.5
    recent = results[-last_n:]
    score_map = {'W': 1.0, 'D': 0.5, 'L': 0.0}
    return sum(score_map[r] for r in recent) / len(recent)


def form_summary(results: list, last_n: int = 5) -> str:
    """Retorna string visual da forma, ex: 'WWDLW'."""
    return ''.join(results[-last_n:]) if results else '-'


# ── Histórico de Copa do Mundo ───────────────────────────────────────────────

def calculate_copa_history(df: pd.DataFrame) -> dict:
    """
    Calcula estatísticas históricas de Copa do Mundo por seleção,
    usando o dataset de resultados internacionais (martj42).

    Filtra apenas 'FIFA World Cup' excluindo qualificatórias.

    Retorna
    -------
    dict: team → {
        matches, wins, draws, losses,
        goals_for, goals_against,
        win_rate, goal_ratio,
        titles, experience_tier
    }
    """
    mask = (
        df['tournament'].str.contains('FIFA World Cup', na=False, case=False) &
        ~df['tournament'].str.contains('qualif', na=False, case=False)
    )
    copa_df = df[mask].copy()

    history: dict[str, dict] = {}

    for _, row in copa_df.iterrows():
        try:
            hs, as_ = int(row['home_score']), int(row['away_score'])
        except (ValueError, TypeError):
            continue

        for team, gf, ga in [
            (str(row['home_team']), hs, as_),
            (str(row['away_team']), as_, hs),
        ]:
            h = history.setdefault(team, {
                'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                'goals_for': 0, 'goals_against': 0,
            })
            h['matches']       += 1
            h['goals_for']     += gf
            h['goals_against'] += ga
            if gf > ga:   h['wins']   += 1
            elif gf == ga: h['draws']  += 1
            else:          h['losses'] += 1

    # Campos derivados
    for team, h in history.items():
        m = h['matches']
        h['win_rate']   = round(h['wins'] / m, 4) if m > 0 else 0.0
        h['goal_ratio'] = round(h['goals_for'] / max(h['goals_against'], 1), 3)
        h['titles']     = COPA_TITLES.get(team, 0)
        h['experience_tier'] = (
            'elite'       if m >= 50 else
            'experienced' if m >= 25 else
            'moderate'    if m >= 10 else
            'limited'
        )

    return history


# ── Funções de bônus de Elo ──────────────────────────────────────────────────

def form_elo_bonus(results: list, max_bonus: float = 30.0, last_n: int = 5) -> float:
    """
    Bônus de Elo por forma recente (max ±max_bonus pontos).
    Score 0.5 (neutro) → 0 bônus.
    Score 1.0 (5W)     → +max_bonus
    Score 0.0 (5L)     → -max_bonus
    """
    return (form_score(results, last_n) - 0.5) * 2.0 * max_bonus


def copa_elo_bonus(copa_hist: dict,
                   baseline_wr: float = 0.40,
                   max_bonus: float = 12.0) -> float:
    """
    Bônus de Elo por histórico de Copa (max ±max_bonus pontos).
    Win rate 40% → 0; acima → positivo; times sem história → leve penalidade.
    """
    if not copa_hist:
        return -max_bonus * 0.35

    wr      = copa_hist.get('win_rate', 0.0)
    titles  = copa_hist.get('titles', 0)
    raw     = (wr - baseline_wr) / max(1 - baseline_wr, 0.01) * max_bonus
    raw    += titles * 1.5
    return max(-max_bonus, min(max_bonus, raw))


# ── Resumo de features por time (útil para UI) ───────────────────────────────

def team_feature_summary(team: str, elos: dict, form: dict,
                          copa_history: dict) -> dict:
    """Agrega todas as features de um time num único dict para display."""
    results     = form.get(team, [])
    copa_hist   = copa_history.get(team, {})

    return {
        'elo':           round(elos.get(team, 1500)),
        'form_l5':       form_summary(results, 5),
        'form_score_l5': round(form_score(results, 5), 3),
        'form_bonus':    round(form_elo_bonus(results), 1),
        'copa_matches':  copa_hist.get('matches', 0),
        'copa_wr':       round(copa_hist.get('win_rate', 0.0) * 100, 1),
        'copa_titles':   copa_hist.get('titles', 0),
        'copa_tier':     copa_hist.get('experience_tier', 'none'),
        'copa_bonus':    round(copa_elo_bonus(copa_hist), 1),
        'effective_elo': round(
            elos.get(team, 1500)
            + form_elo_bonus(results)
            + copa_elo_bonus(copa_hist)
        ),
    }
