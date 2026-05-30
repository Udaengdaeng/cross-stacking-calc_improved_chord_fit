# Tire Chord Fit Cross Stack

## Files to upload to GitHub / Streamlit Cloud

- `app.py`
- `calc.py`
- `visualize.py`
- `requirements.txt`

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Main logic

This version removes fixed `c_base` and uses relaxed chord-fit judgement:

```text
hole inner chord × inner_margin × rubber_allowance
>=
inserted tire outer chord effective × outer_margin
```

The model is a geometry approximation, not a full physics collision simulation.
