# =============================================================================
# ALIASES & TOOL INTEGRATIONS
# =============================================================================
alias vim="nvim"
alias colorscript="$HOME/Documents/Repos/shell-color-scripts/colorscript.sh"

# Zoxide (navegación de directorios inteligente)
if command -v zoxide &> /dev/null; then
  eval "$(zoxide init zsh)"
  alias cd="z"
fi

# EZA Aliases (reemplazo moderno de ls con iconos)
if command -v eza &> /dev/null; then
  alias ls='eza --icons --group-directories-first'
  alias ll='eza -l --icons --group-directories-first --git'
  alias lla='eza -la --icons --group-directories-first --git'
  alias la='eza -la --icons --group-directories-first --git'
  alias lt='eza --tree --icons --level=2 --group-directories-first'
  alias lta='eza --tree --icons --level=2 --group-directories-first -a'
  alias l='eza -lah --icons --group-directories-first --git'
  alias lsiz='eza -lh --icons --group-directories-first --total-size --sort=size'
fi

# BAT Configuration (reemplazo moderno de cat)
if command -v bat &> /dev/null; then
  alias cat='bat --style=auto'
  alias catp='bat --style=plain'
  alias cath='bat --style=header'
  export BAT_THEME="Catppuccin Mocha"
  export BAT_STYLE="numbers,changes,header"
fi
