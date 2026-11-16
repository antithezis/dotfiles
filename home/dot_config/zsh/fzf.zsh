# =============================================================================
# KEY BINDINGS & FZF
# =============================================================================
# Aceptar sugerencias de autosuggestions con Ctrl-Y
bindkey '^Y' autosuggest-accept

# Búsqueda en historial basada en el texto ya escrito (Ctrl+P / Ctrl+N)
autoload -U history-search-end
zle -N history-beginning-search-backward-end history-search-end
zle -N history-beginning-search-forward-end history-search-end
bindkey '^P' history-beginning-search-backward-end
bindkey '^N' history-beginning-search-forward-end

# Cargar key bindings y autocompletado de fzf
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
if [[ -f /opt/homebrew/opt/fzf/shell/key-bindings.zsh ]]; then
  source /opt/homebrew/opt/fzf/shell/key-bindings.zsh
  source /opt/homebrew/opt/fzf/shell/completion.zsh
fi

if command -v fzf &> /dev/null; then
  # Función mejorada para historial con fzf (CTRL-H)
  fzf-history() {
    local selected
    selected=$(fc -rl 1 | fzf --tac --no-sort --tiebreak=index --query="$LBUFFER")
    if [[ -n $selected ]]; then
      LBUFFER=$(echo $selected | sed 's/^[ ]*[0-9]*[ ]*//')
      zle redisplay
    fi
  }
  zle -N fzf-history
  bindkey '^H' fzf-history

  # Detectar tema del sistema (macOS)
  if [[ "$(defaults read -g AppleInterfaceStyle 2>/dev/null)" == "Dark" ]]; then
    # Rose Pine (tema oscuro)
    export FZF_DEFAULT_OPTS="
      --height 40%
      --layout=reverse
      --border
      --inline-info
      --color=fg:#e0def4,bg:#191724,hl:#ebbcba
      --color=fg+:#e0def4,bg+:#26233a,hl+:#ebbcba
      --color=info:#9ccfd8,prompt:#c4a7e7,pointer:#f6c177
      --color=marker:#eb6f92,spinner:#f6c177,header:#ebbcba
      --color=border:#6e6a86,gutter:#191724
      --bind 'ctrl-y:accept'"
  else
    # Rose Pine Dawn (tema claro)
    export FZF_DEFAULT_OPTS="
      --height 40%
      --layout=reverse
      --border
      --inline-info
      --color=fg:#575279,bg:#faf4ed,hl:#d7827e
      --color=fg+:#575279,bg+:#f2e9e1,hl+:#d7827e
      --color=info:#56949f,prompt:#907aa9,pointer:#ea9d34
      --color=marker:#b4637a,spinner:#ea9d34,header:#d7827e
      --color=border:#9893a5,gutter:#faf4ed
      --bind 'ctrl-y:accept'"
  fi

  # Usar fd si está disponible (más rápido que find)
  if command -v fd &> /dev/null; then
    export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
  fi

  # Preview con bat si está disponible
  if command -v bat &> /dev/null; then
    export FZF_CTRL_T_OPTS="--preview 'bat --color=always --style=numbers --line-range=:500 {}'"
  fi

  # Preview de directorios con eza
  if command -v eza &> /dev/null; then
    export FZF_ALT_C_OPTS="--preview 'eza --tree --icons --level=2 --color=always {}'"
  fi
fi
