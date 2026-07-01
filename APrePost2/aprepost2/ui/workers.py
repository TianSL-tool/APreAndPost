from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str, str)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, function, keyword_arguments: dict):
        super().__init__()
        self.function = function
        self.keyword_arguments = keyword_arguments
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.function(**self.keyword_arguments)
        except Exception as error:
            self.signals.failed.emit(str(error), traceback.format_exc())
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit()
