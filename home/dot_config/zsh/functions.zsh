# =============================================================================
# CUSTOM FUNCTIONS
# =============================================================================

# Claude Code: herdr no responde la consulta de fondo, así que el tema "auto" falla.
# Elegimos dark/light según la apariencia de macOS al arrancar.
claude() {
  local _t=light
  [[ "$(defaults read -g AppleInterfaceStyle 2>/dev/null)" == Dark ]] && _t=dark
  command claude --settings "{\"theme\":\"$_t\"}" "$@"
}

# Buscar contenido en archivos con ripgrep + fzf (rgg)
if command -v rg &> /dev/null && command -v fzf &> /dev/null; then
  fzf-rg() {
    local selected
    selected=$(rg --color=always --line-number --no-heading --smart-case "${*:-}" |
      fzf --ansi \
          --delimiter : \
          --preview 'bat --color=always --highlight-line {2} {1}' \
          --preview-window 'up,60%,border-bottom,+{2}+3/3,~3')
    if [[ -n $selected ]]; then
      local file=$(echo $selected | cut -d: -f1)
      local line=$(echo $selected | cut -d: -f2)
      ${EDITOR:-nvim} "$file" "+$line"
    fi
  }
  alias rgg='fzf-rg'
fi

# Buscar y cambiar ramas de git con fzf (gb)
if command -v git &> /dev/null && command -v fzf &> /dev/null; then
  fzf-git-branch() {
    local branches branch
    branches=$(git --no-pager branch -a --format='%(refname:short)') &&
    branch=$(echo "$branches" | fzf --preview 'git log --oneline --graph --date=short --color=always --pretty="format:%C(auto)%cd %h%d %s" {} | head -200') &&
    git checkout $(echo "$branch" | sed "s/.* //" | sed "s#remotes/origin/##")
  }
  alias gb='fzf-git-branch'
fi

# Ver git log con fzf (gl)
if command -v git &> /dev/null && command -v fzf &> /dev/null; then
  fzf-git-log() {
    git log --graph --color=always \
      --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" "$@" |
    fzf --ansi --no-sort --reverse --tiebreak=index \
      --preview 'grep -o "[a-f0-9]\{7,\}" <<< {} | head -1 | xargs git show --color=always' \
      --bind "enter:execute:grep -o '[a-f0-9]\{7,\}' <<< {} | head -1 | xargs git show | less -R"
  }
  alias gl='fzf-git-log'
fi

# pi con llama-server bajo demanda
_pi_llama_release() {
  pgrep -x pi >/dev/null || launchctl kill TERM "gui/$UID/local.llama-server" 2>/dev/null
}

pi() {
  setopt localoptions localtraps
  local job="gui/$UID/local.llama-server" i rc
  if ! launchctl print "$job" 2>/dev/null | grep -q 'state = running'; then
    launchctl kickstart "$job" >/dev/null
    for i in {1..40}; do
      curl -sf http://127.0.0.1:8080/health >/dev/null && break
      sleep 0.25
    done
  fi
  trap '_pi_llama_release' HUP
  command pi "$@"
  rc=$?
  _pi_llama_release
  return $rc
}

# Fastfetch con animación ASCII de dragón volando sobre montañas (~4s)
fastfetch() {
  if [[ $# -eq 0 && -t 1 && -f "$HOME/.config/fastfetch/dragon_anim.py" ]]; then
    local info
    info="$(command fastfetch --logo-type none --pipe false)"
    FASTFETCH_INFO="$info" python3 "$HOME/.config/fastfetch/dragon_anim.py"
  else
    command fastfetch "$@"
  fi
}
