# GTN Audio Assets

This directory contains optional audio assets.

Recommended layout:

- `music/` for background music loops.
- `sfx/ui/` for button and panel sounds.
- `sfx/battle/` for card, damage, heal, counter, and equipment sounds.

The current client plays bundled OGG files and does not synthesize fallback tones.

Current bundled SFX are selected from Kenney RPG Audio and OpenGameArt CC0 RPG packs:

- Source: https://kenney.nl/assets/rpg-audio
- License: Creative Commons Zero 1.0 Universal
- Local selection: book, leather, cloth, knife, and metal Foley sounds suited for
  card and light fantasy UI feedback.
- Source: https://opengameart.org/content/80-cc0-rpg-sfx
- License: Creative Commons Zero 1.0 Universal
- Local selection: soft impact, slime, fire spell, gem, metal, and spell sounds.

Audio direction:

- Keep UI sounds short, soft, and tactile. Prefer paper, cloth, wood, light bell,
  and gentle switch sounds over synth beeps or heavy impacts.
- Use `ui_error` only for real errors or disabled actions. Close, cancel, decline,
  and return actions should use `ui_close`, not an impact-like warning.
- Invitation and social prompts use `ui_invite`, a brighter notice slot that can
  be replaced without touching game logic.
- If adding more assets, prefer matching CC0 Kenney packs such as UI Audio or
  Interface Sounds, and choose only a few small OGG files instead of bundling
  entire packs.

When adding downloaded assets, keep files small and include license/source notes
in `THIRD_PARTY_NOTICES.md`.
