from __future__ import annotations
import math

# Dev testing flags — set DEV_FORCE_TASK to a Task name string to force that task, or None for normal
DEV_FORCE_TASK = "watch_mouse"
DEV_SHORT_WANDER = True
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMetaObject, Qt

from pygoose.engine.vector2 import Vector2
from pygoose.engine.math_utils import lerp, clamp, random_range
from pygoose.engine.easings import cubic_ease_in_out
from pygoose.engine.rig import Rig
from pygoose.engine.deck import Deck
from pygoose.engine.time_keeper import TimeKeeper, DELTA_TIME
from pygoose.goose.renderer import update_rig, render_goose, render_foot_marks
from pygoose.goose.cursor import set_cursor_clip, release_cursor_clip, is_left_mouse_down
from pygoose.goose.sound import Sound


# ---------------------------------------------------------------------------
# Speed tiers
# ---------------------------------------------------------------------------

class SpeedTier(Enum):
    WALK = "walk"
    RUN = "run"
    CHARGE = "charge"

SPEEDS = {
    SpeedTier.WALK:   {"speed": 80.0,  "acceleration": 1300.0, "step_time": 0.2},
    SpeedTier.RUN:    {"speed": 200.0, "acceleration": 1300.0, "step_time": 0.2},
    SpeedTier.CHARGE: {"speed": 400.0, "acceleration": 2300.0, "step_time": 0.1},
}


# ---------------------------------------------------------------------------
# Task enum
# ---------------------------------------------------------------------------

class Task(Enum):
    WANDER = "wander"
    NAB_MOUSE = "nab_mouse"
    COLLECT_WINDOW_MEME = "collect_window_meme"
    COLLECT_WINDOW_NOTEPAD = "collect_window_notepad"
    COLLECT_WINDOW_EXEC = "collect_window_exec"
    TRACK_MUD = "track_mud"
    WATCH_MOUSE = "watch_mouse"


TASK_WEIGHTED_LIST = [
    Task.TRACK_MUD,
    Task.TRACK_MUD,
    Task.COLLECT_WINDOW_MEME,
    Task.COLLECT_WINDOW_MEME,
    Task.COLLECT_WINDOW_NOTEPAD,
    Task.NAB_MOUSE,
    Task.NAB_MOUSE,
    Task.NAB_MOUSE,
    Task.WATCH_MOUSE,
    Task.WATCH_MOUSE,
]


# ---------------------------------------------------------------------------
# Screen direction
# ---------------------------------------------------------------------------

class ScreenDirection(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"


# ---------------------------------------------------------------------------
# Wander state
# ---------------------------------------------------------------------------

@dataclass
class WanderState:
    wander_start_time: float
    wander_duration: float
    pause_start_time: float = -1.0
    pause_duration: float = 0.0

WANDER_GOOD_ENOUGH_DIST = 20.0


# ---------------------------------------------------------------------------
# CollectWindow state
# ---------------------------------------------------------------------------

class CollectWindowStage(Enum):
    WALKING_OFFSCREEN = "walking_offscreen"
    WAITING_TO_BRING_WINDOW_BACK = "waiting_to_bring_window_back"
    DRAGGING_WINDOW_BACK = "dragging_window_back"

WAIT_TIME_MIN = 2.0
WAIT_TIME_MAX = 3.5

@dataclass
class CollectWindowState:
    stage: CollectWindowStage = CollectWindowStage.WALKING_OFFSCREEN
    screen_direction: "ScreenDirection | None" = None
    main_window: object = None
    window_offset_to_beak: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    wait_start_time: float = 0.0
    secs_to_wait: float = 0.0
    window_closed_early: bool = False


# ---------------------------------------------------------------------------
# NabMouse state
# ---------------------------------------------------------------------------

class NabMouseStage(Enum):
    SEEKING_MOUSE = "seeking_mouse"
    DRAGGING_MOUSE_AWAY = "dragging_mouse_away"
    DECELERATING = "decelerating"

MOUSE_GRAB_DISTANCE = 15.0
MOUSE_SUCC_TIME = 0.06
MOUSE_DROP_DISTANCE = 30.0
GIVE_UP_TIME = 9.0
STRUGGLE_RANGE = Vector2(3.0, 3.0)

@dataclass
class NabMouseState:
    stage: NabMouseStage = NabMouseStage.SEEKING_MOUSE
    chase_start_time: float = 0.0
    grabbed_time: float = 0.0
    original_vector_to_mouse: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    drag_to: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))


# ---------------------------------------------------------------------------
# TrackMud state
# ---------------------------------------------------------------------------

class TrackMudStage(Enum):
    DECIDE_TO_RUN = "decide_to_run"
    RUNNING_OFFSCREEN = "running_offscreen"
    RUNNING_WANDERING = "running_wandering"

TRACK_MUD_DURATION = 15.0
DIR_CHANGE_INTERVAL = 100.0
AMOK_DURATION = 2.0

@dataclass
class TrackMudState:
    stage: TrackMudStage = TrackMudStage.DECIDE_TO_RUN
    next_dir_change_time: float = 0.0
    time_to_stop_running: float = 0.0


# ---------------------------------------------------------------------------
# WatchMouse state
# ---------------------------------------------------------------------------

WATCH_MOUSE_DURATION_MIN = 8.0
WATCH_MOUSE_DURATION_MAX = 16.0
BOB_INTERVAL_MIN = 1.2
BOB_INTERVAL_MAX = 3.5
BOB_DURATION = 0.35
WATCH_HONK_INTERVAL_MIN = 5.0
WATCH_HONK_INTERVAL_MAX = 12.0
WATCH_SUB_DURATION_MIN = 2.0
WATCH_SUB_DURATION_MAX = 5.0

class WatchSubState(Enum):
    STAND_STILL = "stand_still"
    WALK_SLOW   = "walk_slow"
    SIT         = "sit"
    CRAWL       = "crawl"  # sit pose while moving — reserved for future use

SIT_MIN_DURATION = 15.0

@dataclass
class WatchMouseState:
    start_time: float
    duration: float
    next_bob_time: float
    next_honk_time: float
    bob_end_time: float = -1.0
    sub_state: WatchSubState = WatchSubState.WALK_SLOW
    next_sub_change_time: float = 0.0
    sit_entered_time: float = -1.0


# ---------------------------------------------------------------------------
# Foot mark
# ---------------------------------------------------------------------------

FOOT_MARK_BUFFER_SIZE = 64

@dataclass
class FootMark:
    position: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    time: float = 0.0


# ---------------------------------------------------------------------------
# Goose
# ---------------------------------------------------------------------------

FEET_DISTANCE_APART = 6.0
OVERSHOOT_FRACTION = 0.4
WANT_STEP_AT_DISTANCE = 5.0


class Goose:
    def __init__(self, config=None):
        self.config = config

        screen = QApplication.primaryScreen().geometry()
        self.screen_w = float(screen.width())
        self.screen_h = float(screen.height())

        self.position = Vector2(-20.0, 120.0)
        self.velocity = Vector2.zero
        self.direction = 0.0
        self.target_pos = Vector2(100.0, 150.0)

        self.current_speed = SPEEDS[SpeedTier.WALK]["speed"]
        self.current_acceleration = SPEEDS[SpeedTier.WALK]["acceleration"]
        self.step_time = SPEEDS[SpeedTier.WALK]["step_time"]

        self.rig = Rig()
        self.override_extend_neck = False

        # Feet
        self.l_foot_pos = Vector2(self.position.x - FEET_DISTANCE_APART, self.position.y)
        self.r_foot_pos = Vector2(self.position.x + FEET_DISTANCE_APART, self.position.y)
        self.l_foot_move_origin = Vector2.zero
        self.r_foot_move_origin = Vector2.zero
        self.l_foot_move_dir = Vector2.zero
        self.r_foot_move_dir = Vector2.zero
        self.l_foot_move_time_start = -1.0
        self.r_foot_move_time_start = -1.0

        # Footmarks
        self.foot_marks = [FootMark() for _ in range(FOOT_MARK_BUFFER_SIZE)]
        self.foot_mark_index = 0
        self.track_mud_end_time = -1.0

        # Task
        self.task_picker_deck = Deck(len(TASK_WEIGHTED_LIST))
        self.current_task = Task.WANDER
        self.task_wander: WanderState | None = None
        self.task_track_mud: TrackMudState | None = None
        self.task_nab_mouse: NabMouseState | None = None
        self.task_collect_window: CollectWindowState | None = None
        self.task_watch_mouse: WatchMouseState | None = None

        # Window placed — watch for angry close
        self._placed_window = None
        self._placed_window_time = -1.0
        self._placed_window_closed = False
        self._placed_window_permanent = False  # if True, anger never expires

        # Mouse polling state
        self._last_mouse_down = False

        self._target_sit_lerp = 0.0
        self._target_neck_tuck = 0.0
        self._freeze_position = False

        self.sound = Sound(silence=config.silence_sounds if config else False)
        self.time_keeper = TimeKeeper()
        self._set_task(Task.WANDER, honk=False)

    # -----------------------------------------------------------------------
    # Public
    # -----------------------------------------------------------------------

    def tick(self):
        self.time_keeper.tick()
        self._check_placed_window()
        self._check_petting()
        self._run_physics()
        self._solve_feet()
        self._update_neck()
        self.rig.sit_lerp_percent       = lerp(self.rig.sit_lerp_percent,       self._target_sit_lerp,  0.06)
        self.rig.neck_tuck_lerp_percent = lerp(self.rig.neck_tuck_lerp_percent, self._target_neck_tuck, 0.06)

    def render(self, painter):
        render_foot_marks(painter, self.foot_marks, self.time_keeper.time)
        update_rig(self.position, self.direction, self.rig)
        render_goose(
            painter, self.rig, self.position, self.direction,
            self.l_foot_pos, self.r_foot_pos,
            self.config,
        )

    # -----------------------------------------------------------------------
    # Speed
    # -----------------------------------------------------------------------

    def _set_speed(self, tier: SpeedTier):
        self.current_speed = SPEEDS[tier]["speed"]
        self.current_acceleration = SPEEDS[tier]["acceleration"]
        self.step_time = SPEEDS[tier]["step_time"]

    # -----------------------------------------------------------------------
    # Physics
    # -----------------------------------------------------------------------

    def _run_physics(self):
        # Compute target direction before AI updates target_pos (matches original order)
        to_target = Vector2.normalize(self.target_pos - self.position)

        self._run_ai()

        # Turn toward target (lerp angle 25% per frame)
        if not (to_target.x == 0.0 and to_target.y == 0.0):
            current_dir_vec = Vector2.get_from_angle_degrees(self.direction)
            blended = Vector2.lerp(current_dir_vec, to_target, 0.25)
            self.direction = math.degrees(math.atan2(blended.y, blended.x))

        if self._freeze_position:
            self.velocity = Vector2(0.0, 0.0)
            return

        # Cap velocity
        mag = Vector2.magnitude(self.velocity)
        if mag > self.current_speed:
            self.velocity = Vector2.normalize(self.velocity) * self.current_speed

        # Accelerate toward target
        self.velocity += Vector2.normalize(self.target_pos - self.position) * self.current_acceleration * DELTA_TIME

        # Integrate
        self.position += self.velocity * DELTA_TIME

    # -----------------------------------------------------------------------
    # Foot solver
    # -----------------------------------------------------------------------

    def _get_foot_home(self, right_foot: bool) -> Vector2:
        b = 1.0 if right_foot else 0.0
        side = Vector2.get_from_angle_degrees(self.direction + 90.0) * b
        return self.position + side * FEET_DISTANCE_APART

    def _solve_feet(self):
        t = self.time_keeper.time

        if self.l_foot_move_time_start < 0 and self.r_foot_move_time_start < 0:
            if Vector2.distance(self.l_foot_pos, self._get_foot_home(False)) > WANT_STEP_AT_DISTANCE:
                self.l_foot_move_origin = Vector2(self.l_foot_pos.x, self.l_foot_pos.y)
                self.l_foot_move_dir = Vector2.normalize(self._get_foot_home(False) - self.l_foot_pos)
                self.l_foot_move_time_start = t
            elif Vector2.distance(self.r_foot_pos, self._get_foot_home(True)) > WANT_STEP_AT_DISTANCE:
                self.r_foot_move_origin = Vector2(self.r_foot_pos.x, self.r_foot_pos.y)
                self.r_foot_move_dir = Vector2.normalize(self._get_foot_home(True) - self.r_foot_pos)
                self.r_foot_move_time_start = t

        elif self.l_foot_move_time_start > 0:
            target = self._get_foot_home(False) + self.l_foot_move_dir * OVERSHOOT_FRACTION * 5.0
            elapsed = t - self.l_foot_move_time_start
            if elapsed <= self.step_time:
                p = elapsed / self.step_time
                self.l_foot_pos = Vector2.lerp(self.l_foot_move_origin, target, cubic_ease_in_out(p))
            else:
                self.l_foot_pos = target
                self.l_foot_move_time_start = -1.0
                self.sound.play_pat()
                if t < self.track_mud_end_time:
                    self._add_foot_mark(self.l_foot_pos)

        elif self.r_foot_move_time_start > 0:
            target = self._get_foot_home(True) + self.r_foot_move_dir * OVERSHOOT_FRACTION * 5.0
            elapsed = t - self.r_foot_move_time_start
            if elapsed <= self.step_time:
                p = elapsed / self.step_time
                self.r_foot_pos = Vector2.lerp(self.r_foot_move_origin, target, cubic_ease_in_out(p))
            else:
                self.r_foot_pos = target
                self.r_foot_move_time_start = -1.0
                self.sound.play_pat()
                if t < self.track_mud_end_time:
                    self._add_foot_mark(self.r_foot_pos)

    # -----------------------------------------------------------------------
    # Neck lerp
    # -----------------------------------------------------------------------

    def _update_neck(self):
        target_neck = 1.0 if (self.override_extend_neck or self.current_speed >= 200.0) else 0.0
        self.rig.neck_lerp_percent = lerp(self.rig.neck_lerp_percent, target_neck, 0.075)

    # -----------------------------------------------------------------------
    # Foot marks
    # -----------------------------------------------------------------------

    def _add_foot_mark(self, pos: Vector2):
        self.foot_marks[self.foot_mark_index].time = self.time_keeper.time
        self.foot_marks[self.foot_mark_index].position = Vector2(pos.x, pos.y)
        self.foot_mark_index = (self.foot_mark_index + 1) % FOOT_MARK_BUFFER_SIZE

    # -----------------------------------------------------------------------
    # AI dispatcher
    # -----------------------------------------------------------------------

    def _run_ai(self):
        if self.current_task == Task.WANDER:
            self._run_wander()
        elif self.current_task == Task.TRACK_MUD:
            self._run_track_mud()
        elif self.current_task == Task.NAB_MOUSE:
            self._run_nab_mouse()
        elif self.current_task in (Task.COLLECT_WINDOW_NOTEPAD, Task.COLLECT_WINDOW_MEME, Task.COLLECT_WINDOW_EXEC):
            self._run_collect_window()
        elif self.current_task == Task.WATCH_MOUSE:
            self._run_watch_mouse()

    # -----------------------------------------------------------------------
    # Placed window anger check
    # -----------------------------------------------------------------------

    def _check_placed_window(self):
        if self._placed_window is None:
            return
        t = self.time_keeper.time
        if self._placed_window_closed:
            self._placed_window = None
            self._placed_window_closed = False
            self._set_task(Task.NAB_MOUSE)
        elif not self._placed_window_permanent and t - self._placed_window_time >= 3.0:
            self._placed_window = None

    def _on_placed_window_closed(self):
        self._placed_window_closed = True

    # -----------------------------------------------------------------------
    # Petting detection
    # -----------------------------------------------------------------------

    def _check_petting(self):
        import random as _random
        from PyQt6.QtGui import QCursor
        mouse_down = is_left_mouse_down()
        if (self.current_task != Task.NAB_MOUSE
                and mouse_down
                and not self._last_mouse_down):
            cursor = QCursor.pos()
            mouse_pos = Vector2(float(cursor.x()), float(cursor.y()))
            goose_head = Vector2(self.position.x, self.position.y + 14.0)
            if Vector2.distance(goose_head, mouse_pos) < 30.0:
                if (self.current_task == Task.WATCH_MOUSE
                        and self.task_watch_mouse
                        and self.task_watch_mouse.sub_state == WatchSubState.SIT):
                    r = _random.random()
                    if r < 0.70:
                        self.sound.honk()
                    elif r < 0.90:
                        self._set_task(Task.WANDER)
                    else:
                        self._set_task(Task.NAB_MOUSE)
                else:
                    self._set_task(Task.NAB_MOUSE)
        self._last_mouse_down = mouse_down

    # -----------------------------------------------------------------------
    # Task: Wander
    # -----------------------------------------------------------------------

    def _set_task(self, task: Task, honk: bool = True):
        self.override_extend_neck = False
        self._target_sit_lerp = 0.0
        self._target_neck_tuck = 0.0
        self._freeze_position = False
        self.current_task = task
        if honk:
            self.sound.honk()
        if task == Task.WANDER:
            self._set_speed(SpeedTier.WALK)
            duration = self._get_random_wander_duration()
            self.task_wander = WanderState(
                wander_start_time=self.time_keeper.time,
                wander_duration=duration,
            )
        elif task == Task.NAB_MOUSE:
            self._set_speed(SpeedTier.CHARGE)
            self.task_nab_mouse = NabMouseState(
                chase_start_time=self.time_keeper.time,
            )
        elif task == Task.COLLECT_WINDOW_NOTEPAD:
            from pygoose.goose.windows.notepad_window import NotepadWindow
            self._start_collect_window(NotepadWindow(font_size=self.config.notepad_font_size))
        elif task == Task.COLLECT_WINDOW_MEME:
            from pygoose.goose.windows.meme_window import MemeWindow
            self._start_collect_window(MemeWindow())
        elif task == Task.COLLECT_WINDOW_EXEC:
            self._set_speed(SpeedTier.WALK)
            direction = self._set_target_offscreen()
            self.task_collect_window.screen_direction = direction
            self._set_window_offset_for_direction(direction)
        elif task == Task.TRACK_MUD:
            self.task_track_mud = TrackMudState()
        elif task == Task.WATCH_MOUSE:
            self._set_speed(SpeedTier.WALK)
            t = self.time_keeper.time
            self.task_watch_mouse = WatchMouseState(
                start_time=t,
                duration=random_range(WATCH_MOUSE_DURATION_MIN, WATCH_MOUSE_DURATION_MAX),
                next_bob_time=t + random_range(0.5, 1.5),
                next_honk_time=t + random_range(2.0, 4.0),
            )

    def _choose_next_task(self):
        if DEV_FORCE_TASK:
            self._set_task(Task(DEV_FORCE_TASK))
            return
        task = TASK_WEIGHTED_LIST[self.task_picker_deck.next()]
        # Skip unimplemented tasks — fall back to wander
        if task not in (Task.WANDER, Task.TRACK_MUD, Task.NAB_MOUSE, Task.COLLECT_WINDOW_NOTEPAD, Task.COLLECT_WINDOW_MEME, Task.WATCH_MOUSE):
            task = Task.WANDER
        # Respect attack_randomly config
        attack_ok = (self.config.attack_randomly if self.config else True)
        if not attack_ok and task == Task.NAB_MOUSE:
            task = Task.WANDER
        self._set_task(task)

    def _get_random_wander_duration(self) -> float:
        if DEV_SHORT_WANDER:
            return 3.0
        if self.config:
            return random_range(
                self.config.min_wandering_time_seconds,
                self.config.max_wandering_time_seconds,
            )
        return random_range(20.0, 40.0)

    def _run_wander(self):
        t = self.time_keeper.time
        w = self.task_wander

        if t - w.wander_start_time > w.wander_duration:
            self._choose_next_task()
            return

        if w.pause_start_time > 0.0:
            if t - w.pause_start_time > w.pause_duration:
                w.pause_start_time = -1.0
                walk_time = random_range(1.0, 6.0)
                max_walk_dist = walk_time * self.current_speed
                new_target = Vector2(
                    random_range(0, self.screen_w),
                    random_range(0, self.screen_h),
                )
                if Vector2.distance(self.position, new_target) > max_walk_dist:
                    new_target = self.position + Vector2.normalize(new_target - self.position) * max_walk_dist
                self.target_pos = new_target
            else:
                self.velocity = Vector2(0.0, 0.0)
        else:
            if Vector2.distance(self.position, self.target_pos) < WANDER_GOOD_ENOUGH_DIST:
                w.pause_start_time = t
                w.pause_duration = random_range(1.0, 2.0)

    # -----------------------------------------------------------------------
    # Task: NabMouse
    # -----------------------------------------------------------------------

    def _get_cursor_pos(self) -> Vector2:
        from PyQt6.QtGui import QCursor
        p = QCursor.pos()
        return Vector2(float(p.x()), float(p.y()))

    def _run_nab_mouse(self):
        t = self.time_keeper.time
        n = self.task_nab_mouse
        cursor_pos = self._get_cursor_pos()
        beak_tip = self.rig.head2_end_point

        if n.stage == NabMouseStage.SEEKING_MOUSE:
            self._set_speed(SpeedTier.CHARGE)
            self.target_pos = cursor_pos - (beak_tip - self.position)

            if Vector2.distance(beak_tip, cursor_pos) < MOUSE_GRAB_DISTANCE:
                n.original_vector_to_mouse = cursor_pos - beak_tip
                n.grabbed_time = t
                # Pick drag destination at least 1.2 charge-seconds away
                drag_to = Vector2(self.position.x, self.position.y)
                while Vector2.distance(drag_to, self.position) / 400.0 < 1.2:
                    drag_to = Vector2(random_range(0, self.screen_w), random_range(0, self.screen_h))
                n.drag_to = drag_to
                self.target_pos = drag_to
                self.sound.chomp()
                n.stage = NabMouseStage.DRAGGING_MOUSE_AWAY

            if t > n.chase_start_time + GIVE_UP_TIME:
                n.stage = NabMouseStage.DECELERATING

        elif n.stage == NabMouseStage.DRAGGING_MOUSE_AWAY:
            if Vector2.distance(self.position, self.target_pos) < MOUSE_DROP_DISTANCE:
                release_cursor_clip()
                n.stage = NabMouseStage.DECELERATING
            else:
                p = min((t - n.grabbed_time) / MOUSE_SUCC_TIME, 1.0)
                clip_vec = Vector2.lerp(n.original_vector_to_mouse, STRUGGLE_RANGE, p)
                clip_x = beak_tip.x + (clip_vec.x if clip_vec.x >= 0 else clip_vec.x)
                clip_y = beak_tip.y + (clip_vec.y if clip_vec.y >= 0 else clip_vec.y)
                set_cursor_clip(clip_x, clip_y, abs(clip_vec.x), abs(clip_vec.y))

        elif n.stage == NabMouseStage.DECELERATING:
            mag = Vector2.magnitude(self.velocity)
            if mag > 0.01:
                self.target_pos = self.position + Vector2.normalize(self.velocity) * 5.0
                self.velocity -= Vector2.normalize(self.velocity) * self.current_acceleration * 2.0 * DELTA_TIME
            if mag < 80.0:
                release_cursor_clip()
                self._set_task(Task.WANDER)

    # -----------------------------------------------------------------------
    # Task: CollectWindow
    # -----------------------------------------------------------------------

    def _start_collect_window(self, window):
        self.task_collect_window = CollectWindowState(main_window=window)
        self._set_task(Task.COLLECT_WINDOW_EXEC, honk=False)

    def _set_window_offset_for_direction(self, direction: ScreenDirection):
        cw = self.task_collect_window
        w = cw.main_window.width() if cw.main_window else 200
        h = cw.main_window.height() if cw.main_window else 150
        if direction == ScreenDirection.LEFT:
            cw.window_offset_to_beak = Vector2(float(w), float(h) / 2)
        elif direction == ScreenDirection.TOP:
            cw.window_offset_to_beak = Vector2(float(w) / 2, float(h))
        elif direction == ScreenDirection.RIGHT:
            cw.window_offset_to_beak = Vector2(0.0, float(h) / 2)

    def _run_collect_window(self):
        t = self.time_keeper.time
        c = self.task_collect_window

        if c.window_closed_early:
            c.window_closed_early = False
            self._set_task(Task.NAB_MOUSE)
            return

        if c.stage == CollectWindowStage.WALKING_OFFSCREEN:
            if Vector2.distance(self.position, self.target_pos) < 5.0:
                c.secs_to_wait = random_range(WAIT_TIME_MIN, WAIT_TIME_MAX)
                c.wait_start_time = t
                c.stage = CollectWindowStage.WAITING_TO_BRING_WINDOW_BACK

        elif c.stage == CollectWindowStage.WAITING_TO_BRING_WINDOW_BACK:
            self.velocity = Vector2(0.0, 0.0)
            if t - c.wait_start_time > c.secs_to_wait:
                c.main_window.closing.connect(self._on_window_closed_early)
                QMetaObject.invokeMethod(c.main_window, "show_dialog", Qt.ConnectionType.QueuedConnection)

                d = c.screen_direction
                w = float(c.main_window.width())
                h = float(c.main_window.height())

                if d == ScreenDirection.LEFT:
                    tx = w + random_range(15, 20)
                    ty = lerp(self.position.y, self.screen_h / 2, random_range(0.2, 0.3))
                elif d == ScreenDirection.RIGHT:
                    tx = self.screen_w - (w + random_range(20, 30))
                    ty = lerp(self.position.y, self.screen_h / 2, random_range(0.2, 0.3))
                else:
                    tx = lerp(self.position.x, self.screen_w / 2, random_range(0.2, 0.3))
                    ty = h + random_range(80, 100)

                self.target_pos = Vector2(
                    clamp(tx, w + 55, self.screen_w - w - 55),
                    clamp(ty, h + 80, self.screen_h),
                )
                c.stage = CollectWindowStage.DRAGGING_WINDOW_BACK

        elif c.stage == CollectWindowStage.DRAGGING_WINDOW_BACK:
            if Vector2.distance(self.position, self.target_pos) < 5.0:
                # Watch window — notepad angers forever, meme angers within 3 seconds
                from pygoose.goose.windows.notepad_window import NotepadWindow
                self._placed_window = c.main_window
                self._placed_window_time = t
                self._placed_window_closed = False
                self._placed_window_permanent = isinstance(c.main_window, NotepadWindow)
                c.main_window.closing.connect(self._on_placed_window_closed)
                self._set_task(Task.WANDER)
                return

            self.override_extend_neck = True
            window_pos = self.rig.head2_end_point - c.window_offset_to_beak
            c.main_window.move_threadsafe(int(window_pos.x), int(window_pos.y))

    def _on_window_closed_early(self):
        if self.task_collect_window:
            self.task_collect_window.window_closed_early = True

    # -----------------------------------------------------------------------
    # Task: WatchMouse
    # -----------------------------------------------------------------------

    def _run_watch_mouse(self):
        import random as _random
        t = self.time_keeper.time
        w = self.task_watch_mouse

        if t - w.start_time > w.duration:
            self._set_task(Task.WANDER)
            return

        # Always face cursor
        cursor_pos = self._get_cursor_pos()
        to_cursor = cursor_pos - self.position
        if Vector2.magnitude(to_cursor) > 1.0:
            self.target_pos = self.position + Vector2.normalize(to_cursor) * 50.0

        # Switch sub-state on timer (SIT holds for at least SIT_MIN_DURATION)
        sit_held_long_enough = (w.sub_state != WatchSubState.SIT or
                                w.sit_entered_time < 0 or
                                t - w.sit_entered_time >= SIT_MIN_DURATION)
        if t > w.next_sub_change_time and sit_held_long_enough:
            new_sub = _random.choice([WatchSubState.STAND_STILL, WatchSubState.WALK_SLOW, WatchSubState.SIT])
            if new_sub == WatchSubState.SIT and w.sub_state != WatchSubState.SIT:
                w.sit_entered_time = t
            elif new_sub != WatchSubState.SIT:
                w.sit_entered_time = -1.0
            w.sub_state = new_sub
            w.next_sub_change_time = t + random_range(WATCH_SUB_DURATION_MIN, WATCH_SUB_DURATION_MAX)

        # Sub-state behaviour
        if w.sub_state == WatchSubState.STAND_STILL:
            self._freeze_position = True
            self._target_sit_lerp = 0.0
        elif w.sub_state == WatchSubState.WALK_SLOW:
            self._freeze_position = False
            self._target_sit_lerp = 0.0
            dist = Vector2.magnitude(to_cursor)
            if dist > 60.0:
                self._set_speed(SpeedTier.WALK)
                self.target_pos = self.position + Vector2.normalize(to_cursor) * 50.0
            else:
                self._freeze_position = True
        elif w.sub_state == WatchSubState.SIT:
            self._freeze_position = True
            self._target_sit_lerp = 1.0
        elif w.sub_state == WatchSubState.CRAWL:
            self._target_sit_lerp = 1.0
            self._target_neck_tuck = 1.0

        # Head bob (skip while sitting)
        if w.sub_state != WatchSubState.SIT:
            if w.bob_end_time > 0.0:
                self.override_extend_neck = True
                if t > w.bob_end_time:
                    w.bob_end_time = -1.0
                    self.override_extend_neck = False
                    w.next_bob_time = t + random_range(BOB_INTERVAL_MIN, BOB_INTERVAL_MAX)
            elif t > w.next_bob_time:
                w.bob_end_time = t + BOB_DURATION
        else:
            self.override_extend_neck = False

        # Rare honk — only a 30% chance each time the timer fires
        if t > w.next_honk_time:
            if _random.random() < 0.30:
                self.sound.honk()
            w.next_honk_time = t + random_range(WATCH_HONK_INTERVAL_MIN, WATCH_HONK_INTERVAL_MAX)

    # -----------------------------------------------------------------------
    # Task: TrackMud
    # -----------------------------------------------------------------------

    def _set_target_offscreen(self) -> ScreenDirection:
        if self.position.x > self.screen_w / 2:
            self.target_pos = Vector2(self.screen_w + 50, lerp(self.position.y, self.screen_h / 2, 0.4))
            return ScreenDirection.RIGHT
        else:
            self.target_pos = Vector2(-50, lerp(self.position.y, self.screen_h / 2, 0.4))
            return ScreenDirection.LEFT

    def _run_track_mud(self):
        t = self.time_keeper.time
        m = self.task_track_mud

        if m.stage == TrackMudStage.DECIDE_TO_RUN:
            self._set_target_offscreen()
            self._set_speed(SpeedTier.RUN)
            m.stage = TrackMudStage.RUNNING_OFFSCREEN

        elif m.stage == TrackMudStage.RUNNING_OFFSCREEN:
            if Vector2.distance(self.position, self.target_pos) < 5.0:
                self.target_pos = Vector2(random_range(0, self.screen_w), random_range(0, self.screen_h))
                m.next_dir_change_time = t + DIR_CHANGE_INTERVAL
                m.time_to_stop_running = t + AMOK_DURATION
                self.track_mud_end_time = t + TRACK_MUD_DURATION
                m.stage = TrackMudStage.RUNNING_WANDERING
                self.sound.play_mud_squish()

        elif m.stage == TrackMudStage.RUNNING_WANDERING:
            if (Vector2.distance(self.position, self.target_pos) < 5.0
                    or t > m.next_dir_change_time):
                self.target_pos = Vector2(random_range(0, self.screen_w), random_range(0, self.screen_h))
                m.next_dir_change_time = t + DIR_CHANGE_INTERVAL

            if t > m.time_to_stop_running:
                self.target_pos = Vector2(
                    clamp(self.position.x + 30.0, 55.0, self.screen_w - 55.0),
                    clamp(self.position.y + 3.0, 80.0, self.screen_h - 80.0),
                )
                self._set_task(Task.WANDER, honk=False)
