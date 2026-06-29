"""
Página 7 — Documentação do Modelo
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from src.elo import win_probability
from src.styles import get_css
from src.sidebar import render_sidebar

st.set_page_config(page_title='Documentação · Bolão 2026', page_icon='📖',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown(get_css(), unsafe_allow_html=True)
render_sidebar()
st.title('📖 Como o Modelo Funciona')

# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(['⚡ Elo Rating', '🎲 Monte Carlo', '📂 Dados', '🚀 Próximos Passos'])

# ------------------------------------------------------------------
with tab1:
    st.header('Sistema de Elo Rating')
    st.markdown("""
O **Elo Rating** é um sistema de ranking numérico criado pelo físico Arpad Elo para xadrez
e amplamente adaptado para futebol (inclusive pela própria FIFA desde 2018).

### Como funciona

Cada seleção começa com um rating base (**1500**). Após cada jogo, pontos são
transferidos entre as equipes de acordo com:

1. **Resultado real** (vitória = 1, empate = 0.5, derrota = 0)
2. **Resultado esperado** — baseado na diferença de Elo entre os times
3. **Fator K** — peso do jogo (Copa do Mundo = 60; amistoso = 20)

### Fórmulas

**Probabilidade esperada de vitória:**
""")
    st.latex(r"E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}")

    st.markdown("""
**Atualização do rating:**
""")
    st.latex(r"R'_A = R_A + K \cdot (S_A - E_A)")

    st.markdown("""
Onde:
- $R_A$, $R_B$ = Elo atual das seleções A e B
- $S_A$ = resultado (1 = vitória, 0.5 = empate, 0 = derrota)
- $E_A$ = resultado esperado para A
- $K$ = fator de peso do torneio

### Fator K por competição

| Competição | K |
|---|---|
| Copa do Mundo FIFA | 60 |
| Qualificatórias / Copas Continentais | 40 |
| Amistosos | 20 |

### Vantagem de jogar em casa
""")
    st.markdown('Adicionamos **+100 Elo** ao mandante (ignorado em campo neutro).')

    # Gráfico interativo
    st.subheader('🔢 Calculadora de Probabilidade')
    c1, c2 = st.columns(2)
    with c1:
        elo_a = st.slider('Elo da Seleção A', 1400, 2200, 1800)
    with c2:
        elo_b = st.slider('Elo da Seleção B', 1400, 2200, 1600)

    prob = win_probability(elo_a, elo_b, neutral=True)
    st.metric('Probabilidade de vitória de A', f'{prob*100:.1f}%')

    x = np.linspace(-600, 600, 200)
    y = 1 / (1 + 10 ** (-x / 400))
    fig = go.Figure(go.Scatter(x=x, y=y * 100, mode='lines', line_color='royalblue'))
    fig.add_vline(x=elo_a - elo_b, line_dash='dash', line_color='red',
                  annotation_text=f'A-B = {elo_a-elo_b}')
    fig.update_layout(
        title='Probabilidade de Vitória × Diferença de Elo',
        xaxis_title='Diferença de Elo (A − B)',
        yaxis_title='Prob. Vitória A (%)',
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
with tab2:
    st.header('Simulação Monte Carlo')
    st.markdown("""
O **Monte Carlo** executa milhares de torneios completos de forma aleatória, usando as
probabilidades do Elo para cada partida. O resultado é a *frequência* com que cada seleção
vence, chega à final, etc.

### Passo a passo

1. **Fase de grupos (12 grupos × 4 times)**
   - Cada dupla joga uma vez (rodada de pontos corridos)
   - Empate, vitória e derrota simulados via variável aleatória com probabilidades Elo
   - Pontuação: vitória = 3 pts, empate = 1 pt, derrota = 0 pt
   - Classificação: pontos > saldo de gols > gols marcados

2. **Classificação**
   - 1º e 2º de cada grupo avançam (24 times)
   - Os 8 melhores 3os colocados avançam (8 times)
   - Total: **32 times** nas oitavas de final

3. **Fase eliminatória (Oitavas → Final)**
   - Sorteio aleatório do chaveamento
   - Sem empate — probabilidade de pênaltis incorporada (~50/50 entre os times)

4. **Repetição**
   - O processo acima é repetido N vezes (padrão: 5.000)
   - Probabilidade de título = nº de vezes que o time venceu / N

### Probabilidade de empate

A probabilidade de empate varia com a diferença de qualidade:
""")
    st.latex(r"P_{draw} = \max(0.05,\ 0.28 - |P_A - 0.5| \times 0.50)")
    st.markdown("""
Jogos equilibrados têm mais empates (~28%); confrontos muito desiguais têm menos (~5%).

### Precisão

Com N = 5.000, o erro padrão para probabilidades em torno de 50% é ~0.7%.
Para probabilidades de título (≈ 20%), o erro é ~0.6%.
Aumente para N = 20.000 para resultados mais estáveis.
""")

# ------------------------------------------------------------------
with tab3:
    st.header('Fontes de Dados')
    st.markdown("""
### 1. martj42/international_results
- **URL:** github.com/martj42/international_results
- **Conteúdo:** Todos os resultados de partidas internacionais desde 1872
- **Colunas:** `date`, `home_team`, `away_team`, `home_score`, `away_score`, `tournament`, `city`, `country`, `neutral`
- **Uso neste projeto:** Base principal para calcular o Elo histórico das seleções

### 2. jfjelstul/worldcup
- **URL:** github.com/jfjelstul/worldcup
- **Conteúdo:** Dados estruturados das Copas do Mundo (partidas, gols, torneios, seleções, grupos)
- **Uso neste projeto:** Enriquecimento do histórico específico de Copa do Mundo

### Download dos dados

Execute no terminal:
```bash
python scripts/download_data.py
```

Isso baixa o `results.csv` automaticamente para a pasta `data/`.

### Dados manuais
Resultados adicionados na página "Novo Resultado" são salvos em `data/manual_results.csv`
e mesclados com o histórico na hora de calcular o Elo.
""")

# ------------------------------------------------------------------
with tab4:
    st.header('🚀 Evoluções Futuras')
    st.markdown("""
Este é um MVP. As funcionalidades abaixo melhorariam significativamente a precisão:

### 📡 Dados adicionais
| Feature | Impacto Estimado | Complexidade |
|---|---|---|
| **Ranking FIFA** | Médio | Baixa |
| **Odds de casas de apostas** | Alto | Média |
| **Elenco atual + avaliação individual** (ex: FIFA ratings) | Alto | Alta |
| **Lesões e suspensões** | Médio | Alta |
| **Forma recente** (últimos 5 jogos) | Alto | Baixa |
| **Head-to-head** | Médio | Baixa |

### 🧠 Melhorias no modelo
- **Weighting dinâmico**: Dar mais peso a resultados recentes
- **Margem de vitória**: Incorporar placar (5×0 ≠ 1×0)
- **Dixon-Coles model**: Modelo de Poisson para gols com correlação casa/fora
- **Pi-rating**: Sistema alternativo mais sofisticado que o Elo
- **Modelos de ML**: Random Forest / XGBoost com features ricas
- **Neural Elo**: LSTM para capturar sequências temporais

### 🖥️ Melhorias no produto
- Comparação entre cenários (com/sem lesões)
- Notificações em tempo real após jogos
- Exportação de relatório PDF
- API REST para consumo externo
- Integração com dados ao vivo (via APIs de futebol)
- Autenticação multi-usuário para o bolão entre amigos
""")
