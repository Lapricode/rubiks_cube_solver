# rubiks_cube_solver

Rubik's cube solver.

The program creates a virtual cube. You can choose between a 2x2x2, a 3x3x3 and
a 4x4x4 cube from the menu, scramble the cube or draw a pattern from a real
cube, and the computer will give you the solving moves. The 2x2 cube uses an
optimal solver. The 4x4 cube uses an in-house reduction solver: it solves the
wings, fixes parity, solves the centres, corrects 3x3 parity when needed, and
then finishes with the beginner method. For the 3x3 cube there are three
automatic solving methods: the beginner method, with code written by me, the
CFOP method and the Kociemba method (which is the fastest in terms of number of
moves), with the last two methods being carried out by the python library
`rubik_solver`. You can also try to solve the virtual cube alone as fast as you
can. The moves can be done on the virtual cube using keyboard or mouse,
depending on your convenience.

Try it if you want.

The menu and bottom control area are rendered with pygame and embedded in the
Tkinter window, while the cube view and its hidden/unfolded drawings remain on
the Tkinter canvas. All three areas can be resized with the draggable dividers,
and their text scales automatically with the available space.

The GUI also includes:

- Move history with undo/redo, plus replay scrubbing, stage jumps, playback and
  adjustable replay speed.
- A live self-solve timer, best/average time statistics, and recent session
  history. Statistics are stored in `~/.rubiks_cube_solver_stats.json`.
- A remappable keyboard-shortcut overlay (`F1` by default). Shortcut bindings are
  stored in `~/.rubiks_cube_solver_shortcuts.json`.
- Guided tutorial hints over the cube view.
- Classic, dark, high-contrast and colorblind-friendly themes.
- Save/load cube state as JSON and export a solution as text.
- Optional smooth turn animation with adjustable duration.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the runtime dependencies:

```bash
pip install -r requirements.txt
```

For development and tests, install the extra tools:

```bash
pip install -r requirements-dev.txt
```

Run the application:

```bash
python rubiks_cube.py
```

## Tests and checks

```bash
pytest
ruff check .
black --check .
```

## Project layout

- `rubiks_cube.py` — application entry point.
- `rubik/cube.py` — pure cube state, validation and move logic.
- `rubik/solvers.py` — beginner solver and lazy CFOP/Kociemba integration.
- `rubik/solver_2x2.py` — optimal 2x2 solver using corner pattern databases.
- `rubik/solver_4x4.py` — in-house 4x4 reduction solver with parity handling.
- `rubik/config.py` — constants, themes, shortcut defaults, face enum, asset paths and key bindings.
- `rubik/texts.py` — user-facing text and tutorial hints.
- `rubik/stats.py` — persistent solve statistics and summaries.
- `rubik/shortcuts.py` — persistent keyboard shortcut bindings.
- `rubik/persistence.py` — cube save/load and solution export helpers.
- `rubik/ui/` — Tkinter application shell, pygame-rendered panels, cube rendering, widgets and animation/replay controllers.
- `rubik/ui/pygame_panels.py` — offscreen pygame panel renderer embedded in Tkinter labels.
- `tests/` — pytest tests for cube logic, solvers, replay/animation, stats, shortcuts and persistence.

The optional `rubik_solver` package is only imported when CFOP or Kociemba is
selected, so the application still starts if it is not installed. Installing it
via `requirements.txt` enables those two methods.

![image](https://github.com/Lapricode/rubiks_cube/assets/91993549/a3e9b5d3-ea56-4060-8108-be3d0fe34685)

![image](https://github.com/Lapricode/rubiks_cube/assets/91993549/14c3ff3c-8beb-439c-9195-f9d9256dd7b0)
