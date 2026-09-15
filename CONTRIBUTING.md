# Contributing

Thanks for interest. This is an early research prototype.

## Rules of the road

1. **No exploit recipes.** PRs that add live discovery of public Schelling points, attack automation, or weaponized payloads will be rejected.
2. **Tests required** for closure / PDP / fixture behavior changes (`pytest`).
3. Keep the label honest: if something is illustrative (flow typing), say so in code and docs.
4. Prefer small PRs: graph model, fixtures, schema, docs.

## Dev setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
mesa-ibi-scan --fixture hf_like
```

## Code of conduct

Be respectful. Security research discussion is welcome; harassment and doxxing are not.
