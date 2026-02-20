# Lyre

A user-first, self-hostable "now listening" bot for Misskey (and Mastodon-compatible instances). Lyre periodically checks what you are listening to via Last.fm or Stats.fm and updates your Misskey profile bio and posts status notes accordingly. When the bot starts, your bio is marked as online; when it shuts down, it is marked as offline.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Debug Flags](#debug-flags)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

- **Music Providers**: Supports both Last.fm (via `pylast`) and Stats.fm (via the beta API) as sources for currently playing track data. Choose your preferred provider through configuration.
- **Bio Status**: Automatically updates your Misskey profile bio to indicate whether the bot is online or offline. When a track is playing, the bio shows what you are currently listening to.
- **Note Posting**: Posts a note to your Misskey timeline whenever the currently playing track changes.
- **Graceful Shutdown**: On receiving SIGINT (Ctrl+C) or SIGTERM (Linux/macOS), the bot sets your bio to offline before exiting.
- **First-Run Setup**: If no `.env` file is found, the bot launches an interactive wizard (`first_exec`) that guides you through entering all required settings and writes the `.env` file for you.
- **Debug Tooling**: Built-in flags for testing API connections and music provider output without running the full bot loop.
- **Docker Support**: Includes a Dockerfile and docker-compose.yml for containerized deployment. A `--docker` CLI flag builds the image directly.
- **Real-time Logging**: Uses `loguru` for structured, colorized, real-time log output to stderr.
- **Cross-platform**: Runs on both Linux and Windows wherever Python 3.11+ is available.

---

## Requirements

- Python 3.11 or higher
- A Misskey (or Mastodon-compatible) account with an API access token
- A Last.fm account with API credentials, or a Stats.fm account

---

## Installation

### Linux

```bash
git clone https://github.com/your-username/lyre.git
cd lyre
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

```powershell
git clone https://github.com/your-username/lyre.git
cd lyre
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Lyre stores its configuration in a platform-specific directory:

| Platform    | Config path                      |
| ----------- | -------------------------------- |
| Linux/macOS | `~/.config/lyre/config.env`      |
| Windows     | `%USERPROFILE%\.lyre\config.env` |

The directory is created automatically on first run.

### Interactive Setup (Recommended)

If no configuration file exists, the bot will automatically launch an interactive setup wizard that walks you through every required setting:

```
============================================================
  Lyre -- First Run Setup
============================================================

No configuration file was found.
Config will be saved to: /home/user/.config/lyre/config.env
This wizard will help you set up the bot.

--- Misskey / Mastodon Configuration ---

Instance URL (e.g. https://misskey.io): _
```

The wizard asks for your Misskey instance URL, API token, choice of music provider, the relevant API keys, and bot preferences. Once complete, the config file is written automatically.

### Manual Setup

Alternatively, create the config file manually. You can use the included `.env.example` as a template:

```bash
# Linux/macOS
mkdir -p ~/.config/lyre
cp .env.example ~/.config/lyre/config.env

# Windows (PowerShell)
New-Item -ItemType Directory -Force ~\.lyre
Copy-Item .env.example ~\.lyre\config.env
```

Open the config file in your editor and set the following values:

| Variable               | Description                                            | Required           |
| ---------------------- | ------------------------------------------------------ | ------------------ |
| `MISSKEY_INSTANCE_URL` | The URL of your Misskey instance                       | Yes                |
| `MISSKEY_TOKEN`        | Your Misskey API access token                          | Yes                |
| `MUSIC_PROVIDER`       | `lastfm` or `statsfm`                                  | Yes                |
| `LASTFM_API_KEY`       | Your Last.fm API key                                   | If using Last.fm   |
| `LASTFM_API_SECRET`    | Your Last.fm API secret                                | If using Last.fm   |
| `LASTFM_USERNAME`      | Your Last.fm username                                  | If using Last.fm   |
| `STATSFM_USERNAME`     | Your Stats.fm username                                 | If using Stats.fm  |
| `UPDATE_BIO`           | Whether to update your profile bio (`true`/`false`)    | No (default: true) |
| `POST_NOTES`           | Whether to post notes on track change (`true`/`false`) | No (default: true) |
| `POLL_INTERVAL`        | Polling interval in seconds                            | No (default: 30)   |

### Obtaining API Credentials

**Misskey Token**: Go to your Misskey instance settings, navigate to API, and generate a new access token with permissions for reading/writing your profile and creating notes.

**Last.fm API Key**: Register an application at [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create) to receive your API key and secret.

**Stats.fm**: Your Stats.fm username is used to query the public beta API. No separate API key is needed for basic usage. Note that this API is unofficial and may change without notice.

---

## Usage

### Run the bot

On Linux/macOS:

```bash
cd lyre
source venv/bin/activate
python -m lyre
```

On Windows:

```powershell
cd lyre
venv\Scripts\activate
python -m lyre
```

To enable verbose (debug) logging, add the `--verbose` flag:

```bash
python -m lyre --verbose
```

The bot will:

1. Set your Misskey bio to "[Online] Currently running."
2. Begin polling your configured music provider every N seconds (default: 30).
3. When a new track is detected, update your bio to show the track and post a note.
4. When playback stops, your bio reverts to "[Online] Currently running."
5. On shutdown (Ctrl+C or SIGTERM), set your bio to "[Offline]" and exit.

---

## Debug Flags

These flags allow you to test individual components without running the full bot.

### Test Music Provider

```bash
python -m lyre --debug-songs
```

This connects to your configured music provider (Last.fm or Stats.fm), fetches the currently playing track (or most recent), prints the result, and exits. Use this to verify that your API credentials are correct and the provider is returning data.

### Test Account Connection

```bash
python -m lyre --debug-acc
```

This connects to your Misskey instance, verifies your access token, prints your account information (username, note count, follower/following counts), and exits. Use this to confirm that your instance URL and token are correct.

---

## Docker

### Using the CLI flag

```bash
python -m lyre --docker
```

This builds a Docker image tagged `lyre:latest` using the included Dockerfile. After building, you can run the container with:

```bash
docker run --env-file .env lyre:latest
```

### Using docker-compose

```bash
docker-compose up -d
```

This builds the image and starts the bot as a background service. The container will restart automatically unless stopped manually.

### Dockerfile details

The Dockerfile uses `python:3.11-slim` as the base image, installs dependencies via Poetry, and sets `python -m lyre` as the entrypoint. The resulting image is minimal and production-ready.

---

## Project Structure

```
lyre/
  __init__.py
  __main__.py           Entry point for `python -m lyre`
  bot.py                Main bot logic, CLI definition, polling loop
  config.py             Configuration loader, first_exec() setup wizard,
                        platform-specific config path resolution
  logger.py             Logging setup (loguru)
  clients/
    __init__.py
    misskey.py           Misskey API client (bio updates, note posting)
    music/
      __init__.py
      base.py            Abstract base class and Track dataclass
      lastfm.py          Last.fm provider (pylast)
      statsfm.py         Stats.fm provider (beta API, httpx)
.env.example             Example environment configuration
requirements.txt         pip dependency list
Dockerfile               Container build instructions
docker-compose.yml       Container orchestration
pyproject.toml           Project metadata and dependencies
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
