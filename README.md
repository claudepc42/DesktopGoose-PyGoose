# PyGoose

A Python/PyQt6 reimplementation of [samperson's Desktop Goose](https://samperson.itch.io/desktop-goose) — a chaotic little goose that wanders your screen, steals your mouse, and leaves you passive-aggressive notes.

![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

---

## What it does

A goose lives on your desktop. He has opinions about you. He will:

- **Wander** around your screen minding his own business (sort of)
- **Steal your mouse** and drag it somewhere else
- **Deliver notepad messages** — handwritten, passive-aggressive, non-negotiable
- **Drop memes** on your screen that you have to deal with
- **Track mud** across everything
- **Watch you** — sit down, stare at your cursor, occasionally honk
- **React to being clicked** depending on his mood

---

## Requirements

- Python 3.12+
- PyQt6
- PyQt6-Qt6
- PyQt6-sip

Install dependencies:

```bash
pip install PyQt6
```

---

## Running

```bash
python main.py
```

The goose appears on your desktop. He runs on top of all windows and cannot be clicked through (by design). Press and hold **ESC** to quit.

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
| `GooseColorUnderbody` | `#d3d3d3` | Underbody color |
| `GooseColorBeak` | `#ffa500` | Beak color |
| `MinWanderingTimeSeconds` | `20` | Min time between tasks |
| `MaxWanderingTimeSeconds` | `40` | Max time between tasks |
| `NotepadFontSize` | `25` | Font size in notepad window |

---

## Adding content

### Notepad messages
Drop `.txt` files into `assets/text/notepad_messages/`. One message per file. The goose will pick from them randomly.

### Memes
Drop image files (`.png`, `.jpg`, `.gif`) into `assets/images/memes/`. The goose will drag them onto your screen.

### Fonts
Drop `.ttf` or `.otf` font files into `assets/fonts/`. The first loaded font is used for the notepad.

---

## Project structure

```
PyGoose/
├── main.py                   # Entry point
├── config.ini                # Auto-generated settings
├── assets/
│   ├── fonts/                # Handwriting fonts for notepad
│   ├── images/memes/         # Meme images
│   ├── sounds/               # Honks, pats, music
│   └── text/notepad_messages/ # Goose notes
├── pygoose/
│   ├── engine/               # Vector math, IK rig, timing, deck shuffle
│   └── goose/                # Game loop, renderer, tasks, windows
└── tests/
```

---

## Credits

- Original Desktop Goose by [samperson](https://samperson.itch.io/desktop-goose)
- Rewritten from scratch in Python — no original assets used (sounds extracted from the original exe for personal use only, not redistributed)
