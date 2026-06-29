"""
Sincroniza resultados reais da Copa do Mundo 2026.

Baixa a versão mais recente do dataset martj42/international_results (que é
atualizado pelo mantenedor conforme as partidas acontecem) e grava como
oficiais, no Bolão, as partidas já disputadas que ainda não tinham placar
registrado. Resultados já gravados (`locked`) nunca são sobrescritos — apenas
os pendentes são preenchidos.

Pensado para rodar diariamente via tarefa agendada (ver
scripts/install_daily_sync.ps1), mas pode ser executado manualmente:

    python scripts/sync_results.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Console do Windows costuma usar cp1252, que não tem os emojis do log.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from datetime import datetime
import pandas as pd
import requests

from src import copa_manager as cm

RESULTS_URL  = ('https://raw.githubusercontent.com/martj42/international_results'
                 '/master/results.csv')
ROOT         = os.path.join(os.path.dirname(__file__), '..')
RESULTS_DEST = os.path.join(ROOT, 'data', 'results.csv')
LOG_FILE     = os.path.join(ROOT, 'data', 'sync_log.txt')

# O dataset martj42 usa nomenclatura diferente da FIFA/config.py para 4 seleções.
_NAME_TO_SOURCE = {
    'Czechia':             'Czech Republic',
    'USA':                 'United States',
    'Bosnia Herzegovina':  'Bosnia and Herzegovina',
    'Curacao':             'Curaçao',
}
_SOURCE_TO_NAME = {v: k for k, v in _NAME_TO_SOURCE.items()}

# Janelas de data por fase (folgadas de propósito). Usadas só para não confundir
# um confronto da fase de grupos com um possível confronto revanche no mata-mata
# entre os mesmos dois times — o casamento real é feito pelo par de seleções,
# não pela data exata, porque as datas fixas em `_MD_DATES` (copa_manager.py)
# podem não bater 100% com o calendário real divulgado pela FIFA.
_GROUP_WINDOW = ('2026-06-01', '2026-06-27')
_KO_WINDOW    = ('2026-06-28', '2026-08-15')


def _log(msg: str) -> None:
    line = f'[{datetime.now().isoformat(timespec="seconds")}] {msg}'
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def _download_fresh_results() -> bool:
    try:
        resp = requests.get(RESULTS_URL, timeout=60)
        resp.raise_for_status()
    except Exception as exc:
        _log(f'❌ Falha ao baixar results.csv: {exc}')
        return False
    os.makedirs(os.path.dirname(RESULTS_DEST), exist_ok=True)
    with open(RESULTS_DEST, 'wb') as f:
        f.write(resp.content)
    return True


def _load_world_cup_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_DEST)
    df = df[df['tournament'] == 'FIFA World Cup'].copy()
    df = df.dropna(subset=['home_score', 'away_score'])
    df['home_team'] = df['home_team'].map(lambda t: _SOURCE_TO_NAME.get(t, t))
    df['away_team'] = df['away_team'].map(lambda t: _SOURCE_TO_NAME.get(t, t))
    return df


def _find_score(df: pd.DataFrame, home: str, away: str, window: tuple[str, str]):
    """Procura o placar real de `home x away` dentro da janela de datas da fase.
    Casa pelo par de seleções (ignora a data exata do nosso calendário interno,
    que pode estar levemente errado); tenta também o confronto invertido.
    """
    cand = df[(df['date'] >= window[0]) & (df['date'] <= window[1])]
    row = cand[(cand['home_team'] == home) & (cand['away_team'] == away)]
    if not row.empty:
        r = row.iloc[0]
        return int(r['home_score']), int(r['away_score'])
    row = cand[(cand['home_team'] == away) & (cand['away_team'] == home)]
    if not row.empty:
        r = row.iloc[0]
        return int(r['away_score']), int(r['home_score'])
    return None


def sync_group_stage(df: pd.DataFrame) -> list[str]:
    schedule = cm.generate_schedule()
    official = cm.load_official()
    added = []
    for m in schedule:
        mid = m['id']
        if mid in official and official[mid].get('locked'):
            continue
        found = _find_score(df, m['home'], m['away'], _GROUP_WINDOW)
        if found is None:
            continue
        hs, as_ = found
        cm.save_official_result(mid, hs, as_, m['home'], m['away'])
        added.append(f'{m["home"]} {hs} x {as_} {m["away"]} (Grupo {m["group"]})')
    return added


def sync_knockout(df: pd.DataFrame) -> list[str]:
    """Roda em passes: cada rodada gravada pode revelar os times da próxima."""
    added = []
    for _ in range(6):
        schedule    = cm.generate_schedule()
        official    = cm.load_official()
        standings   = cm.compute_group_standings(schedule, official, {})
        slots       = cm.resolve_bracket_slots(standings)
        ko_sched    = cm.generate_knockout_schedule()
        ko_official = {k: v for k, v in official.items() if not k.startswith('G_')}
        ko_resolved = cm.resolve_knockout_teams(ko_sched, slots, ko_official, {})

        progressed = False
        for m in ko_resolved:
            mid = m['id']
            if mid in ko_official and ko_official[mid].get('locked'):
                continue
            if not (m.get('home') and m.get('away')):
                continue
            found = _find_score(df, m['home'], m['away'], _KO_WINDOW)
            if found is None:
                continue
            hs, as_ = found
            cm.save_official_result(mid, hs, as_, m['home'], m['away'])
            added.append(f'{m["home"]} {hs} x {as_} {m["away"]} ({m["phase"].upper()})')
            progressed = True
        if not progressed:
            break
    return added


def main() -> None:
    _log('Iniciando sincronização diária de resultados da Copa 2026...')
    if not _download_fresh_results():
        _log('Sincronização abortada — sem dados atualizados.')
        return

    df = _load_world_cup_results()
    added = sync_group_stage(df)
    added += sync_knockout(df)

    if added:
        cm.rebuild_elo_from_officials()
        _log(f'✅ {len(added)} resultado(s) novo(s) gravado(s):')
        for line in added:
            _log(f'   • {line}')
    else:
        _log('Nenhum resultado novo encontrado — tudo já estava em dia.')


if __name__ == '__main__':
    main()
