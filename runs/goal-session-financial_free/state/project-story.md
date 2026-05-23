# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session opened by taking careful stock of what the platform could already do before adding anything new. Running every must-have capability against the live product confirmed an encouraging starting point: six core abilities already work — turning a plain-English strategy into a real backtest, browsing and reopening past runs, stress-testing a strategy across rolling out-of-sample windows, getting ranked AI suggestions, choosing from the available coins and timeframes, and re-running quickly from a warm cache. The big ambition still ahead was a hands-free, automated strategy search.

This iteration laid the first stone of that automated layer — and it works. You can now start a fully hands-free strategy search with a single command, no browser and no clicking. Behind the scenes it seeds a starting strategy, then tries AI-suggested improvements one round at a time, reusing the very same backtest engine and safety sandbox a manual run uses — so an automated run produces records indistinguishable from a hand-driven one. It stops cleanly the moment it either meets the success targets you set or reaches its budget, and it never sneaks in "one more round" past the cap. Crucially, it picks its winner with a skeptical eye: the strategy it marks "best" has to survive an out-of-sample validation test, so a flashier-looking result that doesn't hold up can't take the crown. Each run carries a durable status — its state, why it stopped, which round won, and how much budget it used — that is saved to disk and survives a server restart; if the server is interrupted mid-run, that run is tidied up rather than left stuck "running" forever. Best of all, the whole thing shows up in your normal session list, browsable like any other run.

The next focus is making this visible and clickable: on-screen controls to start an automated run, watch it work live, and stop it — then, after that, the smarter open-ended search that explores symbols and timeframes on its own and learns from past runs.

## What it can do today

The product lets users describe a trading strategy in plain English and run it against real crypto price history, browse and reopen past runs with their full results and trades, validate a strategy across rolling out-of-sample windows, get ranked AI suggestions, pick from the available coins and timeframes, re-run quickly from a warm cache, and — new this round — kick off a hands-free, budget-capped automated strategy search with a single command that runs to a clean finish and marks its most robust result, all visible as an ordinary session.

_Last updated: 2026-05-23 after iteration 1._
