---
title: "Teaching Claude to Plan Our Dinners (Without Putting '(plan doc URL)' on Every Screen in the House)"
date: 2026-11-11
draft: true
featuredImage: "/images/hero-claude-plans-our-dinners.jpeg"
featuredImagePreview: "/images/hero-claude-plans-our-dinners.jpeg"
tags: ["ai", "claude", "mcp", "cloudflare-workers", "skylight", "meal-planning", "automation"]
description: "I built an MCP server so Claude could write our weekly dinners into the family calendar. The first real run broke in five small ways, and none of them were caught by tests."
summary: "I gave Claude hands for the family calendar and asked it to plan a week of dinners. The first run nearly sent a literal placeholder to every screen in the house. Here is what I changed so the next run couldn't."
---

*Header image: generated with Google's Nano Banana. The people in it are AI-generated.*

Last week I almost put the words "(plan doc URL)" on every screen in my house.

Not on purpose. Claude had drafted a week of dinners and shown them to me as "the exact text" for approval, and the drafts carried a literal placeholder where a link should have been. If I had typed "yes", those words would have gone to the wall display and every phone in the family, with a stray "(dessert name)" for company. I caught it because I was reading the drafts like a reviewer. No test caught it, because at that point there was no test that knew what a placeholder looked like.

This is the story of how I got an AI to plan our weekly dinners and write them into our family calendar, how the first real run went wrong in small, specific ways, and what I changed so the weekly run is boring. Boring is the goal. A system that writes to a screen the whole family reads should be the least exciting thing in the house.

![A finished dinner entry in the family calendar app, with recipe link, steps and a start-time note](/images/claude-dinner-popup.png)

*A finished dinner entry as the family sees it. The link to our plan document is covered by a grey box.*

## Why I built this

For years my wife did most of the cooking. When I had a job I cooked now and then: something on the BBQ, pizza in the Ooni, pasta and a few other simple recipes I'd made many times. Then I lost my job, she had to work more, and dinner became mine along with more of the house. I'm not someone who picks varied meals, and it's tiring. The same few dishes on repeat get boring, and the family notices.

Then there's everything around the meals: pick the week, check the calendar for the nights that cut into cooking time, build a grocery list, type it all into the family calendar, and do it again the next week. I hate processes that should be automated. What I wanted was someone else to research, plan and write it down each week, with me steering what works and what doesn't. Changes were the other tedious part: a plan that moved on short notice meant fixing a document and a calendar.

We use Skylight, a calendar that lives on a wall display and in an app on our phones. The plan itself lived in a shared document that Claude and I both edited, until the document changed after a summary had been written from it and there were two versions of the week that disagreed. The calendar is what the family actually looks at, so I decided it should be the only copy, and the document should be a grocery list and a recipe shelf.

I also moved the planning day. It used to be Sunday, which is the day the plan week starts, so any mistake was found with groceries still unbought. Friday leaves two days to shop and to fix a draft before the week begins. It sounds like scheduling trivia, but it's why the rest of the setup had to run without me watching.

Claude can plan a week of dinners from a document without any help. What it can't do on its own is read the calendar or write to it. For that it needs tools, and the standard way to give a chat assistant tools is something called an MCP server. In plain words: a small program that sits between the AI and some other service, and offers the AI a short menu of things it is allowed to do ("list the meals for these dates", "add this meal"). The AI asks, the program does it and reports back.

Skylight doesn't publish documentation for an API, as far as I can tell, so there was nothing official to build against. What I did instead was open the Skylight web app, watch with my browser's developer tools what it sent when I added or edited a meal, and have Claude turn those requests into tools. I pasted only the request body and the response, never the headers that carry sign-in details.

## How it fits together

I started from an open-source Skylight server that someone else wrote (credited in the repo) and extended it. The server runs on a Cloudflare Worker, which is a small program hosted on Cloudflare's network. Hosting it there means Claude can reach it from any chat without my laptop being on.

![Claude reads the plan and calendar, then calls my server, which writes to Skylight after I approve](/images/claude-dinner-planning-flow.svg)

The tools that matter for dinners are few. One lists the meals already on the calendar for a range of dates. One reads calendar events for the same dates. One plans a whole week at once, with a "dry run" mode that shows what would happen without writing anything. And one edits a single existing meal.

The other half is a standing instruction: a block of text attached to the chat that tells Claude how to plan dinners this family's way. It has a hard limit of 2,000 characters, so the full version lives in my project notes and a compressed copy sits in the chat. Every rule in that text exists because something went wrong once.

### What took longer than the dinners

I assumed the hard part would be the planning. The hard part was the server. Every tool started as a question about what the app does. With nothing documented, each one meant rounds of small tests: send the call, read the response, send a variant. I also built it for people who aren't me: more of the API than my family will use, a better sign-in, local and hosted modes, Windows as well as Mac, and notes on what was tested and what wasn't. It took about two weeks, weekends and my birthday included: most days from 9 a.m., after dropping the kids at school, and several nights until 11. After more than 200 commits, Skylight could still change any of it tomorrow.

The iOS app showed things the web app doesn't. I watched its requests through a proxy tool called Proxyman. The web app can't delete or merge labels (Skylight's tags on events); the iOS app can. Delete turned out to be a plain `DELETE` on the label, returning 204, which is what my tool already sent. Merge is the same call with a target label added, returning 200 and the deleted record:

```text
DELETE categories/{id}                                  -> 204
DELETE categories/{id}?reassign_to_category_id={target} -> 200
```

I decided against a merge tool. What happens to a label that still has events was untested, and I don't plan to consolidate labels. Later I tested delete on a label with real events: events carrying only that label were removed, and events with a profile stayed and lost the label.

### Tools & AI assist

Claude extended the server, wrote its tests and the first versions of the standing instructions, and ran the dry runs and the real writes. It also turned my pasted captures into tool code, where it is genuinely faster than I am. The header image was generated with Google's Nano Banana, and the people in it are AI-generated and fictional. I made the decisions: what a meal name should look like, which checks block a write, when the weekly run is allowed to write at all.

The misses are named where they happened, below. One more doesn't fit there: our first prompt was a one-shot paste, because we assumed the chat had no place for standing instructions. It does; each channel has one. No other AI tools were involved.

## What went wrong

### The first run: eight messages for one week

For the first real run I started with a dry run: read the calendar and the meals, draft six dinners, show everything, write nothing.

It took about eight messages to get one week of dinners onto the calendar. That's the honest number, and it's more than the Friday chore it was supposed to replace.

Before any of that, there was a setup cost I hadn't priced in. A tool menu doesn't tell an assistant how this household eats, so Claude needed the house rules stated once: one night a week is takeout, one is meatless, there's one dessert, which equipment we own, where the recipes come from. It also needed the calendar's limits: a name, a 500-character note and up to 2,000 characters of instructions, each with a job.

Five things went wrong, and the tests had caught none of them. The plan document was built Monday to Sunday, but Skylight's week runs Sunday to Saturday. One dinner no longer fit, and the meatless night fell off the end of the week. The cause was an assumption stated in two places and clear in neither. The drafts held the literal placeholders I opened with. Claude fixed a typo after showing me a draft and mentioned it only at the end, a silent edit that makes "exact text" a lie. A cooking step turned up in a field meant for family notes. And Claude doubled or 1.5x-ed four of the five recipes on its own guess that we eat more than a recipe serves. I missed it in the plan. It surfaced only when Claude listed the changed grocery lines and I questioned one: three whole chickens for one dinner. Claude owned it: it had assumed bigger appetites unprompted.

![The Edit Meal screen: empty Instructions field, recipe steps in the note field below it](/images/claude-dinner-edit-meal.png)

*An early dinner entry, family details covered by grey boxes. The recipe steps landed in the note field and Instructions is empty.*

The fix was to turn each surprise into a sentence in the standing instructions. Here is the shape of the rules, trimmed:

```text
Use explicit YYYY-MM-DD dates in every call, never "this week"
(the plan week runs Sunday to Saturday).

Make every recipe as written; scale only if I say so.

Create the plan document first, so the Plan line carries a real link.

Never leave placeholders. If you change a block after showing it,
show it again.

plan_week_meals: dryRun true first, then write ONE meal, read it
back, show me, and wait for my yes before the rest.
```

Each rule traces to a failure above. If I could keep only one, it's the last: a half-finished set of dinners on a wall display is the worst way this can fail.

After the fixes, five dinners went in: one meal first, then the other four. I read the whole week back from Skylight in a separate call and compared it to what I'd approved. It matched.

Even that first week bent for a plainer reason. My wife cooked two nights I had planned for: chicken tacos, with no dessert, and spaghetti and meatballs the next evening, my birthday dinner. We'd gone out on the day itself, and what I actually wanted was spaghetti and meatballs at home. I asked Claude to move the two displaced dinners to the following week. It picked days that were clear on both calendars, showed me the exact changes, and waited for a yes. Then it wrote the changes and read each one back against what I had approved.

### The wall display I photographed and the phone I should have asked about

Meal names turned out to be harder than recipes. I photographed the wall display and found that the month view clips names at around eighteen characters, so "Herb butter baked salmon" showed up as "Herb butter baked s". I shortened three names to fit, felt pleased, and reversed the decision within minutes: my family mostly reads the calendar in the phone app, not on the wall display. The app shows names in full. I had optimized for the screen I'd just photographed, not for the one people use.

That left the rule underspecified. "Keep names short" isn't an instruction a model reads the same way twice, so I gave it a target and a cap instead: aim for 25 characters, never more than 35 with a dessert. Then a second pass from the reader's side: the family already knows what the dish is, so the name should be the plain dish ("Baked salmon") and the descriptive version goes on the first line of the instructions. Identity goes in the field people scan, precision in the field they open.

On the wall display the recipe link in a meal is plain text, not something you can tap, while in the phone app it's a real link. So nothing the cook needs at the stove can live only behind the link. The instructions carry the steps in short sentences with times and temperatures, and the link is a convenience.

A boring one: the standing-instructions field rejected my first version with a generic "link, formatting or a reserved phrase" error. The cause was most likely the angle brackets in my `<name>: <link>` placeholders. Swapping them for plain parentheses fixed it. If you paste text into a settings field and it complains without saying where, check for angle brackets first.

![The standing-instructions box at 7,077 of 2,000 characters, with an over-the-limit error](/images/claude-dinner-instructions-limit.png)

*My full rules ran 7,077 characters against a 2,000 limit. Part of one line is covered by a grey box.*

### Making the server say no

After the first run I stopped trusting myself to be the only check. Everything I'd caught by reading, I wanted the server to catch too, at least the kind of mistake that has no legitimate form. A placeholder on a wall display is always damage. So the server now looks for them before it writes:

```ts
// Text in (), [] or <> that stands in for something missing:
// "(plan doc URL)", "[recipe link]", "<dessert name>"
const BRACKETED_PLACEHOLDER =
  /[([<][^)\]>\n]*\b(?:url|link|needed|to fill in|fill in|placeholder|tbd|todo|dessert name|recipe name|plan doc)\b[^)\]>\n]*[)\]>]/i;

if (found) {
  errors.push(`${label} contains a placeholder: ${JSON.stringify(found)}.`);
}
```

Errors refuse the write. Everything else is only a warning: a name over 25 characters, a dessert longer than two words, a cooking verb in a note. Those have legitimate exceptions, and a false block would stall the weekly run with nobody there to answer it. The trade-off is that this is keyword matching, so "(insert here)" slips through. I accepted that. A missed placeholder costs a human read; a false alarm costs a stalled run.

I tested the check by breaking it on purpose: I removed the "url" keyword and ran the tests. They still passed. That told me the tests weren't checking what I thought, so three cases were added until removing the keyword made them fail.

### Full access, and a log instead of a gate

Here I overruled caution on purpose. I wanted setup to be easy for anyone trying this, and I wanted Claude to have full access instead of stopping to ask before each step. I also tested whether Claude's client would pause for a human yes before a delete. It didn't: it deleted in one call.

Easy still meant that signing in happens at the command line and never through Claude, and no tool Claude can call will log in, log out or read the credential. The project I started from tells you to put your Skylight email and password in environment variables, and the server logs in with them. I didn't want a password in a config file that any tool on the machine can read. So sign-in here happens in the browser: the command prints a Skylight URL, and after I sign in I paste back the address the browser lands on. What gets stored is an encrypted credential, with its key in the macOS Keychain, not the password. The price is a clumsier first step, because that address has to be copied out of browser history. I didn't invent this flow: I took it from another open-source Skylight project and brought it into the server I started from, which only offered the password route.

```text
node dist/index.js auth login
1. Open this URL in your browser and sign in to Skylight
   (Windows Terminal: hold Ctrl and click it; otherwise copy it into your browser):

   [ sign-in URL redacted ]

2. Skylight bounces the browser through https://ourskylight.com/welcome?code=... too fast
   to copy. Get it from browser history: Cmd-Y (Mac) / Ctrl-H (PC), search "welcome?code",
   right-click the Skylight result dated today (top of the list; older ones are earlier
   sign-ins and will not work), Copy link address.

3. Run the same command you just ran, with `complete` instead of `login`,
   and paste the URL at the prompt. This login expires in 10 minutes.
```

The risk is real. Claude could remove the wrong meal or the wrong event. But this is dinners on a family calendar, not money, and a wrong deletion costs me a minute of putting it back. So instead of a gate I asked for a record: one line for every change, with the tool, whether it was a write or a delete, the outcome and a running count, and deliberately no meal text and no IDs. There's also a cap of 60 changes and 10 deletes an hour, as a leash for a runaway loop.

The record earned its place the night I shipped it. I made three calls four seconds apart and each log line said the running count was 1. The count lived in a variable on the server, and I couldn't count on a Worker keeping variables between requests, so the cap I'd just shipped wasn't capping anything. All the tests had passed, because in a test the variable does survive. The fix was to move the counter into a small piece of storage that does persist, and the next run counted up.

Then the scheduled part. The Friday run happens on a schedule, with nobody there to say yes, so its rule is blunt: draft, post the text, stop. It never writes, because a write needs my yes to the exact text, and that text shows on devices around the house where I can't recall it.

![The scheduled task list showing "Weekly dinner plan (Fridays)", every Friday at 10:47 AM](/images/claude-dinner-friday-task.png)

Because Skylight's API is unofficial, a change in what it returns could break a tool without any error. The first place that would show is the unattended Friday run, so the day before there's a canary: every Thursday a scheduled Claude task runs five read-only checks and posts one line in its own channel, pass or fail. It uses the same read-only tools, so it needs no new credential. The catch is that it shares fate with the server it checks, so if the server is down, a missing Thursday line is the signal. A scheduled run can't send mail itself, so I picked the routine's own email alert.

![The canary channel chat: I pick an email alert and a Thursday schedule, and the first run posts a pass](/images/claude-dinner-canary.png)

*The canary's first run, Thursday at 9:46 AM.*

The first run passed five of five and, as intended, sent no email. I haven't watched a real failure arrive yet, so that half of the canary is still a plan.

## Lessons

**The technical one.** "The UI doesn't offer it" is weak evidence the API lacks it. One client's screen is evidence about that client. The web app has no way to delete or merge a label; the iOS app does, and the call behind delete was already in my server.

**The AI one.** Claude is very fast from a symptom to the next step. What it doesn't do is check that the evidence supports where it lands. It told me the plan document matched what was on the calendar. It told me a Friday routine would pick up a queued meal. Both sounded right, and I had checked neither. Reading the week back from Skylight in a separate call, and comparing it to the text I approved, is my job, and it is cheap. A confident sentence is not a measurement.

**The one you can swap your own project into.** State every assumption once, as a number or a date, and test it with a check that can fail. The week boundary, the portion size, the name length and the placeholder were all the same mistake: something I assumed, never wrote down, and discovered only when a real family would have read it. Whatever you hand to an agent that writes where other people can see, write down what it must never leave behind, and then break your own check to see that it fires.

My verdict from my notes after that first week: not easier yet. The test was always the second week. The next Friday run was better, though I still changed things for reasons no rule covers: a sick week, and a night of cooking whatever we already had. Overall it worked, and by my estimate (not a stopwatch) it saves me hours of looking up and planning meals. Claude also checks the plan against the calendar and flags conflicts I missed.

![The Meals view filtered to dinners, Sunday the 8th to Sunday the 15th, with two nights empty](/images/claude-dinner-week-meals.png)

*The app's Meals view, filtered to dinners. The two empty nights are on purpose.*

## Try it yourself

The server is open source (MIT) and unofficial: it talks to endpoints Skylight doesn't document, so it may break without notice, and the README says so plainly. If you can run a few commands, setup is covered there.

- Code and README: [github.com/dwooods/skylight-mcp](https://github.com/dwooods/skylight-mcp)
- Package: `@davidwoods/skylight-mcp` on npm

---

The moment I knew it worked was small. My wife mentioned that tomorrow's dinner looked good. I hadn't told her; she'd seen it on the calendar, and she was excited to try it. That reminded me I needed to go to the grocery store, and that week I made my first trip to an Asian market, for ingredients no local store carries. Deciding was the part worth automating, so that time now goes to cooking, and we've stopped eating the same handful of meals every week.

![The front of a 99 Ranch Market: a gabled entrance with red lettering above a stone-faced wall](/images/claude-dinner-ranch-market.jpeg)

*The front of 99 Ranch Market in Concord, CA.*
