# Lunch/Coffee sign-up reminder

Sends a reminder email the night before each Class Lunch / Class Coffee,
to everyone signed up, CC'ing the professor and you. Runs on GitHub
Actions, no server to maintain.

## How it works

- Runs **hourly** via GitHub Actions cron (`0 * * * *`, UTC).
- `main.py` checks whether it's currently the 5 PM Pacific hour (using
  `zoneinfo`, so it's automatically correct across PST/PDT) and no-ops
  every other hour. This avoids the classic bug of hardcoding a UTC
  cron time that's only right for half the year.
- If it's the right hour, it downloads the Google Sheet as `.xlsx`,
  parses the "Class Lunch" and "Class Coffee" tabs (ignores "Monday
  Snacks" and any other tabs), finds events happening **tomorrow**, and
  emails each event's attendees (Cc: professor + you).
- If nobody's signed up for an event happening tomorrow, it still
  emails just the professor + you with a heads-up (no attendee `To:`).
- If a location is still `TBD`, the email says so.

## One-time setup

### 1. Google Sheets access (read-only)

1. In Google Cloud Console, create a project (or reuse one) and enable
   the **Google Sheets API**.
2. Create a **Service Account**, then create a JSON key for it and
   download it.
3. Open the sign-up Google Sheet, click **Share**, and share it with
   the service account's email (looks like
   `something@project-id.iam.gserviceaccount.com`) as **Viewer**.
4. Copy the Sheet ID from its URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`

### 2. Gmail App Password

1. Enable 2-Step Verification on the sending Gmail account, if not
   already on.
2. Go to <https://myaccount.google.com/apppasswords> and generate an
   app password (name it e.g. "lunch-coffee-notifier").
3. Use that 16-character password as `SMTP_PASSWORD` — not your normal
   Gmail password.

### 3. GitHub repo secrets

In the repo: **Settings → Secrets and variables → Actions → New
repository secret**. Add:

| Secret | Value |
|---|---|
| `GOOGLE_SHEET_ID` | the Sheet ID from step 1.4 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | the *entire contents* of the service account JSON key file, pasted as-is |
| `SMTP_USER` | the Gmail address sending the reminders |
| `SMTP_PASSWORD` | the app password from step 2 |
| `PROFESSOR_EMAIL` | professor's email (always CC'd) |
| `DEBUG_EMAIL` | your email (always CC'd) |

### 4. Enable the workflow

Push this repo to GitHub. The workflow at
`.github/workflows/notify.yml` starts running hourly automatically.
You can also trigger it manually from the **Actions** tab
("Run workflow") — check **dry_run** to preview without sending, or
**force** to bypass the 5 PM Pacific gate for testing at any hour.

## Local testing

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in real values
export $(grep -v '^#' .env | xargs)
python main.py --dry-run --force
```

`--dry-run` prints the emails it *would* send instead of calling
SMTP. `--force` bypasses the "is it 5PM Pacific right now" gate so you
can test at any time of day. Use them together for a safe local check.

## Sheet format assumptions

Each relevant tab (`Class Lunch`, `Class Coffee`) is read as a stack of
blocks, not a normal table:

```
<date header, optionally "(Location)" or "(TBD)">
Name              Email Address
<attendee name>   <attendee email>
...
<blank row>
<next date header>
...
```

- Dates have no year in the sheet; the script infers the nearest
  upcoming occurrence of that month/day relative to today.
- A header without a parenthetical, or with `(TBD)`, is treated as
  "location unknown" and the email says so.
- Any other tab (e.g. "Monday Snacks") is ignored — only tabs named
  exactly `Class Lunch` / `Class Coffee` are read. If those tabs get
  renamed, update `RELEVANT_TABS` in `sheet_parser.py`.

## Known limitations / things to revisit

- **Renamed/reordered tabs or a changed block format** will break
  parsing silently-ish (it'll just find 0 events, not crash) — worth
  glancing at Action run logs occasionally, especially early in the
  semester.
- **No dedup guard**: if you manually re-run the workflow the same day
  it already sent, it will send again. Not an issue for the hourly
  schedule since each hour only fires once, but worth knowing if you
  use `workflow_dispatch` for testing near 5PM.
- **GitHub Actions free-tier scheduled workflows** can be delayed by a
  few minutes during high load, and are auto-disabled after **60 days
  of repo inactivity** (any commit resets this) — worth a calendar
  reminder to check in on it partway through the semester.
