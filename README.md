# ⚽ Bolão Copa do Mundo 2026

Previsão probabilística da Copa do Mundo 2026 usando **Elo Rating** + **Simulação Monte Carlo**.

## Funcionalidades

| Página | Descrição |
|---|---|
| 🏠 Home | Top 10 favoritos ao título |
| 🏆 Campeões | Probabilidades completas por fase |
| 🎲 Simulação | Simular 1 torneio ou rodar Monte Carlo |
| ➕ Novo Resultado | Cadastrar partidas e recalcular Elo |
| 📋 Histórico | Navegar pelo histórico de partidas |
| 📊 Ranking Elo | Ranking atual de todas as seleções |
| 📈 Evolução | Evolução do Elo ao longo do tempo |
| 📖 Documentação | Explicação detalhada do modelo |

---

## Instalação e Execução Local

### 1. Clonar ou baixar o projeto

```bash
# Se estiver usando git
git clone <url-do-repo>
cd bolao

# Ou simplesmente entre na pasta do projeto
cd bolao
```

### 2. Criar ambiente virtual (recomendado)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Baixar dados históricos

```bash
python scripts/download_data.py
```

> Baixa o `results.csv` (~7 MB, ~49.000 partidas desde 1872) do repositório
> [martj42/international_results](https://github.com/martj42/international_results).
>
> **O app funciona sem este passo** (modo demo com ratings pré-calculados),
> mas as probabilidades serão menos precisas.

### 5. Rodar o app

```bash
streamlit run app.py
```

Abra no browser: [http://localhost:8501](http://localhost:8501)

---

## Estrutura de Pastas

```
bolao/
├── app.py                   # Página inicial do Streamlit
├── config.py                # Configurações: grupos da Copa, Elo params
├── requirements.txt
├── README.md
│
├── src/
│   ├── elo.py               # Algoritmo Elo Rating
│   ├── data_loader.py       # Carregamento e persistência de dados
│   └── monte_carlo.py       # Simulação Monte Carlo
│
├── pages/
│   ├── 1_Campeoes.py
│   ├── 2_Simulacao.py
│   ├── 3_Novo_Resultado.py
│   ├── 4_Historico.py
│   ├── 5_Ranking_Elo.py
│   ├── 6_Evolucao.py
│   └── 7_Documentacao.py
│
├── data/
│   ├── results.csv          # Baixado pelo script (não versionado)
│   └── manual_results.csv   # Criado automaticamente pelo app
│
└── scripts/
    └── download_data.py     # Script de download dos dados
```

---

## Configuração dos Grupos

Edite `config.py` para atualizar os grupos da Copa 2026 com o sorteio oficial da FIFA:

```python
COPA_2026_GROUPS = {
    'A': ['Brasil', 'Alemanha', 'Marrocos', 'Japão'],
    # ... atualize com os grupos reais
}
```

---

## Modelo de Dados

### `data/results.csv` (martj42)

| Coluna | Tipo | Descrição |
|---|---|---|
| date | date | Data da partida |
| home_team | string | Time mandante |
| away_team | string | Time visitante |
| home_score | int | Gols mandante |
| away_score | int | Gols visitante |
| tournament | string | Nome da competição |
| city | string | Cidade |
| country | string | País |
| neutral | bool | Campo neutro? |

### `data/manual_results.csv`

Mesmo esquema. Criado automaticamente pela página "Novo Resultado".

---

## Algoritmo Elo

**Probabilidade esperada:**
```
E_A = 1 / (1 + 10^((R_B - R_A) / 400))
```

**Atualização:**
```
R'_A = R_A + K × (S_A - E_A)
```

**Fatores K:**
- Copa do Mundo: 60
- Qualificatórias / Copas Continentais: 40
- Amistosos: 20
- Vantagem de campo: +100 pontos Elo

---

## Simulação Monte Carlo

Para cada simulação:
1. Sorteia resultados da fase de grupos (probabilidades Elo)
2. Classifica 32 times (top-2 + 8 melhores 3os)
3. Simula chaveamento eliminatório
4. Registra o campeão e fases alcançadas

Rodando 5.000× e contando as frequências → probabilidades de título/final/etc.

---

## Fontes de Dados

- **martj42/international_results** — resultados desde 1872
- **jfjelstul/worldcup** — dados estruturados das Copas do Mundo

---

## Próximos Passos

- [ ] Integrar ranking FIFA oficial
- [ ] Incorporar odds de casas de apostas
- [ ] Adicionar efeito de forma recente (últimos 5 jogos)
- [ ] Modelo Dixon-Coles para simulação de gols
- [ ] Considerar lesões/suspensões do elenco
- [ ] Deploy no Streamlit Cloud
