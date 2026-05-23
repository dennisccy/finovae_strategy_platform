# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session began by taking stock of what already worked, and the foundation was strong: you could already turn a plain-English idea into a real backtest, browse and reopen past runs, stress-test a strategy across rolling out-of-sample windows, get ranked AI suggestions, choose among coins and timeframes, and re-run quickly from a warm cache. The big ambition ahead was a hands-free, automated strategy search.

That automated layer arrived in stages. First it gained a brain — a single command could seed a strategy and try AI-suggested improvements round by round, reusing the same backtest engine and safety sandbox a manual run uses, stopping cleanly when it met its targets or hit its budget, and crowning only a winner that survived an out-of-sample test. Then it became something you could see and steer: the search moved entirely onto the server, so you can reload the page or close your laptop and it keeps going; a live status strip shows it working and fresh attempts stream in without a refresh, and a real Stop button cancels it on the server while keeping the best result so far.

This iteration opened up the search itself. Until now it could only refine one fixed setup you handed it; now you can give it just a goal and a budget and let it pick which coins and timeframes to try on its own, exploring a few combinations from a small, deliberately bounded shortlist and keeping the single most robust one. Every automated run is now held to a hard spending limit — a ceiling on AI usage, dollar cost, number of setups, and time — checked before every step, so it never takes "one more." The status strip now shows the AI-token count and the dollar cost climbing live against their caps, plus how many setups have been explored, so you can watch what the search spends as it spends it.

The next chapter makes the search thriftier: screening ideas cheaply first and spending the full, deeper effort only on the most promising survivors, then learning from past runs and showing a leaderboard that refuses to crown an overfit winner.

## What it can do today

The product lets users describe a trading strategy in plain English and backtest it on real crypto history, browse and reopen past runs with their trades and results, validate across rolling out-of-sample windows, get ranked AI suggestions, pick coins and timeframes, and re-run from a warm cache — and run a hands-free automated search that now chooses its own coins and timeframes from just a goal and a budget, stays under a hard spending limit, is watchable live (including AI usage and dollar cost), is stoppable from the screen, and survives page reloads while marking its most robust result.

_Last updated: 2026-05-23 after iteration 3._
