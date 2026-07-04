# CLAUDE.md — Diretrizes do Projeto Bolão Copa 2026

## Contexto

App Streamlit de bolão/predictor para a Copa do Mundo 2026.
Stack: Python · Streamlit · Plotly · Monte Carlo · Elo ratings.

Arquitetura:
- `app.py` — página principal (grupos + mata-mata + favoritos)
- `pages/` — páginas individuais (Campeões, Simulação, Ranking Elo, etc.)
- `src/styles.py` — CSS global injetado em todas as páginas
- `src/sidebar.py` — sidebar de navegação + banner de identidade (compartilhado)
- `src/copa_manager.py`, `src/monte_carlo.py`, `src/elo.py` — core de lógica
- `data/` — estado persistido (resultados, elos, histórico)

## Regra Principal — Preservação do Core

> **Nenhuma melhoria ou correção pode alterar a estrutura central do projeto.**

O que isso significa na prática:

- **Não reorganizar** arquivos, módulos, ou fluxo de dados existentes.
- **Não refatorar** funções que já funcionam só por questão estética.
- **Não adicionar abstrações** ou camadas desnecessárias.
- **Não mudar** a lógica de negócio (simulações, cálculo de Elo, standings, bracket).
- **Não alterar** comportamento de botões, formulários, ou gravação de resultados.
- Aplicar apenas **correções pontuais** ou **ajustes de apresentação** no escopo solicitado.

## O que é permitido (ajustes sem quebrar o core)

- Editar CSS em `src/styles.py` para melhorias visuais.
- Editar `src/sidebar.py` para componentes de navegação/header compartilhados.
- Adicionar/corrigir HTML inline em `st.markdown()` existentes.
- Corrigir bugs isolados sem afetar outros fluxos.
- Melhorar responsividade mobile sem tocar na lógica.

## Componentes compartilhados

O `render_sidebar()` em `src/sidebar.py` é chamado por **todas** as páginas.
Qualquer mudança nele afeta o app inteiro — agir com cuidado.

O `get_css()` em `src/styles.py` é injetado em todas as páginas via `st.markdown(get_css(), unsafe_allow_html=True)`.
