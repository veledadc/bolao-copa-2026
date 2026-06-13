"""
Sistema de Elo Rating para seleções de futebol.
"""
import numpy as np
import pandas as pd
from config import BASE_ELO, HOME_ADVANTAGE, K_FACTORS, DEFAULT_K, DEFAULT_ELO_RATINGS


def get_k_factor(tournament: str) -> float:
    t = tournament.strip()
    for key, k in K_FACTORS.items():
        if key.lower() in t.lower():
            return k
    return DEFAULT_K


def win_probability(elo_a: float, elo_b: float, neutral: bool = True) -> float:
    """Probabilidade de vitória do time A contra o time B."""
    adj_a = elo_a if neutral else elo_a + HOME_ADVANTAGE
    return 1.0 / (1.0 + 10.0 ** ((elo_b - adj_a) / 400.0))


def update_elo(
    elo_a: float,
    elo_b: float,
    score_a: int,
    score_b: int,
    tournament: str,
    neutral: bool = False,
) -> tuple:
    """Retorna (novo_elo_a, novo_elo_b) após um jogo."""
    k = get_k_factor(tournament)
    exp_a = win_probability(elo_a, elo_b, neutral)

    if score_a > score_b:
        result_a = 1.0
    elif score_a < score_b:
        result_a = 0.0
    else:
        result_a = 0.5

    delta = k * (result_a - exp_a)
    return round(elo_a + delta, 2), round(elo_b - delta, 2)


def calculate_elo_ratings(df: pd.DataFrame) -> dict:
    """
    Calcula Elo de todas as seleções a partir do DataFrame histórico.
    Começa com os defaults e vai atualizando cronologicamente.
    """
    elos = dict(DEFAULT_ELO_RATINGS)

    df = df.sort_values('date').reset_index(drop=True)

    for _, row in df.iterrows():
        home = str(row['home_team'])
        away = str(row['away_team'])

        if home not in elos:
            elos[home] = BASE_ELO
        if away not in elos:
            elos[away] = BASE_ELO

        try:
            hs = int(row['home_score'])
            as_ = int(row['away_score'])
        except (ValueError, TypeError):
            continue

        neutral = bool(row.get('neutral', False))
        tournament = str(row.get('tournament', 'Friendly'))

        new_h, new_a = update_elo(elos[home], elos[away], hs, as_, tournament, neutral)
        elos[home] = new_h
        elos[away] = new_a

    return elos


def calculate_elo_history(df: pd.DataFrame, teams: list = None) -> pd.DataFrame:
    """
    Retorna DataFrame com a evolução do Elo ao longo do tempo.
    Se `teams` for fornecida, filtra só esses times.
    """
    elos = dict(DEFAULT_ELO_RATINGS)
    records = []

    df = df.sort_values('date').reset_index(drop=True)

    for _, row in df.iterrows():
        home = str(row['home_team'])
        away = str(row['away_team'])

        if home not in elos:
            elos[home] = BASE_ELO
        if away not in elos:
            elos[away] = BASE_ELO

        try:
            hs = int(row['home_score'])
            as_ = int(row['away_score'])
        except (ValueError, TypeError):
            continue

        neutral = bool(row.get('neutral', False))
        tournament = str(row.get('tournament', 'Friendly'))

        new_h, new_a = update_elo(elos[home], elos[away], hs, as_, tournament, neutral)
        elos[home] = new_h
        elos[away] = new_a

        date = row['date']
        if teams is None or home in teams:
            records.append({'date': date, 'team': home, 'elo': new_h, 'tournament': tournament})
        if teams is None or away in teams:
            records.append({'date': date, 'team': away, 'elo': new_a, 'tournament': tournament})

    return pd.DataFrame(records)
