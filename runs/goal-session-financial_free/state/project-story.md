# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session began on a strong foundation: you could already turn a plain-English idea into a real backtest, browse and reopen past runs, stress-test a strategy across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run quickly from a warm cache. The big ambition ahead was a hands-free, automated strategy search — and it arrived in stages. First it gained a brain: one command could seed a strategy and try AI-suggested improvements round by round, stopping when it met its targets or hit its budget, and crowning only a winner that survived out-of-sample testing. Then it became something you could see and steer — the search moved entirely onto the server, so you can reload the page or close your laptop and it keeps going, a live status strip shows it working, fresh attempts stream in without a refresh, and a real Stop button cancels it while keeping the best result so far.

Next it opened up the search itself: instead of refining one fixed setup, you can give it just a goal and a budget and let it pick its own coins and timeframes from a small, deliberately bounded shortlist, all held to a hard spending limit (AI usage, dollars, number of setups, and time) that climbs live against its caps. Most recently the search became thrifty — it screens several setups cheaply on the cheapest AI model first, then promotes only the single most promising survivor to the full, expensive treatment (rigorous out-of-sample validation on a stronger model), and the "best" badge now only ever lands on a fully validated promoted result, never on a cheap candidate that merely flashed a high return.

This round aimed at the next chapter — teaching the search to learn from your past runs so it can start smarter, with the option to keep a run isolated. The feature was built and passed its tests, but a technical mishap meant the new work was never saved and had to be set aside; nothing existing was affected, so the product works exactly as it did before. That feature will be rebuilt next, followed by a leaderboard that ranks the survivors and refuses to crown an overfit winner.

## What it can do today

The product lets users describe a strategy in plain English and backtest it on real crypto history, browse and reopen past runs with their trades and results, validate across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run from a warm cache — plus run a hands-free automated search that chooses its own coins and timeframes from just a goal and a budget, screens candidates cheaply before spending full effort only on the most promising survivor, stays under a hard spending limit, is watchable live (including AI usage and dollar cost), is stoppable from the screen, survives page reloads, and marks only its most robust, fully validated result.

_Last updated: 2026-05-24 after iteration 5._
