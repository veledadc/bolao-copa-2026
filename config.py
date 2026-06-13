"""
Configurações do projeto Bolão Copa do Mundo 2026.
IMPORTANTE: Atualize COPA_2026_GROUPS com os grupos oficiais do sorteio da FIFA.
"""

# -------------------------------------------------------------------
# COPA DO MUNDO 2026 — Grupos Oficiais (sorteio FIFA, 5 dez 2024)
# 48 times | 12 grupos de 4 | Top 2 + 8 melhores 3os avançam (32 times)
# -------------------------------------------------------------------
COPA_2026_GROUPS = {
    'A': ['Mexico',      'South Africa',   'South Korea',   'Czechia'],
    'B': ['Canada',      'Switzerland',    'Qatar',         'Bosnia Herzegovina'],
    'C': ['Brazil',      'Morocco',        'Haiti',         'Scotland'],
    'D': ['USA',         'Paraguay',       'Australia',     'Turkey'],
    'E': ['Germany',     'Curacao',        'Ivory Coast',   'Ecuador'],
    'F': ['Netherlands', 'Japan',          'Sweden',        'Tunisia'],
    'G': ['Belgium',     'Egypt',          'Iran',          'New Zealand'],
    'H': ['Spain',       'Cape Verde',     'Saudi Arabia',  'Uruguay'],
    'I': ['France',      'Senegal',        'Iraq',          'Norway'],
    'J': ['Argentina',   'Algeria',        'Austria',       'Jordan'],
    'K': ['Portugal',    'DR Congo',       'Uzbekistan',    'Colombia'],
    'L': ['England',     'Croatia',        'Ghana',         'Panama'],
}

# Número de melhores 3os que avançam
N_BEST_THIRDS = 8

# -------------------------------------------------------------------
# ELO — Parâmetros
# -------------------------------------------------------------------
BASE_ELO = 1500
HOME_ADVANTAGE = 100  # pontos de Elo para mandante

K_FACTORS = {
    'FIFA World Cup': 60,
    'FIFA World Cup qualification': 40,
    'Copa América': 40,
    'CONMEBOL': 40,
    'UEFA Euro': 40,
    'UEFA European Championship': 40,
    'Africa Cup of Nations': 35,
    'AFC Asian Cup': 35,
    'CONCACAF Gold Cup': 35,
    'OFC Nations Cup': 30,
    'FIFA Confederations Cup': 40,
    'Friendly': 20,
}
DEFAULT_K = 30

# -------------------------------------------------------------------
# ELO — Ratings padrão para times da Copa 2026 (snapshot pré-competição)
# Esses valores são substituídos quando dados históricos são carregados.
# -------------------------------------------------------------------
DEFAULT_ELO_RATINGS = {
    # ── Elite ────────────────────────────────────────────────────────
    'Argentina':          2063,
    'France':             2031,
    'England':            2003,
    'Brazil':             1989,
    'Portugal':           1972,
    'Spain':              1961,
    'Germany':            1946,
    'Netherlands':        1933,
    # ── Forte ─────────────────────────────────────────────────────────
    'Belgium':            1907,
    'Croatia':            1885,
    'Uruguay':            1865,
    'Colombia':           1845,
    'Morocco':            1820,
    'Japan':              1813,
    'Norway':             1793,
    'USA':                1792,
    'Senegal':            1778,
    'Sweden':             1762,
    'Switzerland':        1760,
    'Turkey':             1748,
    'Mexico':             1742,
    'Ecuador':            1730,
    'South Korea':        1705,
    'Austria':            1695,
    'Algeria':            1688,
    'Australia':          1672,
    'Iran':               1665,
    # ── Médio ─────────────────────────────────────────────────────────
    'Ivory Coast':        1650,
    'Canada':             1648,
    'Tunisia':            1635,
    'Scotland':           1620,
    'Bosnia Herzegovina': 1618,
    'Czechia':            1608,
    'Egypt':              1592,
    'Saudi Arabia':       1588,
    'Ghana':              1582,
    'Paraguay':           1578,
    'DR Congo':           1570,
    'South Africa':       1563,
    # ── Médio-baixo ───────────────────────────────────────────────────
    'Cape Verde':         1558,
    'Jordan':             1545,
    'Panama':             1540,
    'Qatar':              1530,
    'New Zealand':        1520,
    'Iraq':               1515,
    'Uzbekistan':         1512,
    'Haiti':              1490,
    'Curacao':            1448,
    # ── Times fora da Copa (histórico Elo, não usados na simulação) ───
    'Denmark':            1798,
    'Poland':             1718,
    'Serbia':             1695,
    'Romania':            1598,
    'Venezuela':          1590,
    'Honduras':           1545,
    'Costa Rica':         1575,
    'Nigeria':            1660,
    'Cameroon':           1615,
    'Indonesia':          1478,
}

# -------------------------------------------------------------------
# HISTÓRICO — Títulos de Copa do Mundo por seleção
# -------------------------------------------------------------------
COPA_TITLES = {
    'Brazil':    5,
    'Germany':   4,
    'Italy':     4,
    'Argentina': 3,
    'France':    2,
    'Uruguay':   2,
    'England':   1,
    'Spain':     1,
}

# -------------------------------------------------------------------
# SIMULAÇÃO — Parâmetros
# -------------------------------------------------------------------
DEFAULT_N_SIMULATIONS = 5000
MAX_N_SIMULATIONS = 50000

# -------------------------------------------------------------------
# DADOS — Caminhos de arquivo
# -------------------------------------------------------------------
DATA_DIR = 'data'
HISTORICAL_RESULTS_FILE = 'data/results.csv'
MANUAL_RESULTS_FILE = 'data/manual_results.csv'

# Colunas esperadas no CSV histórico (formato martj42/international_results)
EXPECTED_COLUMNS = ['date', 'home_team', 'away_team', 'home_score', 'away_score',
                    'tournament', 'city', 'country', 'neutral']

# Filtrar resultados a partir de (para acelerar cálculo do Elo)
ELO_CUTOFF_YEAR = 1990

# -------------------------------------------------------------------
# DISPLAY — Cores por confederação
# -------------------------------------------------------------------
CONFEDERATION_COLORS = {
    'UEFA':     '#003399',
    'CONMEBOL': '#FFD700',
    'CONCACAF': '#CC0000',
    'AFC':      '#FF6600',
    'CAF':      '#009900',
    'OFC':      '#009999',
    'Other':    '#888888',
}

TEAM_CONFEDERATION = {
    # ── UEFA (16) ─────────────────────────────────────────────────────
    'Germany': 'UEFA', 'France': 'UEFA', 'England': 'UEFA', 'Spain': 'UEFA',
    'Portugal': 'UEFA', 'Netherlands': 'UEFA', 'Croatia': 'UEFA', 'Switzerland': 'UEFA',
    'Belgium': 'UEFA', 'Austria': 'UEFA', 'Scotland': 'UEFA', 'Czechia': 'UEFA',
    'Sweden': 'UEFA', 'Norway': 'UEFA', 'Bosnia Herzegovina': 'UEFA', 'Turkey': 'UEFA',
    # Fora da Copa 2026 mas com Elo histórico
    'Denmark': 'UEFA', 'Poland': 'UEFA', 'Serbia': 'UEFA', 'Romania': 'UEFA',
    # ── CONMEBOL (6) ──────────────────────────────────────────────────
    'Brazil': 'CONMEBOL', 'Argentina': 'CONMEBOL', 'Uruguay': 'CONMEBOL',
    'Colombia': 'CONMEBOL', 'Ecuador': 'CONMEBOL', 'Paraguay': 'CONMEBOL',
    'Venezuela': 'CONMEBOL',
    # ── CONCACAF (6) ──────────────────────────────────────────────────
    'USA': 'CONCACAF', 'Mexico': 'CONCACAF', 'Canada': 'CONCACAF',
    'Panama': 'CONCACAF', 'Haiti': 'CONCACAF', 'Curacao': 'CONCACAF',
    'Costa Rica': 'CONCACAF', 'Honduras': 'CONCACAF',
    # ── AFC (8) ───────────────────────────────────────────────────────
    'Japan': 'AFC', 'South Korea': 'AFC', 'Iran': 'AFC', 'Saudi Arabia': 'AFC',
    'Australia': 'AFC', 'Qatar': 'AFC', 'Uzbekistan': 'AFC', 'Iraq': 'AFC',
    'Jordan': 'AFC',
    # ── CAF (9+1) ─────────────────────────────────────────────────────
    'Morocco': 'CAF', 'Senegal': 'CAF', 'Algeria': 'CAF', 'Ivory Coast': 'CAF',
    'Ghana': 'CAF', 'Egypt': 'CAF', 'DR Congo': 'CAF', 'Tunisia': 'CAF',
    'South Africa': 'CAF', 'Cape Verde': 'CAF',
    'Nigeria': 'CAF', 'Cameroon': 'CAF',
    # ── OFC (1) ───────────────────────────────────────────────────────
    'New Zealand': 'OFC',
    'Indonesia': 'OFC',
}
