# Proof of Skill

A [Cubbie](https://cubbie.ai) Skill that answers a question every student has: *which of my classes actually
helps me get hired?*

Proof of Skill reads your Canvas courses and assignments and builds a skills profile, where every skill points to
the class and project that proves it. Then it finds live internships, new-grad roles, on-campus jobs and research
openings. For each one, it texts you why you fit, naming the real class and assignment, plus the one gap to close.
Ask, and it writes resume bullets from the work you actually did.

```text
Software Engineering Intern, Zillow (Seattle or remote)
https://zillow.wd5.myworkdayjobs.com/...
Why you fit: REST API from CSE 340 Project 3, SQL from CSE 310 Project 2
Gap: Docker (not in any class yet)
```

## Install

Text this link to Cubbie:

```text
https://github.com/shaashvat01/proof-of-skill
```

Cubbie asks before it fetches the Skill; reply "yes". Then try: "What internships could I get with my classes?"

## How it works

- **Coursework**: Cubbie reads your Canvas courses through its own Canvas connection. Your profile stays on your
  Cubbie drive (`~/.config/proof-of-skill/`).
- **Jobs**: `scripts/jobs.py` searches the public [SimplifyJobs](https://github.com/SimplifyJobs) internship and
  new-grad lists, which are updated daily. It reads each posting's requirements from the public Greenhouse, Lever,
  Ashby or Workday job APIs. No keys and no sign-in. On-campus jobs and other fields come from Cubbie's web search
  and browser.
- **Your yes**: it never applies or emails anyone for you.

It's also a standard [Agent Skill](https://agentskills.io), so it works in Claude Code and Codex too.

```bash
python3 scripts/jobs.py search --sample           # offline demo
python3 scripts/jobs.py search --type internship --keywords "software,data" --location Remote
python3 scripts/jobs.py details <id>               # a posting's requirements
```

Built for the [Cubbie Hackathon](https://hackathon.cubbie.ai).
