# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session began on a strong foundation — you could already turn a plain-English idea into a real backtest, browse and reopen past runs, stress-test a strategy across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run quickly from a warm cache. The big ambition was a hands-free automated strategy search, and it arrived in stages. First it gained a brain: one command could seed a strategy and try AI-suggested improvements round by round, stopping when it met its targets or hit its budget, and crowning only a winner that survived out-of-sample testing. Then it became something you could see and steer — the search moved entirely onto the server, so you can reload the page or close your laptop and it keeps going, a live status strip shows it working, fresh attempts stream in without a refresh, and a real Stop button cancels it while keeping the best result so far.

Next it opened up the search itself: instead of refining one fixed setup, you can give it just a goal and a budget and let it pick its own coins and timeframes from a small, deliberately bounded shortlist, all held to a hard spending limit that climbs live against its caps. Then it became thrifty — it screens several setups cheaply on the cheapest AI model first and promotes only the single most promising survivor to the full, expensive treatment, so the "best" badge only ever lands on a fully validated result, never on a cheap candidate that merely flashed a high return.

The latest chapter taught the search to learn from your past runs. It was built once but lost before it could be saved — a technical mishap, with nothing existing affected. This round it was rebuilt and, this time, properly saved and checked end to end: when you opt in, the search reads your earlier results (without ever changing them), works out which coin-and-timeframe combination performed best, tries that one first, and writes a short note into the Activity Log explaining the choice. Keeping a run isolated stays the default. The last piece ahead is a leaderboard that ranks the survivors and refuses to crown a winner that only looks good by luck.

## What it can do today

The product lets users describe a strategy in plain English and backtest it on real crypto history, browse and reopen past runs, validate across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run from a warm cache. On top of that, a hands-free automated search picks its own coins and timeframes from just a goal and a budget, screens candidates cheaply before spending full effort on the most promising survivor, can be told to learn from past runs (or kept isolated), stays under a hard spending limit, is watchable live with AI-usage and dollar cost, is stoppable from the screen, survives page reloads, and marks only its most robust, fully validated result.

_Last updated: 2026-05-24 after iteration 6._
