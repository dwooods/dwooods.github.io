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

Last week I almost put the words "(plan doc URL)" on every screen in my house.

Not on purpose. Claude had drafted a week of dinners and shown them to me as "the exact text" for approval, and the drafts carried a literal placeholder where a link should have been. If I had typed "yes", those words would have gone to the wall display and every phone in the family, with a stray "(dessert name)" for company. I caught it because I was reading the drafts like a reviewer. No test caught it, because at that point there was no test that knew what a placeholder looked like.

This is the story of how I got an AI to plan our weekly dinners and write them into our family calendar, how the first real run went wrong in small, specific ways, and what I changed so the weekly run is boring. Boring is the goal. A system that writes to a screen the whole family reads should be the least exciting thing in the house.

![A finished dinner entry in the family calendar app: dish name, recipe link, short steps, the plan-document link and a note with a start time](/images/claude-dinner-popup.png)

*A finished dinner entry as the family sees it. The link to our plan document is covered by a grey box.*

## Why I built this

Every week I had a small chore that was never hard and never quite finished. Pick six dinners, check the calendar for the evenings that cut into cooking time, build a grocery list, and type all of it into the family calendar so that the wall display and the phone app show what's for dinner. We use Skylight, a calendar that lives on a wall display and in an app on our phones.

The plan itself lived in a shared document that Claude and I both edited. That worked until it didn't: the document changed after a summary had been written from it, and for a while there were two versions of the week that disagreed. The calendar is what the family actually looks at. I decided the calendar should be the only copy, and the document should be a grocery list and a recipe shelf.

I also moved the planning day. It used to be Sunday, which is the day the plan week starts, so any mistake was found with groceries still unbought. Friday leaves two days to shop and to fix a draft before the week begins. It sounds like scheduling trivia, and it's the reason the rest of the setup had to be able to run without me watching.

Claude can plan a week of dinners from a document without any help. What it can't do on its own is read the calendar or write to it. For that it needs tools, and the standard way to give a chat assistant tools is something called an MCP server. In plain words: a small program that sits between the AI and some other service, and offers the AI a short menu of things it is allowed to do ("list the meals for these dates", "add this meal"). The AI asks, the program does it and reports back.

Skylight doesn't publish documentation for an API, as far as I can tell, so there was nothing official to build against. What I did instead was open the Skylight web app, watch with my browser's developer tools what it sent when I added or edited a meal, and have Claude turn those requests into tools. I pasted only the request body and the response, never the headers that carry sign-in details. That habit paid off over and over, but that's another post.

## How it fits together

I started from an open-source Skylight server that someone else wrote (credited in the repo) and extended it. The server runs on a Cloudflare Worker, which is a small program hosted on Cloudflare's network. Hosting it there means Claude can reach it from any chat without my laptop being on. Claude connects to it, gets the menu of tools, and uses them.

![Claude reads the plan document and the calendar, calls my server, and the server writes to Skylight, with me approving the exact text first](/images/claude-dinner-planning-flow.svg)

The tools that matter for dinners are few. One lists the meals already on the calendar for a range of dates. One reads calendar events for the same dates. One plans a whole week at once, with a "dry run" mode that shows what would happen without writing anything. And one edits a single existing meal.

The other half is a standing instruction: a block of text attached to the chat that tells Claude how to plan dinners this family's way. It has a hard limit of 2,000 characters, so the full version lives in my project notes and a compressed copy sits in the chat. Every rule in that text exists because something went wrong once.

### Tools & AI assist

Claude extended the server, wrote its tests and the first versions of the standing instructions, and ran the dry runs and the real writes. It also turned my pasted captures into tool code, which is the kind of work where it is genuinely faster than I am. The header image was generated with Google's Nano Banana, and the people in it are AI-generated and fictional. I made the decisions: what a meal name should look like, which checks block a write, when the weekly run is allowed to write at all.

The misses are worth naming. Claude put placeholders into text it called final, scaled recipes up on its own assumption, edited a draft without telling me, and told me a weekly routine would pick up a task, which I had not verified and which it had no way of knowing. Our first prompt was a one-shot paste, because we assumed the chat had no place for standing instructions. It does; each channel has one. No other AI tools were involved.

## What went wrong

### The first run: eight messages for one week

For the first real run I started with a dry run: read the calendar and the meals, draft six dinners, show everything, write nothing.

It took about eight messages to get one week of dinners onto the calendar. That's the honest number, and it's more than the Friday chore it was supposed to replace.

Before any of that, there was a setup cost I hadn't priced in. A tool menu doesn't tell an assistant how this household eats. Claude needed the rules of the house stated once: one night a week is takeout, one is meatless, there's one dessert, which equipment we own, where the recipes come from. It also needed the limits the calendar enforces, because the dinner entry has three separate fields (a name, a short note of 500 characters, and instructions of up to 2,000) and each has a job. None of this is clever. It's the onboarding any new helper would get, and skipping it means the helper invents a version of your family.

Five things went wrong, and the tests had caught none of them. The plan document was built Monday to Sunday, but Skylight's week runs Sunday to Saturday. One dinner no longer fit, and the meatless night fell off the end of the week. The cause was an assumption stated in two places and clear in neither. The drafts held the literal placeholders I opened with. Claude fixed a typo after showing me a draft and mentioned it only at the end, a silent edit that makes "exact text" a lie. A cooking step turned up in a field meant for family notes. And Claude doubled or 1.5x-ed four of the five recipes on its own guess that we eat more than a recipe serves. I missed it in the plan. It surfaced only when Claude listed the changed grocery lines and I questioned one: three whole chickens for one dinner. Claude owned it: it had assumed bigger appetites unprompted.

![The Edit Meal screen in the family calendar app, with an empty Instructions field and recipe steps sitting in the note field below it](/images/claude-dinner-edit-meal.png)

*An early dinner entry, with a couple of family details covered by grey boxes. The recipe steps ended up in the note field and the "Instructions" field is empty.*

None of these were exotic; any new helper would hit the same unstated assumptions.

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

The reasoning behind each line is the same. The week is stated once, as dates, because "this week" means a different Monday depending on who is reading. Recipes are "as written" because an unstated default is a decision someone else makes for you. The plan document is created first because the 3.1 version of the instructions had a template line, and Claude copied the template line verbatim into real output. And one meal goes first because a half-finished set of dinners on a wall display is the worst way this can fail.

After the fixes, five dinners went in: one meal first, then the other four. I read the whole week back from Skylight in a separate call and compared it to what I'd approved. It matched. Some of the corrections in those eight messages weren't Claude's fault at all: I wanted plain burgers instead of smash burgers, a different dessert, and one dish moved out of the week. Those are taste decisions, and nothing can make them for you.

### The wall display I photographed and the phone I should have asked about

Meal names turned out to be harder than recipes. I photographed the wall display and found that the month view clips names at around eighteen characters, so "Herb butter baked salmon" showed up as "Herb butter baked s". I shortened three names to fit, felt pleased, and reversed the decision within minutes: my family mostly reads the calendar in the phone app, not on the wall display. The app shows names in full. I had optimized for the screen I'd just photographed, not for the one people use.

That left the rule underspecified. "Keep names short" isn't an instruction a model reads the same way twice, so I gave it a target and a cap instead: aim for 25 characters, never more than 35 with a dessert. Then a second pass, this time from the person who reads it every day: the family already knows what the dish is, so the name should be the plain dish ("Baked salmon") and the descriptive version goes on the first line of the instructions. Identity goes in the field people scan, precision in the field they open.

The same photograph taught me one more thing. On the wall display the recipe link in a meal is plain text, not something you can tap, while in the phone app it's a real link. So nothing the cook needs at the stove can live only behind the link. The instructions carry the steps in short sentences with times and temperatures, and the link is a convenience.

A boring one: the standing-instructions field rejected my first version with a generic "link, formatting or a reserved phrase" error. The cause was most likely the angle brackets in my `<name>: <link>` placeholders. Swapping them for plain parentheses fixed it. If you paste text into a settings field and it complains without saying where, check for angle brackets first.

![The standing-instructions box showing 7,077 of 2,000 characters and an error that 5,077 characters are over the limit](/images/claude-dinner-instructions-limit.png)

*The full version of my rules was 7,077 characters against a 2,000 limit. A part of one line is covered by a grey box.*

![The standing-instructions box at 1,884 of 2,000 characters, with an error saying the text has a link, formatting or a reserved phrase](/images/claude-dinner-instructions-rejected.png)

*The compressed version was under the limit and still refused. Part of one line is covered by a grey box.*

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

I tested the check by breaking it on purpose. A test that only passes proves nothing, so I removed the "url" keyword and ran the tests. They still passed. That told me the tests weren't checking what I thought, so three cases were added until removing the keyword made them fail. A break that survives is a finding about the tests, not good luck.

### Full access, and a log instead of a gate

Here I overruled caution on purpose. I wanted setup to be easy for anyone trying this, and I wanted Claude to have full access instead of stopping to ask before each step. I also tested whether Claude's client would pause for a human yes before a delete. It didn't: it deleted in one call.

The risk is real. Claude could remove the wrong meal or the wrong event. But this is dinners on a family calendar, not money, and a wrong deletion costs me a minute of putting it back. So instead of a gate I asked for a record: one line for every change, with the tool, whether it was a write or a delete, the outcome and a running count, and deliberately no meal text and no IDs. There's also a cap of 60 changes and 10 deletes an hour, as a leash for a runaway loop.

The record earned its place the night I shipped it. I made three calls four seconds apart and each log line said the running count was 1. The count lived in a variable on the server, and I couldn't count on a Worker keeping variables between requests, so the cap I'd just shipped wasn't capping anything. All the tests had passed, because in a test the variable does survive. The fix was to move the counter into a small piece of storage that does persist, and the next run counted up.

![One line from the change log in the hosting dashboard: tool plan_week_meals, effect write, outcome ok, recent 1](/images/claude-dinner-change-log.png)

*One line from the change log the night I found the counter wasn't counting. No meal text, no IDs.*

Then the scheduled part. The Friday run happens on a schedule, with nobody there to say yes, so its rule is blunt: draft, post the text, stop. It never writes. ![The scheduled task list showing "Weekly dinner plan (Fridays)", every Friday at 10:47 AM](/images/claude-dinner-friday-task.png)

*The Friday task, in the list of scheduled work.*

Writes need my yes to the exact text, every time, because the text shows on devices around the house and I can't recall it from them. The first scheduled run was also the test of that rule: afterwards, the week's meals in Skylight had to be unchanged, and reading the week back is a check that can fail.

I weighed three ways to run the check. A job in a code-hosting service would need my Skylight sign-in stored as a secret in a third party's hands. A timer on the Worker has no way to reach me. A scheduled Claude task with the same read-only tools needs no new credential and posts to a channel I already read. I took the third, knowing it shares fate with the server it checks: if the server is down, a missing Thursday line is the signal.

Because Skylight's API is unofficial, a change in what it returns could break a tool without any error. The first place that would show is the unattended Friday run, so the day before there's a canary. Every Thursday a scheduled task runs five read-only checks: the frame information, the dinner category, a week of meals with details, a week of calendar events, and the list of synced calendars. It posts one line in its own channel, pass or fail, so a missing Thursday message is itself the alarm. It never writes, not even a dry run. A scheduled run can't send mail itself, because a send needs my yes in the moment, so Claude offered three weaker options and I picked the routine's own email. To turn it on, Claude recreated the task and deleted the old copy, and told me so.

![A chat in the canary channel: Claude explains the alert options, I pick email and a 9:45 AM Thursday schedule, and the first run posts "Skylight canary passed all 5 checks this morning."](/images/claude-dinner-canary.png)

*The canary's setup chat and its first one-line post, Thursday at 9:46 AM.*

The first run passed five of five. What I haven't seen yet is the failure path: the passing run sent no email, as intended, but I have not watched a real failure arrive. Until I do, that half of the canary is a plan.

## Lessons

**The technical one.** A chat keeps the tool list it fetched when it started. After I redeployed the server, a chat I'd been using kept showing the old behavior, even though the server was right. A fresh chat showed the new text. Now a stale client is my first suspect, and I verify any deploy in a new session before touching the code.

**The AI one.** Claude is very fast from a symptom to the next step. What it doesn't do is check that the evidence supports where it lands. It told me the plan document matched what was on the calendar. It told me a Friday routine would pick up a queued meal. Both sounded right, and I had checked neither. Reading the week back from Skylight in a separate call, and comparing it to the text I approved, is my job, and it is cheap. A confident sentence is not a measurement.

**The one you can swap your own project into.** State every assumption once, as a number or a date, and test it with a check that can fail. The week boundary, the portion size, the name length and the placeholder were all the same mistake: something I assumed, never wrote down, and discovered only when a real family would have read it. Whatever you hand to an agent that writes where other people can see, write down what it must never leave behind, and then break your own check to see that it fires.

Even that first week bent for a plainer reason. My wife cooked two nights I had planned for: chicken tacos, with no dessert, and spaghetti and meatballs the next evening, my birthday dinner. We'd gone out on the day itself, and what I actually wanted was spaghetti and meatballs at home. I asked Claude to move the two displaced dinners to the following week. It picked days that were clear on both calendars, showed me the exact changes, and waited for a yes. It rewrote one note, because the practice that shaped it had been a Friday-only thing, and kept the pulled pork on a weekend because the smoker needs one. Then it wrote the changes and read each one back against what I had approved. It also told me the moved meals still pointed at the old plan document, and that it would repoint them once the next run created the new one.

My verdict from my notes after that first week: not easier yet. The test was always the second week. The next Friday run was better, though I still changed things, for reasons unrelated to the rules: the boys started feeling sick on Monday and Tuesday, so I shifted meals around, I hadn't bought the ingredients for some of them, and one night we decided to cook whatever we already had, so I pulled a meal out. Overall it worked, and by my estimate (not a stopwatch) it saves me hours of looking up and planning meals. Claude also checks the plan against the calendar and flags conflicts I missed. And the plan now lives in one place, the calendar the family already uses, not a document and a calendar that drift apart.

![The Meals view in the family calendar app, filtered to dinners, from Sunday the 8th to Sunday the 15th; two nights are empty on purpose](/images/claude-dinner-week-meals.png)

*The app's Meals view, filtered to dinners: one a night, with Wednesday the 11th as today. The two empty nights are on purpose: we're out, or the kids cover dinner, and Claude leaves those alone.*

The moment I knew it worked was small. My wife mentioned that tomorrow's dinner looked good. I hadn't told her; she'd seen it on the calendar, and she was excited to try it. That reminded me I needed to go to the grocery store, and that week I made my first trip to an Asian market, for ingredients no local store carries. I'm the one cooking, and deciding what to cook is the part I hate. Planning was the problem worth automating, so that time now goes to cooking, and we've stopped eating the same handful of meals every week.

## Try it yourself

The server is open source (MIT) and unofficial: it talks to endpoints Skylight doesn't document, so it may break without notice, and the README says so plainly. If you can run a few commands, setup is covered there.

- Code and README: [github.com/dwooods/skylight-mcp](https://github.com/dwooods/skylight-mcp)
- Package: `@davidwoods/skylight-mcp` on npm
