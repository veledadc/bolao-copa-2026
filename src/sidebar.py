"""Menu de navegação lateral — compartilhado por todas as páginas."""
import streamlit as st
import streamlit.components.v1 as components

# JS injetado via iframe — acessa o DOM pai com window.parent
_TOGGLE_HTML = """<script>
(function () {
  var win = window.parent;
  var doc = win.document;
  var BTN = 'bolao-menu-toggle';

  function getSidebar() {
    return doc.querySelector('[data-testid="stSidebar"]');
  }

  function sidebarIsOpen() {
    var s = getSidebar();
    if (!s) return false;
    /* Streamlit colapsa via transform; right fica < 10 quando fechada */
    return s.getBoundingClientRect().right > 10;
  }

  function doToggle() {
    var t = doc.querySelector('[data-testid="stSidebarCollapseButton"] button')
         || doc.querySelector('[data-testid="stSidebarCollapsedControl"] button')
         || doc.querySelector('[data-testid="stSidebar"] button');
    if (t) t.click();
  }

  function mkBtn() {
    if (doc.getElementById(BTN)) return;
    var b = doc.createElement('button');
    b.id    = BTN;
    b.title = 'Menu';
    b.innerHTML =
      '<svg width="18" height="14" viewBox="0 0 18 14" xmlns="http://www.w3.org/2000/svg">'
      + '<rect width="18" height="2" rx="1" y="0"  fill="#c9a902"/>'
      + '<rect width="18" height="2" rx="1" y="6"  fill="#c9a902"/>'
      + '<rect width="18" height="2" rx="1" y="12" fill="#c9a902"/>'
      + '</svg>';
    b.style.cssText =
      'position:fixed;top:8px;left:8px;z-index:2147483647;'
      + 'background:#0c1c2e;border:1px solid #c9a902;border-radius:6px;'
      + 'cursor:pointer;width:44px;height:44px;'
      + 'display:flex;align-items:center;justify-content:center;'
      + 'padding:0;transition:background .15s;outline:none;'
      + 'box-shadow:0 2px 8px rgba(201,169,2,.25);'
      + 'touch-action:manipulation;-webkit-tap-highlight-color:transparent;';
    b.onmouseover = function () { this.style.background = '#13284a'; };
    b.onmouseout  = function () { this.style.background = '#0c1c2e'; };
    b.onclick     = function () { doToggle(); };
    doc.body.appendChild(b);
  }

  /* fecha sidebar ao clicar/tocar fora — capture phase antes do React */
  function closeIfOutside(e) {
    if (!sidebarIsOpen()) return;
    var sidebar = getSidebar();
    var btn     = doc.getElementById(BTN);
    var target  = e.target || (e.touches && e.touches[0] && e.touches[0].target);
    if (sidebar && sidebar.contains(target)) return;
    if (btn     && btn.contains(target))     return;
    doToggle();
  }

  if (!win._bolaoClickSetup) {
    win._bolaoClickSetup = true;
    win.addEventListener('click', closeIfOutside, true);
  }
  /* touchstart para dispositivos móveis (não dispara 'click' imediatamente) */
  if (!win._bolaoTouchSetup) {
    win._bolaoTouchSetup = true;
    win.addEventListener('touchstart', closeIfOutside, true);
  }

  mkBtn();

  new MutationObserver(function () { mkBtn(); })
    .observe(doc.body, { childList: true });
})();
</script>"""


def render_page_header() -> None:
    """Banner de identidade do app — aparece no topo de todas as páginas."""
    st.markdown(
        '<div id="bolao-page-header" style="'
        'background:linear-gradient(135deg,#001133 0%,#002255 70%,#001a40 100%);'
        'border:1px solid #1a3a6a;border-left:4px solid #c9a902;border-radius:10px;'
        'padding:.65rem 1.3rem .55rem;margin-bottom:.85rem;'
        'display:flex;align-items:center;justify-content:space-between;gap:1rem'
        '">'

        '<div style="display:flex;align-items:center;gap:.9rem">'
        '<span style="font-size:2.1rem;line-height:1">⚽</span>'
        '<div>'
        '<div style="font-size:1.1rem;font-weight:900;color:#fff;letter-spacing:-.02em;line-height:1.2">'
        'Bolão Copa 2026'
        '</div>'
        '<div style="font-size:.68rem;color:#5a8ab0;text-transform:uppercase;'
        'letter-spacing:.1em;margin-top:.15rem">'
        '📊 Estatísticas &nbsp;·&nbsp; 🔮 Previsões &nbsp;·&nbsp; 🎯 Monte Carlo Elo'
        '</div>'
        '</div>'
        '</div>'

        '<div style="text-align:right;font-size:.7rem;color:#3a5a78;white-space:nowrap;flex-shrink:0">'
        '<div style="font-weight:800;color:#c9a902;font-size:.78rem">FIFA World Cup™</div>'
        '<div style="margin-top:.15rem">🇺🇸 🇨🇦 🇲🇽 &nbsp;·&nbsp; Jun – Jul 2026</div>'
        '</div>'

        '</div>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Renderiza banner de identidade + botão hamburger + menu de navegação."""
    components.html(_TOGGLE_HTML, height=0, scrolling=False)
    render_page_header()
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
        st.page_link('pages/1_Campeoes.py',    label='🏆  Probabilidades de Título')
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
