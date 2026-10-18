# Agent skills for apps using pyiv

Recommended Cursor/Codex-style skills and a short requirements rule so coding
agents use pyiv correctly (DI, top-level imports, test doubles).

These files are **for downstream projects**, not for developing pyiv itself
(maintainer skills live under `.cursor/skills/`).

**Maintainer requirement:** when public injectables, doubles, Config patterns,
or top-level exports change, update these skills (and
`docs/guide/agent-skills.rst`) in the **same** change. Stale consumer skills
are treated as a docs/product bug — see `AGENTS.md` and
`.cursor/skills/maintain-docs/SKILL.md`.

## Contents

| Path | Purpose |
| --- | --- |
| [`use-pyiv/SKILL.md`](use-pyiv/SKILL.md) | Config, injection, top-level APIs |
| [`pyiv-testing/SKILL.md`](pyiv-testing/SKILL.md) | Bind doubles instead of monkeypatching |
| [`pyiv.mdc`](pyiv.mdc) | Compact always-on-style requirements rule |

## Install into your project

**Cursor skills** — copy a skill directory into `.cursor/skills/`:

```bash
mkdir -p .cursor/skills
curl -fsSL \
  https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/use-pyiv/SKILL.md \
  -o .cursor/skills/use-pyiv/SKILL.md --create-dirs
```

Or clone sparingly:

```bash
git clone --depth 1 https://github.com/rl337/pyiv.git /tmp/pyiv
cp -R /tmp/pyiv/agent-skills/use-pyiv .cursor/skills/
cp -R /tmp/pyiv/agent-skills/pyiv-testing .cursor/skills/
cp /tmp/pyiv/agent-skills/pyiv.mdc .cursor/rules/
```

**Cursor rules** — copy `pyiv.mdc` into `.cursor/rules/` and adjust `globs` if needed.

Prefer **raw URLs on `main`** so agents always fetch the latest published guidance.

## Latest on GitHub

- Browse: https://github.com/rl337/pyiv/tree/main/agent-skills
- use-pyiv (raw): https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/use-pyiv/SKILL.md
- pyiv-testing (raw): https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/pyiv-testing/SKILL.md
- pyiv.mdc (raw): https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/pyiv.mdc

Docs: https://rl337.org/pyiv/guide/agent-skills.html
