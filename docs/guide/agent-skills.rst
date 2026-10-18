Agent skills for your project
=============================

pyiv ships **customer-facing** Cursor/Codex-style skills and a short requirements
rule so coding agents in *your* repository use DI, top-level imports, and test
doubles correctly.

These live in the GitHub tree under ``agent-skills/`` (not the maintainer skills
under ``.cursor/skills/``). **Latest published copies are always on**
``main`` — prefer raw GitHub URLs so you do not pin a stale snapshot.

What to install
---------------

* **use-pyiv** — Config, injection, top-level ``from pyiv import …`` surface
* **pyiv-testing** — bind Memory/Synthetic doubles instead of monkeypatching
* **pyiv.mdc** — compact project rule (globs / always-apply style)

Browse the directory:

https://github.com/rl337/pyiv/tree/main/agent-skills

Latest raw files (``main``)
---------------------------

* use-pyiv:
  https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/use-pyiv/SKILL.md
* pyiv-testing:
  https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/pyiv-testing/SKILL.md
* requirements rule:
  https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/pyiv.mdc
* README (install notes):
  https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/README.md

Copy into Cursor
----------------

.. code-block:: bash

   mkdir -p .cursor/skills/use-pyiv .cursor/skills/pyiv-testing .cursor/rules
   curl -fsSL \
     https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/use-pyiv/SKILL.md \
     -o .cursor/skills/use-pyiv/SKILL.md
   curl -fsSL \
     https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/pyiv-testing/SKILL.md \
     -o .cursor/skills/pyiv-testing/SKILL.md
   curl -fsSL \
     https://raw.githubusercontent.com/rl337/pyiv/main/agent-skills/pyiv.mdc \
     -o .cursor/rules/pyiv.mdc

Adjust ``globs`` in ``pyiv.mdc`` if your app layout differs.

Kept in sync by pyiv maintainers
--------------------------------

When pyiv adds or changes public injectables, doubles, or Config patterns, the
``agent-skills/`` files and this page are updated in the same change. If you
fork or vendor a copy, re-fetch from ``main`` periodically so agents see current
guidance.

See also :doc:`testing` and the stdlib surfaces catalog on GitHub:
https://github.com/rl337/pyiv/blob/main/docs/inspiration/stdlib-injectable-surfaces.md
