# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session began on a strong foundation — you could already turn a plain-English idea into a real backtest, browse and reopen past runs, stress-test a strategy across rolling windows of unseen data, get ranked AI suggestions, pick coins and timeframes, and re-run quickly from a warm cache. The big ambition was a hands-free automated strategy search, and it arrived in stages: first a brain that seeds a strategy and tries AI-suggested improvements round by round, stopping at its target or budget and crowning only a winner that survives out-of-sample testing; then the whole search moved onto the server, so you can reload the page or close your laptop and it keeps going, with a live status strip, fresh attempts streaming in, and a real Stop button that keeps the best result so far.

Next it opened up: give it just a goal and a budget and it picks its own coins and timeframes from a small, deliberately bounded shortlist, held to a hard spending limit that climbs live against its caps. It also turned thrifty — screening several setups cheaply first and promoting only the most promising survivor to the full, expensive treatment, so the "best" badge only ever lands on a fully validated result. Then it learned to learn from your past runs: built once but lost before saving (a technical mishap that affected nothing existing), then rebuilt and properly saved — when you opt in, it reads your earlier results without changing them, tries the historically strongest coin-and-timeframe first, and notes why in the Activity Log; staying isolated stays the default.

The most recent work made the search's skeptical judgment visible: after an automated run the product assembles a ranked leaderboard of every candidate it tried, highlights the one it crowned best, and gives a plain reason each other was passed over — so you can see a flashier, higher-return idea rejected because it didn't hold up on data it wasn't tuned on. In this final chapter that leaderboard was confirmed to paint correctly on screen in a real browser — the last sign-off the lab needed. Checking it on screen also surfaced and fixed a crash that could blank the whole app when older automated runs sat in storage; those now open normally. With that, all sixteen must-have journeys pass and the lab is delivered.

## What it can do today

The product lets users describe a strategy in plain English and backtest it on real crypto history, browse and reopen past runs, validate across rolling windows of unseen data, get ranked AI suggestions, pick coins and timeframes, and re-run from a warm cache. A hands-free automated search picks its own coins and timeframes from just a goal and a budget, screens candidates cheaply before spending full effort on the most promising survivor, can be told to learn from past runs (or kept isolated), stays under a hard spending limit, is watchable live with AI-usage and dollar cost, is stoppable from the screen, survives page reloads, marks only its most robust validated result, and presents a ranked leaderboard that shows at a glance why the winner beat the flashier also-rans.

_Last updated: 2026-05-24 after iteration 8._
