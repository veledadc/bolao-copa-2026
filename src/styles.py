"""Dark sports-editorial CSS for Bolão Copa 2026."""


def get_css() -> str:
    return """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body { font-family:'Inter',system-ui,sans-serif!important; }
.stApp      { background:#05101e!important; color:#d8e2ef!important; }

/* chrome */
#MainMenu,footer,[data-testid="stToolbar"],.stDeployButton{display:none!important;}

/* header */
[data-testid="stHeader"]{
  background:linear-gradient(90deg,#001133,#002255)!important;
  border-bottom:3px solid #c9a902!important;
}

/* hide Streamlit's auto-generated page list */
[data-testid="stSidebarNav"]{display:none!important;}

/* sidebar reopen control — must ALWAYS stay visible & on top so the menu
   can be reopened after it collapses (auto on mobile, or manually) */
[data-testid="stSidebarCollapsedControl"]{
  display:flex!important;
  visibility:visible!important;
  opacity:1!important;
  position:fixed!important;
  top:.55rem!important;
  left:.6rem!important;
  z-index:999999!important;
  background:#0c1c2e!important;
  border:1px solid #c9a902!important;
  border-radius:6px!important;
}
[data-testid="stSidebarCollapsedControl"]:hover{
  background:#13284a!important;
}
[data-testid="stSidebarCollapsedControl"] *{
  color:#c9a902!important;
  fill:#c9a902!important;
  visibility:visible!important;
  opacity:1!important;
}

/* sidebar */
[data-testid="stSidebar"]{
  background:#060f1c!important;
  border-right:1px solid #0d2040!important;
}
[data-testid="stSidebar"] *{color:#8eaabf!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3{color:#c9a902!important;}

/* page_link nav items in sidebar */
[data-testid="stSidebar"] [data-testid="stPageLink"]{
  display:block!important;border-radius:8px!important;
  margin:.15rem 0!important;transition:all .15s!important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] [data-testid="stPageLink"] span,
[data-testid="stSidebar"] [data-testid="stPageLink"] p{
  color:#7a9ab8!important;font-weight:600!important;
  font-size:.87rem!important;text-decoration:none!important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"]:hover{
  background:#0c1e30!important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"]:hover span,
[data-testid="stSidebar"] [data-testid="stPageLink"]:hover p{
  color:#c9a902!important;
}
[data-testid="stSidebar"] [aria-current="page"] [data-testid="stPageLink"],
[data-testid="stSidebar"] [data-testid="stPageLink"][aria-current="page"]{
  background:#0a1e30!important;border-left:3px solid #c9a902!important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"][aria-current="page"] span,
[data-testid="stSidebar"] [data-testid="stPageLink"][aria-current="page"] p{
  color:#c9a902!important;
}
[data-testid="stSidebar"] .stButton>button{
  background:transparent!important;border:1px solid #1a3050!important;
  color:#8eaabf!important;font-weight:600!important;border-radius:6px!important;
  text-align:left!important;width:100%!important;
}
[data-testid="stSidebar"] .stButton>button:hover{
  background:#0c1e30!important;color:#c9a902!important;border-color:#c9a902!important;
}

/* typography */
h1{color:#fff!important;font-weight:900!important;letter-spacing:-.03em!important;}
h2{color:#c9a902!important;font-weight:800!important;}
h3{color:#7eaacc!important;font-weight:700!important;}

/* container */
.main .block-container{padding:1.2rem 1.8rem 3rem!important;max-width:1440px!important;}

/* metrics */
[data-testid="metric-container"]{
  background:#0b1825!important;border:1px solid #0f2540!important;
  border-radius:12px!important;padding:.85rem 1.1rem!important;transition:border-color .2s!important;
}
[data-testid="metric-container"]:hover{border-color:#1e4070!important;}
[data-testid="stMetricLabel"]{color:#5a7a98!important;font-size:.78rem!important;text-transform:uppercase;letter-spacing:.05em;}
[data-testid="stMetricValue"]{color:#c9a902!important;font-weight:900!important;font-size:1.55rem!important;}
[data-testid="stMetricDelta"]{font-size:.78rem!important;}
[data-testid="stMetricDelta"] svg{display:none!important;}

/* buttons */
.stButton>button{border-radius:8px!important;font-weight:700!important;font-size:.88rem!important;transition:all .18s!important;}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#002fa8,#004ee0)!important;border:none!important;
  color:#fff!important;box-shadow:0 2px 8px rgba(0,78,224,.3)!important;
}
.stButton>button[kind="primary"]:hover{
  background:linear-gradient(135deg,#0040cc,#0066ff)!important;
  box-shadow:0 4px 16px rgba(0,102,255,.5)!important;transform:translateY(-1px)!important;
}
.stButton>button[kind="secondary"]{
  background:transparent!important;border:1px solid #cc3333!important;color:#ff7777!important;
}
.stButton>button[kind="secondary"]:hover{background:rgba(204,51,51,.15)!important;border-color:#ff4444!important;}

/* tabs */
.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:2px solid #0d2040!important;gap:0!important;}
.stTabs [data-baseweb="tab"]{
  background:transparent!important;border:none!important;border-radius:0!important;
  border-bottom:2px solid transparent!important;color:#4a6e8a!important;
  font-weight:600!important;padding:.55rem 1.1rem!important;margin-bottom:-2px!important;transition:all .15s!important;
}
.stTabs [data-baseweb="tab"]:hover{color:#8eaacc!important;}
.stTabs [aria-selected="true"]{color:#c9a902!important;border-bottom:2px solid #c9a902!important;background:transparent!important;}

/* alerts */
.stAlert{border-radius:8px!important;}

/* expander */
.streamlit-expanderHeader{
  background:#0b1825!important;border:1px solid #0f2540!important;
  border-radius:8px!important;font-weight:600!important;color:#7eaacc!important;
}
.streamlit-expanderContent{
  background:#08141f!important;border:1px solid #0f2540!important;
  border-top:none!important;border-radius:0 0 8px 8px!important;
}

/* inputs */
[data-baseweb="select"]>div,[data-testid="stNumberInput"]>div>div{
  background:#0b1825!important;border-color:#0f2540!important;color:#d8e2ef!important;
}

/* hr */
hr{border-color:#0d2040!important;margin:1.5rem 0!important;}

/* spinner */
[data-testid="stSpinner"]>div>div{border-top-color:#c9a902!important;}

/* ── custom components ── */
.match-card{
  background:#0b1825;border:1px solid #0f2540;border-radius:8px;
  padding:.6rem .9rem;margin:.25rem 0;
}
.match-card.official{border-left:4px solid #00aa55;}
.match-card.simulated{border-left:4px solid #2255cc;}
.match-card.pending{border-left:4px solid #1a3050;}
.match-row{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;}
.match-team{font-weight:700;font-size:.92rem;flex:1;min-width:80px;}
.match-team.right{text-align:right;}
.match-score{
  font-size:1.1rem;font-weight:900;color:#c9a902;
  min-width:54px;text-align:center;background:#060f1c;
  border-radius:6px;padding:2px 8px;flex:0 0 auto;
}
.match-score.tbd{color:#1e3a60;}
.match-meta{color:#3a5a78;font-size:.72rem;margin-top:.25rem;}
.match-status{font-size:.7rem;font-weight:700;text-align:right;flex:0 0 auto;}
.match-status.lk{color:#00aa55;}
.match-status.sim{color:#2255cc;}

.group-pill{
  display:inline-block;background:#c9a902;color:#000!important;font-weight:800;
  font-size:.8rem;border-radius:4px;padding:1px 8px;letter-spacing:.04em;margin-bottom:.4rem;
}
.section-title{
  font-size:.95rem;font-weight:800;color:#c9a902;text-transform:uppercase;
  letter-spacing:.1em;border-left:4px solid #c9a902;padding:.3rem .8rem;
  background:linear-gradient(90deg,rgba(201,169,2,.08),transparent);
  border-radius:0 4px 4px 0;margin:1.2rem 0 .6rem;
}
.stage-label{
  display:inline-block;background:#0d1e30;border:1px solid #1e3a5a;
  border-radius:20px;padding:3px 14px;font-size:.75rem;font-weight:700;
  color:#5a8ab0;text-transform:uppercase;letter-spacing:.07em;
}
.tv-chip{
  display:inline-block;border-radius:4px;padding:1px 7px;
  font-size:.68rem;font-weight:700;margin:1px 2px;
}
.tv-globo{background:#ff6600;color:#fff!important;}
.tv-sportv{background:#007f28;color:#fff!important;}
.tv-cazé{background:#cc0000;color:#fff!important;}
.tv-globoplay{background:#e50914;color:#fff!important;}
.tv-fifaplus{background:#004d9e;color:#fff!important;}

.bracket-card{
  background:#0b1825;border:1px solid #0f2540;border-radius:8px;
  padding:.55rem .8rem;margin:.2rem 0;font-size:.82rem;
}
.bracket-team{font-weight:700;padding:.18rem .3rem;border-radius:4px;}
.bracket-team.winner{background:#0a2e1a;color:#4cff80;}
.bracket-team.tbd{color:#243a52;font-style:italic;}
.bracket-divider{border-top:1px solid #0d2040;margin:.2rem 0;}

/* ── mobile responsive ── */
@media (max-width:768px){
  /* tighter content padding */
  .main .block-container{padding:.5rem .7rem 2rem!important;max-width:100%!important;}

  /* smaller headings */
  h1{font-size:1.35rem!important;letter-spacing:-.01em!important;}
  h2{font-size:1rem!important;}
  h3{font-size:.9rem!important;}

  /* compact section labels + stage chip */
  .section-title{font-size:.75rem!important;padding:.22rem .6rem!important;margin:.8rem 0 .4rem!important;}
  .stage-label{font-size:.62rem!important;padding:2px 10px!important;}

  /* tighter nav bar */
  nav{gap:.25rem!important;margin-top:.55rem!important;}
  nav a{padding:.28rem .5rem!important;font-size:.7rem!important;gap:.2rem!important;}

  /* compact metrics */
  [data-testid="metric-container"]{padding:.55rem .75rem!important;}
  [data-testid="stMetricValue"]{font-size:1.15rem!important;}
  [data-testid="stMetricLabel"]{font-size:.68rem!important;}

  /* match rows: smaller text */
  .match-meta{font-size:.62rem!important;}
  .match-team{font-size:.82rem!important;}
  .match-score{font-size:.95rem!important;min-width:44px!important;padding:1px 5px!important;}

  /* tv chips */
  .tv-chip{font-size:.6rem!important;padding:1px 5px!important;}

  /* buttons — smaller on mobile */
  .stButton>button{font-size:.78rem!important;padding:.3rem .6rem!important;}

  /* expander header */
  .streamlit-expanderHeader{font-size:.83rem!important;padding:.45rem .7rem!important;}

  /* dataframe — let it scroll horizontally */
  [data-testid="stDataFrame"]{overflow-x:auto!important;}
}

/* very small screens (phones < 480px) */
@media (max-width:480px){
  h1{font-size:1.1rem!important;}
  .main .block-container{padding:.4rem .5rem 1.5rem!important;}
  nav a{font-size:.65rem!important;padding:.24rem .4rem!important;}
}

</style>"""
