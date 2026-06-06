# Third-Party Notices

This project vendors selected third-party data files for build-time moderation
rule generation. The game server does not fetch these repositories at runtime.

## fwwdn/sensitive-stop-words

- Source: https://github.com/fwwdn/sensitive-stop-words
- Local path: `third_party/moderation/sensitive-stop-words`
- Imported revision: `a7d06bb1c321e669943b6841570d9da6dad8ce2b`
- License: Apache License 2.0
- License file: `third_party/moderation/sensitive-stop-words/LICENSE`
- Usage in GTN: `scripts/build_moderation_rules.py` converts selected word-list
  files into `static/data/moderation_rules.json`.
- Excluded from sensitive-word import: `stopword.dic`, because it is a general
  Chinese stopword list rather than a moderation list.

