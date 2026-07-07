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

## PeriTune - Frosylva

- 来源：<https://peritune.com/blog/2026/06/26/frosylva/>
- 作者：PeriTune / むつき醒
- 本地路径：`static/audio/music/frosylva.webm`
- 许可证/使用条款：PeriTune 免费音乐素材使用条款
- 在 GTN 中的用途：主页和大厅背景音乐。
- 说明：PeriTune 条款允许免费使用、商用使用和加工；本项目仍保留来源说明，便于后续审计和替换。

## 临时待授权战斗音乐 - Petal Dance ~ Petal Phantasm

- 来源：<https://www.youtube.com/watch?v=1s_wdcC56FQ>
- 本地路径：`static/audio/music/battle-petal-phantasm.ogg`
- 源文件路径：`static/audio/music/source-pending/petal-dance-petal-phantasm.wav`
- 当前状态：正在取得许可。
- 在 GTN 中的用途：临时战斗背景音乐槽位。
- 说明：该曲目为 Deltarune / Touhou Remix，正式长期使用前应确认授权或替换为明确可用于游戏分发的原创/授权曲目。
