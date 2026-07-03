# What We're Building Next (Plain English)

*This document explains the next security improvement to the EAM SagemCom project in everyday language — no technical background needed.*

## The short version

Every time someone changes the code and saves it to our shared project (this is called a "push" or "commit"), a robot automatically checks the change for problems before it's allowed in. We already have two of these automatic checks running. We're adding a third one.

## What checks do we already have?

1. **"Did someone accidentally leak a password?"** — If a developer accidentally saves a real password, API key, or database login into the code, this check catches it and blocks the change. Think of it like a metal detector at security — it scans everything going through and stops anything that looks like a secret.

2. **"Are we using outdated, unsafe building blocks?"** — Our software is built partly from other people's free code libraries (like using pre-made parts instead of building everything from scratch). Sometimes those pre-made parts get discovered to have security holes after the fact. This check looks up every part we use against a public list of known problems and blocks anything dangerous.

Both of these already work and are turned on.

## What are we adding now?

**"Did the code we wrote ourselves introduce a security bug?"**

The two checks above only look at passwords and borrowed code. Neither one looks at the actual logic our own developers write. That's the gap.

Example of the kind of thing this catches: imagine a form on the website where someone can search for a machine by typing its name. If the code isn't written carefully, someone could type something malicious instead of a machine name and trick the database into giving up information it shouldn't, or even deleting data. This is a well-known category of attack (it has a name — "SQL injection" — but you don't need to remember that).

This new check is a program that reads through all of our own code and looks for risky patterns like that — before the code ever reaches customers. It's like a proofreader, but instead of catching typos, it catches dangerous sentence structures.

## How thorough are we being?

We're running this check **three different ways at once**, each catching slightly different things:

1. A general-purpose scan that automatically adapts to whatever kind of code it's looking at.
2. A scan using a specific, well-known checklist of the 10 most common ways websites get hacked (an industry-standard list security experts maintain).
3. A scan using rules we write ourselves, specifically tailored to the patterns and mistakes that matter most for *our* project.

Running all three costs a bit more time on every check, but gives the widest safety net.

## Where does it check?

Everywhere our own code lives:
- The customer-facing website (frontend)
- The main server that runs the business logic (backend)
- The machine-learning service that predicts failures
- The AI assistant / chat service

Two of these (the ML service and the AI assistant) weren't being checked by anything before — this closes that gap too.

## What happens if it finds something?

- **Serious issue** → the change is blocked until a developer fixes it or explains why it's actually safe (with a written note, so there's a record of the decision).
- **Minor/informational issue** → it gets logged and shown, but doesn't block anything. Developers can review it later.

## What does this mean for the business?

- Security problems get caught **before** they reach production, not after a customer or attacker finds them.
- It's fully automatic — no one has to remember to run a manual check.
- It creates a paper trail: every security decision (fix it or explicitly accept it) is recorded in the code history.
- It's free — no paid tool, no new subscription. Just automation added to the checks we already have.

## What's the catch?

The very first time we turn this on, it's likely to flag a bunch of things at once, because nobody has ever looked for these patterns in the existing code before. That's expected and normal — think of it like the first deep-clean of a house that's never had one. After that first pass, it stays clean going forward with much less noise.

---

*For the technical version of this plan (exact tools, configuration, file names), see the engineering spec in `docs/superpowers/specs/`.*
