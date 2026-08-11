# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-process Discord bot (discord.py) that watches messages in a server, rewrites social-media links (Instagram/Twitter-X/TikTok/Reddit/Facebook) into embed-friendly versions, logs links and media attachments to Postgres, tracks reactions on them, and exposes slash commands for leaderboards and a `/makegif` YouTube-clip-to-GIF command. Flat repo, no package structure beyond `tests/`.

## Commands

Local Postgres (required for anything touching `db.py`):
```
docker compose up db
```
`init.sql` is applied automatically by the Postgres container on first init (via `docker-entrypoint-initdb.d`) — it defines `link_messages`, `media_messages`, and the `reaction_tuple` composite type. **`tables.txt` is a stale scratch file with an older, abandoned JSONB-based schema — it does not reflect the real schema. Always treat `init.sql` as authoritative.**

Run the bot:
```
python main.py
```
Requires a `.env` with `API_KEY` (Discord bot token) and `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

Run the whole bot + db via Docker:
```
docker compose up
```

Tests (stdlib `unittest`, not pytest — no `pytest.ini`/`pyproject.toml` exists even though a couple of test files call `pytest.skip`, which will `NameError` if that path is actually hit):
```
python -m unittest discover -s tests
python -m unittest tests.test_link_util -v
python -m unittest tests.test_link_util.TestUtilFunctions.test_convert_link_uses_primary_backup_when_up
```
- `tests/test_link_util.py` — pure unit tests, no external deps, safe to run anytime.
- `tests/test_main.py` — tests `is_moderator()` directly via a mocked `Interaction`. Importing `main.py` triggers `db.py`'s module-level `psycopg2.connect(...)`, so this still needs a live, reachable Postgres (`docker compose up db -d`) even though the test itself doesn't touch the DB.
- `tests/test_db.py` — imports `db.py`'s module-level `conn` directly and inserts real rows; needs a live, reachable Postgres per your `.env`/env vars (module-level `psycopg2.connect(...)` runs at import time, so a bad connection fails the import itself, not a test).
- `tests/test_gif_util.py` — integration test that does a real `yt-dlp` network download and real `moviepy`/ffmpeg encoding; slow, needs internet.

Environment note: `.venv` must be Python 3.10+ (`py -3.11 -m venv .venv` works) — `requirements.txt` pins `numpy==2.2.5`, which has no 3.9 wheel, and `db.py` uses `int | str` (PEP 604) type-hint syntax that's a hard `TypeError` at import time on 3.9. The Dockerfile uses `python:3.10-slim`. If `.venv` was ever created with 3.9, `pip install -r requirements.txt` fails on the numpy line and `import db` fails outright — delete and recreate `.venv` with 3.10+ rather than patching around it package by package.

Running the bot locally end-to-end: `docker compose up db -d`, put a real Discord bot token in `.env`'s `API_KEY`, then `python main.py`. `client.run(API_KEY)` is guarded by `if __name__ == "__main__":`, so importing `main.py` (e.g. from a test) never tries to connect to Discord — only running it directly does.

## Before considering a change done

Run `python -m py_compile` on every file you touched, then run whichever `unittest` targets above actually cover the change. `test_link_util.py` is always runnable and has no excuse to skip. If a change touches `db.py` or `gif_util.py`, run `test_db.py` / `test_gif_util.py` too — but if the required live infra (Postgres, internet/ffmpeg) isn't available in this environment, say so explicitly rather than reporting the change as verified.

## Architecture

**`main.py`** — the discord.py `Client`, all slash commands (`app_commands`), and raw gateway event handlers (`on_message`, `on_raw_reaction_add/remove`). Owns a `periodic_status_writer()` background task that stamps `last_alive.txt` every 60s, checked on `on_ready()` to detect unclean shutdowns (currently only logs; the actual backlog-recovery call is commented out).

**`db.py`** — all persistence. One module-level, synchronous `psycopg2` connection (`conn`), opened once at import time, reused for every query for the life of the process — there is no connection pool and no reconnect logic. Every `db.py` function is fully synchronous with **no internal `await`**, and this is load-bearing: discord.py dispatches every event handler as its own independent `asyncio.Task` (`Client.dispatch` → `loop.create_task`), so handlers genuinely run concurrently from the event loop's perspective. Because none of the `db.py` calls yield internally, each call is effectively atomic with respect to other tasks — but only as long as that invariant holds. Two consequences to keep in mind when touching this code:
- **DB writes that another handler's SQL depends on must happen before any `await` in the calling handler.** E.g. `on_message` inserts the message row (`db.insert_media`) before doing anything awaited (like sending a converted-link reply), specifically so a fast `on_raw_reaction_add` for that message can't run first and silently no-op its `UPDATE ... WHERE message_id = %s` against a row that doesn't exist yet (no rowcount check, no upsert — a reaction on a not-yet-inserted message is just lost).
- Every `db.py` call blocks the entire event loop for its duration (real network round-trip to Postgres) — don't add slow queries to hot paths like `on_message` without considering that it stalls the whole bot, including gateway heartbeats.

`add_reaction`/`remove_reaction` maintain `reactors` (a `BIGINT[]` of unique user ids) as a value fully re-derived from `reactions` (the `reaction_tuple[]` array) inside the same `UPDATE` statement — both `SET` clauses read the pre-update value of `reactions` (Postgres multi-assignment semantics), so they can't diverge from each other within one statement.

Every message can land in `link_messages` (if `get_link_from_message` finds a URL) and/or `media_messages` (if it has an image/gif/video attachment) — a single message can produce rows in both tables. Reaction updates blindly run against both tables since there's no cheap way to know ahead of time which one a given `message_id` is in.

**`link_util.py`** — regex-based link detection (`get_link_from_message`), platform classification (`get_url_type`), and the embed-fix rewriting (`convert_link`, e.g. `instagram.com` → `instagramez.com`). Also maintains `user_link_count`/`web_link_count`, module-level `defaultdict(int)` counters — these are in-process only, never persisted or read by any command, effectively dead/vestigial state that resets on restart.

**`gif_util.py`** — `yt-dlp` download + `moviepy` clip/resize/GIF-encode, both fully blocking. Called from `/makegif` in `main.py` against **hardcoded shared filenames** (`temp_video.mp4`, `output.gif`) — concurrent `/makegif` invocations can collide on these paths (one invocation's `finally`-block cleanup or overwrite can clobber a different invocation's in-flight file). Known, unresolved.

**Moderator gating discrepancy:** `README.md` claims all commands except `/makegif` are mod-only, including via "any role containing mod/admin." The actual `is_moderator()` check in `main.py` only checks `guild_permissions.manage_messages`/`administrator`, and it's only actually called by `/backfill`. `/top_posts`, `/top_users`, `/top_domain`, and `/contest` have no permission check at all despite the README's claim. Don't trust the README over the code here.
