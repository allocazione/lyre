<h1 align="center">🎻 Lyre</h1>

<p align="center">
  <a href="https://mintlify.com/allocazione/lyre">Documentation</a> · <a href="https://github.com/allocazione/lyre">GitHub</a>
</p>

A user-first, self-hostable "now listening" bot for Misskey (and Mastodon-compatible instances). Lyre periodically checks what you are listening to via Last.fm or Stats.fm and posts status notes to your timeline whenever your music changes.


## Table of Contents

- [Table of Contents](#table-of-contents)
- [Documentation](#documentation)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Linux](#linux)
  - [Windows](#windows)
- [Configuration](#configuration)
  - [Interactive Setup (Recommended)](#interactive-setup-recommended)
  - [Manual Setup](#manual-setup)
  - [Obtaining API Credentials](#obtaining-api-credentials)
- [Usage](#usage)
  - [Run the bot](#run-the-bot)
- [Debug Flags](#debug-flags)
  - [Test Music Provider](#test-music-provider)
  - [Test Account Connection](#test-account-connection)
- [Docker](#docker)
  - [Using the CLI flag](#using-the-cli-flag)
  - [Using docker-compose](#using-docker-compose)
  - [Passing environment variables](#passing-environment-variables)
  - [Instance detection](#instance-detection)
  - [Dockerfile details](#dockerfile-details)
- [Makefile](#makefile)
- [Credential Encryption](#credential-encryption)
- [Project Structure](#project-structure)
- [Credits](#credits)
- [License](#license)

---

## Documentation

Full documentation is available at **[mintlify.com/allocazione/lyre](https://mintlify.com/allocazione/lyre)**. It includes a quick-start guide, detailed installation and configuration instructions, usage examples, and more.


## Features

- **Music Providers**: Supports both Last.fm (via `pylast`) and Stats.fm (via the beta API) as sources for currently playing track data. Choose your preferred provider through configuration.
- **Note Posting**: Posts a note to your Misskey timeline whenever the currently playing track changes. Notes can optionally mention your Fediverse account via the `FEDI_ACCOUNT` setting.
- **Cross-platform Links**: Integrates with [song.link / Odesli](https://odesli.co/) to automatically include cross-platform streaming links (Spotify, Apple Music, YouTube, etc.) in posted notes.
- **Introduction Note**: On first connection, the bot posts a one-time introduction note to your timeline.
- **Graceful Shutdown**: On receiving SIGINT (Ctrl+C) or SIGTERM (Linux/macOS), the bot shuts down cleanly.
- **First-Run Setup**: If no configuration file is found, the bot launches an interactive wizard that guides you through entering all required settings and writes the config file for you.
- **Debug Tooling**: Built-in flags for testing API connections and music provider output without running the full bot loop.
- **Docker Support**: Includes a Dockerfile and docker-compose.yml for containerized deployment. A `--docker` CLI flag builds the image directly. Automatic detection of already-running instances.
- **Credential Encryption**: Sensitive values (API tokens, secrets) are encrypted at rest using Fernet symmetric encryption. The first-run wizard encrypts automatically; existing configs can be encrypted with `--encrypt-config`.
- **Real-time Logging**: Uses `loguru` for structured, colorized, real-time log output to stderr.
- **Cross-platform**: Runs on both Linux and Windows wherever Python 3.11+ is available.



## Requirements

- Python 3.11 or higher
- A Misskey (or Mastodon-compatible) account with an API access token
- A Last.fm account with API credentials, or a Stats.fm account



## Installation

### Linux

```bash
git clone https://github.com/allocazione/lyre.git
cd lyre
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

```powershell
git clone https://github.com/allocazione/lyre.git
cd lyre
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```



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
| `POST_NOTES`           | Whether to post notes on track change (`true`/`false`) | No (default: true) |
| `FEDI_ACCOUNT`         | Your Fediverse handle (e.g. `@user@instance.social`) to mention in posted notes | No |
| `POLL_INTERVAL`        | Polling interval in seconds                            | No (default: 30)   |

### Obtaining API Credentials

**Misskey Token**: Go to your Misskey instance settings, navigate to API, and generate a new access token with permissions for reading/writing your profile and creating notes.

**Last.fm API Key**: Register an application at [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create) to receive your API key and secret.

**Stats.fm**: Your Stats.fm username is used to query the public beta API. No separate API key is needed for basic usage. Note that this API is unofficial and may change without notice.



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

1. Post an introduction note on first-ever connection.
2. Begin polling your configured music provider every N seconds (default: 30).
3. When a new track is detected, post a note with the track info and a cross-platform link (via song.link).
4. On shutdown (Ctrl+C or SIGTERM), exit gracefully.



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



## Docker

### Using the CLI flag

```bash
python -m lyre --docker
```

This builds a Docker image tagged `lyre:latest` using the included Dockerfile.

### Using docker-compose

```bash
# Start the bot as a background service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

The container is named `lyre-bot`, restarts automatically unless stopped manually, and mounts your local config directory.

### Passing environment variables

You can pass your config directly via `--env-file` instead of mounting a directory:

```bash
docker run --env-file ~/.config/lyre/config.env lyre:latest
```

### Instance detection

When starting, Lyre checks if a container named `lyre-bot` is already running. If found, it exits with an error to prevent duplicate instances. You can also check manually:

```bash
python -m lyre --status
# or
make status
```

### Dockerfile details

The Dockerfile uses `python:3.11-slim` as the base image, installs dependencies via pip, and sets `python -m lyre` as the entrypoint. The resulting image is minimal and production-ready.


## Makefile

A `Makefile` is included for common tasks. Run `make help` to see all available targets:

| Target                | Description                                                   |
| --------------------- | ------------------------------------------------------------- |
| `make install`        | Create a virtual environment and install dependencies         |
| `make update`         | Pull latest code, reinstall deps, rebuild Docker image        |
| `make run`            | Run the bot                                                   |
| `make run-verbose`    | Run the bot with debug logging                                |
| `make build`          | Build the Docker image                                        |
| `make up`             | Start via docker-compose (background, rebuilds image)         |
| `make down`           | Stop the docker-compose service                               |
| `make status`         | Check if a Lyre container is running                          |
| `make logs`           | Tail logs from the running container                          |
| `make lint`           | Run linter (ruff)                                             |
| `make test`           | Run tests with pytest                                         |
| `make encrypt-config` | Encrypt sensitive fields in the config file                   |
| `make clean`          | Remove caches, build artefacts, and venv                      |


## Credential Encryption

Sensitive configuration values (`MISSKEY_TOKEN`, `LASTFM_API_KEY`, `LASTFM_API_SECRET`) are encrypted at rest using [Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption.

- **Automatic**: The first-run setup wizard encrypts values before writing to disk.
- **Manual**: Encrypt an existing plaintext config with:
  ```bash
  python -m lyre --encrypt-config
  # or
  make encrypt-config
  ```
- Encrypted values are stored with the `ENC:` prefix and decrypted transparently at startup.
- The encryption key is stored at `CONFIG_DIR/.lyre.key` and should **not** be shared.


## Project Structure

```
lyre/
  __init__.py
  __main__.py           Entry point for `python -m lyre`
  bot.py                Main bot logic, CLI definition, polling loop
  config.py             Configuration loader, first_exec() setup wizard,
                        platform-specific config path resolution
  crypto.py             Credential encryption (Fernet)
  logger.py             Logging setup (loguru)
  clients/
    __init__.py
    misskey.py           Misskey API client (note posting, credential verification)
    songlink.py          Song.link / Odesli cross-platform link lookup
    music/
      __init__.py
      base.py            Abstract base class and Track dataclass
      lastfm.py          Last.fm provider (pylast)
      statsfm.py         Stats.fm provider (beta API, httpx)
.env.example             Example environment configuration
requirements.txt         pip dependency list
Makefile                 Common development and deployment tasks
Dockerfile               Container build instructions
docker-compose.yml       Container orchestration
pyproject.toml           Project metadata and dependencies
```


## Credits

Developed by **Selene** ([@sel@social.fedicate.org](https://social.fedicate.org/@sel)).


## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.


<p align="center">
  Made with ❤️ from Italy, for all the Fediverse users ❤️
</p>
