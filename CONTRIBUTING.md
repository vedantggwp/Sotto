# Contributing to Sotto

Thanks for helping improve Sotto. The project is a local-first macOS voice control and dictation app built with a Tauri frontend and Python sidecar.

## Good First Areas

- Voice command parser tests in `tests/test_command_parser.py`
- IPC protocol coverage in `tests/test_protocol.py`
- Documentation for install, permissions, and troubleshooting
- Frontend settings and pill UI refinements
- Packaging and sidecar reliability

## Local Setup

```bash
git clone https://github.com/vedantggwp/Sotto.git
cd Sotto
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/
```

For the desktop app:

```bash
cd sotto-ui
pnpm install
pnpm build
```

Running the full Tauri app requires macOS, Rust, pnpm, Python, and PortAudio. Sotto also requires microphone and accessibility permissions when testing real dictation or keyboard execution.

## Pull Request Checklist

- Keep the change focused on one bug, feature, or doc improvement.
- Add or update tests when behavior changes.
- Run `pytest tests/` for Python-side changes.
- Run `pnpm build` in `sotto-ui/` for frontend changes.
- Do not commit local logs, model caches, audio recordings, packaged apps, or signing artifacts.

## Reporting Issues

Please include:

- macOS version and hardware;
- Python version;
- whether you are using CLI mode or the Tauri app;
- microphone/accessibility permission status;
- the command, dictation flow, or IPC path involved;
- expected behavior and actual behavior.

Do not attach private voice recordings, transcripts, credentials, or logs containing private text unless you are comfortable publishing them publicly.
