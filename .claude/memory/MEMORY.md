# YT Automation — Session Memory

## Current State
- Project scaffolded and working at ~/Sites/yt-automation/
- GitHub: https://github.com/muhammadrao1988/yt-automation
- Python 3.10.12 (not 3.12), venv at .venv/
- FFmpeg 4.4.2 installed

## API Keys (all configured in .env)
- Pexels: working
- ElevenLabs: working but free tier blocks library/shared voices via API
- YouTube OAuth: working, token at .youtube_token.json
- YouTube channel NOT verified for custom thumbnails

## TTS Decision
- **Edge TTS (hi-IN-MadhurNeural)** selected as best free voice for Roman Urdu
- ElevenLabs default Adam = English accent reading Urdu (bad)
- ElevenLabs library voices (Raqib etc) = paid plan required ($5/mo)
- Google TTS = robotic, rejected
- Edge TTS Madhur = best free option, user approved
- edge-tts package installed, integrated in src/tools/tts.py (engine="edge")

## Videos Uploaded
1. Motivation: https://www.youtube.com/watch?v=uHGitDxcxOc (ElevenLabs voice, English accent)
2. Cooking: https://www.youtube.com/watch?v=WkGyc2H1Cio (Edge TTS Madhur)

## Quality Issues Identified
- Video quality not professional enough — needs improvement
- Stock video clips from Pexels are generic, not food/topic-specific enough
- Subtitles use default system font (no Urdu-compatible font installed)
- Thumbnails use default font (need Noto Nastaliq Urdu or similar)
- No background music in videos yet
- Video transitions are basic (hard cuts between clips)

## Key Technical Learnings
- FFmpeg `loop` filter with 1080x1920@60fps = OOM, took 45min+ before kill
- Concat demuxer fails with mixed codecs/framerates
- Solution: 3-step approach (normalize to .ts → concat protocol → final assembly)
- Tool CLI: single-command tools don't need subcommand names
- Tools need dotenv loading since teammates call via Bash
- client_secret.json (singular, not plural) for YouTube OAuth

## Next Steps to Improve Quality
1. Better stock footage — consider category-specific Pexels keywords or AI-generated visuals
2. Add background music (lofi for motivation, upbeat for cooking)
3. Install Urdu font (Noto Nastaliq Urdu) for subtitles and thumbnails
4. Add transitions (crossfade between clips)
5. Consider text animations / zoom effects on subtitles
6. Improve script quality — more natural, conversational Roman Urdu
7. Consider using Canva API or Remotion for more polished video output
