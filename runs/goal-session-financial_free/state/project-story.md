# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session began on a strong foundation: you could already turn a plain-English idea into a real backtest, browse and reopen past runs, stress-test a strategy across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run quickly from a warm cache. The big ambition ahead was a hands-free, automated strategy search.

That automated layer arrived in stages. First it gained a brain — one command could seed a strategy and try AI-suggested improvements round by round, reusing the same engine and safety sandbox a manual run uses, stopping when it met its targets or hit its budget, and crowning only a winner that survived an out-of-sample test. Then it became something you could see and steer: the search moved entirely onto the server, so you can reload the page or close your laptop and it keeps going; a live status strip shows it working, fresh attempts stream in without a refresh, and a real Stop button cancels it while keeping the best result so far. Next it opened up the search itself — instead of refining one fixed setup you hand it, you can give it just a goal and a budget and let it pick its own coins and timeframes from a small, deliberately bounded shortlist, all held to a hard spending limit (AI usage, dollars, number of setups, and time) it checks before every step, with the token count and dollar cost climbing live against their caps.

This iteration made that search thrifty. Rather than paying full price to deeply evaluate every candidate, it now screens several setups cheaply first — on the cheapest AI model, skipping the heavy out-of-sample validation — then promotes only the single most promising survivor to the full, expensive treatment: rigorous out-of-sample validation on a more powerful model. You can watch the decision happen as it works — a cheap screening sweep followed by the promotion of the winner — and the "best" badge now only ever lands on a fully validated promoted result, never on a cheap candidate that merely flashed a high return.

The next chapter teaches the search to learn from your past runs so it can start smarter (with the option to keep a run isolated), then adds a leaderboard that ranks the survivors and refuses to crown an overfit winner.

## What it can do today

The product lets users describe a strategy in plain English and backtest it on real crypto history, browse and reopen past runs with their trades and results, validate across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run from a warm cache — plus run a hands-free automated search that chooses its own coins and timeframes from just a goal and a budget, screens candidates cheaply before spending full effort only on the most promising survivor, stays under a hard spending limit, is watchable live (including AI usage and dollar cost), is stoppable from the screen, survives page reloads, and marks only its most robust, fully validated result.

_Last updated: 2026-05-23 after iteration 4._
