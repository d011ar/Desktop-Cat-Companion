# Desktop Cat Companion

Desktop Cat Companion is a small desktop pet and LLM companion built with Python and
PySide6.
It renders a transparent, always-on-top cat on your desktop, lets you drag it
around, switch poses and colors, and optionally chat with it through an
OpenAI-compatible API.

Chinese documentation: [README_ZH.md](README_ZH.md)

The project is intentionally small and readable, so it can be used as a starting
point for building your own desktop pet or chat companion.

Note: the current implementation was developed for Windows first. PySide6 is
cross-platform, so the code may also run on macOS or Linux, but transparent,
frameless, always-on-top desktop windows can behave differently across desktop
environments. Issues and platform-specific improvements are welcome.

## Features

- Transparent, always-on-top desktop pet window
- Draggable cat window with a right-side control bubble
- Embedded chat panel
- Action controls: eat, walk side, sleep, walk down, walk up, auto cycle
- Color controls: white, yellow, brown, black
- Sprite-sheet animation from `assets/cat.png`
- Optional OpenAI-compatible chat through `.env`
- Safe local fallback replies when no API key is configured
- Built-in placeholder cat if image assets are missing

## Quick Start

Create the Conda environment:

```powershell
conda env create -f environment.yml
```

Activate it:

```powershell
conda activate desktop-cat
```

Run the app:

```powershell
python main.py
```

## Optional LLM Chat Setup

The app runs without an API key. Without a key, the chat panel uses local
fallback replies.

To enable model-powered chat, create a local `.env` file from the example:

```powershell
copy .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

Never commit `.env`. The repository `.gitignore` excludes `.env` and `.env.*`
while keeping `.env.example`.

## Controls

- Use the `Chat` tab to talk to the cat.
- Use the `Actions` tab to choose a fixed pose or `Auto Cycle`.
- Use the `Colors` tab to switch between white, yellow, brown, and black.
- Double-click the cat to show or hide the bubble panel.
- Right-click the cat for quick actions:
  - `Hide Bubble` / `Show Bubble`
  - `Pause Movement` / `Resume Movement`
  - `Exit`
- Drag the cat or bubble with the left mouse button to move the desktop pet.

## Project Structure

```text
Desktop_Cat/
  assets/
    cat.png              # Optional LPC cat sprite sheet
  .env.example           # Safe example config, no real secrets
  .gitignore             # Ignores local secrets, caches, and environments
  environment.yml        # Conda environment definition
  main.py                # Application entry point
  pet_window.py          # Desktop pet window, sprite animation, controls
  chat_window.py         # Embedded chat panel and background chat worker
  llm_client.py          # OpenAI-compatible chat client and fallback replies
```

## How The Code Works

### `main.py`

`main.py` is the application entry point. It loads environment variables from
`.env`, creates the `QApplication`, constructs `PetWindow`, and starts the Qt
event loop.

This is the best place to add app-level behavior such as startup logging,
single-instance checks, or platform-specific initialization.

### `pet_window.py`

`pet_window.py` contains the main desktop pet UI.

Important pieces:

- `PetWindow`: the transparent always-on-top window.
- `CatPose`: available action states such as `WALK_SIDE`, `SLEEP`, and `WALK_DOWN`.
- `CatColor`: available sprite color groups.
- `AnimationSpec`: describes which sprite row and frames are used for a pose.
- `POSE_SPECS`: the main pose-to-animation mapping.
- `AUTO_SEQUENCE`: the order used by Auto Cycle.

The sprite sheet is treated as a grid of `32x32` frames. Color variants are
stored in groups of four columns:

- White: columns `0-3`
- Yellow: columns `4-7`
- Brown: columns `8-11`
- Black: columns `12-15`

If you want to add new actions, start by adding a new `CatPose`, then add an
entry to `POSE_SPECS`, and finally add a button in `_build_action_tab()`.

If you want to change how movement works, look at:

- `_choose_next_target()`
- `_move_tick()`
- `AnimationSpec.moves`

### `chat_window.py`

`chat_window.py` provides the embedded chat panel.

Important pieces:

- `ChatPanel`: the widget shown inside the `Chat` tab.
- `ChatWorker`: runs the API call in a `QThread` so the UI stays responsive.
- `message_started`: emitted when the user sends a message.
- `message_finished`: emitted when the cat reply is ready.

`PetWindow` listens to those signals and switches the cat to the `WALK_DOWN`
pose while the chat request is running.

### `llm_client.py`

`llm_client.py` wraps the OpenAI-compatible chat API.

It reads:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

If the API key is missing or a request fails, it returns one of the local
fallback replies instead of crashing the app.

This file is the best place to customize the cat's personality, prompt,
temperature, max tokens, or model provider.

## Cat Asset

This project can run without image assets, but the intended desktop pet uses the
LPC cat sprite sheet from OpenGameArt:

- Page: https://opengameart.org/node/69399
- File: `cat.png`
- Put the file at: `assets/cat.png`

The OpenGameArt page describes the asset as LPC-style cats and dogs with walk
animations in four directions, bonus sleeping images, eating animations, and
four colors.

Copyright/Attribution Notice:

```text
"[LPC] Cats and Dogs" Artist: bluecarrot16 License: CC-BY 3.0 / GPL 3.0 / GPL 2.0 / OGA-BY 3.0 Please link to opengameart: http://opengameart.org/content/lpc-cats-and-dogs
```

Check the OpenGameArt page and the selected license before redistributing the
asset or using it in another project.

## Ideas For Further Development

- Add more behaviors from the sprite sheet, such as eating or different walk
  directions.
- Add a mood system with hunger, sleepiness, curiosity, or affection.
- Save user preferences such as selected color and last window position.
- Add desktop notifications or reminders.
- Add voice input or text-to-speech.
- Add multiple pets.
- Add custom sprite-sheet configuration for other animals.
- Add reminders, memory, tool use, or planning features if you want to evolve it
  into a more agent-like desktop companion.
- Package the app with PyInstaller.

## Security Notes Before Publishing

Before pushing this project to GitHub:

- Do not commit `.env`.
- Do not commit real API keys, tokens, cookies, or account identifiers.
- Keep only `.env.example` in the repository.
- Run a local secret scan if you have one available.
- Check `git status --short` before committing.

The included `.gitignore` already ignores `.env`, `.env.*`, virtual
environments, Python caches, build artifacts, logs, and common editor files.
