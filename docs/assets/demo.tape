# Generates docs/assets/demo.gif — the terminal recording used at the top of the README.
#
# Requires vhs (https://github.com/charmbracelet/vhs): brew install vhs
#
# Run from the repo root, with agent-referee installed in your active environment:
#   vhs docs/assets/demo.tape
#
# This records the real `referee demo` command, live — nothing scripted or faked.

Output docs/assets/demo.gif

Set Shell "zsh"
Set FontSize 16
Set Width 1000
Set Height 640
Set Theme "Dracula"
Set Padding 20

Type "referee demo"
Sleep 500ms
Enter
Sleep 6s
