# ICMIC 2026 Short Paper Draft

Short-paper draft for ICMIC 2026:
**Uncertainty-Aware Task Routing for Resilient Edge AI in Mobile and Maritime Networks**

## Build
```bash
pdflatex paper.tex
```

## Setup
Install the Python dependencies before running experiments:

```bash
pip install -r requirements.txt
```

The Kaggle download also requires Kaggle API credentials. You can either place
`kaggle.json` in the Kaggle config directory for your OS, or add credentials to
an ignored `.env` file at the repo root:

```bash
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_api_key
```

If your `.env` already has only the API key as `KAGGLE_API_TOKEN`, add your
Kaggle username alongside it:

```bash
KAGGLE_USERNAME=your_username
KAGGLE_API_TOKEN=your_api_key
```

If you copied the whole `kaggle.json` token into `.env`, this is also supported:

```bash
KAGGLE_API_TOKEN='{"username":"your_username","key":"your_api_key"}'
```

## Experiments
The experiment script now uses Kaggle's **Ships in Satellite Imagery** dataset
instead of CIFAR. Download and extract the dataset so the repo contains either
`data/ships-in-satellite-imagery/shipsnet.json` or an extracted
`data/ships-in-satellite-imagery/shipsnet/` image folder.

```bash
kaggle datasets download -d rhammell/ships-in-satellite-imagery -p data/ships-in-satellite-imagery --unzip
python experiments/run_edge_ai_routing_experiments.py --dataset-root data/ships-in-satellite-imagery
```

The script can also auto-download the Kaggle dataset when `.env` contains valid
credentials, so the explicit `kaggle datasets download ...` step is optional.

The script trains a binary vessel classifier, creates nominal and adverse-weather
confidence traces, and writes the routing result CSV/PDF artifacts at the repo
root by default.
