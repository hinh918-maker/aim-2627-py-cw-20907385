# AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块

> **全部题目、规范、评分、提交见** **[题面.pdf](题面.pdf)。** 本 README 只讲怎么把环境跑起来；没在这里出现的规格细节，一律以题面为准。

## 1. 环境要求

- Python 3.8+，仅标准库（不允许第三方运行时依赖）；
- 开发工具只需 `pytest`（测试）与 `autopep8`（风格，CI 会检查）；
- VS Code 打开仓库会推荐安装 `ms-python.autopep8` 插件（`.vscode/extensions.json`），保存即格式化即可过风格检查。

## 2. 快速开始

```bash
# 1. 用 GitHub 的 Use this template 创建你自己的仓库，然后 clone
git clone https://github.com/<你的用户名>/<你的仓库>.git
cd <你的仓库>   # 直接在 main 分支上开发

# 创建虚拟环境

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. 装依赖
python -m pip install pytest autopep8

# 3. 启用 AI 会话归档钩子（课程要求，见下方第 3 节）
python -m pip install 'agent-session-commit[pre-commit]==0.1.3' -i https://pypi.org/simple
agent-session-commit install --pre-commit   # 交互选择你的 AI 助手与会话目录

# 4. 跑测试（刚到手：全部 skip，CI 是绿的）
python -m pytest

# 5. 看演示
python main.py

# 6. 打开 题面.pdf 读题，开始实现 src/main/__init__.py 里的 TODO
```

## 3. AI 会话归档（pre-commit）

本课程允许使用 AI，提交的 commit 需要携带 AI 会话归档作为透明化记录：每次 `git commit` 后，钩子会把新增会话自动 amend 进同一个提交（`.agent-sessions/bundles/`），不产生额外的归档提交。支持 Claude Code、OpenAI Codex CLI、GitHub Copilot CLI、Qoder、ZCode、Trae、Tencent CodeBuddy 等（完整名单见 [AgentLedger](https://github.com/Gentle-Lijie/AgentLedger)）。

- 配置是仓库本地的：每个 clone 运行一次 `agent-session-commit install --pre-commit`，方向键选择 agent、确认其会话目录即可；
- 不想用 TUI 可手动配置：`git config --local agent-session.agent claude`、`git config --local agent-session.source "<会话目录>"`，然后 `python -m pip install 'pre-commit>=3.2.0' && pre-commit install`；
- 归档是普通 Git 内容且会推送到公开仓库——不要在 AI 会话里粘贴令牌等敏感信息；
- 换了 agent 或目录就重跑一次安装命令；卸载：从 `.pre-commit-config.yaml` 移除该条目后重跑 `pre-commit install`。

## 4. 本地开发循环

- **写代码**：全部作业在 `src/main/__init__.py`，按题面各题规范补全每个标有 TODO 的函数；注释里标注了对应的题面主题，推荐顺序 Q1 → Q6。
- **跑测试**：`python -m pytest` —— 可见测试是规格书的一部分，未实现的函数自动 skip，实现一个、对应测试亮一个。本地全绿 ≠ 满分（见题面）。
- **看演示**：`python main.py`（等价于 `PYTHONPATH=src python -m main`），随实现进度逐段点亮，不进测试。
- **Q6 自测**：`python tools/run_seeds.py --q6`（200 张固定地图统计），单 seed 渲染 `python tools/run_seeds.py --q6 --seed <N> --render`，Bonus 模式 `python tools/run_seeds.py --bonus`。

## 5. 仓库结构（哪些能改）

| 路径                                                                    | 说明                   | 能否修改   |
| --------------------------------------------------------------------- | -------------------- | ------ |
| `src/main/__init__.py`                                                | 你的全部作业（TODO 所在）      | ✅      |
| `README.md`                                                           | 仅末尾两个"你来写"小节         | ✅      |
| `题面.pdf`                                                              | 题面（唯一规格说明）           | ❌ 勿改   |
| `src/main/legacy_patrol.py`                                           | Q7 模块（与主体同步发布，修复其缺陷） | Q7 时 ✅ |
| `.pre-commit-config.yaml`                                             | AI 会话归档钩子配置          | ❌ 勿改   |
| `src/tests/`、`tools/`、`.github/`、`conftest.py`、`pytest.ini`、`main.py` | 测试与基础设施              | ❌ 勿改   |

CI 只允许修改 `src/main/**`、`README.md` 与 `.agent-sessions/**`（AI 会话归档）——其余文件改了直接红；autopep8 `--diff` 非空即败。提交方式（push、问卷、commit 粒度）见题面"提交与验收"一节。

## 6. 设计决策

### Q1 机器人自检

- **血量百分比用整数运算** `hp * 100 // max_hp`，再用`max(0, min(100, ...))`限制取值范围，避免浮点精度问题。\
  整除即向下取整，`hp_ratio(2, 3) = 66`，与样例演示保持一致。
- **电量阈值归属**：`battery >= 60 → OK`、`> 20 → WARNING`、否则 `LOW`，即 60 归 OK、20 归 LOW。\
  演示中 `BAT 20% → LOW` 验证了该选择。
- 报告模板严格按题面格式说明符（`<10` / `^10` / `>3`）书写；超长行利用括号内相邻字符串字面量自动拼接拆成两行，满足 79 列限制且运行时零开销。

### Q2 战斗日志分析

- **"严格正整数"的解释**：damage 必须满足 `isinstance(x, int) and x > 0`；显式排除 `bool`（Python 中 `bool` 是 `int` 子类）。0、负数、浮点、布尔一律按脏行跳过。
- **传感器行做整行合法性校验**：正则提取 `F/L/R:数字` 段后，再检查剔除合法段与逗号后是否有残留字符，防止 `F:10 boom` 这类"部分合法"行被部分计入。
- **id 去重**：仅带 `id` 的 JSON 行参与去重，非整数 id 按脏行处理；不带 id 的 JSON 行独立计数；传感器行无 id 概念。
- **统计契约**：`avg = round(total / 事件数, 2)`，无有效事件时为 `0.0`；`most_hit` 无事件时为 `None`；`by_armor` 三键在任何输入下恒存在。解析全程吞掉 JSON 异常与非 dict 结果，保证不抛出。

### Q3 SentryGrid

- **方向语义只有一个事实源**：移动位移直接取骨架枚举的 `Facing.delta`（世界坐标 y 向上，`UP=(0,1)`），不再手写四分支，杜绝朝向与枚举不一致。
- **碰撞语义**：前方格为障碍**或越界**（统一走 `is_blocked`）时位置/朝向不变、`collision_count += 1`、**不耗电**；正常移动才扣 1 电量。
- **断电语义**：`fuel <= 0` 时前进直接返回原位，不产生位移、不计碰撞。
- setter 只接受长度 2 的 tuple/list，否则 TypeError；元素经 `_clamp_cell` 规范化（越界夹回地图）并以 tuple 存储；落在障碍物上抛 ValueError。

### Q4 贪心导航

- 候选 = 四邻域中"非障碍且曼哈顿距离**严格**减小"的方向（持平不算候选）；无候选返回 `current_facing`。
- **平局打破**：先按目标绝对差较大的轴选向，轴内再按固定顺序（水平 RIGHT→LEFT、竖直 UP→DOWN）取第一个候选，保证结果完全确定。
- 按规范 4 不感知地图边界，界外方向的拦截交给 `SentryGrid.move_forward`；凹形死角失速是已知局限，留给 Q6 脱困。

### Q5 哨兵决策机

- 严格按 **R1→R7 固定顺序**求值，首条命中即返回；用辅助函数 `_engage_action` 统一 R4 与 R6 完全相同的"敌距 ≤3 射击、否则 HERO 右移 / 步兵左移"判定，避免两处复制产生分叉。
- **契约外输入（抛 ValueError）**：sensor 缺任一字段或非 dict；state 不是 SentryState 成员；enemy\_frames 为空或长度超过 6。
- **字段存在但值非法（防御式归一，不抛异常）**：非法 enemy\_dist 按 `None`（视为远距）；非法 robot\_type 按步兵；非法 max\_hp 兜底为 100；帧元素一律按真值解释；bool 不计作合法整数。
- **R5 短暂/持续丢失**：当前帧为假时，前一帧为真 → `HOLD_FIRE`（短暂丢失），否则 → `SCAN`（持续丢失），与 R6"末两帧双确认"对称。`heat` 参数在 R1–R7 中无引用，按纯函数签名保留但不参与决策。

### Q6 巡逻任务

- **失速判定不能依赖** **`next_step_toward`** **的返回值**：它返回 `current_facing` 同时覆盖"正前方本身就是贪心更优格"和"无任何更优邻格"两种情况。主循环另写 `has_candidate()`（四邻域存在严格缩短曼哈顿距离的空格），仅在完全无候选时切入脱困，避免直行时误判失速。
- **脱困采用沿墙走（左手法则）+ 闭环检测换手**：贴墙时优先手侧边格、否则直行、否则反向转或掉头，每一步只走进确认可通行的格子，因此碰撞数恒为 0。记录本轮沿墙已走过的格子，**一旦重复踩回（左手在闭合环路上绕圈）立刻换右手**；同时保留 `1.25 × (width + height)` 步的固定预算作为兜底换手、`2 ×` 预算后整体退出沿墙模式重新评估；到达"存在贪心候选且距离比进入点近（`entry + 1`）"的格子时提前切回贪心。**切入沿墙（及每次换手）时先原地转向让手侧格贴住墙再起步**：若沿贪心原朝向切入时手侧恰为开阔空地，沿墙第一步就会离开墙面绕远，这是 seed 180 死循环的根因。
- **转向用最少次数对齐**（差 3 格时一次左转，否则右转）：转向不耗电也不计入 steps，steps 只统计 `move_forward` 次数，与 `tools/run_seeds.py` 的 BFS 步数比口径一致。
- **200 张固定地图实测**：成功率 **100.0%**（阈值 92%）、平均碰撞 0.00（阈值 1.5）、成功步数/BFS 比均值 1.08（阈值 1.35）；seed 201–500 复验同为 100% / 1.07。迭代三版：固定预算换手 93.5% / 1.20 → 加闭环检测换手 99.5% / 1.15 → 再加"切入即贴墙"初始化 100% / 1.08。对 0.75/1/1.25 倍预算做过参数扫描，1.25 倍综合最优。
- **`report_to_json`** **确定性**：按契约固定五键顺序重建 dict 后 `json.dumps(..., ensure_ascii=True)`，默认紧凑分隔符，任何键序的输入都产生同一字符串。
- `visited_count` 统计包含起点在内的所有到过位置的去重数；`found_enemy` 与 `success` 同取 `grid.found_enemy`（bool）。

### Q7 Debug（六处缺陷定位）

1. **`total_route_meters`：厘米当米累加**——`segment_length_cm` 返回值单位是厘米（格 ×100），求和后直接赋给 `distance_in_meters`。定位：跑 `[(0,0),(3,0),(3,4)]` 得 700 而非 7，除以 100 修正。
2. **`calibrate`：`first_positive`** **返回 None 时崩溃**——`s - baseline` 中 None 参与算术运算抛 TypeError；被遮蔽的是"空列表/无正数样本时 drift 应为 0"的契约。修正：None 时提前返回 0。
3. **`summarize_events`：`<`** **应为** **`<=`**——`id == max_id` 的事件被漏统计。定位：构造 `id=2, max_id=2` 的用例，期望 2 条实测 1 条。
4. **`log`：可变默认参数陷阱**——`history=[]` 在函数定义时创建一次、被所有调用共享，多次调用历史不断累积。修正：`history=None` + 函数体判空新建。
5. **`run_legacy_sim`：终止条件写反**——`if stamina > 20: break` 是"体力充足才停"，与契约"<=20 立即终止"相反。
6. **`run_legacy_sim`：while 循环缺** **`round_ += 1`**——计数器不自增，`round_ < rounds` 永真，死循环。与第 5 条互相遮蔽：条件写反时永远不进入 `break` 分支，缺自增不暴露；先修条件后死循环才显现。

### 代码结构约定（重构后）

- **题面规则数字一律命名常量**：电量档（`BATTERY_OK_MIN/LOW_MAX`）、撤退血量 `RETREAT_HP_PERCENT`、射击距离 `ENGAGE_RANGE`、帧窗 `MAX_FRAME_HISTORY`、沿墙预算 `WALL_BUDGET_FACTOR` 等，判据处只出现语义名；Q7 遗留模块的 100/8/5/3/20 同样命名。
- **几何表只有一份**：朝向左旋/右旋/右转次数三张表集中为模块级 `TURN_LEFT_OF / TURN_RIGHT_OF / RIGHT_TURN_COUNT`，Q3 载体转向、Q4 朝向对齐、Q6 贴墙共用，消除原先三处手抄字典。
- **Q2 解析按职责拆分**：`_parse_json_line` / `_parse_sensor_line` 各管一种格式的校验，`analyze_damage_log` 只做遍历、去重与汇总；有效事件先收集成列表再统一统计，累加逻辑只有一处。
- **Q6 主循环保持在一屏内**：进入脱困、换手、单步贴墙分别是 `enter_wall_mode / switch_hand / follow_wall` 三个单一职责的嵌套函数，两处换手触发点共用 `switch_hand`，左右手差异用 `hand_side/hand_away` 映射表达，不再有按手分支的重复 if-else。
- 重构以"不改变行为"为前提：重构后可见测试 34 passed、500 seed 仍为 100% / 0.00 碰撞 / 1.08 步比。

### Bonus

- （待实现后补充：BFS 替换贪心后的排行榜数据。）

## 7. 踩坑记录

<br />

1. **浮点取整导致低血量误差（Q1）**：初版 `int(hp / max_hp * 100)` 在 `hp=29` 时返回 28——`29/100*100` 经过二进制浮点得到 `28.999...`，截断后少 1。改为先乘后整除 `hp * 100 // max_hp`，全程不经过 float。教训：涉及百分比/分数的整数结果，优先整数运算。
2. **屏幕坐标与数学坐标混淆（Q3/Q4）**：初版按屏幕习惯写 `UP → y-1`，与骨架"y 向上增长、`UP=(0,1)`"相反，演示时哨兵面朝上却往地图外走。修复方式是不手写方向分支、直接使用 `Facing.delta`，让枚举成为唯一事实源。
3. **文件中部重复粘贴枚举定义（Q4/Q5）**：草稿把 `class Facing` / `class SentryState` 连同 `from enum import Enum` 粘到了题目分区之间，中部的值为字符串的新类遮蔽了顶部带 `delta` 的真类，导致 Q3/Q4 行为错乱。修复：删除重复定义，import 只保留文件顶部一处。以后不把 import/类定义粘到函数之间。
4. **嵌套同名函数使逻辑永不执行（Q2）**：初版在 `analyze_damage_log` 内部又定义了同名函数但从不调用，外层返回 `None`，可见测试全部 skip。修复：拍平为单函数，正则编译为模块级常量。
5. **`return`** **之后留** **`raise NotImplementedError`（Q1）**：占位语句没删干净，虽不影响结果但是死代码，人工评阅会扣可读性分。每次替换桩函数时确认 `raise` 整行删除。
6. **裸跑** **`python -m pytest`** **会卡死**：不带路径时会收集 `src/tests/test_legacy.py`（Q7），而 `legacy_patrol.py` 里循环计数器不自增（Q7 故意埋的缺陷），进程无限循环只能强杀。Q7 修完前固定使用 `python -m pytest src/tests/test_main.py`。
7. **macOS 没有** **`python`** **命令、pytest 只在虚拟环境里**：系统只有 `python3` 且未装 pytest。需在 VS Code 选中 `.venv/bin/python` 解释器（或 `source .venv/bin/activate`）后再跑测试与演示。
8. **编辑器未保存缓冲区与磁盘内容不一致**：曾出现测试读到的磁盘文件仍是骨架（全部 skip），而编辑器标签页里是新草稿的现象；中途外部写入磁盘后，若标签页有白点又按保存，旧草稿还会反向覆盖磁盘。避免方式：以 pytest 实际加载结果为准；外部改动后用命令面板 `Revert File` 从磁盘重新加载，不盲目保存。
9. **白名单外文件被误暂存**：`.vscode/settings.json`、`requirements.txt` 不在 CI 白名单，曾被 `git add` 带入暂存区。提交前用 `git status --short` 核对，只 `git add src/main/__init__.py README.md`，不用 `git add .`。
10. **用 Q4 返回值等于当前朝向来判断"失速"（Q6）**：`next_step_toward` 返回 `current_facing` 有两种含义——正前方就是最优格，或根本无更优邻格。初版只比较返回值，导致直路也频繁切入沿墙，步数比超标。修复：单独扫描四邻域判断是否存在严格缩短距离的候选。
11. **文件中部出现** **`import json`（Q6）**：顶部 Q2 已有同名导入，函数之间再写一次属于重复导入且违反 E402（import 必须在文件顶部），autopep8/CI 风格检查会报。修复：删除中部导入，复用顶部那一个。
12. **固定步数预算换手会在环路里空转（Q6）**：第一版脱困 200 张地图成功率 93.5%，刚过 92% 阈值。逐张解剖 13 张失败地图（程序化记录终止原因、进脱困次数、换手次数，而非盯 `--render` 动画）发现全部是 500 步耗尽、在闭合沿墙环路上反复"进入→换手→再进入"，而 BFS 最短路只有 27–36 步。修复：记录本轮沿墙轨迹，重复踩回已访问格即判为闭环、立即换手。结果成功率升到 99.5%、步数比反从 1.20 降到 1.15。教训：成功率贴阈值时先按统一特征归类失败案例，再针对根因改判据，而不是盲目调时间常数。
13. **切入沿墙时初始朝向没贴墙导致唯一失败（Q6 seed 180）**：闭环换手后 200 张仍有 seed 180 跑满 500 步。解剖发现 BFS 最短路仅 30 步、终点距敌人只有 4 格，且每 \~102 步在同一组格子重复、真正出口 `(11,16)` 被踩 0 次。根因：贪心在 `(10,16)` 平局时按竖直优先走进死胡同，切入沿墙时保持原朝向 UP，左手侧 `(9,17)` 恰好是开阔地，沿墙第一步就离开墙面、永远绕过出口。修复：切入沿墙和每次换手后先原地转向，直到手侧格是障碍再起步。修复后 200 张 100%、步数比反降到 1.08——贴对墙后绕路更少。教训：沿墙法的正确性不仅是"沿墙规则"，还取决于进入时是否真的贴在墙上。
14. **传感器行 0 值被当成有效伤害（Q2）**：初版正则 `([FLR]):(\d+)` 会匹配 `F:0`，而题面规范第 5 条要求每段必须是"字母:**正整数**"。后果：`F:0` 虽不加 total，却让 `hit_count` 多计一次，`most_hit` 错误地变成 `"front"`、`avg` 被摊薄；`F:10,L:0` 本应整行判脏，却只计入了 F:10。修复：正则改为 `([FLR]):([1-9]\d*)`，0 值段不匹配后，整行走残留检查被判脏跳过。
15. **构造函数与 setter 校验不一致（Q3）**：初版构造 `start_pos` 直接调 `_clamp_cell`，导致长度 3 的元组被静默截断成 2 维、字符串 `"ab"` 抛 ValueError 而非 setter 规定的 TypeError。题面明确建议构造复用 setter。修复：构造末尾改为 `self.current_pos = start_pos`，类型/长度/夹取/障碍四类校验从此只有一条路径。
16. **负敌距被当作"贴脸"（Q5）**：`enemy_dist=-5` 是非法读数，但旧代码只排除非 int 与 bool，-5 通过 `<= 3` 判据直接返回 SHOOT。修复：归一化时把负数与非 int、bool 一并按 `None`（未知距离→不满足近距→侧移）处理；合法的 0–3 仍正常 SHOOT。
17. **同一张朝向旋转表抄了三遍（DRY）**：Q3 的 `turn_left/turn_right`、Q6 的 `left_of/right_of/right_turns` 各自维护一份函数字典——改朝向语义要动三处、漏一处就出隐蔽 bug。重构时合并为模块级三张表，三处共用；重构后用"连转四次回原朝向"和 500 seed 回归证明行为不变。教训：重复数据比重复代码更危险，应先抽成单一事实源再写逻辑。
18. **超长函数与魔法数字会掩盖控制流意图（Q6/Q2）**：`run_patrol` 一度近 150 行、内嵌两轮几乎相同的换手代码；`analyze_damage_log` 把两种格式解析、校验、去重、统计全揉在一个 for 里。重构时按"每函数只做一件事"拆出 `enter_wall_mode/switch_hand/follow_wall` 与两个行解析器，主循环因此能直接读成"贪心→卡住→贴墙→换手→回到贪心"的状态流；顺手补上 Q2 对非字符串行（如 `None`、数字）的跳过，落实规范第 3 条"全程不得抛异常"。教训：先保证测试与 seed 基线，再做纯结构重构，每步用同一组指标验收。
19. **Q7 `parse_event` 未对非字符串输入做防御（隐藏测试）**：`parse_event` 契约明确"脏行返回 None（不得抛异常）"，但初版直接对 `line` 调用 `.strip().split(",")`。非字符串（`None`、`123`、字节串）会抛 `AttributeError` 或 `TypeError`，违反契约。本地测试 `test_parse_event` 只给了字符串输入，因此全绿。修复：开头加 `if not isinstance(line, str): return None`。教训：凡是契约写了"不得抛异常"的函数，第一条语句就该判断输入类型，不要假设调用方只传字符串。

