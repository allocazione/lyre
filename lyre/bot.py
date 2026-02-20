"""Lyre - Main bot logic.

Entry point and polling loop for the 'now listening' bot.
Cross-platform: works on both Linux and Windows.
"""

import asyncio
import os
import signal
import sys
import subprocess
from pathlib import Path
from typing import Optional

import typer

from lyre.logger import setup_logger, logger


app = typer.Typer(
    name="lyre",
    help="A user-first, self-hostable 'now listening' bot for Mastodon/Misskey.",
    add_completion=False,
)

# Intro note posted on first connection
_INTRO_NOTE = (
    "Hi! I'm an instance of Lyre, a self-hostable 'now listening' bot.\n"
    "I'll post updates about the music currently being played on this account.\n\n"
    "Developed by @sel@social.fedicate.org\n"
    "⭐ me @ https://github.com/allocazione/lyre"
)


def _get_music_provider():
    """Instantiate the configured music provider."""
    from lyre.config import Config
    from lyre.clients.music.lastfm import LastFmProvider
    from lyre.clients.music.statsfm import StatsFmProvider

    provider = Config.MUSIC_PROVIDER
    if provider == "lastfm":
        return LastFmProvider()
    elif provider == "statsfm":
        return StatsFmProvider()
    else:
        logger.error(f"Unknown music provider: {provider}. Use 'lastfm' or 'statsfm'.")
        sys.exit(1)


def _has_introduced() -> bool:
    """Check whether the intro note has already been posted."""
    from lyre.config import CONFIG_DIR
    return (CONFIG_DIR / ".introduced").exists()


def _mark_introduced():
    """Mark that the intro note has been posted."""
    from lyre.config import CONFIG_DIR
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / ".introduced").touch()


async def _post_intro_if_needed(misskey_client):
    """Post the introduction note on first-ever connection."""
    if _has_introduced():
        return

    try:
        logger.info("First connection detected. Posting introduction note...")
        await misskey_client.post_note(_INTRO_NOTE, visibility="public")
        _mark_introduced()
        logger.info("Introduction note posted.")
    except Exception as e:
        logger.error(f"Failed to post introduction note: {e}")


async def _debug_songs():
    """Test the music provider API by fetching the current/recent track."""
    from lyre.config import Config
    from lyre.clients.songlink import SongLinkClient

    Config.validate()
    provider = _get_music_provider()
    songlink = SongLinkClient()
    logger.info(f"Testing music provider: {Config.MUSIC_PROVIDER}")

    track = await provider.get_now_playing()
    if track:
        logger.info(f"Now playing: {track}")
        logger.info(f"  Artist : {track.artist}")
        logger.info(f"  Title  : {track.title}")
        logger.info(f"  Album  : {track.album or 'N/A'}")
        logger.info(f"  URL    : {track.url or 'N/A'}")
        logger.info(f"  Image  : {track.image_url or 'N/A'}")
        logger.info(f"  Playing: {track.is_now_playing}")

        # Test song.link lookup
        if track.url:
            logger.info("Looking up cross-platform links...")
            links = await songlink.get_links(track.url)
            if links:
                for platform, url in links.items():
                    logger.info(f"  {platform}: {url}")
            else:
                logger.info("  No cross-platform links found.")
        else:
            logger.info("  No track URL available for song.link lookup.")
    else:
        logger.info("No track is currently playing.")

    await songlink.close()
    if hasattr(provider, "close"):
        await provider.close()


async def _debug_acc():
    """Test the Misskey/Mastodon connection by verifying credentials."""
    from lyre.config import Config
    from lyre.clients.misskey import MisskeyClient

    Config.validate()
    client = MisskeyClient()
    logger.info(f"Testing connection to: {Config.MISSKEY_INSTANCE_URL}")

    try:
        account = await client.verify_credentials()
        logger.info("Connection successful.")
        logger.info(f"  Username  : @{account.get('username', 'N/A')}")
        logger.info(f"  Name      : {account.get('name', 'N/A')}")
        logger.info(f"  ID        : {account.get('id', 'N/A')}")
        logger.info(f"  Notes     : {account.get('notesCount', 'N/A')}")
        logger.info(f"  Followers : {account.get('followersCount', 'N/A')}")
        logger.info(f"  Following : {account.get('followingCount', 'N/A')}")
    except Exception as e:
        logger.error(f"Connection failed: {e}")
    finally:
        await client.close()


async def _run_bot():
    """Main bot loop: poll music provider, update Misskey bio/notes.

    Handles graceful shutdown on SIGINT (Ctrl+C) on all platforms,
    and SIGTERM on Linux/macOS.
    """
    from lyre.config import Config
    from lyre.clients.misskey import MisskeyClient
    from lyre.clients.music.base import Track
    from lyre.clients.songlink import SongLinkClient

    Config.validate()
    if Config.POLL_INTERVAL < 10:
        logger.warning(f"Poll interval {Config.POLL_INTERVAL}s is too short. Minimum is 10s. Forcing 10s.")
        # We don't modify the class variable directly to avoid side effects if reloaded,
        # but we use a local variable for the loop or just update it once.
        Config.POLL_INTERVAL = 10

    misskey = MisskeyClient()
    provider = _get_music_provider()
    songlink = SongLinkClient()
    last_track: Optional[Track] = None
    running = True

    def handle_shutdown(sig, frame):
        nonlocal running
        logger.info(f"Received signal {sig}. Shutting down gracefully...")
        running = False

    # SIGINT works on all platforms (Ctrl+C).
    signal.signal(signal.SIGINT, handle_shutdown)
    # SIGTERM is only available on Unix-like systems.
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)

    # Post intro note on first connection
    await _post_intro_if_needed(misskey)

    # Set bio to online
    try:
        if Config.UPDATE_BIO:
            await misskey.set_online()
        logger.info(
            f"Bot started. Polling every {Config.POLL_INTERVAL}s "
            f"using {Config.MUSIC_PROVIDER}."
        )
    except Exception as e:
        logger.error(f"Failed to set online status: {e}")

    try:
        while running:
            try:
                track = await provider.get_now_playing()

                if track and track.is_now_playing:
                    track_str = str(track)
                    last_track_str = str(last_track) if last_track else None

                    if track_str != last_track_str:
                        logger.info(f"Now playing: {track_str}")

                        # Look up cross-platform links
                        platform_links = None
                        songlink_url = None
                        if track.url:
                            platform_links = await songlink.get_links(track.url)
                            if platform_links:
                                songlink_url = songlink.format_links(
                                    platform_links, compact=True
                                )
                                logger.info(f"  song.link: {songlink_url}")

                        # Update bio
                        if Config.UPDATE_BIO:
                            bio_extra = ""
                            if songlink_url:
                                bio_extra = f"\n{songlink_url}"
                            await misskey.update_now_playing(
                                track_str + bio_extra
                            )

                        # Post note with platform links
                        if Config.POST_NOTES:
                            note_text = f"Now listening: {track_str}"
                            if songlink_url:
                                note_text += f"\n\n{songlink_url}"
                            elif track.url:
                                note_text += f"\n{track.url}"
                            await misskey.post_note(note_text)

                        last_track = track
                    else:
                        logger.debug(f"Still playing: {track_str}")

                elif last_track is not None:
                    # Was playing, now stopped
                    logger.info("Playback stopped.")
                    if Config.UPDATE_BIO:
                        await misskey.set_online()
                    last_track = None
                else:
                    logger.debug("No track currently playing.")

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            # Wait for the next poll cycle (1-second ticks for responsiveness)
            for _ in range(Config.POLL_INTERVAL):
                if not running:
                    break
                await asyncio.sleep(1)

    finally:
        # Set bio to offline before exiting
        try:
            if Config.UPDATE_BIO:
                await misskey.set_offline()
        except Exception as e:
            logger.error(f"Failed to set offline status: {e}")

        await songlink.close()
        if hasattr(provider, "close"):
            await provider.close()
        await misskey.close()
        logger.info("Bot stopped.")


def _docker_build():
    """Build the Docker image for Lyre."""
    logger.info("Building Docker image...")
    try:
        subprocess.run(
            ["docker", "build", "-t", "lyre:latest", "."],
            check=True,
        )
        logger.info("Docker image built successfully: lyre:latest")
        logger.info("Run with: docker run --env-file .env lyre:latest")
    except FileNotFoundError:
        logger.error("Docker not found. Please install Docker first.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker build failed: {e}")
        sys.exit(1)


@app.command()
def main(
    debug_songs: bool = typer.Option(
        False,
        "--debug-songs",
        help="Test the music provider API and exit.",
    ),
    debug_acc: bool = typer.Option(
        False,
        "--debug-acc",
        help="Test the Misskey/Mastodon connection and exit.",
    ),
    docker: bool = typer.Option(
        False,
        "--docker",
        help="Build the Docker image and exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose (debug) logging.",
    ),
):
    """Lyre -- a self-hostable 'now listening' bot for Misskey/Mastodon."""
    setup_logger(debug=verbose)

    # Load config -- skip the interactive wizard for debug/docker flags
    # so they work even without a .env file.
    from lyre.config import init_config
    is_debug = debug_songs or debug_acc or docker
    init_config(skip_wizard=is_debug)

    try:
        if docker:
            _docker_build()
            return

        if debug_songs:
            asyncio.run(_debug_songs())
            return

        if debug_acc:
            asyncio.run(_debug_acc())
            return

        # Default: run the bot
        asyncio.run(_run_bot())

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    app()
