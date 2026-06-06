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
