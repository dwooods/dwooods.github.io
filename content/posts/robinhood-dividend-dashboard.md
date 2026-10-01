---
title: "Spec by Screenshot: Building a Dividend Dashboard on Robinhood's MCP Server"
date: 2026-09-30
draft: true
tags: ["robinhood", "mcp", "claude", "artifacts", "dividends", "personal-finance", "dataviz"]
description: "How I built a live income dashboard for my Robinhood account with Claude, and the product decisions along the way: copying the real app, being honest about what the data can't show, and a rule that protects Robinhood from me."
summary: "Robinhood's app is built for watching prices move. I wanted a page that answers a different question: what does this account pay me, and when? Most of the spec for that page turned out to be screenshots of Robinhood's own app."
featuredImage: "/images/hero-income-book.jpeg"
featuredImagePreview: "/images/hero-income-book.jpeg"
---

I kept asking Claude the same questions about one Robinhood account. When does each dividend pay? What is each one paying? How much have I made this year? The answers were right, and a week later I'd ask again.

I open Robinhood's app often. But a company's app can only show me how the company thinks I look at my finances, and that's a generalist's view. I always have questions, and I like to look at the same data from different angles. I'm a product manager, so I'm curious by trade.

None of my questions were about prices. The account that raises them is full of mortgage REITs, business development companies, a pipeline MLP and a covered-call ETF, and it exists to throw off income, not to be watched by the minute.

So I built a page for those questions. I call it the Dividend Dashboard. I didn't write any of the code; Claude did. My job turned out to be something I'd do at work without thinking: product management, mostly by holding up a screenshot of Robinhood's app and saying "I like this, but it doesn't show me what I'm getting paid."

Most of what's been written about Robinhood's MCP server is about letting AI trade for you. This post is about the other half: using it to see your account the way you actually think about it.

## Why I Built This

Some context first. This account is money I had to spare, not my retirement. A financial advisor handles my retirement investments, and for now that isn't changing. I've been a Robinhood customer since 2017, years before AI assistants like Claude came along, and I keep this money there because I can trade without stopping to think about what each trade will cost me. There are no commissions, so trying something out doesn't come with a fee. Robinhood also keeps investing in a product people like using.

When I started, I wasn't sure what Robinhood's MCP server and its Agentic account would do for me. When Robinhood launched [Agentic Trading](https://robinhood.com/us/en/support/articles/agentic-trading-overview/), it published an official MCP server — the same open protocol Claude uses to talk to outside tools — and a dedicated brokerage account that AI agents connect to. Per Robinhood's overview, an agent gets read access to account data, and any trade it places can only land in that Agentic account. That gave me a low-stakes way to use AI with my own money, and it has made me a little more comfortable investing. I do wonder: if this works out, could AI help with my retirement too? I'd rather find out first with money that matters less if I lose it or the AI gets something wrong.

Asking Claude in chat gave me good answers that I'd forgotten a week later. I wanted a view I could open and get the same answers from every time, because a picture beats a paragraph, and I wanted to see whether I could build what Robinhood's app didn't show me. That's the case for an MCP server: no company can build one dashboard that works for every customer, but it can let each customer build their own. Few brokerages offer one; Fidelity, Schwab and E\*TRADE [don't as of this writing](https://www.stockbrokers.com/guides/ai-agent-brokers). Robinhood has since added a dividend tracker of its own, which I'll get to.

## What I Built

The whole thing is one web page that lives in my Claude account. Click Refresh and the page [calls Robinhood's MCP server itself](https://x.com/ClaudeDevs/status/2077489907350856038), using my own connection. It's only allowed five read-only tools, so the worst it can do is look at my money, which is also my main hobby. (I use the same connection with Claude to research and make trades, but that's a different post.)

I expected to lose a weekend to hosting, a database and somewhere safe to keep a password. I lost none. Claude built the page, published it and gave it a small database, all inside Claude.

What's on it: an account-value chart, today's change, unrealized gain, estimated annual income, holdings ranked by size, a Positions table with a tiny chart in every row, and a dividend tracker. Click a row and that stock's chart drops open. Hover over any chart and it reads out the date and value, just like Robinhood's.

{{< admonition type="info" title="Sample data, not my account" open=true >}}
Except for the two Robinhood app screenshots in the dividend tracker section, every screenshot in this post runs on the same made-up sample portfolio, not my account. The tickers are real; the share counts, prices and dollar amounts are not.
{{< /admonition >}}

<p align="center"><img src="/images/income-view-concept-positions.png" alt="The Positions table with AGNC expanded to a three-month chart, cursor reading a single day's value. Sample portfolio, not real numbers." style="max-width:100%;"></p>

### Tools & AI Assist

Claude wrote every line of code, made every call to Robinhood and published all sixteen versions over about two weeks. Every version is still recoverable, which is why the screenshots below are labeled by version, and at the end Claude wrote up a decision journal that most of this post comes from.

My part was deciding what I wanted to see and how I wanted to see it. I held the Robinhood app up next to each version, kept what I liked, and worked out what should be different. When the data had a gap, I proposed a way around it. I didn't want to build anything myself; I just knew what I wanted, which any product manager will tell you is the hard part. (Engineers may disagree.)

## The Product Decisions

The interesting part of this project wasn't the engineering. It was a string of product calls (what to show, what to be honest about, what to copy) and a few roadblocks that needed a way around. The best example: at the time, neither Robinhood's app nor its MCP server showed what I'd been paid month by month, and Claude's first version didn't either. But the history was sitting in an export of my account activity, so I told Claude to use it and build the view Robinhood didn't have.

### What the MCP server gives you, and what it doesn't

Robinhood's MCP server handles the basics well. Positions, cash, live quotes, each holding's dividend schedule and price history all came back reliably, which was enough to draw every chart on the page. The gaps showed up the moment I asked for the two things an income investor wants most: what I've actually been paid, and what my account was worth over time. The MCP server has neither, even though Robinhood's own app draws that account-value chart.

The export fix had its own twist: for a week the page carried a footnote warning that the export looked incomplete. More on that below.

### Designing by screenshot

The page started with the details (1): a table of every holding and what it pays. The longer I looked at it, the more I wanted the big picture first, with the numbers rolled up at the top and the details a click away. That's the same drill-down Robinhood's app already uses, so most of the redesign was me sending Claude a screenshot of the app and saying "that."

<p align="center"><img src="/images/dividend-dashboard-design-steps.png" alt="Three versions of the page. Version 4: a serif headline, stat cards and a bar chart of holdings. Version 7: an account-value chart across the top. Version 13: Robinhood's colors and type, with a green Refresh button. Sample data." style="max-width:100%;"></p>

*From the details, to the big picture, to Robinhood's look. All sample data.*

Inside the table, I swapped the three "sort by" buttons for clickable column headers, since two ways to sort one table is one too many. Claude argued that a stock's chart should drop open under its row instead of living in its own section, and it was right: the chart sits next to the numbers you were just reading.

Then came the roll-up (2): an account chart across the top and a tiny "Today" chart in every row, both copied from screenshots of the app. The big chart came with a catch. The MCP server has no account-value history, so the only way to draw it is to take each holding's price history, multiply by what I own *today*, and add it up. That line looks exactly like Robinhood's chart and means something different: it's what today's portfolio would have been worth, not what my account was. Claude flagged it before I did, so it ships with a footnote saying so. I'd rather have an honest approximation than a convincing one.

There's a cartoon every product manager knows, and it's older than most of us: it first ran in a [1973 University of London Computer Centre newsletter](https://www.businessballs.com/amusement-stress-relief/tree-swing-cartoon-pictures-early-versions/). It shows a tree swing drawn the way the customer explained it, the way the project lead understood it, the way the programmer built it, and so on, until the last panel shows what the customer actually needed, which is a tire on a rope. I was the customer this time, and I still got a few wrong swings. What I asked for kept turning out to be not quite what I'd pictured, which is why there are sixteen versions.

The one-day chart is the best example. I asked for "the last 24 hours," and that's exactly what Claude built, with the points spread evenly across the width. It's also not what a one-day stock chart means. Next to Robinhood's 1D view the difference was obvious: Robinhood pins the chart to the trading day, 6:30am to 1pm Pacific, and the line stops at now, leaving the rest of the day blank. The rebuild did the same and measured the day's change from yesterday's close, the way Robinhood does. No test would have caught it, because the code did exactly what I asked.

The same side-by-side caught a smaller one later: pick a range like 3M and the header should say "Past 3 months," not "Today." (It's measured on the reconstructed line, so it won't match the app's figure exactly.)

<p align="center"><img src="/images/dividend-dashboard-1d-iterations.png" alt="Three versions of the account chart. Version 7: the last 24 hours stretched across the full width. Version 9: the chart pinned to the trading day, with the line stopping at now and a dotted line at yesterday's close. Version 15: 3M selected, with the header reading the change over the past 3 months. Sample data." style="max-width:100%;"></p>

*One chart, three swings: what I asked for, what I pictured, and what I noticed once I had it.*

Once the page did what I wanted, I wanted it to look finished (3), not like a backend with a chart bolted on. The data came from Robinhood, and Robinhood already has a design system, so why not borrow it? I opened Chrome's inspector on robinhood.com and found the real thing: Robinhood's colors and type sizes, sitting right there as named variables. The page uses them now.

My favorite detail: Robinhood's accent color turns orange on a down day and green on an up day. Mine does too, with one exception. The Refresh button stays green no matter what the market does. Optimism is a design choice. The one thing I couldn't copy is the font. Robinhood's is licensed, so mine falls back to Inter.

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

So of course I asked Claude to rebuild it, with the same playbook as before: a screenshot and "that." The forward-looking half is all in the MCP server: each holding's dividend per share, how often it pays, and when. Shares times dividend, for every payment left this year, landed within about one percent of Robinhood's projection, and NLY matched to the cent.

<p align="center"><img src="/images/income-book-dividend-tracker.png" alt="The Dividend Dashboard's version of the dividend tracker: year-to-date received, an annual projection, green actual and gray projected monthly bars, and a list of yielding positions with one expanded to show yield, dividend per share, received, annual projected and next dates. Sample data." style="max-width:100%;"></p>

*My copy of the tracker, on the sample portfolio. Green is paid, gray is projected, same as Robinhood's.*

Comparing the two turned up a surprise. Robinhood's tracker counts one account, and I'd only moved my positions into the Agentic account in July and August, so it showed a fraction of what I'd been paid this year. My export came from my individual account, where most of those dividends landed before the move. That's also why the export had looked incomplete: the rest were in the other account. Put together with the Agentic account's statements, my page shows the whole year across both accounts. Robinhood's tracker can't, because it only sees one account at a time.

I'm not claiming mine is better. The app has an edge that matters: it reads Robinhood's own records, while mine is only as good as what I feed it. But mine has the shape I wanted: every holding on one sortable page, next to price, cost and yield on cost.

That last one taught me something about my own holdings. The yield Robinhood lists is the last year of payouts against today's price. What I actually earn depends on what I paid, so the page shows both.

### If you compare your numbers with the app's

Three things will make your numbers and the app's disagree, even when both are right.

**Everything is per account.** The tracker, the export and the MCP data are all scoped to one account. If you've moved positions between accounts — say, into an Agentic account — your dividend history is split across them, and it's very easy to pull the wrong one (ask me how I know).

**Payment dates can move.** Robinhood's [Early Dividends](https://finance.yahoo.com/news/robinhood-breaking-wall-street-paying-222238237.html) program can release eligible dividends about 17 days early, according to Robinhood, so a projection keyed to official pay dates, like mine, can put a payment in a different month than the tracker does.

**"Annual income" means different things.** Robinhood's annual projection is what you've received this year plus what's still scheduled; my stat tile's market value times yield is a run rate. The two won't match.

## What I'd Ask Robinhood For

For what I'm building, the MCP server gets more right than wrong. Positions, quotes, dividend schedules and price history are exactly what you need to build a real dashboard. The wishlist is short and specific. First, **account value over time**: Robinhood already draws this chart in its own app, and without it every outside dashboard has to reconstruct it with a disclaimer. Second, **dividend and activity history** as data. The app has a dividend tracker, but as far as I can tell it isn't on Robinhood's website, and the MCP server has no dividend history, so outside the app the only way to know what you've been paid is a CSV export, one account at a time, and an AI agent connected to your account can see the future but not the past. The history appears to exist: community-built tools that use Robinhood's unofficial API list a dividend-history call. Those tools ask for your Robinhood password, though, which is exactly what the official MCP server was designed to avoid. Third, **market hours**, including holidays and early closes, so a one-day chart knows when the trading day actually ends. And fourth, **yesterday's official closing price**, so a day's change matches the app's. None of these is exotic. Each is something Robinhood's own app already shows me.

I'd rather show them than just list it, so Claude built a second copy of the page for sharing, running on a made-up sample portfolio so none of my numbers are in it. It's labeled as a concept, says plainly it isn't affiliated with Robinhood, and ends with a short write-up of the idea and the wishlist above. These are a customer's suggestions, from someone who uses the product. It's [here if you want to click around](https://claude.ai/artifact/PBQkes53zewq1pNiPGYxZY).

## Beyond Robinhood: Everything Else I Own

Robinhood is one account. The rest of what I own lives in other places, and most of them have nothing like an MCP server. A stock plan from a former employer sits with a separate stock-plan provider, and none of it has a connector I can attach to Claude.

So I feed it in by hand. I take a screenshot of a positions page or download a statement, give it to Claude, and from there I can ask the same kind of questions I ask about the Robinhood account: what do I hold, what did each lot cost, which lots are cheapest to sell. It works better than I expected. Claude reads a screenshot of a stock-plan portal or a PDF statement and turns it into rows, and I can keep refining the answer in conversation.

It's also the wrong way to do this. A screenshot goes stale the day after I take it, I'm the integration layer, and every refresh is another manual step. For a Robinhood holding I can ask for a live price. For these, I'm working from whatever I last uploaded. I'd much rather have a connector, but I haven't found one for personal use, so uploads are the only way in. My advisor's tools cover my retirement accounts, including anything rolled over from a company 401(k), but not this Robinhood account or the stock plan. Nothing I've found covers all of it.

Which leads to the thing I can't find. Most finance tooling seems to be built for one of two people. One doesn't want to think about their finances and wants a simple, reassuring number. The other is a full-time investor who wants everything on a terminal. I'm neither. I have some investments, I check them regularly, and I have questions about them. Where is the tool for that person: one view across what I hold, that I can reshape when a new question comes up?

That's what an MCP server plus an AI assistant gives me today, in a rough form. There's live data where a server exists, uploads where it doesn't, and a view I can change on request. It's clumsy at the edges. It's also the first time I've been able to look at my own money the way I actually think about it.

## Lessons Learned & What's Next

The data lesson came three times in one project: my dividend panel was confidently wrong for a week because I never asked which account the export came from, the page's first numbers looked current after they stopped being current, and the account chart looked exactly like Robinhood's while meaning something different. Each time the fix was the same: decide what the real source of truth is, treat everything else as an approximation, and say so on the page. Stale or reconstructed data that looks live is worse than an empty box.

The AI lesson is the one this blog keeps relearning. Claude was fast and, honestly, careful. It checked real responses instead of trusting its own guesses about field names, it flagged the reconstructed chart before I asked, and it told me after every publish what it had and hadn't tested against live data. But it built the one-day chart exactly as I'd described it, and my description was wrong. A test can confirm the code does what was asked. It can't tell you that what was asked doesn't match what a one-day chart means to anyone who's ever looked at one. The only check that caught that was me holding the real app next to ours. AI got me from "I want this" to a working version in minutes; deciding whether the working version actually means what I think it means stayed my job.

The product lesson is the one I didn't expect to write. I thought I was building a dashboard, and the dashboard turned out to be the least interesting part. What mattered was the loop around it: I'd notice a question, ask for the view to change, look again, and decide something. Every version in this post is one turn of that loop, and several of the best turns, like the trading-hours chart, the dividend tracker and the per-account fix, came from putting the page next to the real app and asking why the two disagreed. An app's view is someone else's answer to the average customer's question, and you can't loop with it because you can't change it. A view you can change the same afternoon is a different kind of thing. That's what I'd want anyone to take from this over any detail of the MCP server: the value of connecting an assistant to your own data is that the view stops being fixed.

What's next: Robinhood's HOOD Summit '26, at the end of September, pushed in a different direction from mine. The [newsroom post](https://robinhood.com/us/en/newsroom/hood-summit-2026/) announces built-in Robinhood Agents that can analyze the market, build strategies and trade for you in a dedicated agentic account, plus "Loops" that turn a strategy into a standing instruction, plus a set of paid data-partner apps. [Fortune](https://fortune.com/2026/09/29/robinhood-trading-agents-hood-openai-anthropic/) reports the agents rolling out to Robinhood's customers right after the event, while the newsroom still says "coming soon," so check what's live for you. It also reports more than 150,000 customers have opened agentic accounts since the MCP server arrived in May. What I didn't find in any of the coverage is dividend history or account-value history for outside tools, so the wishlist above still looks open as of this writing.

It's an interesting contrast. Loops is a loop for acting, and what I built is a loop for looking, and I'd like both. The agents aren't in my Android app yet, so I can't compare them with my setup. I'd try them, but I doubt I'd switch. They look built to help you be a trader, and I'm not a big day trader. I'd rather stay with my Claude project, because it can pull in and line up investments that aren't in Robinhood, which an agent inside Robinhood's own app can't do.

On my side, the page only keeps the latest pull, so the obvious follow-up is a daily history log I own, so I can chart actual income over time instead of reconstructing it.

## Try This Yourself

If you use Robinhood, the thing I'd most like you to take from this is to try the MCP server: connect it to an assistant and ask it a question the app doesn't answer. Setup takes a few minutes on a computer.

1. **Add the connector.** In the Claude desktop app, go to Settings → Connectors → Add custom connector and paste `https://agent.robinhood.com/mcp/trading`. ChatGPT, Cursor and Claude Code work too; Robinhood's [setup article](https://robinhood.com/us/en/support/articles/agentic-trading-overview/) has the steps for each.
2. **Sign in through Robinhood.** Connecting sends you to Robinhood to log in, so the assistant never sees your password. You need an individual investing account in good standing.
3. **Finish the Agentic account setup** that opens after you connect, and know what you're granting: per Robinhood, the assistant can read all your Robinhood accounts, including account numbers, but can only place trades in the Agentic account.

Then ask it something. Three questions to start with:

- "When does each of my holdings pay its next dividend, and roughly how much will I get?"
- "What's my yield on cost for each position, and how does it compare with the yield Robinhood shows?"
- "Rank my holdings by estimated annual income and show it as a chart."

There's no repo for this one — it's a single artifact and a long conversation, not a code project. To see it working, the [sample-data version](https://claude.ai/artifact/PBQkes53zewq1pNiPGYxZY) is fully clickable — hover the charts, sort the columns, open a row. If you want to build something similar, start with the announcement that [Claude artifacts can call MCP connectors](https://x.com/ClaudeDevs/status/2077489907350856038), and Robinhood's [dividend tracker help article](https://robinhood.com/us/en/support/articles/dividends/) for what the app itself now offers. From there, the fastest spec I found was a screenshot of the app I was trying to improve on. If you've found a clean way to get dividend history or account-value history out of Robinhood's MCP server, I'd like to hear about it.

---

The point of all this was one page that answers the questions I kept asking about this account: what is it paying me, and when. It does that now, in one glance, and when the question changes, the page can too.

And the most sophisticated piece of engineering in the whole project is a rule that keeps my curiosity from hitting Robinhood's servers more than once an hour.
