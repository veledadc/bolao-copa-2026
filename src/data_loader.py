"""
Carregamento e persistência dos dados de partidas.
"""
import os
import pandas as pd
from datetime import date
from config import (
    HISTORICAL_RESULTS_FILE,
    MANUAL_RESULTS_FILE,
    EXPECTED_COLUMNS,
    ELO_CUTOFF_YEAR,
    DATA_DIR,
)

_MANUAL_COLS = ['date', 'home_team', 'away_team', 'home_score', 'away_score',
                'tournament', 'city', 'country', 'neutral']


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_historical_results() -> pd.DataFrame:
    """Carrega results.csv (martj42). Retorna DataFrame vazio se arquivo ausente."""
    if not os.path.exists(HISTORICAL_RESULTS_FILE):
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    df = pd.read_csv(HISTORICAL_RESULTS_FILE, parse_dates=['date'])

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes em {HISTORICAL_RESULTS_FILE}: {missing}")

    df = df[EXPECTED_COLUMNS].copy()
    df = df[df['date'].dt.year >= ELO_CUTOFF_YEAR]
    # Partidas da Copa 2026 são geridas exclusivamente via data/copa_official.json
    # (com locking/edição/exclusão pela página "Corrigir Placar Gravado"). Excluímos
    # aqui para não contar o mesmo jogo duas vezes no Elo quando results.csv for
    # atualizado pelo sync diário com os placares reais do torneio.
    df = df[~((df['tournament'] == 'FIFA World Cup') & (df['date'].dt.year == 2026))]
    df = df.dropna(subset=['home_score', 'away_score'])
    df['home_score'] = df['home_score'].astype(int)
    df['away_score'] = df['away_score'].astype(int)
    df['neutral'] = df['neutral'].astype(bool)
    return df.reset_index(drop=True)


def load_manual_results() -> pd.DataFrame:
    """Carrega resultados inseridos manualmente pelo usuário."""
    _ensure_data_dir()
    if not os.path.exists(MANUAL_RESULTS_FILE):
        return pd.DataFrame(columns=_MANUAL_COLS)

    df = pd.read_csv(MANUAL_RESULTS_FILE, parse_dates=['date'])
    for c in _MANUAL_COLS:
        if c not in df.columns:
            df[c] = None
    df['neutral'] = df['neutral'].fillna(False).astype(bool)
    df['home_score'] = df['home_score'].astype(int)
    df['away_score'] = df['away_score'].astype(int)
    return df[_MANUAL_COLS].reset_index(drop=True)


def get_all_results() -> pd.DataFrame:
    """Retorna histórico + manuais, ordenados por data.

    `pd.concat` rebaixa a coluna `date` para dtype `object` quando um dos
    DataFrames está vazio (ex.: ainda não há `manual_results.csv`), o que
    quebra qualquer `.dt` accessor usado depois (página Histórico, Evolução).
    Forçamos o dtype de volta aqui — uma única vez, na fonte — em vez de em
    cada página que consome este DataFrame.
    """
    hist = load_historical_results()
    manual = load_manual_results()
    df = pd.concat([hist, manual], ignore_index=True)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def save_manual_result(
    match_date: date,
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    tournament: str = 'FIFA World Cup',
    city: str = '',
    country: str = '',
    neutral: bool = True,
) -> None:
    """Salva um novo resultado no arquivo de resultados manuais."""
    _ensure_data_dir()

    new_row = pd.DataFrame([{
        'date': pd.Timestamp(match_date),
        'home_team': home_team,
        'away_team': away_team,
        'home_score': int(home_score),
        'away_score': int(away_score),
        'tournament': tournament,
        'city': city,
        'country': country,
        'neutral': bool(neutral),
    }])

    write_header = not os.path.exists(MANUAL_RESULTS_FILE)
    new_row.to_csv(MANUAL_RESULTS_FILE, mode='a', header=write_header, index=False)


def delete_manual_result(index: int) -> None:
    """Remove resultado manual pelo índice."""
    df = load_manual_results()
    if 0 <= index < len(df):
        df = df.drop(index=index).reset_index(drop=True)
        df.to_csv(MANUAL_RESULTS_FILE, index=False)


def get_all_teams(df: pd.DataFrame = None) -> list:
    """Retorna lista ordenada de todos os times presentes nos dados."""
    from config import COPA_2026_GROUPS
    copa_teams = sorted({t for teams in COPA_2026_GROUPS.values() for t in teams})

    if df is not None and not df.empty:
        data_teams = sorted(set(df['home_team'].tolist() + df['away_team'].tolist()))
        all_teams = sorted(set(copa_teams + data_teams))
    else:
        all_teams = copa_teams

    return all_teams
