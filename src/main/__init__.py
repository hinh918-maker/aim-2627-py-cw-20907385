# aim-py-cw-known
# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
import re
from collections import deque
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
MAX_PERCENT = 100
BATTERY_OK_MIN = 60      # battery >= 60 -> OK
BATTERY_LOW_MAX = 20     # battery <= 20 -> LOW, otherwise WARNING


def hp_ratio(hp, max_hp):
    """Hit point percentage as an int clamped to [0, 100]."""
    if max_hp <= 0:
        return 0
    ratio = hp * MAX_PERCENT // max_hp
    return max(0, min(MAX_PERCENT, ratio))


def status_report(name, robot_type, hp, max_hp, battery):
    """One-line self-check report; levels and widths follow the Q1 spec."""
    hp_percent = hp_ratio(hp, max_hp)
    if battery >= BATTERY_OK_MIN:
        level = "OK"
    elif battery > BATTERY_LOW_MAX:
        level = "WARNING"
    else:
        level = "LOW"
    return (f"{name:<10}|{robot_type:^10}|HP {hp_percent:>3}%"
            f"|BAT {battery:>3}%|{level}")


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------


_ARMOR_KEYS = ("front", "left", "right")
_SENSOR_CODE = {"F": "front", "L": "left", "R": "right"}
_SENSOR_RE = re.compile(r"([FLR]):([1-9]\d*)")


def _parse_json_line(line):
    """Validate one JSON log line.

    Return (armor, damage, event_id, has_id) for a valid event, or None
    when the line is dirty and must be skipped.
    """
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    armor = data.get("armor")
    damage = data.get("damage")
    if (armor not in _ARMOR_KEYS
            or not isinstance(damage, int)
            or isinstance(damage, bool)
            or damage <= 0):
        return None
    has_id = "id" in data
    event_id = data.get("id")
    if has_id and (not isinstance(event_id, int)
                   or isinstance(event_id, bool)):
        return None
    return armor, damage, event_id, has_id


def _parse_sensor_line(line):
    """Validate an 'F:32,L:5' line; return [(armor, damage), ...] or None."""
    pairs = _SENSOR_RE.findall(line)
    if not pairs:
        return None
    # Anything left after stripping valid segments/commas means the line
    # carries garbage (e.g. 'F:10;X'): the whole line is dirty.
    residue = _SENSOR_RE.sub("", line).replace(",", "").strip()
    if residue:
        return None
    return [(_SENSOR_CODE[code], int(value)) for code, value in pairs]


def analyze_damage_log(lines):
    """Parse mixed damage logs; skip dirty lines; return Q2 stats dict."""
    events = []
    seen_ids = set()
    for raw_line in lines:
        # Spec rule 3: parsing must never raise; non-text lines are dirty.
        if not isinstance(raw_line, str):
            continue
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{") and line.endswith("}"):
            parsed = _parse_json_line(line)
            if parsed is None:
                continue
            armor, damage, event_id, has_id = parsed
            if has_id:
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)
            events.append((armor, damage))
        else:
            parsed = _parse_sensor_line(line)
            if parsed is None:
                continue
            events.extend(parsed)

    by_armor = {key: 0 for key in _ARMOR_KEYS}
    for armor, damage in events:
        by_armor[armor] += damage
    hit_count = len(events)
    total = sum(damage for _, damage in events)
    most_hit = max(by_armor, key=by_armor.get) if hit_count else None
    avg = round(total / hit_count, 2) if hit_count else 0.0
    return {"total": total, "by_armor": by_armor,
            "most_hit": most_hit, "avg": avg}


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
# World-coordinate rotation tables, shared by SentryGrid turns (Q3),
# greedy alignment and wall following (Q6): one source of geometry truth.
TURN_LEFT_OF = {
    Facing.UP: Facing.LEFT,
    Facing.LEFT: Facing.DOWN,
    Facing.DOWN: Facing.RIGHT,
    Facing.RIGHT: Facing.UP,
}
TURN_RIGHT_OF = {side: front for front, side in TURN_LEFT_OF.items()}
RIGHT_TURN_COUNT = {
    face: index for index, face in enumerate(
        (Facing.UP, Facing.RIGHT, Facing.DOWN, Facing.LEFT))
}


class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        # Reuse the setter so start_pos gets the exact same validation
        # (type, length, clamp, obstacle) as a later current_pos assignment.
        self.current_pos = start_pos

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """Validate, normalize and store the position as a 2-tuple."""
        if not isinstance(value, (tuple, list)):
            raise TypeError("current_pos only accepts tuple or list")
        if len(value) != 2:
            raise TypeError("current_pos must be a coordinate of length 2")
        new_pos = self._clamp_cell(value)
        if new_pos in self._obstacles:
            raise ValueError("current_pos must not be on an obstacle")
        self._pos = new_pos

    def move_forward(self):
        """Move one cell toward the current facing; return the new position."""
        if self._fuel <= 0:
            return self._pos
        dx, dy = self._facing.delta
        next_pos = (self._pos[0] + dx, self._pos[1] + dy)
        if self.is_blocked(*next_pos):
            self._collision_count += 1
            return self._pos
        self._pos = next_pos
        self._fuel -= 1
        return self._pos

    def turn_left(self):
        """Rotate 90 degrees counterclockwise; return the new Facing."""
        self._facing = TURN_LEFT_OF[self._facing]
        return self._facing

    def turn_right(self):
        """Rotate 90 degrees clockwise; return the new Facing."""
        self._facing = TURN_RIGHT_OF[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
_HORIZONTAL_FACINGS = (Facing.RIGHT, Facing.LEFT)
_VERTICAL_FACINGS = (Facing.UP, Facing.DOWN)


def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """Return the Facing of a free neighbor that strictly reduces distance."""
    x, y = pos
    tx, ty = target
    cur_dist = abs(x - tx) + abs(y - ty)
    better = set()
    for facing in Facing:
        dx, dy = facing.delta
        nxt = (x + dx, y + dy)
        if nxt in obstacles:
            continue
        if abs(nxt[0] - tx) + abs(nxt[1] - ty) < cur_dist:
            better.add(facing)
    if not better:
        return current_facing
    if abs(tx - x) > abs(ty - y):
        preferred = _HORIZONTAL_FACINGS + _VERTICAL_FACINGS
    else:
        preferred = _VERTICAL_FACINGS + _HORIZONTAL_FACINGS
    for facing in preferred:
        if facing in better:
            return facing


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


RETREAT_HP_PERCENT = 30   # at/below this HP share the sentry retreats
ENGAGE_RANGE = 3          # enemy within this many cells: shoot
MAX_FRAME_HISTORY = 6     # accepted enemy_frames window length
CONFIRM_FRAMES = 2        # consecutive sightings needed to engage
DEFAULT_MAX_HP = 100


def _engage_action(enemy_dist, is_hero):
    """R4/R6 shared choice: shoot at close range, strafe otherwise."""
    if enemy_dist is not None and enemy_dist <= ENGAGE_RANGE:
        return "SHOOT"
    return "MOVE_RIGHT" if is_hero else "MOVE_LEFT"


def decide(sensor, state, hp, heat):
    """Apply rules R1-R7 in fixed order; return (action, SentryState)."""
    required = ("enemy_frames", "enemy_dist", "robot_type", "max_hp")
    if (not isinstance(sensor, dict)
            or any(key not in sensor for key in required)):
        raise ValueError("sensor is missing required fields")
    if not isinstance(state, SentryState):
        raise ValueError("state must be a SentryState member")
    raw_frames = sensor["enemy_frames"]
    if isinstance(raw_frames, (tuple, list)):
        frames = [bool(frame) for frame in raw_frames]
    else:
        frames = [bool(raw_frames)]
    if not 1 <= len(frames) <= MAX_FRAME_HISTORY:
        raise ValueError("enemy_frames length must be between 1 and 6")
    enemy_dist = sensor["enemy_dist"]
    if (not isinstance(enemy_dist, int)
            or isinstance(enemy_dist, bool)
            or enemy_dist < 0):
        enemy_dist = None
    is_hero = sensor["robot_type"] == "HERO"
    max_hp = sensor["max_hp"]
    if (not isinstance(max_hp, int) or isinstance(max_hp, bool)
            or max_hp <= 0):
        max_hp = DEFAULT_MAX_HP
    try:
        hp_int = int(hp)
    except (TypeError, ValueError):
        hp_int = 0
    hp_pct = max(0, min(MAX_PERCENT,
                        hp_int * MAX_PERCENT // max_hp))
    visible = frames[-1]

    if hp_pct <= RETREAT_HP_PERCENT:
        return ("RETREAT", SentryState.RETREAT)
    if state is SentryState.RETREAT:
        return ("RETURN", SentryState.RETURN)
    if state is SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)
    if state is SentryState.ENGAGE:
        if visible:
            return (_engage_action(enemy_dist, is_hero),
                    SentryState.ENGAGE)
        if len(frames) >= CONFIRM_FRAMES and frames[-2]:
            return ("HOLD_FIRE", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)
    if visible:
        if len(frames) >= CONFIRM_FRAMES and frames[-2]:
            return (_engage_action(enemy_dist, is_hero),
                    SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)
    if state is SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)
    return ("SCAN", SentryState.SUSPECT)


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
WALL_BUDGET_FACTOR = 1.25   # per-hand step budget = factor * (w + h)
WALL_EXIT_MULTIPLIER = 2   # after 2x budget give up wall following
GREEDY_RETURN_MARGIN = 1   # resume greedy only near entry distance
U_TURN_STEPS = 2
LEFT_HAND = "L"
RIGHT_HAND = "R"


def loop_detect_hand(grid, loop_path):
    """True when the current cell was already visited in this wall loop."""
    return grid.current_pos in loop_path


def run_patrol(grid, max_steps=500):
    """Run the sense-decide-act patrol loop; return the Q6 stats dict.

    Greedy moves while a neighbor strictly reduces Manhattan distance;
    on a stall, follow the wall left-handed, switching to the right
    hand when a closed loop is revisited (or after a step budget),
    until greedy progress is available again.
    """
    # Per-hand geometry: which side the hand tracks, the opposite side,
    # and the turn that points the carrier toward each of them.
    hand_side = {LEFT_HAND: TURN_LEFT_OF, RIGHT_HAND: TURN_RIGHT_OF}
    hand_away = {LEFT_HAND: TURN_RIGHT_OF, RIGHT_HAND: TURN_LEFT_OF}

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def cell_at(pos, facing):
        dx, dy = facing.delta
        return (pos[0] + dx, pos[1] + dy)

    def blocked(pos, facing):
        return grid.is_blocked(*cell_at(pos, facing))

    def has_candidate():
        """True when a free neighbor strictly reduces distance."""
        pos = grid.current_pos
        dist = manhattan(pos, grid.enemy_pos)
        return any(
            not blocked(pos, facing)
            and manhattan(cell_at(pos, facing), grid.enemy_pos) < dist
            for facing in Facing)

    def align(facing):
        """Turn in place with fewest turns (turns cost no fuel)."""
        diff = (RIGHT_TURN_COUNT[facing]
                - RIGHT_TURN_COUNT[grid.facing]) % 4
        if diff == 3:
            grid.turn_left()
        else:
            for _ in range(diff):
                grid.turn_right()

    def stick_to_wall(hand):
        """Rotate in place until the chosen hand-side cell is a wall."""
        for _ in Facing:
            if blocked(grid.current_pos, hand_side[hand][grid.facing]):
                return
            if hand == LEFT_HAND:
                grid.turn_left()
            else:
                grid.turn_right()

    def enter_wall_mode(pos):
        """Switch from greedy to left-handed wall following at pos."""
        nonlocal wall_mode, hand, wall_steps, entry_dist, loop_path
        wall_mode = True
        hand = LEFT_HAND
        wall_steps = 0
        entry_dist = manhattan(pos, grid.enemy_pos)
        loop_path = {pos}
        stick_to_wall(hand)

    def switch_hand():
        """Abandon the looping hand; track the wall with the other one."""
        nonlocal hand, wall_steps, loop_path
        hand = RIGHT_HAND
        wall_steps = 0
        loop_path = {grid.current_pos}
        stick_to_wall(hand)

    def follow_wall(pos):
        """Rotate to keep the active hand on the wall; caller then moves."""
        turn_to_hand = (grid.turn_left if hand == LEFT_HAND
                        else grid.turn_right)
        turn_away = (grid.turn_right if hand == LEFT_HAND
                     else grid.turn_left)
        side = hand_side[hand][grid.facing]
        if not blocked(pos, side):
            turn_to_hand()
        elif blocked(pos, grid.facing):
            away = hand_away[hand][grid.facing]
            if not blocked(pos, away):
                turn_away()
            else:
                for _ in range(U_TURN_STEPS):
                    grid.turn_right()

    visited = {grid.current_pos}
    steps = 0
    wall_mode = False
    hand = LEFT_HAND
    wall_steps = 0
    entry_dist = 0
    loop_path = set()
    step_budget = WALL_BUDGET_FACTOR * (grid.width + grid.height)

    while steps < max_steps and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos

        # Enter escape mode exactly when greedy has no improving neighbor.
        if not wall_mode and not has_candidate():
            enter_wall_mode(pos)

        if wall_mode:
            follow_wall(pos)
        else:
            direction = next_step_toward(pos, grid.enemy_pos,
                                         grid.obstacles, grid.facing)
            align(direction)

        grid.move_forward()
        steps += 1
        visited.add(grid.current_pos)

        if not wall_mode:
            continue
        wall_steps += 1

        # Revisited a cell of this wall-following loop: the left hand is
        # circling; switch hands immediately and restart the trail.
        if loop_detect_hand(grid, loop_path) and hand == LEFT_HAND:
            switch_hand()
            continue

        loop_path.add(grid.current_pos)
        if wall_steps > step_budget and hand == LEFT_HAND:
            # Left hand runs too long without progress: switch hands.
            switch_hand()
        elif wall_steps > WALL_EXIT_MULTIPLIER * step_budget:
            wall_mode = False
        elif (has_candidate()
              and manhattan(grid.current_pos, grid.enemy_pos)
              < entry_dist + GREEDY_RETURN_MARGIN):
            wall_mode = False

    found = grid.found_enemy
    return {
        "steps": steps,
        "collisions": grid.collision_count,
        "visited_count": len(visited),
        "found_enemy": found,
        "success": found,
    }


def report_to_json(stats):
    """Serialize stats to a deterministic JSON string (fixed key order)."""
    keys = ("steps", "collisions", "visited_count",
            "found_enemy", "success")
    ordered = {key: stats[key] for key in keys}
    return json.dumps(ordered, ensure_ascii=True)


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """Return the shortest four-neighbor path length.

    Return 0 when start and target are the same cell, and -1 when the
    target is unreachable. Per the Bonus contract, the caller must put
    map boundaries in obstacles.
    """
    if start == target:
        return 0
    blocked = set(obstacles) if obstacles else set()

    queue = deque([(start, 0)])
    visited = {start}
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while queue:
        (x, y), distance = queue.popleft()
        for dx, dy in directions:
            nxt = (x + dx, y + dy)
            if nxt in visited or nxt in blocked:
                continue
            if nxt == target:
                return distance + 1
            visited.add(nxt)
            queue.append((nxt, distance + 1))
    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
