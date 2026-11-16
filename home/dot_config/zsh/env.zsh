# =============================================================================
# ENVIRONMENT VARIABLES & PATH
# =============================================================================
export OLLAMA_MODELS="$HOME/Documents/llama/models/"
export DOTNET_ROOT="/usr/local/share/dotnet"
export CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1

# Build PATH cleanly and eliminate duplicates
typeset -U path
path=(
  "$HOME/bin"
  "$HOME/.local/bin"
  /usr/local/bin
  /opt/homebrew/opt/postgresql@18/bin
  "$HOME/.cargo/bin"
  "$HOME/.local/share/bob/nvim-bin"
  "$HOME/.antigravity/antigravity/bin"
  "$HOME/.antigravity-ide/antigravity-ide/bin"
  "$HOME/.opencode/bin"
  "$HOME/Downloads/flutter/bin"
  "$DOTNET_ROOT"
  "$HOME/.dotnet/tools"
  "$HOME/.spicetify"
  "/Applications/Obsidian.app/Contents/MacOS"
  "$HOME/Library/Application Support/JetBrains/Toolbox/scripts"
  $path
)
export PATH
