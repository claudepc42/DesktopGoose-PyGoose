# PyGoose

A Python/PyQt6 reimplementation of [samperson's Desktop Goose](https://samperson.itch.io/desktop-goose) — a chaotic little goose that wanders your screen, steals your mouse, and leaves you passive-aggressive notes.

![Version](https://img.shields.io/badge/version-0.32-orange) ![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green) ![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white) ![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white) ![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)

---

## What it does

A goose lives on your desktop. He has opinions about you. He will:

- **Wander** around your screen minding his own business (sort of)
- **Watch your cursor** — sit down nearby, stare at it, occasionally honk, stare some more. is he planning?
- **Follow you around** at a comfortable distance, march-honking when the mood strikes
- **Sneak up on you** — creep in crawl pose, wait for the right moment, then pounce and steal your mouse
- **Steal your mouse** and drag it somewhere else, honking triumphantly
- **Deliver notepad messages** — handwritten, passive-aggressive, non-negotiable
- **Drop memes** on your screen that you have to deal with
- **Track mud** across everything while running amok
- **Sleep in the corner** — circles down in a spiral, tucks his head, and takes a nap
- **Fake sleep** — sometimes he's just pretending, and if he opens one eye and you're too close, he panics

---

## Requirements

- Python 3.12+
- PyQt6

Install dependencies:

```bash
pip install PyQt6
```

---

## Running

```bash
python main.py
```

The goose appears on your desktop. He runs on top of all windows and cannot be clicked through (by design).

---

## Configuration

A `config.ini` is created automatically on first run. Edit it to customize behavior:

| Key | Default | Description |
|-----|---------|-------------|
| `SilenceSounds` | `false` | Mute all sounds |
| `AttackRandomly` | `false` | Goose attacks mouse unprompted |
| `Task_CanAttackMouse` | `true` | Allow mouse-stealing at all |
| `UseCustomColors` | `false` | Enable custom goose colors |
| `GooseColorBody` | `#ffffff` | Body color |
| `GooseColorUnderbody` | `#d3d3d3` | Underbody/outline color |
| `GooseColorBeak` | `#ffa500` | Beak and feet color |
| `MinWanderingTimeSeconds` | `20` | Min time between tasks |
| `MaxWanderingTimeSeconds` | `40` | Max time between tasks |
| `NotepadFontSize` | `25` | Font size in notepad window |

---

## Adding content

### Notepad messages
Drop `.txt` files into `assets/text/notepad_messages/`. One message per file. The goose will pick from them randomly alongside the built-in phrases.

### Memes
Drop image files (`.png`, `.jpg`, `.gif`, `.webp`) into `assets/images/memes/`. The goose will drag them onto your screen.

### Fonts
Drop `.ttf` or `.otf` font files into `assets/fonts/`. The first loaded font is used for the notepad. A handwriting-style font works well.

---

## Goose behaviors

| Behavior | Description |
|----------|-------------|
| Wander | Walks to random screen positions, pausing occasionally |
| Watch Mouse | Sits near the cursor, staring at it. Bobs head. Rarely honks. Will sit and crouch if the mood takes him. |
| Follow Mouse | Rushes to preferred distance (90–160px) and trails the cursor. Flees if you get too close. Occasionally honks in a march. |
| Sneak Attack | Crouches into a crawl, sneaks toward cursor, then pounces and drags the mouse |
| Nab Mouse | Chases cursor at full speed, grabs it with his beak, drags it away |
| Track Mud | Runs offscreen into a mud puddle, then sprints back across the screen leaving footprints |
| Collect Notepad | Drags a passive-aggressive notepad message onto your screen |
| Collect Meme | Drags a meme image onto your screen |
| Sleep | Walks to a corner, circles in a shrinking spiral, then tucks in for 90 seconds to 8 minutes |
| Fake Sleep | Looks like real sleep but isn't — see above |
| Peek Back | Post-freak-out return sequence: crawl to edge, peek in, sweep gaze, walk back |

---

## Quitting

Hold **ESC** for ~5 seconds. A progress bar slides down from the top of the screen. Keep holding to evict the goose.

---

## Project structure

```
PyGoose/
├── main.py                    # Entry point
├── config.ini                 # Auto-generated settings (not tracked)
├── assets/
│   ├── fonts/                 # Handwriting fonts for notepad
│   ├── images/memes/          # Meme images
│   ├── sounds/                # Honks, pats, music
│   └── text/notepad_messages/ # Goose notes
├── pygoose/
│   ├── engine/                # Vector math, IK rig, timing, deck shuffle
│   └── goose/                 # Game loop, renderer, tasks, windows
└── tests/
```

---

## Developer flags

For testing specific behaviors without waiting for them to appear naturally, edit the top of `pygoose/goose/goose.py`:

```python
DEV_FORCE_TASK = None          # Force a specific task every time (e.g. "sleep")
DEV_SHORT_WANDER = False       # Wander lasts only 3 seconds
DEV_FORCE_FAKE_SLEEP = False   # Always fake sleep instead of 15% chance
```

---

## Credits

- Original Desktop Goose by [samperson](https://samperson.itch.io/desktop-goose)
- Rewritten from scratch in Python — no original assets used (sounds extracted from the original exe for personal use only, not redistributed)
