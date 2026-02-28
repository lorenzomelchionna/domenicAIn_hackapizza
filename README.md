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
├── README.md
├── requirements.txt
└── hackapizza_env/     # Virtual environment (gitignored)
```

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
