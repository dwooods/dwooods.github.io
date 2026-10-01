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

### What the data gives you, and what it doesn't

The core data is solid. Positions, cash, live quotes and each holding's dividend schedule (yield, payout frequency, next ex-dividend and pay dates) all came back reliably, and the price history is flexible enough to draw every chart on the page. The gaps showed up the moment I asked for the two things an income investor wants. Nothing says "you were paid this much, on this date, from this holding," and nothing gives account value over time, even though Robinhood's own app draws exactly that chart.

The export fix had its own twist. For a week the page carried a footnote warning that the export looked incomplete. The real explanation is further down, and it's a better story.

### Designing by screenshot

Most of the design happened one request at a time, and most requests were a screenshot.

<p align="center"><img src="/images/income-book-evolution-01.png" alt="Version 4: serif headline font, four stat cards, a holdings bar chart, and sort buttons above the Positions table." style="max-width:100%;"></p>

*Version 4, where this story starts: rounded cards, a serif headline, a bar chart of holdings, and three buttons for sorting the table.*

Sortable columns came first. The only real decision was to rip out the three "sort by" buttons the page already had and make every column header clickable, since two ways to sort the same table is one too many. For the per-stock chart I asked Claude for a design opinion: a drop-down under the row, or a separate chart section? Claude argued for the drop-down and I agreed. The chart stays next to the numbers you were just reading, only one opens at a time, and it keeps your chosen range when you open the next stock, so comparing two holdings is one click.

Then I sent a screenshot of Robinhood's stock list with its little inline charts, and a screenshot of its account chart, and asked for both. The little charts became a "Today" column. The big chart became the headline of the page, and the most interesting problem in the project.

<p align="center"><img src="/images/income-book-evolution-03.png" alt="Version 7: a portfolio-value chart across the top with range buttons, and three stat cards below it." style="max-width:100%;"></p>

*Version 7: the portfolio chart takes over the top of the page, and every row gains a tiny Today chart.*

### The chart that has to admit it's a reconstruction

Robinhood draws an account-value chart. The MCP server doesn't expose one. So there's only one way to draw it from the outside: take each holding's price history, multiply by how many shares I own *today*, add cash, and add it all up.

That produces a line that looks exactly like Robinhood's chart and doesn't mean the same thing. It's what my current portfolio *would have been worth* over that period, not what my account actually was worth, so any time I bought or sold during the range, the line is wrong. It looks authoritative, it's reconstructed, and nothing about the picture tells you which. Claude flagged this before I did, and we shipped it with a footnote directly under the chart saying exactly that. I'd rather have an honest approximation than a convincing one.

### Where the real app caught what testing couldn't

Two problems came from holding the real app next to ours, and both are the kind that pass every test you think to write.

The first was small, and Claude caught it on its own: a date mix-up that would have put every chart label a day off. The second was mine to catch. The one-day chart had been built as "the last 24 hours," with points spaced evenly across the width. That's literally what I'd asked for, and it's not what a one-day stock chart means. I put a screenshot of Robinhood's 1D view next to ours: Robinhood pins the chart to the trading day, 6:30am to 1pm Pacific, and the line only runs as far as *now*, leaving the rest of the day blank. Ours stretched whatever data existed across the whole width.

The rebuild pinned every one-day view to the trading session and changed the dotted reference line from "the first price on the chart" to "yesterday's close," so the day's change means what it means in Robinhood.

<p align="center"><img src="/images/income-book-evolution-05.png" alt="Version 9: the one-day portfolio chart covers only the morning so far, with the rest of the trading day left blank." style="max-width:100%;"></p>

*Version 9: the one-day view pinned to market hours. The line stops at “now,” the rest of the session stays empty, and the dotted line is yesterday’s close.*

Later the same side-by-side caught something smaller: pick a range like 3M and the headline change should say "Past 3 months," not "Today," just as the app does. It's measured on the reconstructed line, so it won't match the app's figure exactly.

<p align="center"><img src="/images/income-book-evolution-08.png" alt="Version 15: the account-value header with 3M selected, reading a gain over the past 3 months, with the green accent following the range's direction. Sample data." style="max-width:100%;"></p>

*Version 15: pick a range and the header's change follows it, and the accent color follows that direction.*

### A rule to protect Robinhood from me

Another change was about how often the page talks to Robinhood. Every Refresh went straight to Robinhood, and a dashboard has no business hitting someone else's servers every time I get curious, so I asked for the page to remember what it last pulled and only go back if that's more than an hour old. Under an hour, Refresh says so and makes no calls. If a pull fails, the page keeps showing the last saved data instead of going blank. That came from a real mistake: for a week, the page's saved copy kept showing old holdings, and it looked just as current as a fresh pull. An empty page now says "click Refresh" instead of showing week-old holdings as if they were today's, which is less pretty and more honest.

### Making it look like it belongs in the app

Once the page did what I wanted, I asked for it to look like it belonged inside Robinhood. Partly that was so it would feel native to me, something I'd actually want to open next to the app. Partly it was so that a page I'd show people on LinkedIn would look finished, with real thought put into the experience, instead of a backend with a chart bolted on. Claude pulled the exact green and orange out of my screenshots and rebuilt the page flat, with no cards, hairline dividers and plain-text range tabs. Then I opened Chrome's inspector on robinhood.com and sent Claude screenshots of the styles panel, which turned out to be the real thing: Robinhood's colors, grays and type sizes are all sitting on the page as named variables, and the page now uses those values directly. My favorite detail: the site's primary color appears to follow the account's direction, orange on a down day and green on an up day. The Dividend Dashboard does the same now, with one exception I asked for: the Refresh button stays Robinhood green no matter what the market is doing. Optimism is a design choice.

<p align="center"><img src="/images/income-book-evolution-07.png" alt="Version 13: Robinhood's design tokens and a green Refresh button." style="max-width:100%;"></p>

*Version 13: Robinhood's own color and type values from the browser inspector, an accent that follows the day's direction, and a Refresh button that stays green regardless.*

The one thing I couldn't copy is the font. Robinhood's typeface is licensed, so the page asks for it first and falls back to Inter, which is what almost everyone will actually see.

## Then Robinhood Shipped a Dividend Tracker

A week into this, Robinhood's app got the feature I'd been building toward. The backstory: at HOOD Summit '25 in Las Vegas in September 2025, Vlad Tenev polled the audience on what Robinhood should build next, and [dividend tracking and portfolio comparisons were the top two picks](https://www.tipranks.com/news/the-fly/robinhood-ceo-tenev-polls-hood-summit-25-audience-for-next-platform-feature-thefly). A couple of days later, [Robinhood posted](https://x.com/RobinhoodApp/status/1966587161240559713): "Customers ask, we execute. Dividend Tracking and Portfolio Comparisons coming next year." They delivered — [announced on X](https://x.com/RobinhoodApp/status/2086845029616886188) in August, ahead of [HOOD Summit '26](https://robinhood.com/us/en/newsroom/robinhood-presents-hood-summit-26-engines-of-creation/) in Houston at the end of September.

Per Robinhood's [help article](https://robinhood.com/us/en/support/articles/dividends/), you find it by typing "Dividend tracker" into the app's search. It shows the net dividends you've received this year, a projection for the rest of the year as gray bars, past years, and a list of "yielding positions." Tap a position for what you've received from it, its yield (the 30-day SEC yield for ETFs like JEPI), a projected annual amount, and the dividend per share. It's basically the income half of the page I'd been building.

<div style="display:flex; gap:16px; justify-content:center; align-items:flex-start; flex-wrap:wrap;">
<img src="/images/robinhood-app-dividends-card.png" alt="Robinhood's per-stock Dividends card: yield, dividend per share, received year to date, annual projected, next ex-dividend and pay dates, and a View all dividends link. Dollar amounts covered." style="width:52%; min-width:260px; max-width:100%;">
<img src="/images/robinhood-app-dividend-tracker.png" alt="Robinhood's Dividend tracker screen: a 2026 and MAX toggle, a monthly bar chart of actual and projected dividends, and a list of yielding positions with yield. Dollar amounts and share counts covered." style="width:36%; min-width:200px; max-width:100%;">
</div>

*Robinhood's app: one stock's Dividends card on the left, the Dividend tracker on the right. These are screenshots from my own account, with the dollar amounts and share counts covered.*

So of course I asked Claude to rebuild it. The forward-looking half is completely available through the MCP server: Robinhood's data includes each holding's dividend per share, how often it pays, and its next ex-dividend and pay dates. Projecting the rest of the year is just shares owned times the dividend, for every payment still due before December 31. Using nothing else, Claude's projection landed within about one percent of Robinhood's; NLY's annual projection matched to the cent; and the monthly bars came out in the same proportions. Fed the same per-holding received amounts Robinhood shows, the yielding-positions list matched line for line.

<p align="center"><img src="/images/income-book-dividend-tracker.png" alt="The Dividend Dashboard's version of the dividend tracker: year-to-date received, an annual projection, green actual and gray projected monthly bars, and a list of yielding positions with one expanded to show yield, dividend per share, received, annual projected and next dates. Sample data." style="max-width:100%;"></p>

*The Dividend Dashboard's copy of the tracker (version 14, with dollar amounts over each bar added in version 16), on the sample portfolio. Green is paid, gray is projected — same convention as Robinhood's.*

The humbling part came from comparing the two. Robinhood's tracker said my Agentic account had received less than a sixth of what my dividends panel had been claiming for a week. The reason was sitting in the CSV the whole time: it was my *individual* account's export, not the Agentic account's. Its transfer rows show my positions moving into Agentic in July and August, so most of those dividends were paid before the move, in a different account. The TRIN dividend I thought was "missing" was paid after TRIN moved; the sale that wasn't in the file happened in Agentic. The export wasn't incomplete. It was faithfully reporting one account, and neither Claude nor I noticed until Robinhood's own feature showed a number that disagreed. What settled it was lining up my monthly statements: the export matched the individual account's statements to the cent, and the Agentic payments showed up in that account's own records.

Side by side, the app's tracker is better than mine in one way that matters: it shows what the account has actually been paid, because it's Robinhood's app reading Robinhood's own data. Mine is only as good as what I feed it. That's a data gap, not a design gap.

I'm not claiming mine is better than Robinhood's. It's a view that works for what I want. The app shows one stock's dividend card at a time, and the tracker's projected bars aren't something I can click into. The Dividend Dashboard puts the same fields for every holding on one sortable page, next to price, cost and yield on cost. The app has the data, and mine has the shape I wanted.

Building it also taught me something about my own holdings: the yield on my purchases didn't match the yield Robinhood listed. The listed yield is a trailing figure, the last year of payouts against today's price. What I earn depends on what I paid and when, and if you keep buying through the year you only collect the dividends paid after each purchase. Claude explained that, and it's why the page shows yield on cost next to the listed yield.

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

The data lesson came three times in one project: my dividend panel was confidently wrong for a week because I never asked which account the export came from, the saved snapshot looked current after it stopped being current, and the account chart looked exactly like Robinhood's while meaning something different. Each time the fix was the same: decide what the real source of truth is, treat everything else as an approximation, and say so on the page. Stale or reconstructed data that looks live is worse than an empty box.

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
