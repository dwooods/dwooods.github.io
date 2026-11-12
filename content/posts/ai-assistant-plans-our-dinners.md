---
title: "I Gave an AI Assistant a Chore I Hate. The Hard Part Was Building What It Needed"
date: 2026-11-11
draft: true
featuredImage: "/images/hero-claude-plans-our-dinners.jpeg"
featuredImagePreview: "/images/hero-claude-plans-our-dinners.jpeg"
tags: ["ai", "claude", "duet", "mcp", "cloudflare-workers", "skylight", "meal-planning", "automation"]
description: "How an AI assistant plans our weekly dinners and writes them into our Skylight family calendar through an MCP server I built, and the five things that went wrong that no test caught."
summary: "The first real run nearly put a literal \"(plan doc URL)\" on the wall display and every phone in the family. Here is what I built, and what I changed, so the next run couldn't."
---

*Header image: generated with Google's Nano Banana. The people in it are AI-generated.*

Last week I almost put the words "(plan doc URL)" on every screen in my house.

Not on purpose. My AI assistant (Duet) had drafted a week of dinners and shown them to me as "the exact text" for approval, and the drafts carried a literal placeholder where the link to our shared meal-plan Google Doc should have been. If I had typed "yes", those words would have gone to the wall display and every phone in the family, with a stray "(dessert name)" for company. I caught it only because I was reading the drafts like a reviewer; no test knew what a placeholder looked like.

This is how I got an AI to plan our weekly dinners and write them into our family calendar, how the first real run went wrong in small ways, and what I changed so the weekly run is boring. A system that writes to a screen the whole family reads should be the least exciting thing in the house.

![A finished dinner entry in the family calendar app, with recipe link, steps and a start-time note](/images/claude-dinner-popup.png)

*A finished dinner entry as the family sees it. The link to our plan document is covered by a grey box.*

## Why I built this

For years my wife did most of the cooking. When I had a job I cooked now and then: something on the BBQ, pizza in the Ooni, pasta and a few other simple recipes I'd made many times. Then I lost my job, she had to work more, and dinner became mine along with more of the house. I'm not someone who picks varied meals, and it's tiring. The same few dishes on repeat get boring, and the family notices.

Then there's everything around the meals: planning the week, the grocery list, getting it into the calendar, and doing it again the next week. I hate processes that should be automated. I like planning and coordinating when it's a product. Planning a dinner not everyone will like, deciding when to cook it and telling everyone what it is, I don't. What I wanted was someone else to research, plan and write it down each week, with me steering what works and what doesn't.

We use Skylight, a calendar that lives on a wall display and in an app on our phones. My first attempt was only a test of what Duet could do: it planned meals in a Google Doc I'd share with everyone. It worked, but it was never going to be the plan. The real plan needed a real interface like Skylight, which my wife and the family already use and Duet couldn't reach. The calendar is what the family looks at, so it is the only copy of the plan. The document is still created each week: it puts the whole week on one page, easier to scan than meals spread across days, and easier to share, though a poor meal plan.

I also moved the planning day. I'd planned on Saturday for a Monday-to-Sunday week, but Skylight's week runs Sunday to Saturday, so the first version of the document didn't line up with the calendar and I reworked the plan. Friday for a Sunday-to-Saturday week fixes that and leaves two days to shop and fix a draft. Duet had to be told the new day, and the weekly canary moved to Thursday.

To reach Skylight, an assistant needs tools, and the standard way to give a chat assistant tools is something called an MCP server. In plain words: a small program between the AI and another service that offers the AI a short menu of things it may do ("list the meals for these dates", "add this meal").

Skylight doesn't publish documentation for an API, as far as I can tell, so there was nothing official to build against. What I did instead was open the Skylight web app, watch with my browser's developer tools what it sent when I added or edited a meal, and have Claude turn those requests into tools. I pasted only the request body and the response, never the headers that carry sign-in details.

## How it fits together

I started from an open-source Skylight server that someone else wrote (credited in the repo) and extended it. It runs on a Cloudflare Worker, a small program hosted on Cloudflare's network, so Duet can reach it from any chat without my laptop being on. I built it as an integration any AI assistant could use, not just Duet: a library, a local version and a hosted version, and I planned it so another calendar could replace Skylight later.

![The assistant reads the plan and calendar, then calls my server, which writes to Skylight after I approve](/images/claude-dinner-planning-flow.svg)

Four tools matter for dinners: one lists the meals on the calendar for a range of dates, one reads calendar events for the same dates, one plans a whole week at once (with a "dry run" mode that writes nothing), and one edits a single meal.

The other half is a standing instruction: a block of text attached to the chat that tells Duet how to plan dinners this family's way. It has a hard limit of 2,000 characters, so the full version lives in my project notes and a compressed copy sits in the chat. Every rule in it exists because something went wrong once.

### What took longer than the dinners

I assumed the hard part would be the planning. The hard part was the server. With nothing documented, each tool meant rounds of small tests: send the call, read the response, send a variant. I also built it for people who aren't me: more of the API than my family will use, a browser sign-in, local and hosted modes, Windows as well as Mac, and notes on what was and wasn't tested. It took about two weeks, weekends and my birthday included: most days from 9 a.m., after dropping the kids at school, and several nights until 11. After more than 200 commits, Skylight could still change any of it tomorrow.

The iOS app showed things the web app doesn't. I watched its requests through a proxy tool called Proxyman. As far as I could tell, the web app can't delete or merge labels (Skylight's tags on events); the iOS app can. Delete turned out to be a plain `DELETE` on the label, returning 204, which is what my tool already sent. Merge is the same call with a target label added. I decided against a merge tool: what happens to a label that still has events was untested, and I don't plan to consolidate labels. Later I tested delete on a label with real events: events carrying only that label were removed, and events with a profile stayed and lost the label.

I also compared 16 read endpoints between the API version my server defaults to and the one the apps send. Twelve came back identical, two (messages and avatars) differed in shape, and two (chores and rewards) were empty that day. The messages difference was a real bug: every message showed as sent to "selected devices" even when it went to everyone. This only compares shape; a change in meaning would be invisible.

### Tools & AI assist

Two AI tools did different jobs. Claude built the server: it extended the open-source project, wrote its tests and turned my pasted captures into tool code, where it is genuinely faster than I am. Duet, an AI assistant I have through my Claude access, runs it each week: it drafts the dinners, does the dry runs and the real writes, and handles the Friday run and the Thursday check. Any assistant that can call tools could do that job; Duet is the one I had. The hand-off wasn't clean, because Duet runs differently from the tool I built with. The header image was generated with Google's Nano Banana, and the people in it are AI-generated and fictional. I made the decisions: what a meal name should look like, which checks block a write, when the weekly run is allowed to write at all.

One miss doesn't fit below: our first prompt was a one-shot paste, because we assumed the chat had no place for standing instructions. It does; each channel has one.

## What went wrong

### The first run: eight messages for one week

For the first real run I started with a dry run: read the calendar and the meals, draft six dinners, show everything, write nothing.

It took about eight messages to get one week onto the calendar, more than the Friday chore it was supposed to replace.

Before any of that came a setup cost I hadn't priced in: a tool menu doesn't tell an assistant how this household eats, so Duet needed the house rules stated once: one night a week is takeout, one is meatless, there's one dessert, which equipment we own, where the recipes come from. It also needed the calendar's limits: a name, a 500-character note and up to 2,000 characters of instructions, each with a job.

Five things went wrong, and the tests had caught none of them. The plan document was built Monday to Sunday, but Skylight's week runs Sunday to Saturday. One dinner no longer fit, and the meatless night fell off the end of the week. The assumption was stated in two places and clear in neither. The drafts held the literal placeholders I opened with. Duet fixed a typo after showing me a draft and mentioned it only at the end, a silent edit that makes "exact text" a lie. A cooking step turned up in a field meant for family notes. And Duet doubled or 1.5x-ed four of the five recipes on its own guess that we eat more than a recipe serves. I missed it in the plan. It surfaced only when I questioned one grocery line: three whole chickens for one dinner. Duet owned it: it had assumed bigger appetites unprompted.

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

Each rule traces to a failure above. If I could keep only one, it's the last: half a week of dinners on a wall display is the worst way this can fail.

After the fixes, five dinners went in: one meal first, then the other four. I read the whole week back from Skylight in a separate call and compared it to what I'd approved. It matched.

Even that first week bent for a plainer reason. My wife cooked two nights I had planned for: chicken tacos, with no dessert, and spaghetti and meatballs the next evening, my birthday dinner. We'd gone out on the day itself, and what I actually wanted was spaghetti and meatballs at home. I asked Duet to move the two displaced dinners to the following week. It picked days that were clear on both calendars, showed me the exact changes, and waited for a yes. Then it wrote them and read each one back.

### The wall display I photographed and the phone I should have asked about

Meal names turned out to be harder than recipes. The wall display's month view clips names at around eighteen characters, so "Herb butter baked salmon" showed up as "Herb butter baked s". I shortened three names to fit, then reversed it within minutes: my family mostly reads the calendar in the phone app, which shows names in full. I had optimized for the screen I'd photographed, not the one people use.

"Keep names short" isn't an instruction a model reads the same way twice, so I gave it a target and a cap: aim for 25 characters, never more than 35 with a dessert. Then a second pass from the reader's side: the family already knows the dish, so the name should be the plain dish ("Baked salmon") and the descriptive version goes on the first line of the instructions. Identity goes in the field people scan, precision in the field they open.

On the wall display a recipe link is plain text you can't tap, so nothing the cook needs at the stove can live only behind it. The instructions carry the steps with times and temperatures, and the link is a convenience.

![The standing-instructions box at 7,077 of 2,000 characters, with an over-the-limit error](/images/claude-dinner-instructions-limit.png)

*My full rules ran 7,077 characters against a 2,000 limit. Part of one line is covered by a grey box.*

### Making the server say no

After the first run I stopped trusting myself to be the only check. Everything I'd caught by reading, I wanted the server to catch too, at least mistakes with no legitimate form. A placeholder on a wall display is always damage, so the server now looks for them before it writes:

```ts
// Text in (), [] or <> that stands in for something missing:
// "(plan doc URL)", "[recipe link]", "<dessert name>"
const BRACKETED_PLACEHOLDER =
  /[([<][^)\]>\n]*\b(?:url|link|needed|to fill in|fill in|placeholder|tbd|todo|dessert name|recipe name|plan doc)\b[^)\]>\n]*[)\]>]/i;

if (found) {
  errors.push(`${label} contains a placeholder: ${JSON.stringify(found)}.`);
}
```

Errors refuse the write. Everything else is only a warning: a name over 25 characters, a dessert longer than two words, a cooking verb in a note. Those have legitimate exceptions, and a false block would stall the weekly run with nobody there to answer it. The trade-off is that this is keyword matching, so "(insert here)" slips through. A missed placeholder costs a human read; a false alarm costs a stalled run.

I broke the check on purpose by removing the "url" keyword. The tests still passed, so they weren't checking what I thought; three cases were added until removing the keyword made them fail.

### Full access, and a log instead of a gate

Here I overruled caution on purpose. I wanted setup to be easy for anyone trying this, and I wanted Duet to have full access instead of stopping to ask before each step. I also tested whether Duet's client would pause for a human yes before a delete. It didn't: it deleted in one call.

Easy still meant that signing in happens at the command line and never through the assistant, and no tool Duet can call will log in, log out or read the credential. The project I started from wants your Skylight password in environment variables, and I didn't want one in a config file any tool on the machine can read. So sign-in happens in the browser: I sign in, then paste back the address the browser lands on, and what gets stored is an encrypted credential keyed in the macOS Keychain, not the password. The price is a clumsier first step. I took the flow from another open-source Skylight project and brought it into the server I started from, which only offered the password route.

The risk is real: Duet could remove the wrong meal or event. But this is dinners on a family calendar, not money, and a wrong deletion costs a minute. So instead of a gate I asked for a record: one line for every change, with the tool, whether it was a write or a delete, the outcome and a running count, and deliberately no meal text and no IDs. There's also a cap of 60 changes and 10 deletes an hour, as a leash for a runaway loop.

The record earned its place the night I shipped it. I made three calls four seconds apart and each log line said the running count was 1. The count lived in a variable on the server, and I couldn't count on a Worker keeping variables between requests, so the cap I'd just shipped wasn't capping anything. All the tests had passed, because in a test the variable does survive. The fix was to move the counter into a small piece of storage that does persist, and the next run counted up.

Then the scheduled part. The Friday run happens on a schedule, with nobody there to say yes, so its rule is blunt: draft, post the text, stop. It never writes, because a write needs my yes to the exact text, and that text shows on devices around the house where I can't recall it.

![Scheduled task list: Weekly dinner plan, Fridays](/images/claude-dinner-friday-task.png)

Because Skylight's API is unofficial, a change in what it returns could break a tool without any error. The first place that would show is the unattended Friday run, so the day before there's a canary: every Thursday a scheduled Duet task runs five read-only checks and posts one line in its own channel, pass or fail. It uses the same read-only tools, so it needs no new credential. It shares fate with the server it checks, so a missing Thursday line is the signal.

![The canary channel chat: email alert, Thursday schedule, first run passes](/images/claude-dinner-canary.png)

The first run passed five of five and, as intended, sent no email. I haven't watched a real failure arrive yet, so that half of the canary is still a plan.

## Lessons

**The technical one.** "The UI doesn't offer it" is weak evidence the API lacks it. One client's screen is evidence about that client. As far as I could tell, the web app has no way to delete or merge a label; the iOS app does, and the call behind delete was already in my server.

**The AI one.** Duet is very fast from a symptom to the next step. What it doesn't do is check that the evidence supports where it lands. It told me the plan document matched the calendar, and that a Friday routine would pick up a queued meal. Both sounded right; I had checked neither. Reading the week back from Skylight in a separate call and comparing it to the text I approved is my job, and it is cheap. A confident sentence is not a measurement.

**The one you can swap your own project into.** State every assumption once, as a number or a date, and test it with a check that can fail. The week boundary, the portion size, the name length and the placeholder were all the same mistake: something I assumed, never wrote down, and discovered only when a real family would have read it. Whatever you hand to an agent that writes where other people can see, write down what it must never leave behind, then break your own check to see it fire.

My verdict from my notes after that first week: not easier yet. The next Friday run was better, though I still changed things for reasons no rule covers: a sick week, and a night of cooking whatever we already had. By my estimate (not a stopwatch), doing it properly by hand took two to four hours a week. In practice I never did: I printed lists, gave up, planned day to day and made a store run most mornings based on whatever I'd found online that morning. Now the meals arrive on Friday, I review them, change what I want and send one prompt, and a full week is in the calendar, shared with the family and documented in under 20 minutes. About half the weeks go that way. The rest bend when people are tired, events move or nobody wants to cook, and ordering food wins. Two weeks of long days won't pay back in hours any time soon. What I got back is the daily search for what to make.

![The Meals view for the week, with two nights empty](/images/claude-dinner-week-meals.png)

*The app's Meals view, filtered to dinners. The two empty nights are on purpose.*

## Try it yourself

The server is open source (MIT) and unofficial: it talks to endpoints Skylight doesn't document, so it may break without notice, and the README says so plainly. Skylight's terms don't allow access outside its supported interfaces and let it suspend accounts, so using this puts the account you sign in with at risk, not just the integration. If you can run a few commands, setup is covered there.

- Code and README: [github.com/dwooods/skylight-mcp](https://github.com/dwooods/skylight-mcp)
- Package: `@davidwoods/skylight-mcp` on npm

---

The moment I knew it worked was small. My wife mentioned that tomorrow's dinner looked good. I hadn't told her; she'd seen it on the calendar. On Tuesday I cooked the [green chicken enchiladas](https://damndelicious.net/2019/03/01/green-chicken-enchiladas/), and the family loved them. Left to me, it would have been one of our usual handful of meals again. Duet picked something we like and don't cook often, and I didn't have to think about it.
