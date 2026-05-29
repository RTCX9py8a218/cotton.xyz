# Origin basis analysis

## Brazil

Run `python3 brazil_basis_model.py` for demo calibration.

Backtest vs actual CEPEA + ICE + USD/BRL:

```bash
cd backend && source .venv/bin/activate
python analysis/brazil_basis_backtest.py
python analysis/generate_backtest_docx.py
```

**v3 model:** `Mark = ICE + β_const` (504d median CEPEA−ICE). Residual basis on-book.

Outputs:
- `analysis/data/backtest_results.json`
- `analysis/data/constant_params.json` — per-origin β for relayer
- `docs/brazil-basis-backtest.docx`

## Australia

Data reliability assessment and provisional β_const:

```bash
cd backend && source .venv/bin/activate
python analysis/australia_basis_backtest.py
```

Australia uses the same v4 relayer engine as Brazil. β is provisional (~+2.8¢/lb) until ABARES AUD/bale series is wired.
