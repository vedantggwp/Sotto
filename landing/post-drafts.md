# Sotto — Post Drafts

## LinkedIn

I got tired of every voice tool sending my audio to someone else's server.

So I built Sotto. It's a macOS app that gives you push-to-talk dictation and 30+ voice commands, all running locally on your machine. You press a hotkey, speak, and either text appears at your cursor or a system command fires. No cloud. No API calls. No audio ever leaves your Mac.

The architecture was the interesting part. Tauri v2 handles the Rust shell and window management. React renders a minimal floating pill that shows your recording state and a live waveform. A Python sidecar running faster-whisper does the actual speech recognition, communicating with the frontend through stdin/stdout JSON. On Apple Silicon, it uses Metal GPU acceleration through CTranslate2, so transcription is near-instant.

I built the whole thing with Claude Code as my primary dev tool. Not as a novelty, but because it's genuinely how I ship software now. The process itself is part of the product for me.

Sotto is open source and MIT licensed.

GitHub: github.com/vedantggwp/Sotto
Landing page: getsotto.vercel.app

If you work on a Mac and talk faster than you type, give it a try.

---

## X / Twitter

```
built a macos app that does voice control without touching the cloud

whisper AI runs locally on your mac. press a hotkey, speak, text appears at your cursor. 30+ system commands. zero network calls

built entirely with claude code

github.com/vedantggwp/Sotto
```
