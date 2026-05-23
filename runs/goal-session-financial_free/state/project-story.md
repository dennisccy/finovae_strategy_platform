# Project story so far

Finovae Strategy Platform is an AI-assisted crypto strategy lab: you describe a trading idea in plain English and get a rigorous, backtested verdict on real market history.

## How it has grown

The session began by taking careful stock of what the platform could already do. Running every must-have ability against the live product confirmed an encouraging start: six core abilities already worked — turning a plain-English strategy into a real backtest, browsing and reopening past runs, stress-testing a strategy across rolling out-of-sample windows, getting ranked AI suggestions, choosing from the available coins and timeframes, and re-running quickly from a warm cache. The big ambition still ahead was a hands-free, automated strategy search.

The first stone of that automated layer landed next — and it worked. A single command could start a search that seeds a starting strategy and then tries AI-suggested improvements one round at a time, reusing the very same backtest engine and safety sandbox a manual run uses. It stopped cleanly the moment it met the success targets or hit its budget, never sneaking in "one more round," and it picked its winner with a skeptical eye: the strategy it marked "best" had to survive an out-of-sample test, so a flashier result that didn't hold up couldn't take the crown. Each run carried a durable status — its state, why it stopped, which round won — that survived a server restart and showed up in the normal session list. But at that point the search lived entirely behind the scenes.

This iteration made that automated search something you can actually see and steer. Auto Run now runs entirely on the server instead of inside the browser tab, so you can reload the page or close your laptop and it keeps going; reopening shows it still progressing and then finishing. A new status strip pinned to the top of the results panel shows the run working live — whether it's running, how many improvement rounds it has done against the budget, how much time has elapsed, why it stopped, and which attempt is the current best — and fresh strategy attempts appear on their own with no manual refresh. The Stop button is now real: it cancels the run on the server, freezes the attempt count, and keeps the best result so far. The old in-browser loop and its separate scoring shortcut were removed, leaving a single, trustworthy definition of "best."

The next chapter opens up the search itself — letting it pick coins and timeframes on its own from just an objective and a budget, holding it to a hard spending cap, screening ideas cheaply before committing to deeper tests, learning from past runs, and showing a leaderboard that refuses to crown an overfit winner.

## What it can do today

The product lets users describe a trading strategy in plain English and run it against real crypto price history, browse and reopen past runs with their full results and trades, validate a strategy across rolling out-of-sample windows, get ranked AI suggestions, pick from the available coins and timeframes, re-run quickly from a warm cache, and run a hands-free, budget-capped automated strategy search — now startable, watchable live, and stoppable right from the screen, surviving page reloads and marking its most robust result.

_Last updated: 2026-05-23 after iteration 2._
