# DomenicAIn — Hackapizza 2.0

Official repository of the **DomenicAIn** team for **Hackapizza 2.0**.

## About Hackapizza 2.0

Hackapizza 2.0 is a hackathon focused on building innovative solutions with **Generative AI**. The event is connected to [DataPizza](https://datapizza.tech/), the Italian tech community and AI company behind the open-source **Datapizza AI** framework — a Python framework for building LLM-powered agents, RAG systems, and production-ready GenAI applications.

## Team DomenicAIn

We're building something cool with AI. 🍕

## Tech Stack

This project uses the [Datapizza AI](https://github.com/datapizza-labs/datapizza-ai) framework — a lightweight, API-first GenAI framework designed for speed and reliability.

- **Framework:** [Datapizza AI](https://github.com/datapizza-labs/datapizza-ai)
- **Language:** Python

## Setup

### Prerequisites

- Python 3.12
- pip

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/lorenzomelchionna/domenicAIn_hackapizza.git
   cd domenicAIn_hackapizza
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv hackapizza_env
   source hackapizza_env/bin/activate  # On Windows: hackapizza_env\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

```
domenicAIn_hackapizza/
├── src/
│   ├── agents/              # Definizioni degli agenti (Restaurant Manager + sub-agenti)
│   │   ├── restaurant_manager.py   # Orchestratore principale
│   │   ├── diplomatico.py          # Diplomazia e messaggi tra team
│   │   ├── menu_decider_pre_bid.py # Selezione ricette pre-asta
│   │   ├── menu_decider_post_bid.py# Menu finale e prezzi post-asta
│   │   ├── analyst.py             # Analisi prezzi d'asta (storico bid)
│   │   ├── auction_broker.py      # Invio offerte asta ingredienti
│   │   ├── market_broker.py       # Mercato interno (scambi tra ristoranti)
│   │   └── maitre.py              # Gestione ordini e servizio clienti
│   ├── prompts/             # System prompt per ogni agente
│   ├── state/               # GameState e StateUpdater (stato condiviso)
│   ├── sse/                 # Listener eventi SSE real-time
│   ├── tools/               # Wrapper MCP (game_tools, analyst_tools, mcp_client)
│   ├── schemas/             # Modelli Pydantic (Recipe, MenuItem, AuctionBid, ecc.)
│   ├── data_collector/      # Raccolta dati per analytics e storico
│   ├── config.py
│   ├── main.py              # Entry point asincrono, loop eventi
│   ├── blog_sentiment.py    # Blog Insight Agent (Cronache del Cosmo)
│   └── blog_archetype.py    # Scraping post blog
├── knowledge/               # Documentazione e diagrammi
│   ├── agent_flow_graph.html    # Grafo interattivo del flusso agenti
│   ├── hackapizza_knowledge_graph.html
│   └── challenge_description.md
├── run.py                   # Entry point (python run.py)
├── streamlit_app.py         # Dashboard di monitoraggio
├── requirements.txt
└── .env.example             # TEAM_ID, TEAM_API_KEY, REGOLO_API_KEY
```

## Architettura Multi-Agent

Il sistema segue un modello **orchestratore + sub-agenti** guidato dagli eventi SSE del gioco.

### Flusso delle fasi di gioco

Ogni turno attraversa le fasi: `speaking` → `closed_bid` → `waiting` → `serving` → `stopped`.

| Fase | Descrizione | Agenti attivi |
|------|-------------|---------------|
| **speaking** | Pianificazione, diplomazia, selezione ricette | Restaurant Manager, Blog Insight, Menu Decider Pre-Bid, Analyst, Diplomatico |
| **closed_bid** | Asta cieca ingredienti | Auction Broker |
| **waiting** | Menu finale e prezzi | Menu Decider Post-Bid |
| **serving** | Servizio clienti | Maître (triggered da SSE) |
| **stopped** | Fine turno | Orchestratore (raccolta dati) |

### Ruoli degli agenti

- **Restaurant Manager** — Orchestratore centrale. Riceve il contesto e delega ai sub-agenti in base alla fase. Non ha tool propri (tranne `update_restaurant_is_open`); usa `can_call()` per invocare gli altri agenti.
- **Blog Insight Agent** — Legge l’ultimo post delle *Cronache del Cosmo* e produce un insight strategico per la selezione ricette (Case A: primo turno o notizie nuove).
- **Menu Decider Pre-Bid** — Sceglie le ricette per il draft menu usando `get_recipes`, `get_dish_popularity_stats` (se DB presente) e `save_draft_menu`. Usa l’insight del blog o i top venduti (Case B).
- **Analyst** — Analizza lo storico delle aste (`get_winning_bid_statistics`) e produce `suggested_bids` (prezzi suggeriti per ingrediente) con `save_suggested_bids`.
- **Auction Broker** — In fase `closed_bid` invia le offerte all’asta con `closed_bid`, usando `draft_menu` e `suggested_bids`.
- **Menu Decider Post-Bid** — Dopo l’asta, calcola i prezzi finali con `calculate_suggested_prices` e pubblica il menu con `save_menu`.
- **Maître** — Gestisce ordini e servizio. Viene invocato dagli eventi SSE `client_spawned` e `preparation_complete`. Usa `prepare_dish` e `serve_dish`, rispettando le intolleranze.
- **Diplomatico** — Invia messaggi agli altri team con `send_message`.
- **Market Broker** — (attualmente disabilitato) Gestisce scambi sul mercato interno (`create_market_entry`, `execute_transaction`, `delete_market_entry`).

### Stato condiviso (GameState)

Tutti gli agenti condividono un `GameState` aggiornato da `StateUpdater` (HTTP) e dagli eventi SSE. Contiene: `phase`, `turn_id`, `balance`, `reputation`, `inventory`, `menu`, `draft_menu`, `suggested_bids`, `actual_bids`, `meals`, `pending_clients`, `blog_insight`, ecc.

### Eventi SSE e reazioni

| Evento | Azione |
|--------|--------|
| `game_started` | Apertura ristorante, refresh stato, Blog Insight (se Case A), orchestratore speaking |
| `game_phase_changed` | Esecuzione orchestratore o Auction Broker (se `closed_bid`) |
| `client_spawned` | Maître: match ordine → piatto, `prepare_dish` |
| `preparation_complete` | Maître: `serve_dish` |

### Diagramma del flusso

Un grafo interattivo dell’architettura è disponibile in `knowledge/agent_flow_graph.html`.

## Esecuzione

### Avvio del sistema multi-agent

1. Copia `.env.example` in `.env` e imposta `TEAM_ID`, `TEAM_API_KEY`, `REGOLO_API_KEY`
2. Esegui: `python run.py` (dalla root del repo)

### Monitoraggio con Streamlit

Per monitorare il sistema tramite dashboard web invece che da terminale:

1. In un terminale: `python run.py` (avvia il gioco)
2. In un altro terminale: `streamlit run streamlit_app.py`

La dashboard mostra fase, turno, saldo, reputazione, menu, inventario, entry di mercato e un log eventi in tempo reale. Si aggiorna ogni 3 secondi.

## Git Flow

We use a simple **Git Flow** workflow for collaborative coding:

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code. Always deployable. |
| `develop` | Integration branch. Latest changes for the next release. |
| `feature/*` | New features (e.g. `feature/add-rag-pipeline`). |
| `fix/*` | Bug fixes (e.g. `fix/agent-timeout`). |

### Workflow

1. **Start work** — Branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Commit & push** — Push your branch and open a Pull Request to `develop`:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feature/your-feature-name
   ```

3. **Merge** — After review, merge the PR into `develop`. Delete the feature branch after merge.

4. **Release** — When ready for production, merge `develop` into `main` and tag the release.

### Commit messages

Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`.

## Resources

- [Datapizza AI Documentation](https://docs.datapizza.ai)
- [Datapizza AI GitHub](https://github.com/datapizza-labs/datapizza-ai)
- [DataPizza Community](https://datapizza.tech/)

## License

TBD
