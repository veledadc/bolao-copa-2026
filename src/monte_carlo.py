"""
Simulação Monte Carlo da Copa do Mundo 2026.

Bugs corrigidos vs versão anterior:
- Stage tracking correto: ambos os times são creditados por CHEGAR a uma fase,
  não apenas o vencedor.
- _ROUND_NAMES corrigido para o formato de 48 times (Rodada de 32 → Oitavas
  → Quartas → Semifinal → Final).
- simulate_group_match retorna (pts_a, pts_b, goals_a, goals_b) com gols reais,
  eliminando o cálculo incorreto de gf.
- Fórmula de probabilidade em eliminatórias corrigida para empate → pênaltis.
- Contagem de fases em run_simulations sem cascata, usando lookup direto.
"""

import numpy as np
from collections import defaultdict
from src.elo import win_probability


# ── Nomes de fase por número de times na rodada ─────────────────────────────
_ROUND_NAMES = {
    32: 'Rodada de 32',   # Oitavas-de-final da Copa 2026 (48 times)
    16: 'Oitavas',        # Round of 16
    8:  'Quartas',        # Quarterfinals
    4:  'Semifinal',
    2:  'Final',
}

# Pesos de torneio para forma recente (importados de features se disponível)
_FRIENDLY_KEYWORDS = ('friendly', 'amistoso')


# ── Probabilidade de empate ──────────────────────────────────────────────────

def _draw_probability(prob_a: float) -> float:
    """
    Probabilidade de empate calibrada para futebol internacional (~22% médio).
    Diminui com a diferença de qualidade entre os times.
    """
    return max(0.08, 0.26 - abs(prob_a - 0.5) * 0.45)


# ── Simulação de partida individual ─────────────────────────────────────────

def _effective_elo(elo: float, form: list, copa_hist: dict,
                   form_weight: float = 30.0, copa_weight: float = 12.0) -> float:
    """
    Elo efetivo incorporando forma recente e histórico de Copa.

    form_weight  : bônus máximo (±pts) pela forma dos últimos 5 jogos
    copa_weight  : bônus máximo (±pts) pelo aproveitamento histórico em Copas
    """
    # Forma recente: últimos 5 jogos competitivos
    score_map = {'W': 1.0, 'D': 0.5, 'L': 0.0}
    if form:
        recent = form[-5:]
        avg_form = sum(score_map.get(r, 0.5) for r in recent) / len(recent)
        form_bonus = (avg_form - 0.5) * 2 * form_weight
    else:
        form_bonus = 0.0

    # Histórico de Copa: aproveitamento histórico em Mundiais
    copa_wr = copa_hist.get('win_rate', None)
    titles  = copa_hist.get('titles', 0)
    if copa_wr is not None:
        copa_bonus = (copa_wr - 0.40) / 0.60 * copa_weight + titles * 1.5
        copa_bonus = max(-copa_weight, min(copa_weight, copa_bonus))
    else:
        copa_bonus = -copa_weight * 0.4   # leve penalidade por ausência de história

    return elo + form_bonus + copa_bonus


def simulate_group_match(
    elo_a: float,
    elo_b: float,
    form_a: list = None,
    form_b: list = None,
    copa_a: dict = None,
    copa_b: dict = None,
) -> tuple:
    """
    Simula partida de fase de grupos.
    Retorna (pts_a, pts_b, goals_a, goals_b).
    """
    form_a  = form_a  or []
    form_b  = form_b  or []
    copa_a  = copa_a  or {}
    copa_b  = copa_b  or {}

    eff_a = _effective_elo(elo_a, form_a, copa_a)
    eff_b = _effective_elo(elo_b, form_b, copa_b)

    prob_a = win_probability(eff_a, eff_b, neutral=True)
    draw_p = _draw_probability(prob_a)
    win_a_p = (1.0 - draw_p) * prob_a

    r = np.random.random()

    if r < win_a_p:                        # A vence
        ga = max(1, np.random.poisson(1.6))
        gb = max(0, min(ga - 1, np.random.poisson(0.8)))
        return 3, 0, ga, gb

    elif r < win_a_p + draw_p:             # Empate
        ga = np.random.poisson(1.05)
        return 1, 1, ga, ga

    else:                                   # B vence
        gb = max(1, np.random.poisson(1.6))
        ga = max(0, min(gb - 1, np.random.poisson(0.8)))
        return 0, 3, ga, gb


def simulate_knockout_match(
    elo_a: float,
    elo_b: float,
    form_a: list = None,
    form_b: list = None,
    copa_a: dict = None,
    copa_b: dict = None,
) -> int:
    """
    Simula jogo eliminatório (sem empate — empate → pênaltis).
    Retorna 0 se A vencer, 1 se B vencer.
    """
    form_a = form_a or []
    form_b = form_b or []
    copa_a = copa_a or {}
    copa_b = copa_b or {}

    eff_a = _effective_elo(elo_a, form_a, copa_a)
    eff_b = _effective_elo(elo_b, form_b, copa_b)

    prob_a = win_probability(eff_a, eff_b, neutral=True)
    draw_p = _draw_probability(prob_a)

    # P(A win) = P(A win in 90min) + P(draw) × P(A win on penalties ≈ 0.5)
    adj_a = (1.0 - draw_p) * prob_a + draw_p * 0.5
    adj_a = max(0.03, min(0.97, adj_a))

    return 0 if np.random.random() < adj_a else 1


def _simulate_goals(eff_a: float, eff_b: float) -> tuple[int, int]:
    """Poisson-distributed goals scaled by effective ELO gap."""
    prob_a  = win_probability(eff_a, eff_b, neutral=True)
    share_a = max(0.2, min(0.8, 0.5 + (prob_a - 0.5) * 0.6))
    xg_a    = max(0.45, 2.3 * share_a)
    xg_b    = max(0.45, 2.3 * (1.0 - share_a))
    return int(np.random.poisson(xg_a)), int(np.random.poisson(xg_b))


def _simulate_penalty_score() -> tuple[int, int]:
    """Simulate penalty shootout. Returns (winner_pens, loser_pens)."""
    w, l = 0, 0
    for _ in range(5):
        if np.random.random() < 0.76:
            w += 1
        if np.random.random() < 0.76:
            l += 1
    # Sudden death until someone wins
    while w == l:
        rw = np.random.random() < 0.76
        rl = np.random.random() < 0.76
        w += int(rw)
        l += int(rl)
    return (w, l) if w > l else (l, w)


def simulate_knockout_match_with_score(
    elo_a: float, elo_b: float,
    form_a: list = None, form_b: list = None,
    copa_a: dict = None, copa_b: dict = None,
) -> tuple[int, int, bool, int, int, int]:
    """
    Knockout match with realistic scoreline.
    Returns (goals_a, goals_b, went_to_pens, winner_idx, pen_a, pen_b).
    winner_idx: 0 = A venceu, 1 = B venceu.
    pen_a/pen_b: penalty goals (0 when no shootout).
    """
    form_a = form_a or []
    form_b = form_b or []
    copa_a = copa_a or {}
    copa_b = copa_b or {}
    eff_a  = _effective_elo(elo_a, form_a, copa_a)
    eff_b  = _effective_elo(elo_b, form_b, copa_b)
    goals_a, goals_b = _simulate_goals(eff_a, eff_b)
    if goals_a != goals_b:
        return goals_a, goals_b, False, (0 if goals_a > goals_b else 1), 0, 0
    prob_a  = win_probability(eff_a, eff_b, neutral=True)
    pen_p   = max(0.3, min(0.7, 0.5 + (prob_a - 0.5) * 0.15))
    winner  = 0 if np.random.random() < pen_p else 1
    pen_w, pen_l = _simulate_penalty_score()
    pen_a = pen_w if winner == 0 else pen_l
    pen_b = pen_l if winner == 0 else pen_w
    return goals_a, goals_b, True, winner, pen_a, pen_b


# ── Fase de Grupos ───────────────────────────────────────────────────────────

def simulate_group_stage(
    groups: dict,
    elos: dict,
    form: dict = None,
    copa_history: dict = None,
) -> dict:
    """
    Simula a fase de grupos completa.

    Retorna dict por grupo:
      { 'standings': [...], 'points': {...}, 'goal_diff': {...}, 'goals_for': {...} }
    """
    form         = form         or {}
    copa_history = copa_history or {}
    results      = {}

    for group_name, teams in groups.items():
        pts = {t: 0 for t in teams}
        gd  = {t: 0 for t in teams}
        gf  = {t: 0 for t in teams}

        for i, ta in enumerate(teams):
            for tb in teams[i + 1:]:
                ea = elos.get(ta, 1500)
                eb = elos.get(tb, 1500)

                pa, pb, ga, gb = simulate_group_match(
                    ea, eb,
                    form.get(ta, []), form.get(tb, []),
                    copa_history.get(ta, {}), copa_history.get(tb, {}),
                )

                pts[ta] += pa;  pts[tb] += pb
                gd[ta]  += ga - gb;  gd[tb] += gb - ga
                gf[ta]  += ga;  gf[tb] += gb

        standings = sorted(teams,
                           key=lambda t: (pts[t], gd[t], gf[t]),
                           reverse=True)

        results[group_name] = {
            'standings': standings,
            'points':    pts,
            'goal_diff': gd,
            'goals_for': gf,
        }

    return results


def get_advancing_teams(group_results: dict, n_best_thirds: int = 8) -> list:
    """
    Retorna os 32 times que avançam para a fase eliminatória:
    top-2 de cada grupo (24 times) + 8 melhores 3os colocados.
    """
    advancing = []
    thirds    = []

    for gname, data in group_results.items():
        s = data['standings']
        advancing.append(s[0])
        advancing.append(s[1])
        if len(s) >= 3:
            t = s[2]
            thirds.append({
                'team': t,
                'pts': data['points'][t],
                'gd':  data['goal_diff'][t],
                'gf':  data['goals_for'][t],
            })

    thirds_sorted = sorted(thirds,
                           key=lambda x: (x['pts'], x['gd'], x['gf']),
                           reverse=True)
    for entry in thirds_sorted[:n_best_thirds]:
        advancing.append(entry['team'])

    return advancing


# ── Fase Eliminatória ────────────────────────────────────────────────────────

def simulate_knockout_stage(
    teams: list,
    elos: dict,
    form: dict = None,
    copa_history: dict = None,
) -> dict:
    """
    Simula fase eliminatória com tracking correto de fases.

    CORREÇÃO: ambos os times de cada confronto são creditados por CHEGAR
    à fase, independente do resultado.

    Retorna dict: team → set de fases alcançadas (strings de _ROUND_NAMES).
    """
    form         = form         or {}
    copa_history = copa_history or {}

    reached = defaultdict(set)
    current = list(teams)
    np.random.shuffle(current)      # TODO v2: usar chaveamento determinístico Copa 2026

    while len(current) > 1:
        round_label = _ROUND_NAMES.get(len(current), f'Rodada de {len(current)}')
        next_round  = []

        for i in range(0, len(current) - 1, 2):
            ta, tb = current[i], current[i + 1]

            # ── Ambos chegaram a esta fase ──
            reached[ta].add(round_label)
            reached[tb].add(round_label)

            ea = elos.get(ta, 1500)
            eb = elos.get(tb, 1500)

            res    = simulate_knockout_match(ea, eb,
                                             form.get(ta, []), form.get(tb, []),
                                             copa_history.get(ta, {}), copa_history.get(tb, {}))
            winner = ta if res == 0 else tb
            next_round.append(winner)

        # Bye (número ímpar de times — não deve ocorrer em Copa normal)
        if len(current) % 2 == 1:
            bye = current[-1]
            reached[bye].add(round_label)
            next_round.append(bye)

        current = next_round

    if current:
        reached[current[0]].add('Campeão')

    return reached


# ── Simulação Monte Carlo completa ───────────────────────────────────────────

def run_simulations(
    groups: dict,
    elos: dict,
    n_simulations: int = 5000,
    n_best_thirds: int = 8,
    form: dict = None,
    copa_history: dict = None,
) -> dict:
    """
    Executa N simulações completas da Copa do Mundo.

    Parâmetros
    ----------
    groups        : {'A': ['Brazil', ...], ...}
    elos          : {'Brazil': 1989, ...}
    n_simulations : número de torneios simulados
    n_best_thirds : quantos 3os colocados avançam (padrão=8 para Copa 2026)
    form          : {'Brazil': ['W','W','D',...], ...}  — opcional
    copa_history  : {'Brazil': {'win_rate': 0.67, 'titles': 5, ...}, ...}  — opcional

    Retorna
    -------
    dict: team → {
      'campeao', 'final', 'semifinal', 'quartas', 'oitavas', 'rodada32', 'grupo'
    } com probabilidades em [0, 1].
    """
    form         = form         or {}
    copa_history = copa_history or {}

    all_teams = [t for teams in groups.values() for t in teams]

    _zero = lambda: {
        'campeao': 0, 'final': 0, 'semifinal': 0,
        'quartas': 0, 'oitavas': 0, 'rodada32': 0,
    }
    counts = {t: _zero() for t in all_teams}

    for _ in range(n_simulations):
        # 1. Fase de grupos
        group_res  = simulate_group_stage(groups, elos, form, copa_history)
        advancing  = get_advancing_teams(group_res, n_best_thirds)

        for t in advancing:
            if t in counts:
                counts[t]['rodada32'] += 1     # passou da fase de grupos

        # 2. Fase eliminatória
        reached = simulate_knockout_stage(advancing, elos, form, copa_history)

        for team, stages in reached.items():
            if team not in counts:
                continue
            c = counts[team]
            # Lookup direto — sem cascata (o tracking já é acumulativo)
            if 'Campeão'      in stages:  c['campeao']   += 1
            if 'Final'        in stages or 'Campeão' in stages:
                                           c['final']     += 1
            if 'Semifinal'    in stages:   c['semifinal'] += 1
            if 'Quartas'      in stages:   c['quartas']   += 1
            if 'Oitavas'      in stages:   c['oitavas']   += 1

    # Converte para probabilidades
    probs = {}
    for t in all_teams:
        c = counts[t]
        probs[t] = {k: round(v / n_simulations, 4) for k, v in c.items()}
        probs[t]['grupo'] = probs[t]['rodada32']   # alias de compatibilidade

    return probs


# ── Cenários de bracket (SF → Final) ────────────────────────────────────────

def run_bracket_scenarios(
    groups: dict,
    elos: dict,
    n_simulations: int = 2000,
    n_best_thirds: int = 8,
    form: dict = None,
    copa_history: dict = None,
) -> list:
    """
    Runs N full simulations tracking the bracket from semis to the final.

    Returns a list of dicts, one per simulation:
      'sf1':        (team_a, team_b, winner)
      'sf2':        (team_a, team_b, winner)
      'final':      (finalist_1, finalist_2, champion)
      'third':      (loser_1, loser_2, third_place_winner)
      'champion':   team
      'runner_up':  team
      'third_place': team
      'fourth':     team
    """
    form         = form         or {}
    copa_history = copa_history or {}
    scenarios    = []

    for _ in range(n_simulations):
        group_res = simulate_group_stage(groups, elos, form, copa_history)
        advancing = get_advancing_teams(group_res, n_best_thirds)
        np.random.shuffle(advancing)

        # Run R32 → R16 → QF until 4 remain
        current = list(advancing)
        while len(current) > 4:
            nxt = []
            for i in range(0, len(current) - 1, 2):
                ta, tb = current[i], current[i + 1]
                r = simulate_knockout_match(
                    elos.get(ta, 1500), elos.get(tb, 1500),
                    form.get(ta, []), form.get(tb, []),
                    copa_history.get(ta, {}), copa_history.get(tb, {}),
                )
                nxt.append(ta if r == 0 else tb)
            if len(current) % 2 == 1:
                nxt.append(current[-1])
            current = nxt

        sf1_a, sf1_b, sf2_a, sf2_b = current[0], current[1], current[2], current[3]

        gs1a, gs1b, sp1, r1, ps1a, ps1b = simulate_knockout_match_with_score(
            elos.get(sf1_a, 1500), elos.get(sf1_b, 1500),
            form.get(sf1_a, []), form.get(sf1_b, []),
            copa_history.get(sf1_a, {}), copa_history.get(sf1_b, {}))
        sf1_w = sf1_a if r1 == 0 else sf1_b
        sf1_l = sf1_b if r1 == 0 else sf1_a

        gs2a, gs2b, sp2, r2, ps2a, ps2b = simulate_knockout_match_with_score(
            elos.get(sf2_a, 1500), elos.get(sf2_b, 1500),
            form.get(sf2_a, []), form.get(sf2_b, []),
            copa_history.get(sf2_a, {}), copa_history.get(sf2_b, {}))
        sf2_w = sf2_a if r2 == 0 else sf2_b
        sf2_l = sf2_b if r2 == 0 else sf2_a

        gfa, gfb, fpens, rf, pfa, pfb = simulate_knockout_match_with_score(
            elos.get(sf1_w, 1500), elos.get(sf2_w, 1500),
            form.get(sf1_w, []), form.get(sf2_w, []),
            copa_history.get(sf1_w, {}), copa_history.get(sf2_w, {}))
        champion  = sf1_w if rf == 0 else sf2_w
        runner_up = sf2_w if rf == 0 else sf1_w

        gta, gtb, tpens, rt, pta, ptb = simulate_knockout_match_with_score(
            elos.get(sf1_l, 1500), elos.get(sf2_l, 1500),
            form.get(sf1_l, []), form.get(sf2_l, []),
            copa_history.get(sf1_l, {}), copa_history.get(sf2_l, {}))
        third  = sf1_l if rt == 0 else sf2_l
        fourth = sf2_l if rt == 0 else sf1_l

        scenarios.append({
            'sf1':         (sf1_a, sf1_b, sf1_w),
            'sf1_score':   (gs1a, gs1b, sp1, ps1a, ps1b),
            'sf2':         (sf2_a, sf2_b, sf2_w),
            'sf2_score':   (gs2a, gs2b, sp2, ps2a, ps2b),
            'final':       (sf1_w, sf2_w, champion),
            'final_score': (gfa, gfb, fpens, pfa, pfb),
            'third':       (sf1_l, sf2_l, third),
            'third_score': (gta, gtb, tpens, pta, ptb),
            'champion':    champion,
            'runner_up':   runner_up,
            'third_place': third,
            'fourth':      fourth,
        })

    return scenarios
