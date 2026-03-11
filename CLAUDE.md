# YouTube Automation Pipeline

> All Claude Code sessions (lead and teammates) read this file automatically.

## Project Overview

Automated YouTube content pipeline for 3 Roman Urdu channels:
- **Motivation** — inspirational shorts for Pakistani youth
- **Cooking** — desi recipe videos
- **Hot Topics** — trending news/commentary shorts

## Available Tools (call via Bash)

All tools are Python CLI scripts. Run from project root (`~/Sites/yt-automation/`).

### TTS (Text-to-Speech)
```bash
python -m src.tools.tts --text "Aaj hum baat karenge..." --engine google --output output/motivation/2026-03-11/voice.mp3
python -m src.tools.tts --text-file script.txt --engine elevenlabs --output voice.mp3
```

### Stock Video (Pexels)
```bash
python -m src.tools.stock_video --keywords "motivation,success" --count 3 --orientation portrait --output-dir output/motivation/2026-03-11/clips/
```

### Video Assembly (FFmpeg)
```bash
python -m src.tools.video_maker \
  --clips-dir output/motivation/2026-03-11/clips/ \
  --audio output/motivation/2026-03-11/voice.mp3 \
  --subtitles output/motivation/2026-03-11/subtitles.json \
  --template-file templates/motivation.json \
  --output output/motivation/2026-03-11/final.mp4
```

### Thumbnail
```bash
python -m src.tools.thumbnail --title "Kamyabi ka Raaz" --template-file templates/motivation.json --video output/motivation/2026-03-11/final.mp4 --output output/motivation/2026-03-11/thumb.jpg
```

### Upload to YouTube
```bash
python -m src.tools.uploader upload --video final.mp4 --title "Title" --description "..." --tags "tag1,tag2" --thumbnail thumb.jpg --shorts --privacy private
```
Note: uploader has subcommands `upload` and `setup`.

## Output Structure

```
output/{category}/{YYYY-MM-DD}/
├── script.txt          # Roman Urdu script
├── subtitles.json      # Timed subtitle segments
├── voice.mp3           # TTS audio
├── clips/              # Stock video clips
├── final.mp4           # Assembled video
└── thumb.jpg           # Thumbnail
```

## Subtitle JSON Format

```json
[
  {"start": 0.0, "end": 3.5, "text": "Aaj hum baat karenge..."},
  {"start": 3.5, "end": 7.0, "text": "Kamyabi ka sabse bara raaz..."}
]
```

## Script Guidelines

- **Language:** Roman Urdu (Urdu written in English alphabet)
- **Audience:** Pakistani youth (18-35)
- **Hook:** First 3 seconds must grab attention
- **CTA:** End with "Like karein, subscribe karein!"
- **Duration:** Shorts = 45-90s, Long = 3-8min

## Templates

Category configs are in `templates/{category}.json`. They define resolution, colors, font sizes, stock video keywords, and tags.

## Video Specs

| Format | Resolution | Duration |
|--------|-----------|----------|
| Shorts | 1080x1920 | 45-90s |
| Long | 1920x1080 | 3-8min |

## Important Rules

1. Always use `python -m src.tools.{tool}` to run tools (not direct file paths)
2. Replace `{date}` with today's date in YYYY-MM-DD format
3. Create output directories before writing files
4. All uploads default to `--privacy private` for safety
5. If a tool fails, check the error and retry once with adjusted parameters
