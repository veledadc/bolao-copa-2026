"""
Baixa os dados históricos necessários e reconstrói o estado do modelo.

Fontes:
  1. martj42/international_results — resultados internacionais desde 1872 (~7 MB)
  2. jfjelstul/worldcup            — dados estruturados de Copas (~2 MB)

Uso:
  python scripts/download_data.py            # baixa tudo
  python scripts/download_data.py --rebuild  # baixa + reconstrói state.json
"""

import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests

ROOT     = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(ROOT, 'data')

SOURCES = {
    'results': {
        'url':  ('https://raw.githubusercontent.com/martj42/international_results'
                 '/master/results.csv'),
        'dest': os.path.join(DATA_DIR, 'results.csv'),
        'desc': 'Resultados internacionais (martj42)',
    },
    'goalscorers': {
        'url':  ('https://raw.githubusercontent.com/martj42/international_results'
                 '/master/goalscorers.csv'),
        'dest': os.path.join(DATA_DIR, 'goalscorers.csv'),
        'desc': 'Artilheiros internacionais (martj42)',
    },
    'copa_matches': {
        'url':  ('https://raw.githubusercontent.com/jfjelstul/worldcup'
                 '/master/data-csv/matches.csv'),
        'dest': os.path.join(DATA_DIR, 'copa_matches.csv'),
        'desc': 'Partidas de Copa do Mundo (jfjelstul)',
    },
    'copa_teams': {
        'url':  ('https://raw.githubusercontent.com/jfjelstul/worldcup'
                 '/master/data-csv/teams.csv'),
        'dest': os.path.join(DATA_DIR, 'copa_teams.csv'),
        'desc': 'Seleções por Copa (jfjelstul)',
    },
}


def _download(key: str, info: dict, skip_existing: bool = False) -> bool:
    dest = info['dest']
    if skip_existing and os.path.exists(dest):
        size = os.path.getsize(dest) // 1024
        print(f'  ⏭  {info["desc"]} já existe ({size} KB) — pulando')
        return True

    print(f'\n  ⬇  {info["desc"]}')
    print(f'     {info["url"]}')

    try:
        resp = requests.get(info['url'], stream=True, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f'  ❌ Erro ao baixar {key}: {e}')
        return False

    total      = int(resp.headers.get('content-length', 0))
    downloaded = 0

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(dest, 'wb') as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f'\r     {pct:.0f}%  ({downloaded//1024} / {total//1024} KB)',
                      end='', flush=True)

    size = os.path.getsize(dest) // 1024
    print(f'\r  ✅ {info["desc"]} — {size} KB')
    return True


def download_all(skip_existing: bool = False):
    print('=' * 58)
    print('  Bolão Copa 2026 — Download de Dados')
    print('=' * 58)
    os.makedirs(DATA_DIR, exist_ok=True)

    results = {}
    for key, info in SOURCES.items():
        results[key] = _download(key, info, skip_existing)

    ok  = sum(results.values())
    nok = len(results) - ok
    print(f'\n  {ok}/{len(results)} arquivos obtidos com sucesso.')
    if nok:
        print(f'  ⚠  {nok} arquivo(s) falharam — verifique conexão e tente novamente.')

    return ok == len(results)


def rebuild_state():
    print('\n' + '=' * 58)
    print('  Reconstruindo state.json com dados históricos...')
    print('=' * 58)

    from src import state_manager as sm, data_loader as dl

    df    = dl.get_all_results()
    print(f'  Partidas carregadas: {len(df):,}')

    state = sm.build_state(df)
    sm.save_state(state)

    n_teams = len(state['elos'])
    n_form  = len([t for t, f in state['form'].items() if f])
    n_copa  = len(state['copa_history'])
    print(f'  Times com Elo:              {n_teams}')
    print(f'  Times com forma recente:    {n_form}')
    print(f'  Times com histórico Copa:   {n_copa}')
    print(f'  Hash do estado:             {state["state_hash"]}')
    print('  ✅ state.json salvo em data/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download e setup dos dados do Bolão Copa 2026')
    parser.add_argument('--rebuild',       action='store_true',
                        help='Reconstrói state.json após o download')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Pula arquivos já baixados')
    args = parser.parse_args()

    success = download_all(skip_existing=args.skip_existing)

    if success and args.rebuild:
        rebuild_state()
    elif not args.rebuild:
        print('\n  💡 Dica: rode com --rebuild para recalcular o modelo após o download.')

    print()
