# 卡专用原子改写规则模块

`tools/refactor_card_atoms.py` 启动时会自动加载本目录下所有 `*.py`（文件名以 `_` 开头的除外），
把每个模块里的 `REWRITES = {op 名: builder}` 合并进 `GENERIC_STEP_REWRITES`——
同名时 `refactor_card_atoms.py` 里的内联规则优先。

这样每个卡包/每轮改写可以写自己的模块，并行改不同卡包时不会互相冲突。

约定：

- `builder(params)` 收到原步骤里除 `op`/`type`/`params` 之外展平的参数，返回**新的步骤列表**。
- 只使用通用能力（`mod_runtime_v2.py` 的 op、`ADVANCED_ATOMIC_OPS` 里的通用原子）。
- 规则必须幂等：只有卡数据里还残留该卡专用 op 时才会触发，重复运行不产生变化。
- key 必须是**卡专用 op 名**，不要用通用 op 名（否则会改写所有卡）。
- 保留战报文本用 `log` 模板（`{target}`/`{source}`/`{amount}`/`{count}`/`{status}`/`{name}`）；
  `"log": False` 表示不打印。

运行：

```
python tools/refactor_card_atoms.py                     # 全部卡包
python tools/refactor_card_atoms.py --only "Arctic*"    # 只跑匹配的卡包（可重复 --only）
```
