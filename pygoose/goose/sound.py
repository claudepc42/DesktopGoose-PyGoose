import os
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

from pygoose.engine.math_utils import get_rng
from pygoose.paths import resource_path


def _path(filename: str) -> str:
    return resource_path("assets", "sounds", filename)


def _exists(filename: str) -> bool:
    return os.path.isfile(_path(filename))


def _make_player(volume: float) -> tuple[QMediaPlayer, QAudioOutput]:
    player = QMediaPlayer()
    audio = QAudioOutput()
    audio.setVolume(volume)
    player.setAudioOutput(audio)
    return player, audio


class Sound:
    def __init__(self, silence: bool = False):
        self._silence = silence
        if silence:
            return

        self._honk_players: list[tuple[QMediaPlayer, QAudioOutput]] = []
        for i in range(1, 5):
            fname = f"Honk{i}.mp3"
            if _exists(fname):
                p, a = _make_player(0.8)
                p.setSource(QUrl.fromLocalFile(_path(fname)))
                self._honk_players.append((p, a))

        self._bite_player: tuple[QMediaPlayer, QAudioOutput] | None = None
        if _exists("BITE.mp3"):
            p, a = _make_player(0.07)
            p.setSource(QUrl.fromLocalFile(_path("BITE.mp3")))
            self._bite_player = (p, a)

        self._mud_player: tuple[QMediaPlayer, QAudioOutput] | None = None
        if _exists("MudSquith.mp3"):
            p, a = _make_player(0.8)
            p.setSource(QUrl.fromLocalFile(_path("MudSquith.mp3")))
            self._mud_player = (p, a)

        self._pat_players: list[tuple[QMediaPlayer, QAudioOutput]] = []
        for i in range(1, 4):
            fname = f"Pat{i}.wav"
            if _exists(fname):
                p, a = _make_player(0.8)
                p.setSource(QUrl.fromLocalFile(_path(fname)))
                self._pat_players.append((p, a))

        self._music_player: tuple[QMediaPlayer, QAudioOutput] | None = None
        if _exists("Music.mp3"):
            p, a = _make_player(0.5)
            p.setSource(QUrl.fromLocalFile(_path("Music.mp3")))
            p.setLoops(QMediaPlayer.Loops.Infinite)
            self._music_player = (p, a)
            p.play()

    def honk(self):
        if self._silence or not self._honk_players:
            return
        rng = get_rng()
        p, _ = self._honk_players[int(rng.random() * len(self._honk_players))]
        p.setPosition(0)
        p.play()

    def chomp(self):
        if self._silence or not self._bite_player:
            return
        p, _ = self._bite_player
        p.setPosition(0)
        p.play()

    def play_pat(self):
        if self._silence or not self._pat_players:
            return
        rng = get_rng()
        p, _ = self._pat_players[int(rng.random() * len(self._pat_players))]
        p.setPosition(0)
        p.play()

    def play_mud_squish(self):
        if self._silence or not self._mud_player:
            return
        p, _ = self._mud_player
        p.setPosition(0)
        p.play()
