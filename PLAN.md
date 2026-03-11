# YouTube Automation Pipeline — Claude Code Agent Teams Architecture

## Context
Build a fully automated YouTube content pipeline for 3 channels (Motivation, Cooking, Hot Topics) in Roman Urdu. Uses **Claude Code Agent Teams** (experimental feature) — the lead session orchestrates 3 category teammates that each research, write scripts, and produce videos. Playwright MCP for web research, FFmpeg for video generation. Zero cost infrastructure — runs locally on Ubuntu.

**Location:** `~/Sites/yt-automation/`
**Plan also copied to:** `~/Sites/yt-automation/PLAN.md`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  YOU (CLI command)                        │
│          yt-auto generate [category|all]                  │
└──────────────────────┬──────────────────────────────────┘
                       │ spawns claude with team prompt
                       ▼
┌─────────────────────────────────────────────────────────┐
│              TEAM LEAD (Claude Code session)              │
│  - Creates shared task list                               │
│  - Spawns 3 category teammates                            │
│  - Monitors progress, synthesizes results                 │
│  - Handles errors/retries                                 │
├────────────┬────────────────┬───────────────────────────┤
│            │                │                             │
▼            ▼                ▼                             │
┌──────────┐ ┌────────────┐ ┌─────────────┐               │
│MOTIVATION│ │  COOKING   │ │ HOT TOPICS  │  ← Teammates  │
│TEAMMATE  │ │ TEAMMATE   │ │  TEAMMATE   │  (parallel    │
│(claude)  │ │ (claude)   │ │  (claude)   │   sessions)   │
└────┬─────┘ └─────┬──────┘ └──────┬──────┘               │
     │             │               │                        │
     ▼             ▼               ▼                        │
┌─────────────────────────────────────────────┐            │
│         SHARED PYTHON TOOLS                  │            │
│  (each teammate calls via Bash tool)         │            │
│  tts.py │ stock_video.py │ video_maker.py    │            │
│  thumbnail.py │ uploader.py                  │            │
└─────────────────────────────────────────────┘            │
│                                                           │
│  Research: Playwright MCP (each teammate has access)      │
│  Scripts:  Each teammate writes directly (Claude is brain)│
└─────────────────────────────────────────────────────────┘
```

**How it works:**
1. CLI script runs `claude` with a team-creation prompt
2. Lead creates a shared task list and spawns 3 teammates (motivation, cooking, hot_topics)
3. Each teammate is a full Claude Code session with Playwright MCP + Bash access
4. Teammates research via Playwright MCP, write scripts directly, call Python tools via Bash
5. Teammates communicate findings to each other (e.g., hot topics teammate shares trending info)
6. Lead monitors, handles errors, and reports results when done

---

## Project Structure

```
~/Sites/yt-automation/
├── pyproject.toml              # Python dependencies
├── .env                        # API keys (YouTube, Pexels, ElevenLabs)
├── .env.example
├── CLAUDE.md                   # Project-level instructions for ALL teammates
├── PLAN.md                     # This plan
│
├── prompts/                    # Prompts for team lead and teammates
│   ├── lead.md                 # Team lead orchestration prompt
│   ├── motivation.md           # Motivation teammate spawn prompt
│   ├── cooking.md              # Cooking teammate spawn prompt
│   └── hot_topics.md           # Hot topics teammate spawn prompt
│
├── src/
│   ├── __init__.py
│   ├── cli.py                  # CLI entry — spawns claude team lead
│   ├── config.py               # Settings from .env (pydantic-settings)
│   │
│   └── tools/                  # Python tools (teammates call via Bash)
│       ├── __init__.py
│       ├── tts.py              # Google TTS + ElevenLabs
│       ├── stock_video.py      # Pexels API video fetcher
│       ├── video_maker.py      # FFmpeg video assembly
│       ├── thumbnail.py        # Pillow thumbnail generator
│       └── uploader.py         # YouTube Data API uploader
│
├── templates/                  # Video style configs per category
│   ├── motivation.json
│   ├── cooking.json
│   └── hot_topics.json
│
├── assets/
│   ├── fonts/                  # Urdu-compatible fonts
│   ├── music/                  # Royalty-free background tracks
│   └── overlays/               # Logo, subscribe button
│
├── output/                     # Generated videos (gitignored)
│   ├── motivation/
│   ├── cooking/
│   └── hot_topics/
│
└── tests/
    ├── test_tts.py
    ├── test_video_maker.py
    └── test_uploader.py
```

---

## Implementation Plan

### Step 1: Project Setup
**Files:** `pyproject.toml`, `.env.example`, `src/config.py`, `CLAUDE.md`, `.gitignore`

- Create full directory structure
- `pyproject.toml` dependencies:
  - `typer` — CLI framework
  - `pydantic-settings` — config from .env
  - `gtts` — Google TTS (free, no API key)
  - `elevenlabs` — ElevenLabs TTS (optional, 10K chars/mo free)
  - `httpx` — Pexels API
  - `google-api-python-client` + `google-auth-oauthlib` — YouTube upload
  - `Pillow` — thumbnail generation
- `.env.example` with required keys
- `CLAUDE.md` — project instructions that ALL teammates auto-load:
  - Available tools and how to call them
  - Output directory structure
  - Script format (Roman Urdu, subtitle JSON format)
  - Video specs (resolution, duration)
- Enable agent teams: add `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` to settings
- `.gitignore` — output/, .env, .youtube_token.json

### Step 2: Python Tools Layer (teammates call via Bash)
**Files:** `src/tools/tts.py`, `src/tools/stock_video.py`, `src/tools/video_maker.py`, `src/tools/thumbnail.py`, `src/tools/uploader.py`

Each tool is a standalone CLI script:

**2a. `src/tools/tts.py`**
```bash
python src/tools/tts.py --text "Aaj hum baat karenge..." --engine google --output output/motivation/2026-03-11/voice.mp3
python src/tools/tts.py --text-file script.txt --engine elevenlabs --output voice.mp3
```
- `gtts` for Google (free, no key)
- `elevenlabs` for premium (optional)
- Accepts text or text-file input

**2b. `src/tools/stock_video.py`**
```bash
python src/tools/stock_video.py --keywords "motivation,success,pakistan" --count 3 --orientation portrait --output-dir output/motivation/2026-03-11/clips/
```
- Pexels API (free key from pexels.com)
- Downloads matching stock videos
- Filters by orientation (portrait=shorts, landscape=long)

**2c. `src/tools/video_maker.py`**
```bash
python src/tools/video_maker.py \
  --clips-dir output/motivation/2026-03-11/clips/ \
  --audio output/motivation/2026-03-11/voice.mp3 \
  --subtitles output/motivation/2026-03-11/subtitles.json \
  --template templates/motivation.json \
  --music assets/music/lofi-01.mp3 \
  --output output/motivation/2026-03-11/final.mp4
```
- FFmpeg subprocess: clips + voice + subtitles + background music
- Crossfade between clips, burn subtitles with outline
- 1080x1920 shorts / 1920x1080 long format

**2d. `src/tools/thumbnail.py`**
```bash
python src/tools/thumbnail.py \
  --title "Kamyabi ka Raaz" \
  --template templates/motivation.json \
  --video output/motivation/2026-03-11/final.mp4 \
  --output output/motivation/2026-03-11/thumb.jpg
```
- Extracts frame from video, bold text overlay with Urdu font

**2e. `src/tools/uploader.py`**
```bash
python src/tools/uploader.py \
  --video output/motivation/2026-03-11/final.mp4 \
  --title "Kamyabi ka Raaz | Motivation" \
  --description "..." \
  --tags "motivation,urdu,pakistan" \
  --thumbnail output/motivation/2026-03-11/thumb.jpg \
  --shorts
```
- YouTube Data API v3 with OAuth2
- One-time setup stores token in `.youtube_token.json`

### Step 3: Team Prompts
**Files:** `prompts/lead.md`, `prompts/motivation.md`, `prompts/cooking.md`, `prompts/hot_topics.md`

**3a. `prompts/lead.md` — Team Lead Prompt**
```
You are the lead of a YouTube content generation team. Your job:

1. Create a shared task list with tasks for each category
2. Spawn 3 teammates: motivation, cooking, hot_topics
3. Each teammate gets 5-6 tasks: research → script → voice → video → thumbnail → upload
4. Monitor progress, handle any failures
5. When all teammates finish, report results (video URLs, any errors)

Spawn prompts are in prompts/ directory. Use Sonnet for teammates to save tokens.
```

**3b. `prompts/motivation.md` — Motivation Teammate**
```
You are a Pakistani motivational content creator for youth. Language: Roman Urdu.

YOUR WORKFLOW:
1. RESEARCH: Use Playwright MCP to browse:
   - Google "motivational quotes Urdu 2026"
   - YouTube trending motivation Pakistan
   - Islamic wisdom, success stories
   Pick the best trending topic.

2. WRITE SCRIPT: Create a Roman Urdu motivational script.
   Save to output/motivation/{date}/script.txt
   Save subtitle segments to output/motivation/{date}/subtitles.json
   Format: [{"start": 0.0, "end": 3.5, "text": "Aaj hum baat karenge..."}, ...]

3. GENERATE VOICE: Run:
   python src/tools/tts.py --text-file output/motivation/{date}/script.txt --engine google --output output/motivation/{date}/voice.mp3

4. FETCH STOCK VIDEO: Run:
   python src/tools/stock_video.py --keywords "<from research>" --count 4 --orientation portrait --output-dir output/motivation/{date}/clips/

5. ASSEMBLE VIDEO: Run:
   python src/tools/video_maker.py --clips-dir output/motivation/{date}/clips/ --audio output/motivation/{date}/voice.mp3 --subtitles output/motivation/{date}/subtitles.json --template templates/motivation.json --output output/motivation/{date}/final.mp4

6. THUMBNAIL: Run:
   python src/tools/thumbnail.py --title "<video title>" --template templates/motivation.json --video output/motivation/{date}/final.mp4 --output output/motivation/{date}/thumb.jpg

7. UPLOAD: Run:
   python src/tools/uploader.py --video output/motivation/{date}/final.mp4 --title "<title>" --description "<desc>" --tags "motivation,urdu" --thumbnail output/motivation/{date}/thumb.jpg --shorts

Report the YouTube URL back to the lead when done.
```

**3c. `prompts/cooking.md`** — Same structure, different persona:
- Research: trending Pakistani recipes, seasonal foods, viral cooking
- Script: recipe with ingredients + steps
- Keywords: food-related stock footage

**3d. `prompts/hot_topics.md`** — Same structure, different persona:
- Research: Twitter/X Pakistan, Google Trends PK, YouTube Trending PK, Reddit r/pakistan, Dawn/Geo/ARY news
- Script: news-anchor style factual summary
- Keywords: news/current events footage

### Step 4: CLI Orchestrator
**File:** `src/cli.py`

```bash
# Generate all (spawns team of 3)
yt-auto generate all

# Generate single category (spawns team of 1)
yt-auto generate motivation
yt-auto generate cooking --format long
yt-auto generate hot-topics

# Research only
yt-auto research hot-topics

# Manual upload
yt-auto upload output/motivation/2026-03-11/final.mp4

# YouTube OAuth setup
yt-auto setup
```

Under the hood, `generate all` does:
```python
import subprocess
prompt = open("prompts/lead.md").read()
subprocess.run([
    "claude",
    "--print",  # or interactive
    "--prompt", prompt,
    "--allowedTools", "Bash,Read,Write,Glob,Grep,Agent",
])
```

The lead then uses Claude Code's built-in team functionality to spawn teammates.

### Step 5: Templates & Assets
**Files:** `templates/*.json`, download fonts

- `templates/motivation.json`: dark gradient bg, white bold text, lofi music, 60s shorts / 3min long
- `templates/cooking.json`: warm tones, recipe card overlay, upbeat music, 5-8min
- `templates/hot_topics.json`: news-style red/white, ticker font, urgent music, 60-90s
- Download Noto Sans Urdu font (Google Fonts, free)
- Include 2-3 royalty-free music tracks

### Step 6: Settings & Integration
**Files:** Claude Code settings

- Enable agent teams in settings:
  ```json
  { "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
  ```
- Ensure Playwright MCP is available for all teammates
- Set teammate mode to `in-process` (default, works in any terminal)

---

## Teammate Flow (per video)

```
Teammate (e.g., Motivation)
│
├─ 1. RESEARCH (Playwright MCP — built into Claude Code)
│     Browse Google Trends, YouTube, social media
│     Pick best trending topic
│     Message lead: "Researching: <topic>"
│
├─ 2. WRITE SCRIPT (Claude writes directly)
│     Roman Urdu script + subtitle JSON + metadata
│     Save to output/{category}/{date}/
│
├─ 3. GENERATE VOICE (Bash → python src/tools/tts.py)
│     Script → audio file
│
├─ 4. FETCH STOCK VIDEO (Bash → python src/tools/stock_video.py)
│     Keywords → downloaded clips from Pexels
│
├─ 5. ASSEMBLE VIDEO (Bash → python src/tools/video_maker.py)
│     FFmpeg: clips + voice + subtitles + music → final.mp4
│
├─ 6. THUMBNAIL (Bash → python src/tools/thumbnail.py)
│     Extract frame + text overlay → thumb.jpg
│
├─ 7. UPLOAD (Bash → python src/tools/uploader.py)
│     Upload to YouTube → get URL
│
└─ 8. REPORT (Message to lead)
      "Done! Video URL: https://youtube.com/..."
      Mark task as completed
```

---

## Dependencies

| Package | Purpose | Cost |
|---------|---------|------|
| Claude Code CLI | Agent teams runtime + AI + Playwright MCP | Your existing subscription |
| `gtts` | Google Text-to-Speech | Free, no API key |
| `elevenlabs` | Premium TTS (optional) | 10K chars/mo free |
| `httpx` | Pexels API calls | Free |
| `Pillow` | Thumbnails | Free |
| `google-api-python-client` | YouTube upload | Free |
| `typer` | CLI framework | Free |
| `pydantic-settings` | Config | Free |
| FFmpeg (system) | Video assembly | Free |

---

## API Keys Needed (.env)

```
PEXELS_API_KEY=            # Free at pexels.com/api
ELEVENLABS_API_KEY=        # Free at elevenlabs.io (optional)
YOUTUBE_CLIENT_ID=         # Google Cloud Console (free)
YOUTUBE_CLIENT_SECRET=     # Google Cloud Console (free)
```

---

## Scheduling

- **Manual:** `yt-auto generate all`
- **Automated:** Claude Code `/loop 12h yt-auto generate all`

---

## Build Order

1. **Step 1** — Project setup, pyproject.toml, config, CLAUDE.md, .gitignore
2. **Step 2a** — TTS tool
3. **Step 2b** — Stock video tool
4. **Step 2c** — Video maker tool
5. **Step 2d** — Thumbnail tool
6. **Step 2e** — Uploader tool
7. **Step 3** — Team prompts (lead + 3 teammates)
8. **Step 4** — CLI orchestrator
9. **Step 5** — Templates and assets
10. **Step 6** — Settings, enable agent teams, end-to-end test

---

## Verification

1. Test each Python tool independently:
   - `python src/tools/tts.py --text "Test" --engine google --output test.mp3`
   - `python src/tools/stock_video.py --keywords "nature" --count 1 --output-dir /tmp/test/`
   - `python src/tools/video_maker.py` with test inputs
2. Test single teammate: `yt-auto generate motivation --dry-run`
3. Check output files in `output/motivation/{date}/`
4. Test full team: `yt-auto generate all --dry-run`
5. Test upload: `yt-auto upload output/motivation/{date}/final.mp4`
6. Verify YouTube video appears correctly
