# Desktop Cat Companion

Desktop Cat Companion is a small desktop pet and lightweight agent built with
Python and PySide6. It renders a transparent, always-on-top cat on your desktop,
lets you drag it around, switch poses and colors, chat through an
OpenAI-compatible API, and use local agent features such as memory, reminders,
todos, and gentle proactive care.

Chinese documentation: [README_ZH.md](README_ZH.md)

## Features

- Transparent, always-on-top desktop pet window
- Draggable cat window with a right-side control bubble
- Embedded chat panel with optional OpenAI-compatible LLM support
- LLM-based structured intent parsing for reminders, todos, and memories
- Local memory for preferences, nickname, notes, and last window position
- Local reminders and todos stored in JSON
- `Tasks` tab for reviewing, completing, deleting, and clearing tasks
- Reminder popups inside the cat bubble when reminders become due
- Low-frequency proactive care messages during long idle periods
- Action controls: eat, walk side, sleep, walk down, walk up, auto cycle
- Color controls: white, yellow, brown, black
- Sprite-sheet animation from `assets/cat.png`
- Safe fallback replies when no API key or OpenAI package is available

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

## Optional LLM Setup

The app runs without an API key, but natural-language intent parsing works best
when an OpenAI-compatible model is configured. Without a model, the app keeps
safe English fallback replies and simple local behavior.

Create a local `.env` file from the example:

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

## Agent Examples

- `remind me in 10 seconds to drink water`
- `tomorrow 10am remind me to call mom`
- `add a todo to buy cat food`
- `remember that I prefer the black cat`
- `what tasks do I have?`
- Natural requests in other languages also work when an LLM is configured.

The agent asks the LLM to privately analyze the user's message and return strict
JSON with English internal fields. Python code executes only validated local
actions, while the LLM writes the user-facing reply in the user's language. The
hidden reasoning is not displayed or stored.

## Controls

- Use the `Chat` tab to talk to the cat and create memories, reminders, or todos.
- Use the `Tasks` tab to view open reminders and todos.
- Use the `Actions` tab to choose a fixed pose or `Auto Cycle`.
- Use the `Colors` tab to switch between white, yellow, brown, and black.
- Double-click the cat to show or hide the bubble panel.
- Right-click the cat for quick actions:
  - `Hide Bubble` / `Show Bubble`
  - `Pause Movement` / `Resume Movement`
  - `Show Tasks`
  - `Clear Completed`
  - `Exit`
- Drag the cat or bubble with the left mouse button to move the desktop pet.

## Local Data And Privacy

Agent data is stored locally in the project `data/` directory:

```text
data/memory.json
data/reminders.json
```

This directory is ignored by Git. The app does not execute arbitrary system
commands, read user files, control your computer, or send reminders/todos to an
external service. If an API key is configured, chat messages, memory context,
and agent parsing requests may be sent to the configured OpenAI-compatible model
provider.

## Project Structure

```text
Desktop_Cat_Companion/
  assets/
    cat.png              # Optional LPC cat sprite sheet
  data/                  # Local ignored agent data
  .env.example           # Safe example config, no real secrets
  agent_core.py          # Local action execution and Agent orchestration
  memory_store.py        # Local JSON memory store
  reminder_store.py      # Local JSON reminders and todos
  tasks_panel.py         # Tasks tab UI
  chat_window.py         # Embedded chat panel and background worker
  pet_window.py          # Desktop pet window, animation, timers, controls
  llm_client.py          # OpenAI-compatible chat and structured parser client
  main.py                # Application entry point
  environment.yml        # Conda environment definition
```

## Cat Asset

This project can run without image assets, but the intended desktop pet uses the
LPC cat sprite sheet from OpenGameArt:

- Page: https://opengameart.org/node/69399
- File: `cat.png`
- Put the file at: `assets/cat.png`

Copyright/Attribution Notice:

```text
"[LPC] Cats and Dogs" Artist: bluecarrot16 License: CC-BY 3.0 / GPL 3.0 / GPL 2.0 / OGA-BY 3.0 Please link to opengameart: http://opengameart.org/content/lpc-cats-and-dogs
```

See [ATTRIBUTION.md](ATTRIBUTION.md) for third-party asset credits and license
information.

## Security Notes Before Publishing

Before pushing this project to GitHub:

- Do not commit `.env`.
- Do not commit `data/`.
- Do not commit real API keys, tokens, cookies, or account identifiers.
- Keep only `.env.example` in the repository.
