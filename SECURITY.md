# Security Policy

## Supported Versions

Sotto is pre-1.0 software. Security fixes target the `main` branch and the latest public release.

## Reporting a Vulnerability

Please do not open a public issue for vulnerabilities involving keyboard simulation, unsafe AppleScript execution, private audio leakage, local file exposure, dependency compromise, or signing/package integrity.

Report privately by opening a GitHub security advisory for this repository if available, or contact the maintainer through the email on the GitHub profile.

Useful reports include:

- affected component, command, or IPC message;
- reproduction steps using non-sensitive input;
- whether microphone, accessibility, sidecar, or packaging behavior is involved;
- expected and observed behavior.

## Privacy Boundary

Sotto is designed to run speech recognition locally. Public issues and PRs should not include private recordings, transcripts, credentials, local logs with sensitive text, model caches, packaged apps, or signing materials.
