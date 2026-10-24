---
name: proof-of-skill
description: Matches the student's own Canvas classes and projects to live jobs and internships, says which class proves each requirement, and writes resume bullets from that real coursework. Use when the student asks what jobs or internships they qualify for, which of their classes or projects help them get hired, wants resume bullets from class work, or wants new matching postings each week, even if they don't say "job search".
---

# Proof of Skill

Students do real projects in every class, but they rarely know which ones count for which job. This Skill turns
the student's Canvas coursework into a skills profile, where every skill points to the class and assignment that
proves it. It then finds live postings, explains the fit requirement by requirement, and writes resume bullets
from the student's actual work.

## When to use

- "What internships could I actually get with my classes?"
- "Which of my projects should I put on my resume for this job?"
- "Find me on-campus jobs that fit what I'm good at."
- "Is my CSE 310 project good enough for a backend internship?"
- "Send me new matches every Sunday."

This Skill is not for general study plans or for emailing professors; Cubbie's built-in Skills handle those.

## Steps

Run every command from this Skill's folder. The script needs only Python 3, no setup or keys.

### 1. Build the skills profile (first time, then when a new semester starts)

1. Run `python3 scripts/jobs.py profile show`. If it prints a profile from this semester, skip to step 2.
2. Read the student's Canvas courses, this semester and past ones. For **each** course, open its assignment list
   and read the individual assignments and projects: titles, descriptions, rubrics, and the student's own
   submissions when Canvas shows them. Also read the syllabus or course description. Course names and topics on
   their own are weak evidence; the point of this Skill is naming the actual project. If a course shows no
   assignments (common for past semesters), note it as "course only". If most courses are "course only", tell the
   student and ask them to text two or three projects they did, then add those as evidence.
   If Canvas is not connected, ask the student to connect it. If they would rather not, ask them to text their
   classes and two or three projects they're proud of, and build the profile from that.
3. Pull out concrete skills: languages, tools, methods, and things built or analyzed ("normalized a relational
   schema", "built a REST API in Flask", "ran a regression in R", "wrote a 10-page policy analysis"). Each skill
   needs at least one piece of evidence: the course, the assignment, and one line on what the student did.
   Use only what Canvas or the student showed you. A skill used once in a small exercise is "familiar", not
   "strong". Never invent a skill, tool, number or result.
4. Save it by writing this JSON to a file and running `python3 scripts/jobs.py profile save --file <that file>`:

   ```json
   {
     "major": "Computer Science", "grad": "May 2028",
     "interests": {"roles": ["backend", "data"], "types": ["internship", "on-campus"],
                   "locations": ["Phoenix", "Remote"], "degree": "bachelors"},
     "skills": [
       {"skill": "SQL and relational schema design", "level": "strong",
        "evidence": [{"course": "CSE 310", "assignment": "Project 2: Library DB",
                      "what": "Designed a 9-table schema and wrote the queries for a library system"}]}
     ]
   }
   ```

5. Text the student a short summary: their top five skills, each with the class behind it. Ask if anything is
   missing, such as a hackathon, club or job project. Add what they mention as evidence too.

### 2. Learn what they want (first time only, before the first search)

Ask only what the student hasn't already said, one question at a time, each with a default they can accept with
"yes". Ask these before searching, because they decide which postings the student is eligible for. Save the
answers in `interests`:

- Degree level and graduation month and year
- Whether they will need visa sponsorship (for example F-1, CPT or OPT). Ask plainly and without judgment; it is
  optional, and "prefer not to say" is fine.
- Roles or fields ("software, data, design, marketing, research...?")
- Types: internship, full-time after graduation, on-campus job, research position
- Locations, and whether remote is fine

### 3. Find postings

Use whichever sources fit the student's interests. Combine them if several fit.

- **Tech, data, product, hardware and quant internships and new-grad roles**: run

  ```bash
  python3 scripts/jobs.py search --type <internship|new-grad|all> --keywords "<role words>" --location "<place>" --location "Remote" --degree <bachelors|masters|phd>
  ```

  Use role words that appear in job titles for `--keywords` ("software, backend, data analyst, machine learning,
  embedded, product"), not skill words: requirements are checked in the next step. Add `--term "Summer 2027"` for
  a specific internship term and `--days 14` for new postings only. The search skips postings already shown to the
  student. Each result is an 8-character id, the title, company, location, term, posting date, and the link.
- **On-campus jobs**: search the web for the student's school's student employment page, and its Handshake or
  Workday listings if they are public. Open them in the browser if needed. If the site requires the student to
  sign in, ask them to sign in in the browser, or to take over the browser for that step.
- **Other fields** (business, design, health, education, arts, policy...) and **research positions**: search the
  web for current postings that fit the student's roles and location. Research positions include undergraduate
  research programs, lab openings on department pages, and REU programs. Use only postings with a live link and
  a visible deadline or posting date.

Shortlist up to eight postings from the titles.

### 4. Check the fit

1. Read the requirements: `python3 scripts/jobs.py details <id> <id> ...` (up to 5 at a time, ids or links). If it
   says a posting is closed, drop it. If it says to open the posting in the browser, read it there.
2. Check the eligibility rules first: degree level, graduation window, minimum GPA, work authorization,
   citizenship or sponsorship, and where remote work is allowed. Drop a posting the student clearly doesn't
   qualify for. If a rule depends on something you don't know (such as GPA), keep the posting and say so in one
   line.
3. Compare every must-have requirement with the profile. Mark each requirement as covered (name the course **and**
   the assignment), partly covered (the course only, or one small exercise), or missing proof.
4. Rank postings by how many must-haves are covered, then by deadline and posting date. Leave out postings where
   the student meets fewer than half of the must-haves, unless nothing better turned up. If so, say that the
   match is a stretch.

### 5. Text the top three

Send at most three postings, **one message per posting**, in this shape:

```text
Backend Intern, Example Payments (Phoenix or remote)
https://example.com/jobs/123
Why you fit: REST API from CSE 340 Project 3, SQL from CSE 310 Project 2
Missing proof: Docker (not in any class yet)
Heads up: needs a 3.0 GPA
```

Every posting includes its link, on its own line; if you don't have a live link, leave the posting out. Use the
"Heads up" line only for an eligibility rule the student should check. Before the postings, send one line saying
what you searched for; after them, one line with your pick.

Then ask "Want resume bullets for any of these?" When the student has seen the postings, run
`python3 scripts/jobs.py shown <id> <id> ...` so later searches skip them. If the student wants more than three,
send the next three; for ten or more, make a short PDF or sheet instead.

### 6. Resume bullets (when asked)

For the posting the student picks, write two to four bullets:

- Each bullet is built from one assignment in the profile: start with a strong verb, say what was built or
  analyzed and with what, and echo the posting's own words where they honestly apply.
- Add a course tag only when it helps ("Course project, CSE 310").
- Use numbers only if they came from the coursework (tables, users, records, accuracy). Never make one up.
- After the bullets, add one line saying which requirement each bullet covers.

A cover letter is only written when the student asks, as a draft for them to edit. Never apply, submit a form or
email a recruiter for the student. If they want help applying, open the application in the browser and hand it to
them.

### 7. Weekly matches (offer once)

After the first results, offer a weekly check-in: "Want new matches every Sunday at 6 pm?" Create it only after
the student agrees, at the time and frequency they choose. Word it so it works days later: "Proof of Skill weekly
matches: run `python3 scripts/jobs.py profile show`, search for postings from the last 7 days that fit the saved
interests, check the fit, and text the top three new ones. If there are none, send one line saying so." If the
student says a posting isn't a fit, ask why in a few words, and update `interests` so next week's matches improve.

## Replies

Keep each text to a few short lines, plain text, no Markdown. One posting per message. Put every link on its own
line. Name the real class and assignment every time a fit is claimed; that evidence is what makes the Skill
worth using. Be honest about gaps. Suggest how to close one only when a class the student is already taking, or a
quick project, really would.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Bad arguments or profile JSON | Fix the command or the JSON and run it again |
| 3 | No profile saved | Build it (step 1) |
| 4 | A job list or posting couldn't be downloaded | Say the job feed is not reachable right now and use web search instead |
| 5 | Posting closed or unreadable | Drop it if closed; otherwise read it in the browser |

When a search finds nothing, say so in one line and offer to widen it: more locations, remote, or another type.
Never send a link you haven't seen in a search result or on a live page, and never guess a deadline.

## Privacy

The profile stays on the student's own drive, in `~/.config/proof-of-skill/`. Nothing is sent anywhere except
the job sites themselves. If the student asks, show them the profile, or delete it.
