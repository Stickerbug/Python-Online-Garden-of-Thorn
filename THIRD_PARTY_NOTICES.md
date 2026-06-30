# 第三方来源说明

本项目在仓库中保留了部分第三方数据文件，用于在构建阶段生成聊天审核规则。
游戏服务器运行时不会联网拉取这些第三方仓库。

## fwwdn/sensitive-stop-words

- 来源：<https://github.com/fwwdn/sensitive-stop-words>
- 本地路径：`third_party/moderation/sensitive-stop-words`
- 导入版本：`a7d06bb1c321e669943b6841570d9da6dad8ce2b`
- 许可证：Apache License 2.0
- 许可证文件：`third_party/moderation/sensitive-stop-words/LICENSE`
- 在 GTN 中的用途：`scripts/build_moderation_rules.py` 会把选定的词库文件转换为
  `static/data/moderation_rules.json`。
- 未导入敏感词规则的文件：`stopword.dic`。该文件是通用中文停用词表，不是聊天审核词库。

## Kenney RPG Audio

- 来源：<https://kenney.nl/assets/rpg-audio>
- 本地路径：`static/audio/sfx/ui`、`static/audio/sfx/battle`
- 许可证：Creative Commons Zero 1.0 Universal (CC0)
- 在 GTN 中的用途：按钮、弹窗、卡牌、反制、装备、伤害、回复等轻量音效。
- 说明：Kenney 页面标注该包为 CC0，包含 50 个 RPG/fantasy/foley 音效文件；本项目只选取其中少量
  book、leather、cloth、knife、metal 类短音效，控制体积和带宽。

## 80 CC0 RPG SFX

- 来源：<https://opengameart.org/content/80-cc0-rpg-sfx>
- 作者：rubberduck
- 本地路径：`static/audio/sfx/battle`
- 许可证：Creative Commons Zero 1.0 Universal (CC0)
- 在 GTN 中的用途：替换和补充伤害、灼烧、中毒、回复、资源、反制、装备、回合开始等战斗音效。
- 说明：OpenGameArt 页面标注该包为 CC0；本项目只选取其中少量较小的 OGG 文件，避免增加过多带宽负担。
