# dotfiles (macOS)

Gestionados con [chezmoi](https://chezmoi.io).

```bash
brew install chezmoi
chezmoi init --apply antithezis/dotfiles --branch macos
```

Flujo diario: `chezmoi edit <archivo>` o `chezmoi re-add`, luego `chezmoi cd && git commit -am "..." && git push`.
