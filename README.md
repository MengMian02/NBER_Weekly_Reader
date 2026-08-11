# NBER Weekly Reader

NBER Weekly Reader sends a personalized weekly email containing open-access NBER Working Papers. It is designed for readers who enjoy NBER's weekly discovery format but prefer papers that are already outside the 18-month access window.

The application uses NBER's official weekly metadata and does not bypass any access restriction.

## What it does

Each issue contains 13 papers:

- 10 papers from the latest NBER release batch that has crossed the 18-month open-access threshold;
- 3 highly relevant papers selected from the older archive.

Papers are ranked using preferred topics, NBER program codes, authors, and example paper titles. Successfully delivered papers are recorded locally so they are not recommended again.

The email includes:

- a topic-distribution summary showing the main subjects covered in the issue;
- a clickable table of contents;
- titles, authors, release dates, and recommendation reasons;
- abstract excerpts;
- direct links to the free NBER PDF and abstract page.

## Application files

The production application is [`nber_digest.py`](nber_digest.py). The other files provide configuration and Windows automation:

- `config.example.json` — safe configuration template;
- `run_preview.bat` — builds an HTML preview without sending email;
- `run_send.bat` — refreshes metadata and sends the weekly email;
- `install_startup_task.ps1` — creates a per-user Windows startup shortcut;
- `.gitignore` — prevents private configuration, history, previews, and cached data from being committed.

## Requirements

- Python 3.10 or later;
- internet access to download NBER metadata;
- an SMTP-enabled email account. Gmail is supported through an app password.

The program uses only the Python standard library.

## Setup

1. Copy `config.example.json` to `config.json`.
2. Edit `config.json` with your interests and email settings.
3. If you use Gmail, enable two-step verification and create an app password. Do not use your normal Google account password.
4. Store the app password in an environment variable:

   ```powershell
   setx NBER_SMTP_PASSWORD "your-app-password"
   ```

5. Sign out of Windows and sign in again so the new environment variable is available.

Never put the app password directly in `config.json`.

## Preview an issue

Double-click `run_preview.bat`, or run:

```powershell
python nber_digest.py --config config.json --refresh
```

This creates `preview.html` without sending an email or updating the delivery history.

## Send an issue

```powershell
python nber_digest.py --config config.json --refresh --send
```

The delivery history is updated only after the email is sent successfully. The application also prevents more than one delivery in the same ISO calendar week unless `--force` is supplied.

## Run automatically on Windows

After configuring the Gmail app password, run `install_startup_task.ps1` in PowerShell. It creates a shortcut named **NBER Weekly Reader** in the current user's Windows Startup folder. This does not require administrator access.

Because the application enforces one delivery per calendar week, restarting or signing in multiple times during the same week will not send duplicate issues. The computer must be on and connected to the internet when the task runs.

To disable automatic startup, press `Win + R`, enter `shell:startup`, and delete the **NBER Weekly Reader** shortcut. This does not remove the application, configuration, or delivery history.

The installer intentionally uses the per-user Startup folder instead of Windows Task Scheduler. This avoids administrator requirements and `0x80070005 Access Denied` errors on systems where standard users cannot register scheduled tasks.

## Personalize recommendations

Edit the `preferences` section in `config.json`:

- `topics` maps English phrases to weights; larger numbers mean stronger preferences;
- `avoid_topics` lowers the score of papers containing unwanted phrases;
- `programs` contains NBER program codes such as `ME`, `IFM`, `AP`, and `EFG`;
- `authors` prioritizes selected researchers;
- `liked_papers` learns vocabulary from NBER Working Paper IDs such as `w12345`;
- `liked_titles` learns from paper titles, including papers that are not yet NBER Working Papers.

## Privacy and repository safety

The following files and directories are intentionally excluded from Git:

- `config.json`, which may contain a personal email address;
- `state.json`, which contains delivery history;
- `preview.html`;
- downloaded metadata under `data/`;
- Python bytecode and cache directories.

SMTP credentials are read only from the `NBER_SMTP_PASSWORD` environment variable.

## Data source

Metadata comes from the official [NBER Working Papers and Chapters Metadata](https://www.nber.org/research/data/nber-working-papers-and-chapters-metadata) dataset. Paper and PDF links point directly to NBER.

## Roadmap

Planned and exploratory improvements are tracked as GitHub Issues. Current ideas include:

- [reader feedback controls and preference learning](https://github.com/MengMian02/NBER_Weekly_Reader/issues/1);
- [stronger semantic similarity and topic-diversity ranking](https://github.com/MengMian02/NBER_Weekly_Reader/issues/2);
- [structured `Method`, `Data`, and `Why it matters` summaries](https://github.com/MengMian02/NBER_Weekly_Reader/issues/3);
- [PDF availability checks, retry handling, and run logs](https://github.com/MengMian02/NBER_Weekly_Reader/issues/4);
- [an interactive setup wizard](https://github.com/MengMian02/NBER_Weekly_Reader/issues/5);
- [a searchable archive of previously delivered issues](https://github.com/MengMian02/NBER_Weekly_Reader/issues/6).

Items in this list describe possible future work rather than committed release dates. Completed features are documented in the main sections above.

