---
title: "Spec by Screenshot: Building a Dividend Dashboard on Robinhood's MCP Server"
date: 2026-10-01
draft: false
tags: ["robinhood", "mcp", "claude", "artifacts", "dividends", "personal-finance", "dataviz"]
description: "How I built a live income dashboard for my Robinhood account with Claude, and the product decisions along the way: copying the real app, being honest about what the data can't show, and a rule that protects Robinhood from me."
summary: "Robinhood's app is built for watching prices move. I wanted a page that answers a different question: what does this account pay me, and when? Most of the spec for that page turned out to be screenshots of Robinhood's own app."
featuredImage: "/images/hero-income-book.jpeg"
featuredImagePreview: "/images/hero-income-book.jpeg"
---

I kept asking Claude the same questions about one Robinhood account. When does each dividend pay? What is each one paying? How much have I made this year? The answers were right, and a week later I'd ask again. None of the questions were about prices. The account is full of mortgage REITs, business development companies, a pipeline MLP and a covered-call ETF, and it exists to throw off income, not to be watched by the minute. Robinhood's app is built for watching, and most of what's been written about its MCP server is about letting AI trade for you. This post is about the other half: using it to see your account the way you actually think about it.

So I built a page for those questions. I call it the Dividend Dashboard. I didn't write any of the code; Claude did. My job turned out to be something I'd do at work without thinking: product management, mostly by holding up a screenshot of Robinhood's app and saying "I like this, but it doesn't show me what I'm getting paid."

## Why I Built This

This account is money I had to spare, not my retirement. A financial advisor handles that, and for now it isn't changing. I've been a Robinhood customer since 2017, long before AI assistants like Claude, because there are no commissions, so trying something out doesn't come with a fee.

When Robinhood launched [Agentic Trading](https://robinhood.com/us/en/support/articles/agentic-trading-overview/), it published an official MCP server, a secure connection that lets an assistant like Claude read your account without ever seeing your password, and a dedicated Agentic account that AI agents connect to. An agent can read my account data, and any trade it places can only land in that account. That's a low-stakes way to use AI with my own money. I do wonder: if this works out, could AI help with my retirement too? I'd rather find out first with money that matters less if the AI gets something wrong.

Few brokerages offer an MCP server; Fidelity, Schwab and E\*TRADE [don't as of this writing](https://www.stockbrokers.com/guides/ai-agent-brokers). Robinhood has since added a dividend tracker of its own, which I'll get to.

## What I Built

The whole thing is one web page that lives in my Claude account. Click Refresh and the page [calls Robinhood's MCP server itself](https://x.com/ClaudeDevs/status/2077489907350856038), using my own connection. It's only allowed five read-only tools, so the worst it can do is look at my money, which is also my main hobby. (I use the same connection with Claude to research and make trades, but that's a different post.)

I expected to lose a weekend to hosting, a database and somewhere safe to keep a password. I lost none. Claude built the page, published it and gave it a small database, all inside Claude.

What's on it: account value, today's change, estimated income, a Positions table with a tiny chart in every row, and a dividend tracker. Click a row and that stock's chart drops open. Hover over any chart and it reads out the date and value, just like Robinhood's.

{{< admonition type="info" title="Sample data, not my account" open=true >}}
Except for the two Robinhood app screenshots in the dividend tracker section, every screenshot in this post runs on the same made-up sample portfolio, not my account. The tickers are real; the share counts, prices and dollar amounts are not.
{{< /admonition >}}

<p align="center"><img src="/images/income-view-concept-positions.png" alt="The Positions table with AGNC expanded to a three-month chart, cursor reading a single day's value. Sample portfolio, not real numbers." style="max-width:100%;"></p>

Claude wrote every line of code, made every call to Robinhood and published all sixteen versions over about two weeks. Every version is still recoverable, which is why the screenshots below are labeled by version. Claude also kept a decision journal as we went: what we changed, what we tried and dropped, and why. I now ask for one at the start of every project, because I never know which ones will turn into a blog post, and the conversation that built it may be three chats back by the time I write. Most of this post comes from that journal.

My part was deciding what I wanted to see and how I wanted to see it. I held the Robinhood app up next to each version, kept what I liked, and worked out what should be different. When the data had a gap, I proposed a way around it. I didn't want to build anything myself; I just knew what I wanted, which any product manager will tell you is the hard part. (Engineers may disagree.)

## The Product Decisions

The interesting part of this project wasn't the engineering. It was a string of product calls (what to show, what to be honest about, what to copy) and a few roadblocks that needed a way around. The MCP server handled the basics well: positions, cash, live quotes, each holding's dividend schedule and price history, enough to draw every chart on the page. What it didn't have was the two things an income investor wants most, what I've actually been paid and what the account was worth over time. The first I solved by hand: I downloaded my account activity as a CSV from Robinhood's Reports page and gave it to Claude, which stored it in the page alongside the live data. The second I had to reconstruct, and the reconstruction is honest about what it is.

### Designing by screenshot

Most of the spec for this page was a screenshot of Robinhood's app and the word "that." The page started with the details (1): a table of every holding and what it pays. The longer I looked at it, the more I wanted the big picture first, with the numbers rolled up at the top and the details a click away. That's the same drill-down Robinhood's app already uses.

<p align="center"><img src="/images/dividend-dashboard-design-steps.png" alt="Three versions of the page. Version 4: a serif headline, stat cards and a bar chart of holdings. Version 7: an account-value chart across the top. Version 13: Robinhood's colors and type, with a green Refresh button. Sample data." style="max-width:100%;"></p>

*From the details, to the big picture, to Robinhood's look. All sample data.*

Inside the table, I swapped the three "sort by" buttons for clickable column headers, since two ways to sort one table is one too many. Claude argued that a stock's chart should drop open under its row instead of living in its own section, and it was right: the chart sits next to the numbers you were just reading.

Then came the roll-up (2): an account chart across the top and a tiny "Today" chart in every row, both copied from screenshots of the app. The big chart came with a catch. The MCP server has no account-value history, so the only way to draw it is to take each holding's price history, multiply by what I own *today*, and add it up. That line looks exactly like Robinhood's chart and means something different: it's what today's portfolio would have been worth, not what my account was. Claude flagged it before I did, so it ships with a footnote saying so. I'd rather have an honest approximation than a convincing one.

Once the page did what I wanted, I wanted it to look finished (3), not like a backend with a chart bolted on. The data came from Robinhood, and Robinhood already has a design system, so why not borrow it? I opened Chrome's inspector on robinhood.com and found the real thing: Robinhood's colors and type sizes, sitting right there as named variables. The page uses them now.

My favorite detail: Robinhood's accent color turns orange on a down day and green on an up day. Mine does too, with one exception. The Refresh button stays green no matter what the market does. Optimism is a design choice. The one thing I couldn't copy is the font. Robinhood's is licensed, so mine falls back to Inter.

### The wrong swings

<p align="center"><img src="/images/tree-swing-cartoon.png" alt="The tree swing cartoon: ten panels showing how the customer explained it, how each role understood or built it, and the tire on a rope the customer really needed." style="max-width:100%;"></p>

*Every product manager knows this one. ([Source](https://www.productftw.com/productftw-2-the-tire-swing-cartoon/))*

I was the customer this time, and I still got a few wrong swings, which is why there are sixteen versions.

The one-day chart is the best example. I asked for "the last 24 hours," and that's exactly what Claude built, with the points spread evenly across the width. It's also not what a one-day stock chart means. Next to Robinhood's 1D view the difference was obvious: Robinhood pins the chart to the trading day, 6:30am to 1pm Pacific, and the line stops at now, leaving the rest of the day blank. The rebuild did the same and measured the day's change from yesterday's close, the way Robinhood does. No test would have caught it, because the code did exactly what I asked.

The same side-by-side caught a smaller one later: pick a range like 3M and the header should say "Past 3 months," not "Today." (It's measured on the reconstructed line, so it won't match the app's figure exactly.)

<p align="center"><img src="/images/dividend-dashboard-1d-iterations.png" alt="Three versions of the account chart side by side. Version 7: the last 24 hours stretched across the full width. Version 9: the chart pinned to the trading day, with the line stopping at now and a dotted line at yesterday's close. Version 15: 3M selected, with the header reading the change over the past 3 months. Sample data." style="max-width:100%;"></p>

*One chart, three swings, left to right: what I asked for, what I pictured, and what I noticed once I had it.*

### A rule to protect Robinhood from me

The early versions had a problem I didn't catch right away: Claude had baked the numbers from its first pull into the page itself. For a week the page kept showing those holdings, and they looked just as current as a fresh pull. So I asked Claude to store the data properly and check how old it was.

That's caching: keep a copy of an answer so you don't have to ask for it every time. It makes the page faster and means fewer calls to Robinhood. The trade-off is that the copy can go stale, so you have to decide how old is too old. (Claude's connection to Robinhood keeps a few minutes of its own cache, but the page is mine, so I wanted it handled on my side.) I picked an hour. Under an hour, Refresh says the data is fresh and makes no calls; after that, it pulls again. If a pull fails, the page keeps the last saved data instead of going blank, and an empty page says "click Refresh" instead of passing off week-old numbers as today's. Less pretty, more honest, and a dashboard has no business hitting someone else's servers every time I get curious.

## Then Robinhood Shipped a Dividend Tracker

A week into this, Robinhood shipped the feature I'd been building toward: a dividend tracker. Customers asked for it. At HOOD Summit '25, Vlad Tenev polled the audience on what to build next, and [dividend tracking was one of the top two picks](https://www.tipranks.com/news/the-fly/robinhood-ceo-tenev-polls-hood-summit-25-audience-for-next-platform-feature-thefly). Robinhood [promised it for this year](https://x.com/RobinhoodApp/status/1966587161240559713) ("Customers ask, we execute") and [delivered](https://x.com/RobinhoodApp/status/2086845029616886188).

It's basically the income half of my page. Type "Dividend tracker" into the app's search ([help article](https://robinhood.com/us/en/support/articles/dividends/)) and you get what you've been paid this year, a projection for the rest of it, and your yielding positions. Tap one for its yield, dividend per share and projected annual amount.

<div style="display:flex; gap:16px; justify-content:center; align-items:flex-start; flex-wrap:wrap;">
<img src="/images/robinhood-app-dividends-card.png" alt="Robinhood's per-stock Dividends card: yield, dividend per share, received year to date, annual projected, next ex-dividend and pay dates, and a View all dividends link. Dollar amounts covered." style="width:52%; min-width:260px; max-width:100%;">
<img src="/images/robinhood-app-dividend-tracker.png" alt="Robinhood's Dividend tracker screen: a 2026 and MAX toggle, a monthly bar chart of actual and projected dividends, and a list of yielding positions with yield. Dollar amounts and share counts covered." style="width:36%; min-width:200px; max-width:100%;">
</div>

*Robinhood's app: one stock's Dividends card on the left, the Dividend tracker on the right. These are screenshots from my own account, with the dollar amounts and share counts covered.*

So of course I asked Claude to rebuild it, with the same playbook as before. The forward-looking half is all in the MCP server: each holding's dividend per share, how often it pays, and when. Shares times dividend, for every payment left this year, landed within about one percent of Robinhood's projection, and NLY matched to the cent.

<p align="center"><img src="/images/income-book-dividend-tracker.png" alt="The Dividend Dashboard's version of the dividend tracker: year-to-date received, an annual projection, green actual and gray projected monthly bars, and a list of yielding positions with one expanded to show yield, dividend per share, received, annual projected and next dates. Sample data." style="max-width:100%;"></p>

*My copy of the tracker, on the sample portfolio. Green is paid, gray is projected, same as Robinhood's.*

Comparing the two turned up a surprise. Robinhood's tracker counts one account, and I'd only moved my positions into the Agentic account in July and August, so it showed a fraction of what I'd been paid this year. My export came from my individual account, where most of those dividends landed before the move. That's also why the export had looked incomplete: the rest were in the other account. Put together with the Agentic account's statements, my page shows the whole year across both accounts. Robinhood's tracker can't, because it only sees one account at a time.

The app has one edge that matters: it reads Robinhood's own records, while mine is only as good as what I feed it. But mine has the shape I wanted: every holding on one sortable page, next to price, cost and yield on cost.

That last one taught me something about my own holdings. The yield Robinhood lists is the last year of payouts against today's price. What I actually earn depends on what I paid, so the page shows both.

{{< admonition type="tip" title="Why my numbers and the app's don't match (and both are right)" open=true >}}
| | Robinhood's tracker | My page |
|---|---|---|
| **Accounts** | One at a time | Both, combined |
| **Pay dates** | Can pay up to ~17 days early ([Early Dividends](https://finance.yahoo.com/news/robinhood-breaking-wall-street-paying-222238237.html)) | Official pay dates |
| **"Annual income"** | Paid this year + still scheduled | Market value × yield (a run rate) |
{{< /admonition >}}

## What I'd Ask Robinhood For

The MCP server gets more right than wrong: positions, quotes, dividend schedules and price history are enough to build a real dashboard. Four additions would close the gaps, and Robinhood's own app already shows every one of them.

1. **Account value over time.** The app draws this chart. Without it, every outside dashboard has to rebuild one and add a disclaimer.
2. **Dividend and activity history.** Right now an agent can see what's coming but not what's been paid. The data seems to exist: community-built tools using Robinhood's unofficial API list a dividend-history call. But they ask for your Robinhood password, which is exactly what the official server was built to avoid.
3. **Market hours,** including holidays and early closes, so a one-day chart knows when the trading day ends.
4. **Yesterday's official close,** so a day's change matches the app's.

### Try the concept

I'd rather show than tell, so Claude built a shareable copy of the page on a made-up sample portfolio, with the wishlist written into it. It's a customer's suggestion, not affiliated with Robinhood. Click around:

<p align="center"><a href="https://claude.ai/artifact/PBQkes53zewq1pNiPGYxZY"><img src="/images/dividend-dashboard-concept-preview.png" alt="The concept page: an income-first account view with an account-value chart, on a made-up sample portfolio. Click to open it." style="max-width:100%; border:1px solid #e3e9ed; border-radius:12px;"></a></p>

<p align="center"><strong><a href="https://claude.ai/artifact/PBQkes53zewq1pNiPGYxZY">Open the live concept &rarr;</a></strong><br><em>Hover the charts, sort the columns, open a row. Sample data only.</em></p>

## Lessons Learned & What's Next

**The data lesson: know your source of truth.** Three times the page looked right and wasn't. I never asked which account the export covered, the first numbers went stale without looking stale, and the account chart looked like Robinhood's while meaning something else. The fix was always the same: decide what's real, treat everything else as an approximation, and say so on the page. Stale data that looks live is worse than an empty box.

**The AI lesson: it builds what you ask, not what you meant.** Claude was fast and careful. It checked real data, flagged the reconstructed chart before I did, and told me what it had and hadn't tested. But it built the one-day chart exactly as I described it, and my description was wrong. Getting to a working version took minutes. Deciding whether it meant what I thought was still my job.

**The product lesson: the loop beats the dashboard.** The best changes came from a simple loop: notice a question, change the view, look again. Most of them started with putting my page next to the real app and asking why the two disagreed. You can't loop with someone else's app, because you can't change it.

**Beyond Robinhood: everything else I own.** Robinhood is one of many places my money lives. There's property, a company 401(k) and other retirement accounts with my financial advisor, a stock plan from a former employer, short-term notes and savings. Getting the full picture used to mean logging into each one and doing the math in my head. My head is not a great spreadsheet. Now Robinhood connects live, and for everything else I hand Claude a screenshot or a statement and it turns them into rows I can ask questions about. It's clumsy: a screenshot is stale the next day, and I'm the integration layer.

Most finance tools seem built for one of two people: someone who wants one reassuring number, or a full-time investor who wants a terminal. I'm neither. I want one view across everything I own that I can reshape when a new question comes up. Live data where there's a server, uploads where there isn't, and a view that changes on request: it's rough, but it's the first time I've seen my money the way I actually think about it.

**What's next: looking vs. acting.** At [HOOD Summit '26](https://robinhood.com/us/en/newsroom/hood-summit-2026/), Robinhood announced built-in agents that research and trade for you, plus "Loops" that turn a strategy into a standing instruction; [Fortune](https://fortune.com/2026/09/29/robinhood-trading-agents-hood-openai-anthropic/) reports more than 150,000 agentic accounts opened since May. Loops is a loop for acting; mine is a loop for looking.

I'm not a day trader, and the agents aren't in my Android app yet, so I'll likely stay with Claude, which can see more than my Robinhood account. Nothing in the coverage mentions dividend or account-value history for outside tools, so the wishlist still stands. Next on my list: a daily history log, so I can chart real income over time instead of reconstructing it.

## Try This Yourself

If you use Robinhood, the thing I'd most like you to take from this is to try the MCP server: connect it to an assistant and ask it a question the app doesn't answer. Setup takes a few minutes on a computer.

1. **Add the connector.** In the Claude desktop app, go to Settings → Connectors → Add custom connector and paste `https://agent.robinhood.com/mcp/trading`. ChatGPT, Cursor and Claude Code work too; Robinhood's [setup article](https://robinhood.com/us/en/support/articles/agentic-trading-overview/) has the steps for each.
2. **Sign in through Robinhood.** Connecting sends you to Robinhood to log in, so the assistant never sees your password. You need an individual investing account in good standing.
3. **Finish the Agentic account setup.** Know what you're granting: the assistant can read all your Robinhood accounts but can only trade in the Agentic one.

Then ask it something. Three questions to start with:

- "When does each of my holdings pay its next dividend, and roughly how much will I get?"
- "What's my yield on cost for each position, and how does it compare with the yield Robinhood shows?"
- "Rank my holdings by estimated annual income and show it as a chart."

If you want to go further:

- **See it working:** the [sample-data version](https://claude.ai/artifact/PBQkes53zewq1pNiPGYxZY) is fully clickable.
- **Build your own:** start with [Claude's announcement](https://x.com/ClaudeDevs/status/2077489907350856038) that its pages can pull live data from connected services, then hold up a screenshot of the app you're trying to improve on. There's no repo; this was one artifact and a long conversation.
- **Found a clean way** to get dividend history or account-value history out of Robinhood's MCP server? I'd like to hear about it.

## TL;DR

{{< admonition type="abstract" title="The whole post in three lines" open=true >}}
- **The question:** what is this account paying me, and when? One page now answers it at a glance, and changes when my question does.
- **Lines of code I wrote:** zero. **Versions I asked for:** sixteen. **Times I said "that's not what I meant":** more than sixteen.
- **The most sophisticated engineering in the whole project:** a rule that stops me from checking my portfolio more than once an hour.
{{< /admonition >}}
