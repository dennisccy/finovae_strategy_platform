# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

This session opened by taking careful stock of what the platform can already do, before adding anything new. Rather than guess, we ran every must-have capability against the live product and wrote down exactly what works today and what still needs building.

The result is an encouraging starting point. Six core abilities are already in place and working: you can turn a plain-English strategy into a real backtest, browse and reopen your past runs, stress-test a strategy across rolling time windows to see if it holds up on data it wasn't tuned on, get ranked AI suggestions for improvements, choose from the available coins and timeframes, and re-run a backtest quickly without re-downloading data.

The big ambition still ahead is a hands-free, automated strategy search — kicking off a budget-capped session from a single command that explores many strategies on its own, learns from past runs to spend effort where it pays off, watches its own spending, and surfaces the most robust result right inside the same app. That whole automated layer doesn't exist yet, so it's the clear next focus. The plan is to build the foundation first — starting an automated session, watching it run live, stopping it, and making the app's server the single source of truth that survives a reload — and then layer the smarter open-ended search on top.

## What it can do today

The product lets users describe a trading strategy in plain English and run it against real crypto price history, browse and reopen past runs with their full results and trades, validate a strategy across rolling out-of-sample windows, get ranked AI suggestions for improvements, pick from the available coins and timeframes, and re-run the same backtest quickly from a warm local cache.

_Last updated: 2026-05-23 after iteration 0._
