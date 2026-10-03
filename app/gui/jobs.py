"""時間のかかる処理（bag の読み込みなど）をバックグラウンドのスレッドで実行する。

コールバックは必ずメインスレッドで呼ばれる（JobRunner のスロット経由で受け取るため）。
"""
import itertools
import traceback

from .qt import QtCore, Signal, Slot


class _JobSignals(QtCore.QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)
    progress = Signal(int, int, int)


class _Job(QtCore.QRunnable):
    def __init__(self, job_id, fn, args, kwargs, with_progress):
        super().__init__()
        self.job_id = job_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.with_progress = with_progress
        self.signals = _JobSignals()

    def run(self):
        kwargs = dict(self.kwargs)
        if self.with_progress:
            kwargs["progress"] = lambda done, total: self.signals.progress.emit(self.job_id, done, total)
        try:
            result = self.fn(*self.args, **kwargs)
        except Exception as e:
            message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            self.signals.failed.emit(self.job_id, message)
        else:
            self.signals.finished.emit(self.job_id, result)


class JobRunner(QtCore.QObject):
    # 実行中のジョブ数
    running_changed = Signal(int)
    # (完了数, 全体数)
    progress = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QtCore.QThreadPool.globalInstance()
        self._ids = itertools.count()
        self._jobs = {}

    @property
    def running(self):
        return len(self._jobs)

    def submit(self, fn, *args, on_done=None, on_error=None, with_progress=False, **kwargs):
        """fn(*args, **kwargs) をスレッドで実行する。

        with_progress=True なら fn に progress=コールバック を渡す。
        on_done(result) / on_error(message) はメインスレッドで呼ばれる。
        """
        job_id = next(self._ids)
        job = _Job(job_id, fn, args, kwargs, with_progress)
        job.signals.finished.connect(self._on_finished)
        job.signals.failed.connect(self._on_failed)
        job.signals.progress.connect(self._on_progress)
        # 完了まで参照を保持する（GC で signals が消えないように）
        self._jobs[job_id] = (job, on_done, on_error)
        self._pool.start(job)
        self.running_changed.emit(self.running)
        return job_id

    def wait(self, msecs=-1):
        """全ジョブの終了を待ち、溜まったシグナルを処理する（テスト・終了処理用）。"""
        self._pool.waitForDone(msecs)
        QtCore.QCoreApplication.processEvents()

    def _pop(self, job_id):
        _, on_done, on_error = self._jobs.pop(job_id)
        self.running_changed.emit(self.running)
        return on_done, on_error

    @Slot(int, object)
    def _on_finished(self, job_id, result):
        on_done, _ = self._pop(job_id)
        if on_done:
            on_done(result)

    @Slot(int, str)
    def _on_failed(self, job_id, message):
        _, on_error = self._pop(job_id)
        if on_error:
            on_error(message)

    @Slot(int, int, int)
    def _on_progress(self, job_id, done, total):
        self.progress.emit(done, total)
