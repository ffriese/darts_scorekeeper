import difflib
import os
import time
from collections import deque
from enum import Enum
from threading import Thread
from typing import List

import numpy as np
import sounddevice as sd
import soundfile as sf

from PyQt5.QtCore import QObject

from logic.settings import Settings
from models.objects.player import Player


class SoundJob(object):
    class Status(Enum):
        CREATED = 0
        WAITING = 1
        PLAYING = 2
        DONE = 3

    def __init__(self, sound_file: str, blocking: bool = True, delay_ms: int = 0, frame_rate: int = None):
        self.file_name = sound_file

        try:
            self.sound_file, self.frame_rate = sf.read('sounds/%s' % sound_file)
        except Exception as e:
            print(type(e), e)
            self.sound_file, self.frame_rate = None, None
            print('SOUND-FILE NOT FOUND!')
        if frame_rate is not None:
            self.frame_rate = frame_rate
        self._execution_thread = Thread(target=self._run)
        self.blocking = blocking
        self.delay_ms = delay_ms
        self._status = SoundJob.Status.CREATED

    def play(self, blocking=None):
        if Settings.SOUND_ENABLED.get():
            if blocking is None:
                blocking = self.blocking
            self._execution_thread.start()
            if blocking:
                self._execution_thread.join()
        else:
            self._status = SoundJob.Status.DONE

    @staticmethod
    def from_player_name(player: Player):
        return SoundJob(player.sound_file)

    @staticmethod
    def from_score(score: int):
        return SoundJob('z%s.mp3.wav' % score)

    @staticmethod
    def from_required_score(req_score: int):
        return SoundJob('yr_%s.wav' % req_score)

    @staticmethod
    def from_game_shot():
        return SoundJob('gameshot.mp3.wav')

    @staticmethod
    def from_set_shot():
        return SoundJob('set.mp3.wav')

    @staticmethod
    def from_leg_shot():
        return SoundJob('gameshotleg.mp3.wav')

    @staticmethod
    def from_next_leg():
        return SoundJob('nextleg.mp3.wav')

    @staticmethod
    def from_next_set():
        return SoundJob('nextset.mp3.wav')

    def _run(self):
        if self.delay_ms > 0:
            self._status = SoundJob.Status.WAITING
            time.sleep(self.delay_ms / 1000.0)
        self._status = SoundJob.Status.PLAYING
        if self.sound_file is not None:
            sd.play(self.sound_file, self.frame_rate, blocking=True)
        self._status = SoundJob.Status.DONE

    def is_playing(self):
        return self._status == SoundJob.Status.PLAYING

    def is_done(self):
        return self._status == SoundJob.Status.DONE

    def status(self):
        return self._status


class SoundSeries(object):
    def __init__(self, jobs: List[SoundJob]):
        self._execution_thread = Thread(target=self._run)
        self._queue = deque(jobs)

    def play(self):
        self._execution_thread.start()

    def wait_for_completion(self):
        if self._execution_thread.is_alive():
            self._execution_thread.join()

    def _run(self):
        while self._queue:
            job = self._queue.popleft()
            job.play(blocking=False)
            while not job.is_done():
                time.sleep(0.001)

    @staticmethod
    def from_sound_file_game_shot(sound_file: str):
        return SoundSeries([SoundJob.from_game_shot(), SoundJob(sound_file)])

    @staticmethod
    def from_sound_file_set_shot(sound_file: str):
        return SoundSeries([SoundJob.from_leg_shot(), SoundJob(sound_file),
                            SoundJob.from_set_shot(), SoundJob.from_next_set()])

    @staticmethod
    def from_sound_file_leg_shot(sound_file: str):
        return SoundSeries([SoundJob.from_leg_shot(), SoundJob(sound_file), SoundJob.from_next_leg()])


class SoundController(QObject):
    _instance = None

    @classmethod
    def instance(cls):
        if SoundController._instance is None:
            SoundController._instance = SoundController()
        return SoundController._instance

    def __init__(self):
        super().__init__()
        self.MUTE = False
        self.override_stream_function()  # enable overlapping sounds
        self._is_playing = False
        self._job_queue = deque()

    @staticmethod
    def _play_sound_series(series: SoundSeries, blocking: bool = False):
        series.play()
        if blocking:
            series.wait_for_completion()

    def play_job_series(self, jobs: List[SoundJob], blocking: bool = False):
        if self.MUTE:
            return
        if isinstance(jobs, SoundSeries):
            series = jobs
        else:
            series = SoundSeries(jobs)
        return self._play_sound_series(series, blocking)

    def play_job(self, job: SoundJob, blocking: bool = False):
        if self.MUTE:
            return
        series = SoundSeries([job])
        return self._play_sound_series(series, blocking)

    @staticmethod
    def ensure_player_sound_file(player: Player):
        if player.sound_file is None:
            sound_file = '%s.mp3.wav' % player.name.lower()
            if not os.path.exists('sounds/%s' % sound_file):
                print('player-sound %s does not exist. close matches:' % sound_file)
                files = os.listdir('sounds')
                replacement = difflib.get_close_matches(sound_file, files, 4, 0.9)
                s = difflib.SequenceMatcher()
                s.set_seq2(sound_file)
                scores = []
                for r in replacement:
                    s.set_seq1(r)
                    scores.append((r, s.ratio()))
                print(scores)
                if replacement:
                    sound_file = replacement[0]
                else:
                    sound_file = 'player.mp3.wav'
            print('set soundfile to ', sound_file)
            player.sound_file = sound_file

    # noinspection PyProtectedMember
    @staticmethod
    def override_stream_function():
        """
            this method overrides the start_stream-function in the sound-device class,
            so that it does not stop sounds that are still currently being played.
        """
        # noinspection PyPep8Naming,SpellCheckingInspection,PyGlobalUndefined
        def start_stream(obj, StreamClass, samplerate, channels, dtype, callback,
                         blocking, **kwargs):
            obj.stream = StreamClass(samplerate=samplerate,
                                     channels=channels,
                                     dtype=dtype,
                                     callback=callback,
                                     finished_callback=obj.finished_callback,
                                     **kwargs)
            obj.stream.start()
            global _last_callback
            _last_callback = obj
            if blocking:
                obj.wait()

        sd._CallbackContext.start_stream = start_stream


