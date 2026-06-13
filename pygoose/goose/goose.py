from __future__ import annotations
import math
import random
# Module-level aliases so hot per-tick task handlers don't re-import every frame
_math = math
_random = random

from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMetaObject, Qt, QRect
from PyQt6.QtGui import QCursor

from pygoose.engine.vector2 import Vector2
from pygoose.engine.math_utils import lerp, clamp, random_range
from pygoose.engine.easings import cubic_ease_in_out
from pygoose.engine.rig import Rig
from pygoose.engine.deck import Deck
from pygoose.engine.time_keeper import TimeKeeper, DELTA_TIME
from pygoose.goose.renderer import (
    update_rig, render_goose, render_foot_marks,
    FOOT_MARK_LIFETIME, FOOT_MARK_SHRINK_TIME,
)
from pygoose.goose.cursor import set_cursor_clip, release_cursor_clip, is_left_mouse_down
from pygoose.goose.sound import Sound


# ---------------------------------------------------------------------------
# Speed tiers
# ---------------------------------------------------------------------------

class SpeedTier(Enum):
    SNEAK  = "sneak"
    WALK   = "walk"
    RUN    = "run"
    CHARGE = "charge"

SPEEDS = {
    SpeedTier.SNEAK:  {"speed": 28.0,  "acceleration": 600.0,  "step_time": 0.45},
    SpeedTier.WALK:   {"speed": 80.0,  "acceleration": 1300.0, "step_time": 0.2},
    SpeedTier.RUN:    {"speed": 200.0, "acceleration": 1300.0, "step_time": 0.2},
    SpeedTier.CHARGE: {"speed": 400.0, "acceleration": 2300.0, "step_time": 0.1},
}


# ---------------------------------------------------------------------------
# Task enum
# ---------------------------------------------------------------------------

class Task(Enum):
    WANDER                = "wander"
    NAB_MOUSE             = "nab_mouse"
    COLLECT_WINDOW_MEME   = "collect_window_meme"
    COLLECT_WINDOW_NOTEPAD= "collect_window_notepad"
    COLLECT_WINDOW_EXEC   = "collect_window_exec"
    TRACK_MUD             = "track_mud"
    WATCH_MOUSE           = "watch_mouse"
    FOLLOW_MOUSE          = "follow_mouse"
    SNEAK_ATTACK          = "sneak_attack"
    SLEEP                 = "sleep"
    PEEK_BACK             = "peek_back"


TASK_WEIGHTED_LIST = [
    Task.TRACK_MUD,
    Task.TRACK_MUD,
    Task.COLLECT_WINDOW_MEME,
    Task.COLLECT_WINDOW_MEME,
    Task.COLLECT_WINDOW_NOTEPAD,
    Task.COLLECT_WINDOW_NOTEPAD,
    Task.COLLECT_WINDOW_NOTEPAD,
    Task.NAB_MOUSE,
    Task.NAB_MOUSE,
    Task.NAB_MOUSE,
    Task.WATCH_MOUSE,
    Task.WATCH_MOUSE,
    Task.FOLLOW_MOUSE,
    Task.FOLLOW_MOUSE,
    Task.SNEAK_ATTACK,
    Task.SLEEP,
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
    WALKING_TO_EVICT = "walking_to_evict"
    EVICTING_WINDOW = "evicting_window"
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
    window_type: str = ""                    # "meme" or "notepad"
    evict_window: object = None              # existing window being dragged off
    evict_window_offset: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))


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
WATCH_MOUSE_DURATION_MAX = 180.0
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
# FollowMouse state
# ---------------------------------------------------------------------------

FOLLOW_PREFERRED_DIST_MIN  = 90.0
FOLLOW_PREFERRED_DIST_MAX  = 160.0
FOLLOW_FLEE_DIST           = 45.0
FOLLOW_FLEE_DURATION       = 1.5
FOLLOW_BOREDOM_MIN         = 15.0
FOLLOW_BOREDOM_MAX         = 30.0
FOLLOW_SNAP_GRAB_CHANCE    = 0.05
HONK_MARCH_CHANCE          = 0.12   # chance per check interval to start a march
HONK_MARCH_CHECK_INTERVAL  = 10.0
HONK_MARCH_DURATION        = 2.5
HONK_MARCH_RATE            = 0.38   # seconds between honks during march

class FollowMouseStage(Enum):
    RUSHING   = "rushing"
    FOLLOWING = "following"
    FLEEING   = "fleeing"

@dataclass
class FollowMouseState:
    start_time: float
    boredom_time: float
    preferred_dist: float
    stage: FollowMouseStage = FollowMouseStage.RUSHING
    flee_target: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    flee_until: float = -1.0
    honk_march_until: float = -1.0
    next_march_honk_time: float = -1.0
    next_march_check_time: float = 0.0


# ---------------------------------------------------------------------------
# SneakAttack state
# ---------------------------------------------------------------------------

SNEAK_STRIKE_DIST  = 65.0
SNEAK_MAX_DURATION = 44.0
SNEAK_HONK_RATE    = 0.32

class SneakAttackStage(Enum):
    SNEAKING  = "sneaking"
    POUNCING  = "pouncing"
    DRAGGING  = "dragging"
    DECELERATING = "decelerating"

@dataclass
class SneakAttackState:
    start_time: float
    give_up_time: float
    stage: SneakAttackStage = SneakAttackStage.SNEAKING
    grabbed_time: float = -1.0
    original_vector_to_mouse: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    drag_to: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    next_honk_time: float = -1.0


# ---------------------------------------------------------------------------
# Sleep state
# ---------------------------------------------------------------------------

SLEEP_CIRCLE_RADIUS   = 88.0
SLEEP_CIRCLE_SPEED    = 0.75  # radians per second — slow dog-like circling
SLEEP_CIRCLES_MIN     = 2.0
SLEEP_CIRCLES_MAX     = 3.0
SLEEP_SETTLE_DURATION = 2.2
SLEEP_MIN_DURATION    = 90.0
SLEEP_MAX_DURATION    = 480.0
SLEEP_CORNER_MARGIN   = 165.0  # px from screen edge

class SleepStage(Enum):
    WALKING_TO_CORNER = "walking_to_corner"
    CIRCLING          = "circling"
    SETTLING          = "settling"
    SLEEPING          = "sleeping"

@dataclass
class SleepState:
    nest_pos: Vector2
    spiral_start_angle: float = 0.0
    stage: SleepStage = SleepStage.WALKING_TO_CORNER
    spiral_t: float = 0.0
    settle_start_time: float = -1.0
    wake_time: float = -1.0
    is_fake_sleep: bool = False
    next_eye_event_time: float = -1.0  # when to open or close the peeking eye
    eye_is_open: bool = False
    spotted_time: float = -1.0


# ---------------------------------------------------------------------------
# Peek-back state (after fake-sleep freak-out)
# ---------------------------------------------------------------------------

PEEK_INSET = 14.0   # px from screen edge for the peek position

@dataclass
class PeekBackState:
    peek_pos: Vector2
    enter_pos: Vector2
    face_dir: float         # direction facing inward at edge (degrees)
    sweep_deg: float        # total sweep angle (25-65 deg)
    stage: str = "peeking_in"
    look_start_time: float = -1.0
    look_duration: float = 8.8
    walk_in_dist: float = -1.0
    pause_start_time: float = -1.0
    pause_duration: float = 0.0


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

# Dirty-rect extents around the goose position (px). Must fully contain every
# drawn pixel in all states (extended neck, beak, shadow, feet, sleep bubbles,
# exclamation) or repaints would clip. Measured worst-case extents across the
# full state space (all directions, neck/sit/tuck extremes, bubbles, exclamation)
# are L=49.5 R=51.3 U=96.0 D=36.5, so these are comfortably generous. (Shrinking
# the box was measured to give no CPU benefit — Qt re-blits the whole translucent
# layered window per update regardless of region — so we keep the safe margins.)
DIRTY_LEFT  = 100
DIRTY_RIGHT = 100
DIRTY_UP    = 110
DIRTY_DOWN  = 90


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
        self.task_follow_mouse: FollowMouseState | None = None
        self.task_sneak_attack: SneakAttackState | None = None
        self.task_sleep: SleepState | None = None
        self.task_peek_back: PeekBackState | None = None

        # Placed windows — up to 2 of each type kept on screen
        self._placed_memes: list = []
        self._placed_notepads: list = []
        # Anger tracking: only the most recently placed window triggers NAB_MOUSE if closed
        self._anger_window = None
        self._anger_time = -1.0
        self._anger_closed = False
        self._anger_permanent = False

        # Mouse polling state
        self._last_mouse_down = False

        # Render-skip: signature of the last frame's render-affecting state.
        # When nothing that influences drawn pixels has changed, the overlay can
        # skip the repaint entirely (the layered window keeps the last frame).
        self._last_render_sig = None

        self._target_sit_lerp = 0.0
        self._target_neck_tuck = 0.0
        self._freeze_position = False
        self._freak_out_until = -1.0
        self._freak_out_next_honk = -1.0
        self._freak_bounce_a: Vector2 = Vector2.zero
        self._freak_bounce_b: Vector2 = Vector2.zero
        self._freak_bounce_to_a: bool = True

        self.sound = Sound(silence=config.silence_sounds if config else False)
        self.time_keeper = TimeKeeper()
        self._set_task(Task.WANDER, honk=False)

    # -----------------------------------------------------------------------
    # Public
    # -----------------------------------------------------------------------

    def tick(self):
        self.time_keeper.tick()
        self._check_placed_windows()
        self._check_petting()
        self._run_physics()
        self._solve_feet()
        self._update_neck()
        self.rig.sit_lerp_percent       = lerp(self.rig.sit_lerp_percent,       self._target_sit_lerp,  0.06)
        self.rig.neck_tuck_lerp_percent = lerp(self.rig.neck_tuck_lerp_percent, self._target_neck_tuck, 0.06)
        sleeping = (self.current_task == Task.SLEEP
                    and self.task_sleep is not None
                    and self.task_sleep.stage == SleepStage.SLEEPING)
        self.rig.is_sleeping = sleeping
        self.rig.show_sleep_bubbles = sleeping and (self.task_sleep is not None and not self.task_sleep.is_fake_sleep)
        if not sleeping:
            self.rig.peek_eye = 0
        if sleeping:
            self.rig.sleep_phase += DELTA_TIME

    def render(self, painter):
        render_foot_marks(painter, self.foot_marks, self.time_keeper.time)
        update_rig(self.position, self.direction, self.rig)
        render_goose(
            painter, self.rig, self.position, self.direction,
            self.l_foot_pos, self.r_foot_pos,
            self.config,
        )

    def dirty_rect(self):
        """Decide whether this frame needs repainting and, if so, which region.

        Returns ``None`` when every pixel-affecting input is unchanged from the
        last painted frame (the overlay then skips the repaint — the layered
        window already holds identical pixels). Otherwise returns the QRect to
        invalidate: the goose's box, unioned with any footmarks mid-shrink.

        The signature below is the *complete* set of inputs consumed by
        ``render_foot_marks`` + ``update_rig`` + ``render_goose``. Comparing the
        raw values (not quantized) guarantees a skipped frame is bitwise
        identical, so this can never change what the user sees.
        """
        rig = self.rig
        # sleep_phase only affects pixels while bubbles are shown (real sleep);
        # during fake sleep it still increments but draws nothing, so exclude it.
        sleep_token = rig.sleep_phase if rig.show_sleep_bubbles else 0.0
        sig = (
            self.position.x, self.position.y, self.direction,
            self.l_foot_pos.x, self.l_foot_pos.y,
            self.r_foot_pos.x, self.r_foot_pos.y,
            rig.sit_lerp_percent, rig.neck_tuck_lerp_percent, rig.neck_lerp_percent,
            rig.is_sleeping, rig.show_sleep_bubbles, rig.peek_eye, rig.show_exclamation,
            sleep_token,
        )

        t = self.time_keeper.time
        r = QRect(int(self.position.x) - DIRTY_LEFT, int(self.position.y) - DIRTY_UP,
                  DIRTY_LEFT + DIRTY_RIGHT, DIRTY_UP + DIRTY_DOWN)
        any_mark_animating = False
        for m in self.foot_marks:
            if m.time == 0.0:
                continue
            shrink_start = m.time + FOOT_MARK_LIFETIME
            if shrink_start - 0.1 <= t <= shrink_start + FOOT_MARK_SHRINK_TIME + 0.1:
                any_mark_animating = True
                r = r.united(QRect(int(m.position.x) - 6, int(m.position.y) - 6, 12, 12))

        changed = (sig != self._last_render_sig) or any_mark_animating
        self._last_render_sig = sig
        if not changed:
            return None
        return r

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

        # Freak-out override: run away from mouse at charge speed, honking
        t = self.time_keeper.time
        if self._freak_out_until > 0 and t < self._freak_out_until:
            bounce_target = self._freak_bounce_a if self._freak_bounce_to_a else self._freak_bounce_b
            self.target_pos = bounce_target
            if Vector2.distance(self.position, bounce_target) < 30.0:
                self._freak_bounce_to_a = not self._freak_bounce_to_a
            self._set_speed(SpeedTier.CHARGE)
            self._freeze_position = False
            if t >= self._freak_out_next_honk:
                self.sound.honk()
                self._freak_out_next_honk = t + 0.3
        elif self._freak_out_until > 0:
            self._freak_out_until = -1.0
            self._set_task(Task.PEEK_BACK, honk=False)

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
        s = self.rig.sit_lerp_percent
        b = 1.0 if right_foot else 0.0
        side = Vector2.get_from_angle_degrees(self.direction + 90.0) * b
        # When crawling: reduce perpendicular spread and push feet downward so
        # they poke below the lowered body in both left and right facing directions.
        perp_dist  = lerp(FEET_DISTANCE_APART, 2.0, s)
        crawl_drop = lerp(0.0, 8.0, s)
        return self.position + side * perp_dist + Vector2(0.0, crawl_drop)

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
        elif self.current_task == Task.FOLLOW_MOUSE:
            self._run_follow_mouse()
        elif self.current_task == Task.SNEAK_ATTACK:
            self._run_sneak_attack()
        elif self.current_task == Task.SLEEP:
            self._run_sleep()
        elif self.current_task == Task.PEEK_BACK:
            self._run_peek_back()

    # -----------------------------------------------------------------------
    # Placed window anger check
    # -----------------------------------------------------------------------

    def _check_placed_windows(self):
        if self._anger_window is None:
            return
        t = self.time_keeper.time
        if self._anger_closed:
            self._anger_window = None
            self._anger_closed = False
            self._set_task(Task.NAB_MOUSE)
        elif not self._anger_permanent and t - self._anger_time >= 3.0:
            self._anger_window = None

    def _make_placed_window_close_cb(self, window, window_type: str):
        def on_close():
            lst = self._placed_memes if window_type == "meme" else self._placed_notepads
            if window in lst:
                lst.remove(window)
            if self._anger_window is window:
                self._anger_closed = True
        return on_close

    # -----------------------------------------------------------------------
    # Petting detection
    # -----------------------------------------------------------------------

    def _check_petting(self):
        mouse_down = is_left_mouse_down()
        if (self.current_task != Task.NAB_MOUSE
                and mouse_down
                and not self._last_mouse_down):
            cursor = QCursor.pos()
            mouse_pos = Vector2(float(cursor.x()), float(cursor.y()))
            goose_head = Vector2(self.position.x, self.position.y + 14.0)
            if Vector2.distance(goose_head, mouse_pos) < 30.0:
                if (self.current_task == Task.SLEEP
                        and self.task_sleep
                        and self.task_sleep.stage == SleepStage.SLEEPING):
                    self.sound.honk()
                    self._set_task(Task.WANDER)
                elif (self.current_task == Task.WATCH_MOUSE
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
        self.rig.is_sleeping = False
        self.rig.show_sleep_bubbles = False
        self.rig.peek_eye = 0
        self.rig.show_exclamation = False
        self.rig.sleep_phase = 0.0
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
            self._start_collect_window(NotepadWindow(font_size=self.config.notepad_font_size), "notepad")
        elif task == Task.COLLECT_WINDOW_MEME:
            from pygoose.goose.windows.meme_window import MemeWindow
            self._start_collect_window(MemeWindow(), "meme")
        elif task == Task.COLLECT_WINDOW_EXEC:
            self._set_speed(SpeedTier.WALK)
            c = self.task_collect_window
            if c and c.stage == CollectWindowStage.WALKING_TO_EVICT:
                pass  # target/direction already set up by _start_collect_window
            else:
                direction = self._set_target_offscreen()
                c.screen_direction = direction
                self._set_window_offset_for_direction(direction)
        elif task == Task.TRACK_MUD:
            self.task_track_mud = TrackMudState()
        elif task == Task.FOLLOW_MOUSE:
            self._set_speed(SpeedTier.RUN)
            t = self.time_keeper.time
            self.task_follow_mouse = FollowMouseState(
                start_time=t,
                boredom_time=t + random_range(FOLLOW_BOREDOM_MIN, FOLLOW_BOREDOM_MAX),
                preferred_dist=random_range(FOLLOW_PREFERRED_DIST_MIN, FOLLOW_PREFERRED_DIST_MAX),
                next_march_check_time=t + random_range(3.0, 6.0),
            )
        elif task == Task.SNEAK_ATTACK:
            self._set_speed(SpeedTier.SNEAK)
            t = self.time_keeper.time
            self.task_sneak_attack = SneakAttackState(
                start_time=t,
                give_up_time=t + SNEAK_MAX_DURATION,
            )
        elif task == Task.SLEEP:
            self._set_speed(SpeedTier.WALK)
            corners = [
                Vector2(SLEEP_CORNER_MARGIN, SLEEP_CORNER_MARGIN),
                Vector2(self.screen_w - SLEEP_CORNER_MARGIN, SLEEP_CORNER_MARGIN),
                Vector2(self.screen_w - SLEEP_CORNER_MARGIN, self.screen_h - SLEEP_CORNER_MARGIN),
            ]
            nest = corners[0] if self.config.dev_force_task else _random.choice(corners)
            nest += Vector2(random_range(-15, 15), random_range(-15, 15))
            self.task_sleep = SleepState(
                nest_pos=nest,
                spiral_start_angle=_random.uniform(0, 2 * _math.pi),
            )
            self.target_pos = nest
        elif task == Task.PEEK_BACK:
            self._set_speed(SpeedTier.SNEAK)
            self.rig.sit_lerp_percent = 1.0
            self.rig.neck_tuck_lerp_percent = 1.0
            self._target_sit_lerp = 1.0
            self._target_neck_tuck = 1.0
            # Determine which screen edge is nearest and set peek/enter positions
            edge_dists = {
                'left':   self.position.x,
                'right':  self.screen_w - self.position.x,
                'top':    self.position.y,
                'bottom': self.screen_h - self.position.y,
            }
            nearest = min(edge_dists, key=edge_dists.get)
            cx, cy = self.screen_w / 2, self.screen_h / 2
            diag = random_range(80, 180) * _random.choice([-1, 1])
            if nearest == 'left':
                peek_pos  = Vector2(PEEK_INSET, clamp(self.position.y, 80, self.screen_h - 80))
                face_dir  = 0.0
                enter_x   = random_range(150, self.screen_w / 2)
                enter_pos = Vector2(enter_x, clamp(self.position.y + diag, 80, self.screen_h - 80))
            elif nearest == 'right':
                peek_pos  = Vector2(self.screen_w - PEEK_INSET, clamp(self.position.y, 80, self.screen_h - 80))
                face_dir  = 180.0
                enter_x   = random_range(self.screen_w / 2, self.screen_w - 150)
                enter_pos = Vector2(enter_x, clamp(self.position.y + diag, 80, self.screen_h - 80))
            elif nearest == 'top':
                peek_pos  = Vector2(clamp(self.position.x, 80, self.screen_w - 80), PEEK_INSET)
                face_dir  = 90.0
                enter_y   = random_range(80, self.screen_h / 2)
                enter_pos = Vector2(clamp(self.position.x + diag, 80, self.screen_w - 80), enter_y)
            else:  # bottom
                peek_pos  = Vector2(clamp(self.position.x, 80, self.screen_w - 80), self.screen_h - PEEK_INSET)
                face_dir  = -90.0
                enter_y   = random_range(self.screen_h / 2, self.screen_h - 80)
                enter_pos = Vector2(clamp(self.position.x + diag, 80, self.screen_w - 80), enter_y)
            self.task_peek_back = PeekBackState(
                peek_pos=peek_pos,
                enter_pos=enter_pos,
                face_dir=face_dir,
                sweep_deg=random_range(45.0, 150.0),
            )
            self.target_pos = peek_pos
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
        if self.config.dev_force_task:
            self._set_task(Task(self.config.dev_force_task))
            return
        task = TASK_WEIGHTED_LIST[self.task_picker_deck.next()]
        # Skip unimplemented tasks — fall back to wander
        if task not in (Task.WANDER, Task.TRACK_MUD, Task.NAB_MOUSE, Task.COLLECT_WINDOW_NOTEPAD, Task.COLLECT_WINDOW_MEME, Task.WATCH_MOUSE, Task.FOLLOW_MOUSE, Task.SNEAK_ATTACK, Task.SLEEP):
            task = Task.WANDER
        # Respect attack_randomly config
        attack_ok = (self.config.attack_randomly if self.config else True)
        if not attack_ok and task == Task.NAB_MOUSE:
            task = Task.WANDER
        self._set_task(task)

    def _get_random_wander_duration(self) -> float:
        if self.config.dev_skip_wander:
            return 0.0
        if self.config.dev_short_wander:
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

    def _start_collect_window(self, window, window_type: str):
        lst = self._placed_memes if window_type == "meme" else self._placed_notepads
        state = CollectWindowState(main_window=window, window_type=window_type)

        if len(lst) >= 2:
            evict_win = _random.choice(lst)
            lst.remove(evict_win)
            if self._anger_window is evict_win:
                self._anger_window = None
            wpos = evict_win.pos()
            w = float(evict_win.width())
            h = float(evict_win.height())
            cx = float(wpos.x()) + w / 2
            mid_y = float(wpos.y()) + h / 2
            if cx < self.screen_w / 2:
                # Window is on the left — grab its right edge
                evict_offset = Vector2(w, h / 2)
                grab_x = float(wpos.x()) + w
            else:
                # Window is on the right — grab its left edge
                evict_offset = Vector2(0.0, h / 2)
                grab_x = float(wpos.x())
            state.evict_window = evict_win
            state.evict_window_offset = evict_offset
            state.stage = CollectWindowStage.WALKING_TO_EVICT
            self.task_collect_window = state
            self.target_pos = Vector2(grab_x, mid_y)
            self._set_task(Task.COLLECT_WINDOW_EXEC, honk=False)
        else:
            self.task_collect_window = state
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

        if c.window_closed_early and c.stage not in (
            CollectWindowStage.WALKING_TO_EVICT, CollectWindowStage.EVICTING_WINDOW
        ):
            c.window_closed_early = False
            self._set_task(Task.NAB_MOUSE)
            return

        if c.stage == CollectWindowStage.WALKING_TO_EVICT:
            if Vector2.distance(self.position, self.target_pos) < 15.0:
                # Reached the old window — now drag it offscreen
                ew = c.evict_window
                cx = float(ew.pos().x()) + ew.width() / 2
                if cx < self.screen_w / 2:
                    self.target_pos = Vector2(-80.0, lerp(self.position.y, self.screen_h / 2, 0.3))
                else:
                    self.target_pos = Vector2(self.screen_w + 80.0, lerp(self.position.y, self.screen_h / 2, 0.3))
                c.stage = CollectWindowStage.EVICTING_WINDOW

        elif c.stage == CollectWindowStage.EVICTING_WINDOW:
            offscreen = self.position.x < -40 or self.position.x > self.screen_w + 40
            if offscreen or c.evict_window is None:
                if c.evict_window is not None:
                    try:
                        c.evict_window.closing.disconnect()
                    except Exception:
                        pass
                    c.evict_window.hide()
                    c.evict_window.deleteLater()
                    c.evict_window = None
                self.override_extend_neck = False
                direction = self._set_target_offscreen()
                c.screen_direction = direction
                c.stage = CollectWindowStage.WALKING_OFFSCREEN
                self._set_window_offset_for_direction(direction)
            else:
                self.override_extend_neck = True
                window_pos = self.rig.head2_end_point - c.evict_window_offset
                c.evict_window.move_threadsafe(int(window_pos.x), int(window_pos.y))

        elif c.stage == CollectWindowStage.WALKING_OFFSCREEN:
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
                    tx = w + random_range(15, 300)
                    ty = random_range(h + 40, self.screen_h - 60)
                elif d == ScreenDirection.RIGHT:
                    tx = self.screen_w - (w + random_range(15, 300))
                    ty = random_range(h + 40, self.screen_h - 60)
                else:
                    tx = random_range(w + 60, self.screen_w - w - 60)
                    ty = h + random_range(80, 350)

                # If one of this type is already on screen, place the new one
                # messily overlapping — further in, random jitter in any direction.
                lst = self._placed_memes if c.window_type == "meme" else self._placed_notepads
                if lst:
                    if d == ScreenDirection.LEFT:
                        tx += random_range(50, 130)
                        ty += random_range(-150, 150)
                    elif d == ScreenDirection.RIGHT:
                        tx -= random_range(50, 130)
                        ty += random_range(-150, 150)
                    else:
                        ty += random_range(50, 130)
                        tx += random_range(-150, 150)

                self.target_pos = Vector2(
                    clamp(tx, w + 55, self.screen_w - w - 55),
                    clamp(ty, h + 80, self.screen_h),
                )
                c.stage = CollectWindowStage.DRAGGING_WINDOW_BACK

        elif c.stage == CollectWindowStage.DRAGGING_WINDOW_BACK:
            if Vector2.distance(self.position, self.target_pos) < 5.0:
                from pygoose.goose.windows.notepad_window import NotepadWindow
                lst = self._placed_memes if c.window_type == "meme" else self._placed_notepads
                lst.append(c.main_window)
                c.main_window.closing.connect(self._make_placed_window_close_cb(c.main_window, c.window_type))
                # Most recently placed window is the one that angers the goose if closed
                self._anger_window = c.main_window
                self._anger_time = t
                self._anger_closed = False
                self._anger_permanent = isinstance(c.main_window, NotepadWindow)
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
    # Task: FollowMouse
    # -----------------------------------------------------------------------

    def _run_follow_mouse(self):
        t = self.time_keeper.time
        f = self.task_follow_mouse
        cursor_pos = self._get_cursor_pos()
        to_cursor = cursor_pos - self.position
        dist = Vector2.magnitude(to_cursor)

        # Boredom timeout
        if t >= f.boredom_time:
            if _random.random() < FOLLOW_SNAP_GRAB_CHANCE:
                self._set_task(Task.NAB_MOUSE)
            else:
                self._set_task(Task.WANDER)
            return

        FOLLOW_DEADBAND = 35.0

        if f.stage == FollowMouseStage.RUSHING:
            self._set_speed(SpeedTier.RUN)
            if dist > 1.0:
                self.target_pos = cursor_pos - Vector2.normalize(to_cursor) * f.preferred_dist
            if dist <= f.preferred_dist + FOLLOW_DEADBAND:
                f.stage = FollowMouseStage.FOLLOWING

        elif f.stage == FollowMouseStage.FOLLOWING:
            if dist < FOLLOW_FLEE_DIST:
                # Too close — flee
                flee_dir = Vector2.normalize(self.position - cursor_pos) if dist > 1.0 else Vector2(1.0, 0.0)
                f.flee_target = self.position + flee_dir * 180.0
                f.flee_until = t + FOLLOW_FLEE_DURATION
                f.stage = FollowMouseStage.FLEEING
            elif dist > f.preferred_dist + FOLLOW_DEADBAND:
                # Drifted too far — walk back into range
                self._set_speed(SpeedTier.WALK)
                self._freeze_position = False
                if dist > 1.0:
                    self.target_pos = cursor_pos - Vector2.normalize(to_cursor) * f.preferred_dist
            else:
                # Comfortable zone — stop and face cursor
                self._freeze_position = True
                if dist > 1.0:
                    self.target_pos = self.position + Vector2.normalize(to_cursor) * 50.0

            # Honk march check — only trigger if no march is already running
            march_active = f.honk_march_until > 0 and t < f.honk_march_until
            if t >= f.next_march_check_time and not march_active:
                f.next_march_check_time = t + HONK_MARCH_CHECK_INTERVAL + random_range(-1.0, 2.0)
                if _random.random() < HONK_MARCH_CHANCE:
                    f.honk_march_until = t + HONK_MARCH_DURATION
                    f.next_march_honk_time = t

            # Execute honk march
            if f.honk_march_until > 0 and t < f.honk_march_until:
                if t >= f.next_march_honk_time:
                    self.sound.honk()
                    f.next_march_honk_time = t + HONK_MARCH_RATE

        elif f.stage == FollowMouseStage.FLEEING:
            self._freeze_position = False
            self._set_speed(SpeedTier.RUN)
            self.target_pos = f.flee_target
            if t >= f.flee_until:
                f.stage = FollowMouseStage.FOLLOWING

    # -----------------------------------------------------------------------
    # Task: SneakAttack
    # -----------------------------------------------------------------------

    def _run_sneak_attack(self):
        t = self.time_keeper.time
        s = self.task_sneak_attack
        cursor_pos = self._get_cursor_pos()
        to_cursor = cursor_pos - self.position
        dist = Vector2.magnitude(to_cursor)

        if s.stage == SneakAttackStage.SNEAKING:
            # Give up if taking too long
            if t >= s.give_up_time:
                self._set_task(Task.WANDER)
                return

            self._set_speed(SpeedTier.SNEAK)
            self._target_sit_lerp = 1.0
            self._target_neck_tuck = 1.0
            if dist > 1.0:
                self.target_pos = cursor_pos

            if dist < SNEAK_STRIKE_DIST:
                # Pounce!
                self._target_sit_lerp = 0.0
                self._target_neck_tuck = 0.0
                self._set_speed(SpeedTier.CHARGE)
                s.stage = SneakAttackStage.POUNCING
                s.next_honk_time = t

        elif s.stage == SneakAttackStage.POUNCING:
            self._set_speed(SpeedTier.CHARGE)
            beak_tip = self.rig.head2_end_point
            self.target_pos = cursor_pos - (beak_tip - self.position)

            # Honk while charging
            if t >= s.next_honk_time:
                self.sound.honk()
                s.next_honk_time = t + SNEAK_HONK_RATE

            if Vector2.distance(beak_tip, cursor_pos) < MOUSE_GRAB_DISTANCE:
                s.original_vector_to_mouse = cursor_pos - beak_tip
                s.grabbed_time = t
                drag_to = Vector2(self.position.x, self.position.y)
                while Vector2.distance(drag_to, self.position) / 400.0 < 1.2:
                    drag_to = Vector2(random_range(0, self.screen_w), random_range(0, self.screen_h))
                s.drag_to = drag_to
                self.target_pos = drag_to
                self.sound.chomp()
                s.stage = SneakAttackStage.DRAGGING

            # Missed entirely — give up after charge window
            if t >= s.give_up_time + SNEAK_MAX_DURATION:
                self._set_task(Task.WANDER)

        elif s.stage == SneakAttackStage.DRAGGING:
            beak_tip = self.rig.head2_end_point
            if Vector2.distance(self.position, s.drag_to) < MOUSE_DROP_DISTANCE:
                release_cursor_clip()
                s.stage = SneakAttackStage.DECELERATING
            else:
                p = min((t - s.grabbed_time) / MOUSE_SUCC_TIME, 1.0)
                clip_vec = Vector2.lerp(s.original_vector_to_mouse, STRUGGLE_RANGE, p)
                clip_x = beak_tip.x + clip_vec.x
                clip_y = beak_tip.y + clip_vec.y
                set_cursor_clip(clip_x, clip_y, abs(clip_vec.x), abs(clip_vec.y))

            # Keep honking while dragging
            if t >= s.next_honk_time:
                self.sound.honk()
                s.next_honk_time = t + SNEAK_HONK_RATE

        elif s.stage == SneakAttackStage.DECELERATING:
            mag = Vector2.magnitude(self.velocity)
            if mag > 0.01:
                self.target_pos = self.position + Vector2.normalize(self.velocity) * 5.0
                self.velocity -= Vector2.normalize(self.velocity) * self.current_acceleration * 2.0 * DELTA_TIME
            if mag < 80.0:
                release_cursor_clip()
                self._set_task(Task.WANDER)

    # -----------------------------------------------------------------------
    # Task: Sleep
    # -----------------------------------------------------------------------
    # Task: PeekBack
    # -----------------------------------------------------------------------

    def _run_peek_back(self):
        t = self.time_keeper.time
        s = self.task_peek_back

        if s.stage == "peeking_in":
            dist = Vector2.distance(self.position, s.peek_pos)
            self._set_speed(SpeedTier.SNEAK if dist < 80.0 else SpeedTier.WALK)
            self._target_sit_lerp = 1.0
            self._target_neck_tuck = 1.0
            self.target_pos = s.peek_pos
            if dist < 12.0:
                s.look_start_time = t
                s.stage = "looking"
                self.rig.sit_lerp_percent = 1.0
                self.rig.neck_tuck_lerp_percent = 1.0
                self._target_sit_lerp = 1.0
                self._target_neck_tuck = 1.0

        elif s.stage == "looking":
            self._freeze_position = True
            self._target_sit_lerp = 1.0
            self._target_neck_tuck = 1.0
            elapsed = t - s.look_start_time
            # Sine sweep: one full left-right arc over look_duration
            t_norm = clamp(elapsed / s.look_duration, 0.0, 1.0)
            ramp = 0.18
            ease_in  = clamp(t_norm / ramp, 0.0, 1.0)
            ease_out = clamp((1.0 - t_norm) / ramp, 0.0, 1.0)
            envelope = min(ease_in * ease_in * (3 - 2 * ease_in),
                           ease_out * ease_out * (3 - 2 * ease_out))
            sweep = _math.sin(t_norm * 2 * _math.pi) * (s.sweep_deg / 2.0) * envelope
            target_dir = s.face_dir + sweep
            rad = _math.radians(target_dir)
            sweep_pt = self.position + Vector2(_math.cos(rad), _math.sin(rad)) * 300.0
            # During fade-out, blend target toward enter_pos so direction is right for walking_in
            exit_blend = clamp((t_norm - (1.0 - ramp)) / ramp, 0.0, 1.0)
            self.target_pos = Vector2(
                lerp(sweep_pt.x, s.enter_pos.x, exit_blend),
                lerp(sweep_pt.y, s.enter_pos.y, exit_blend),
            )
            if elapsed >= s.look_duration:
                self._freeze_position = False
                s.stage = "walking_in"

        elif s.stage == "walking_in":
            self._set_speed(SpeedTier.SNEAK)
            self.target_pos = s.enter_pos
            dist_remaining = Vector2.distance(self.position, s.enter_pos)
            if s.walk_in_dist < 0:
                s.walk_in_dist = max(dist_remaining, 1.0)
            progress = clamp(1.0 - dist_remaining / s.walk_in_dist, 0.0, 1.0)
            self._target_sit_lerp  = 1.0 - progress
            self._target_neck_tuck = 1.0 - progress
            if dist_remaining < 12.0:
                s.pause_start_time = t
                s.pause_duration = random_range(0.5, 1.5)
                s.stage = "pausing"

        elif s.stage == "pausing":
            self._freeze_position = True
            if t - s.pause_start_time >= s.pause_duration:
                self._set_task(Task.WANDER)

    # -----------------------------------------------------------------------

    def _run_sleep(self):
        t = self.time_keeper.time
        s = self.task_sleep

        if s.stage == SleepStage.WALKING_TO_CORNER:
            self._set_speed(SpeedTier.WALK)
            self.target_pos = s.nest_pos
            if Vector2.distance(self.position, s.nest_pos) < 8.0:
                s.stage = SleepStage.CIRCLING

        elif s.stage == SleepStage.CIRCLING:
            self._set_speed(SpeedTier.SNEAK)
            # Advance at constant 40px/s arc speed so target always stays ahead of goose
            arc_len = max(SLEEP_CIRCLE_RADIUS * (1.0 - s.spiral_t) * 1.5 * 2 * _math.pi, 1.0)
            s.spiral_t = min(s.spiral_t + (40.0 / arc_len) * DELTA_TIME, 1.0)
            angle = s.spiral_start_angle + s.spiral_t * 1.5 * 2 * _math.pi
            radius = SLEEP_CIRCLE_RADIUS * (1.0 - s.spiral_t)
            self.target_pos = Vector2(
                s.nest_pos.x + _math.cos(angle) * radius,
                s.nest_pos.y + _math.sin(angle) * radius,
            )
            if s.spiral_t >= 0.6:
                s.settle_start_time = t
                s.stage = SleepStage.SETTLING

        elif s.stage == SleepStage.SETTLING:
            self._freeze_position = True
            elapsed = t - s.settle_start_time
            progress = clamp(elapsed / SLEEP_SETTLE_DURATION, 0.0, 1.0)
            self._target_sit_lerp = progress
            self._target_neck_tuck = progress

            if elapsed >= SLEEP_SETTLE_DURATION:
                s.wake_time = t + random_range(SLEEP_MIN_DURATION, SLEEP_MAX_DURATION)
                s.is_fake_sleep = self.config.dev_force_fake_sleep or _random.random() < 0.15
                if s.is_fake_sleep:
                    s.next_eye_event_time = t + random_range(5.0, 15.0)
                s.stage = SleepStage.SLEEPING

        elif s.stage == SleepStage.SLEEPING:
            self._freeze_position = True
            self._target_sit_lerp = 1.0
            self._target_neck_tuck = 1.0

            if s.is_fake_sleep:
                if not s.eye_is_open and t >= s.next_eye_event_time:
                    self.rig.peek_eye = _random.choice([1, 2])
                    s.eye_is_open = True
                    s.next_eye_event_time = t + random_range(0.5, 2.5)
                elif s.eye_is_open and t >= s.next_eye_event_time:
                    self.rig.peek_eye = 0
                    s.eye_is_open = False
                    s.next_eye_event_time = t + random_range(5.0, 15.0)

                if s.eye_is_open and s.spotted_time < 0 and Vector2.distance(self.position, self._get_cursor_pos()) < 150.0:
                    s.spotted_time = t
                if s.spotted_time > 0:
                    self._freeze_position = True
                    elapsed = t - s.spotted_time
                    if elapsed < 0.75:
                        # Phase 1: one eye open, no exclamation
                        self.rig.show_exclamation = False
                    elif elapsed < 1.5:
                        # Phase 2: both eyes open + exclamation
                        self.rig.peek_eye = 3
                        self.rig.show_exclamation = True
                    else:
                        # Phase 3: run screaming
                        mouse = self._get_cursor_pos()
                        away = Vector2.normalize(self.position - mouse)
                        perp = Vector2(-away.y, away.x)
                        off_base = self.position + away * 400.0
                        self._freak_bounce_a = off_base + perp * 70.0
                        self._freak_bounce_b = off_base - perp * 70.0
                        self._freak_bounce_to_a = True
                        self._freak_out_until = t + 4.0
                        self._freak_out_next_honk = t
                        self._set_task(Task.WANDER, honk=False)
                        return

            if t >= s.wake_time:
                self._set_task(Task.WANDER)

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
