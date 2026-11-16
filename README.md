# dotfiles (macOS)

Gestionados con [chezmoi](https://chezmoi.io) usando `.chezmoiroot` (`home/`).

```bash
brew install chezmoi
chezmoi init --apply antithezis/dotfiles --branch macos
```

## Estructura

- `home/dot_zshenv`: define `XDG_*` y `ZDOTDIR=~/.config/zsh`
- `home/dot_config/`: configuraciones en `~/.config/` (`zsh`, `nvim`, `ghostty`, `git`, `gh`, `bat`, `btop`, `fastfetch`, `herdr`, `karabiner`, `zed`)

Flujo diario: `chezmoi edit <archivo>` o `chezmoi re-add`, luego `chezmoi cd && git commit -am "..." && git push`.
