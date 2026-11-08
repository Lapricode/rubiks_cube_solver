"""User-facing text shown by the application."""

CUBE_NOTATION_TEXT = (
    "In the picture above you can see the official cube notation that I am using in this program. Typing in your keyboard\n"
    "one of these letter-keys you can execute the corresponding move on the cube. If you type a letter-key holding shift-\n"
    "key, you can execute the move in the opposite direction. Additionally, you can make all the moves using only your\n"
    "mouse (left click and drag for layer moves and right click and drag for rotations).\n"
    "The notation for the opposite direction moves uses the exact same letters but with an apostrophe next to them. For\n"
    "example, R' (R prime) means R move but in the opposite direction. Finally, you may also meet the case where a letter\n"
    "is followed by the number 2, which means that you have to execute the specified move two times in a row. For\n"
    "example, the notation U2 (in this writing you can consider it as one move), is equivalent to U, U.\n"
    "On the 4x4 cube, lowercase letters turn inner slices (r, u, f, ...) and letters followed by w turn two layers\n"
    "(Rw, Uw, Fw, ...).\n"
    "Image source: https://jperm.net/3x3/moves ."
)

RESET_TEXT = (
    "You may press the ⓘ (it appears at the upper left corner of the window) to understand how to read the Rubik's cube\n"
    "notation and how to enter the moves into the program in order to be executed. Choose the cube size from the menu;\n"
    "middle slice moves are only available on the 3x3 cube, while the 4x4 cube uses lowercase inner-slice and w wide\n"
    "moves. You can change the observation view of the cube pressing the numbers 4, 6, 8, 2 and also reset it to\n"
    "default (top white side, front green side, right red side) pressing 5.\n"
    "Additionally, you can move the cube around inside the window and zoom-in or zoom-out using the mousewheel.\n"
    'Scramble the cube typing moves or pressing the "random scramble" button and then solve it yourself or let the computer\n'
    'solve it pressing the "solve" button. An other very important feature of the program is that you have the opportunity to\n'
    'draw a (valid of course) scrambled cube pattern (pressing the "draw pattern" button) and see the solution on your screen.'
)

MOVES_SCRAMBLE_TEXT = (
    'You can make {max_moves} scramble moves maximum. Whenever you are ready press the "solve" button '
    "or try to solve the cube yourself pressing the button below."
)

DRAW_SCRAMBLE_TEXT = (
    'Choose the proper colors and paint the cube. Move around the cube pressing the "view" numbers 4, 6, 8, 2\n'
    'and 5. Whenever you \'re ready press the "solve" button to see the solution of the cube pattern you made.'
)

CUBE_IS_SOLVED_TEXT = (
    'You can make new scramble moves or draw a pattern pressing the buttons "random scramble" and "draw\n'
    'pattern" respectively. Alternatively you can make the same scramble pressing the button below.'
)

WRONG_PATTERN_TEXT = "This cube pattern cannot be derived from a solved cube. You can fix the scramble pressing the button below."

REPLAY_MOVES_TEXT = (
    'You can use the buttons above\nto replay the solve moves. It also\nworks if you press "0", "1", "3"\n'
    'and "double 0" respectively.'
)

TUTORIAL_HINTS = {
    "default": "Tip: press F1 for the shortcut overlay. Use the menu to discover actions.",
    "reset": "Start with random scramble or draw a pattern, then replay the solution.",
    "moves_scramble": "Type cube moves, use the mouse, or press random scramble. Undo with Ctrl+Z.",
    "draw_scramble": "Pick a color, then click facelets to paint the pattern. Use clear/fill to start over.",
    "self_solve": "Solve the cube yourself. The timer runs until every face is a single color.",
    "self_solve_done": "Use the replay controls to review your solve, or try again for a better time.",
    "choose_method": "Choose a solver. Beginner is easiest to follow; CFOP and Kociemba need extra packages.",
    "already_solved": "The cube is already solved. Make a new scramble to continue.",
    "choose_color": "Choose which color the beginner solver should solve first.",
    "solving": "The solver is working. The solution will replay automatically when ready.",
    "solve_result": "Scrub the timeline, jump between stages, or press play to replay at your chosen speed.",
    "history": "Undo or redo moves here. History contains interactive moves from the current session.",
    "stats": "Best and average times are stored per cube size between sessions.",
    "error": "The cube pattern or solver reported an error. Fix the scramble and try again.",
}
