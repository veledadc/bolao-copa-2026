"""Menu de navegação lateral — compartilhado por todas as páginas."""
import streamlit as st


def render_sidebar() -> None:
    """Renderiza o menu de navegação no sidebar.

    Chamada por toda página logo após `get_css()`, garantindo que o link
    para voltar/navegar exista sempre, mesmo em páginas que antes não
    tinham nenhum menu (ex.: Evolução, Simulação, Ranking Elo).
    """
    with st.sidebar:
        st.markdown(
            '<div style="padding:.4rem 0 .8rem">'
            '<div style="font-size:1.25rem;font-weight:900;color:#c9a902;letter-spacing:-.02em">'
            '⚽ Copa 2026</div>'
            '<div style="font-size:.7rem;color:#3a5a78;text-transform:uppercase;'
            'letter-spacing:.08em;margin-top:2px">Predictor</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div style="font-size:.68rem;color:#2a4a68;text-transform:uppercase;'
                    'letter-spacing:.1em;padding:.2rem 0 .3rem">Copa 2026</div>',
                    unsafe_allow_html=True)
        st.page_link('app.py',                      label='🏠  Início')
        st.page_link('pages/8_Cenarios_Finais.py',  label='🔮  Cenários das Finais')

        st.markdown('<div style="border-top:1px solid #0d2040;margin:.6rem 0 .5rem"></div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="font-size:.68rem;color:#2a4a68;text-transform:uppercase;'
                    'letter-spacing:.1em;padding:.1rem 0 .3rem">Análises</div>',
                    unsafe_allow_html=True)
        st.page_link('pages/1_Campeoes.py',   label='🏆  Probabilidades de Título')
        st.page_link('pages/5_Ranking_Elo.py', label='📊  Ranking Elo')
        st.page_link('pages/2_Simulacao.py',   label='🎲  Simulação Monte Carlo')
        st.page_link('pages/6_Evolucao.py',    label='📈  Evolução do Elo')

        st.markdown('<div style="border-top:1px solid #0d2040;margin:.6rem 0 .5rem"></div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="font-size:.68rem;color:#2a4a68;text-transform:uppercase;'
                    'letter-spacing:.1em;padding:.1rem 0 .3rem">Dados</div>',
                    unsafe_allow_html=True)
        st.page_link('pages/4_Historico.py',         label='📜  Histórico de Partidas')
        st.page_link('pages/3_Novo_Resultado.py',    label='➕  Registrar Resultado')
        st.page_link('pages/9_Editar_Resultados.py', label='✏️  Corrigir Placar Gravado')
        st.page_link('pages/7_Documentacao.py',      label='📚  Documentação')
