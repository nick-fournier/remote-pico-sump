import os
import logging


def try_remove(fn: str) -> None:
    """Try to remove a file if it existst."""
    try:
        os.remove(fn)
    except OSError:
        pass


def get_filesize(fn: str) -> int:
    """Return size of a file."""
    return os.stat(fn)[6]


class RotatingFileHandler(logging.Handler):
    """A rotating file handler like RotatingFileHandler.

    Compatible with CPythons `logging.handlers.RotatingFileHandler` class.
    """

    def __init__(self, filename, maxBytes=0, backupCount=0):
        super().__init__()
        self.filename = filename
        self.maxBytes = maxBytes
        self.backupCount = backupCount

        try:
            self._counter = get_filesize(self.filename)
        except OSError:
            self._counter = 0

    def emit(self, record):
        """Write to file."""
        msg = self.formatter.format(record)
        s_len = len(msg)

        if self.maxBytes and self.backupCount and self._counter + s_len > self.maxBytes:
            # remove the last backup file if it is there
            try_remove(self.filename + ".{0}".format(self.backupCount))

            for i in range(self.backupCount - 1, 0, -1):
                if i < self.backupCount:
                    try:
                        os.rename(
                            self.filename + ".{0}".format(i),
                            self.filename + ".{0}".format(i + 1),
                        )
                    except OSError:
                        pass

            try:
                os.rename(self.filename, self.filename + ".1")
            except OSError:
                pass
            self._counter = 0

        with open(self.filename, "a") as f:
            f.write(msg + "\n")

        self._counter += s_len


class BufferingHandler(logging.Handler):
    """
  A handler class which buffers logging records in memory. Whenever each
  record is added to the buffer, a check is made to see if the buffer should
  be flushed. If it should, then flush() is expected to do what's needed.
    """
    def __init__(self, capacity):
        """
        Initialize the handler with the buffer size.
        """
        logging.Handler.__init__(self)
        self.capacity = capacity
        self.buffer = []

    def shouldFlush(self, record):
        """
        Should the handler flush its buffer?

        Returns true if the buffer is up to capacity. This method can be
        overridden to implement custom flushing strategies.
        """
        return (len(self.buffer) >= self.capacity)

    def emit(self, record):
        """
        Emit a record.

        Append the record. If shouldFlush() tells us to, call flush() to process
        the buffer.
        """
        
        record_msg = self.format(record)
        self.buffer.append(record_msg)
        if self.shouldFlush(record):
            self.flush()

    def flush(self, zap = False):
        """
        Override to implement custom flushing behaviour.

        If zap = True, This just zaps the buffer to empty.
        
        Otherwise it clears the buffer until under capacity.
        """
        if zap:
            self.buffer.clear()
        else:
            self.buffer = self.buffer[-self.capacity:]               
        

    def close(self):
        """
        Close the handler.

        This version just flushes and chains to the parent class' close().
        """
        try:
            self.flush(zap=True)
        finally:
            logging.Handler.close(self)
            

class MemoryHandler(BufferingHandler):
    """
    A handler class which buffers logging records in memory, periodically
    flushing them to a target handler. Flushing occurs whenever the buffer
    is full, or when an event of a certain severity or greater is seen.
    """
    def __init__(self, capacity, flushLevel=logging.ERROR, target=None,
                 flushOnClose=True):
        """
        Initialize the handler with the buffer size, the level at which
        flushing should occur and an optional target.

        Note that without a target being set either here or via setTarget(),
        a MemoryHandler is no use to anyone!

        The ``flushOnClose`` argument is ``True`` for backward compatibility
        reasons - the old behaviour is that when the handler is closed, the
        buffer is flushed, even if the flush level hasn't been exceeded nor the
        capacity exceeded. To prevent this, set ``flushOnClose`` to ``False``.
        """
        BufferingHandler.__init__(self, capacity)
        self.flushLevel = flushLevel
        self.target = target
        # See Issue #26559 for why this has been added
        self.flushOnClose = flushOnClose

    def shouldFlush(self, record):
        """
        Check for buffer full or a record at the flushLevel or higher.
        """
        return (len(self.buffer) >= self.capacity) or \
                (record.levelno >= self.flushLevel)

    def setTarget(self, target):
        """
        Set the target handler for this handler.
        """
        self.target = target

    # def flush(self):
    #     """
    #     For a MemoryHandler, flushing means just sending the buffered
    #     records to the target, if there is one. Override if you want
    #     different behaviour.

    #     The record buffer is only cleared if a target has been set.
    #     """
    #     if self.target:
    #         for record in self.buffer:
    #             self.target.handle(record)
    #         self.buffer.clear()

    def close(self):
        """
        Flush, if appropriately configured, set the target to None and lose the
        buffer.
        """
        try:
            if self.flushOnClose:
                self.flush()
        finally:
            self.target = None
            BufferingHandler.close(self)
