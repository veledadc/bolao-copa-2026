"""Página 9 — Editar Resultados Gravados (Copa 2026)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st

from src.styles import get_css
from src import copa_manager as cm, state_manager as sm
from src.sidebar import render_sidebar

st.set_page_config(
    page_title='Editar Resultados · Bolão 2026',
    page_icon='✏️',
    layout='centered',
    initial_sidebar_state='expanded',
)
st.markdown(get_css(), unsafe_allow_html=True)
render_sidebar()

st.title('✏️ Editar Resultados Gravados')
st.markdown(
    'Aqui você pode **corrigir ou excluir** placares que foram gravados '
    'como oficiais na Copa 2026. Após qualquer alteração o modelo Elo é '
    'recalculado automaticamente.'
)

# ── Load data ─────────────────────────────────────────────────────────────────
schedule    = cm.generate_schedule()
ko_sched    = cm.generate_knockout_schedule()
official    = cm.load_official()

# Build lookup: match_id → match metadata
_id_to_match: dict[str, dict] = {}
for m in schedule:
    _id_to_match[m['id']] = m
for m in ko_sched:
    _id_to_match[m['id']] = m

if not official:
    st.info(
        '📭 **Nenhum placar gravado ainda na Copa 2026.**\n\n'
        'Para gravar um resultado oficial, vá até **🏠 Início** e clique em '
        '**📝 Gravar** ao lado de qualquer partida da Copa 2026. '
        'Depois volte aqui para corrigir se necessário.'
    )
    st.stop()

# ── Phase labels ──────────────────────────────────────────────────────────────
_PHASE_LABEL = {
    'group': 'Fase de Grupos',
    'r32':   'Rodada de 32',
    'r16':   'Oitavas de Final',
    'qf':    'Quartas de Final',
    'sf':    'Semifinais',
    'tp':    'Disputa 3º Lugar',
    'final': 'Final',
}

# Sort by recorded_at then display
sorted_results = sorted(
    official.items(),
    key=lambda kv: kv[1].get('recorded_at', ''),
)

st.markdown(
    f'<div style="color:#5a8ab0;font-size:.82rem;margin-bottom:.8rem">'
    f'Total de resultados gravados: <strong style="color:#c9a902">{len(official)}</strong>'
    f'</div>',
    unsafe_allow_html=True,
)

_edited_any = False

for mid, res in sorted_results:
    match_info = _id_to_match.get(mid, {})

    # Resolve team names: stored in result > schedule info
    home = res.get('home') or match_info.get('home') or mid
    away = res.get('away') or match_info.get('away') or mid

    phase  = match_info.get('phase', 'group')
    date   = match_info.get('date', '')
    hs_cur = int(res.get('home_score', 0))
    as_cur = int(res.get('away_score', 0))

    recorded_at = res.get('recorded_at', '')[:16].replace('T', ' ')
    updated_at  = res.get('updated_at', '')
    badge = ''
    if updated_at:
        badge = f' <span style="color:#c9a902;font-size:.65rem">(editado)</span>'

    with st.expander(
        f'{home} {hs_cur} × {as_cur} {away}  —  {_PHASE_LABEL.get(phase, phase)}',
        expanded=False,
    ):
        st.markdown(
            f'<div style="font-size:.72rem;color:#3a5a78;margin-bottom:.5rem">'
            f'ID: <code>{mid}</code> · Data: {date} · Gravado: {recorded_at}{badge}'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_h, col_sep, col_a = st.columns([5, 1, 5])
        with col_h:
            st.markdown(
                f'<div style="text-align:right;font-weight:700;padding-top:.4rem">{home}</div>',
                unsafe_allow_html=True,
            )
        with col_sep:
            st.markdown(
                '<div style="text-align:center;padding-top:.45rem;color:#3a5a78">×</div>',
                unsafe_allow_html=True,
            )
        with col_a:
            st.markdown(
                f'<div style="font-weight:700;padding-top:.4rem">{away}</div>',
                unsafe_allow_html=True,
            )

        ec1, ec2, ec3 = st.columns([2, 2, 4])
        with ec1:
            new_hs = st.number_input(
                f'Gols {home}', 0, 20, hs_cur,
                key=f'edit_hs_{mid}',
            )
        with ec2:
            new_as = st.number_input(
                f'Gols {away}', 0, 20, as_cur,
                key=f'edit_as_{mid}',
            )

        changed = (new_hs != hs_cur) or (new_as != as_cur)

        bc1, bc2 = st.columns(2)
        with bc1:
            save_label = '💾 Salvar Correção' if changed else '✅ Placar atual'
            if st.button(save_label, key=f'save_{mid}',
                         type='primary' if changed else 'secondary',
                         use_container_width=True,
                         disabled=not changed):
                cm.update_official_result(mid, new_hs, new_as)
                with st.spinner('Recalculando Elo…'):
                    new_state = cm.rebuild_elo_from_officials()
                    sm.save_state(new_state)
                st.session_state['state_dirty'] = True
                _edited_any = True
                st.success(f'✅ {home} {new_hs} × {new_as} {away} — salvo e Elo recalculado.')
                st.rerun()

        with bc2:
            if st.button('🗑️ Excluir resultado', key=f'del_{mid}',
                         use_container_width=True):
                st.session_state[f'confirm_del_{mid}'] = True

        if st.session_state.get(f'confirm_del_{mid}'):
            st.warning(
                f'⚠️ Tem certeza que quer **excluir** '
                f'`{home} {hs_cur} × {as_cur} {away}`? '
                f'O Elo será recalculado sem este jogo.',
                icon='🗑️',
            )
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button('Confirmar exclusão', key=f'yes_del_{mid}',
                             type='secondary', use_container_width=True):
                    cm.delete_official_result(mid)
                    with st.spinner('Recalculando Elo…'):
                        new_state = cm.rebuild_elo_from_officials()
                        sm.save_state(new_state)
                    st.session_state['state_dirty'] = True
                    st.session_state.pop(f'confirm_del_{mid}', None)
                    _edited_any = True
                    st.success('Resultado excluído. Elo recalculado.')
                    st.rerun()
            with dc2:
                if st.button('Cancelar', key=f'no_del_{mid}', use_container_width=True):
                    st.session_state.pop(f'confirm_del_{mid}', None)
                    st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown('---')
st.markdown(
    '<div style="font-size:.75rem;color:#3a5a78">'
    '💡 Dica: após editar ou excluir, volte à página <strong>Home</strong> '
    'para ver as probabilidades atualizadas.'
    '</div>',
    unsafe_allow_html=True,
)
