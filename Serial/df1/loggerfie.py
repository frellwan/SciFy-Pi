"""
A rotating, browsable log file.
"""

# System Imports
import os, glob, time, stat


class DailyLogger(object):
    """A log file that is rotated daily (at or after midnight localtime)
    """
    def __init__(self, name, directory, defaultMode=None, maxRotatedFiles=7):
        """
        Create a log file.
        @param name: name of the file
        @param directory: directory holding the file
        @param defaultMode: permissions used to create the file. Default to
        current permissions of the file if the file exists.
        """
        self.directory = directory
        self.name = name
        self.maxRotatedFiles = maxRotatedFiles
        self.path = os.path.join(directory, name)
        if defaultMode is None and os.path.exists(self.path):
            self.defaultMode = stat.S_IMODE(os.stat(self.path)[stat.ST_MODE])
        else:
            self.defaultMode = defaultMode
        self._openFile()

    
    def _openFile(self):
        self.closed = False

        if os.path.exists(self.path):
            self._file = file(self.path, "r+", 1)
            self._file.seek(0, 2)
        else:
            if self.defaultMode is not None:
                # Set the lowest permissions
                oldUmask = os.umask(0o777)
                try:
                    self._file = file(self.path, "w+", 1)
                finally:
                    os.umask(oldUmask)
            else:
                self._file = file(self.path, "w+", 1)

        if self.defaultMode is not None:
            try:
                os.chmod(self.path, self.defaultMode)
            except OSError:
                # Probably /dev/null or something?
                pass

        self.lastDate = self.toDate(os.stat(self.path)[8])

    def shouldRotate(self):
        """Rotate when the date has changed since last write"""
        return self.toDate() > self.lastDate

    def toDate(self, *args):
        """Convert a unixtime to (year, month, day) localtime tuple,
        or return the current (year, month, day) localtime tuple.
        This function primarily exists so you may overload it with
        gmtime, or some cruft to make unit testing possible.
        """
        # primarily so this can be unit tested easily
        return time.localtime(*args)[:3]

    def dateFile(self, t):
        """Return the file name given a (year, month, day) tuple or unixtime"""
        try:
            return '%02d%02d%02d00.csv' % (t[0]-100*(int(t[0]/100)), t[1], t[2])
        except:
            # try taking a float unixtime
            return '_'.join(map(str, self.toDate(tupledate)))

    def getLog(self, identifier):
        """Given a unix time, return a LogReader for an old log file."""
        if self.toDate(identifier) == self.lastDate:
            return self.getCurrentLog()
        filename = "%s" % (os.path.join(self.directory, self.dateFile(identifier)))
        if not os.path.exists(filename):
            raise ValueError, "no such logfile exists"
        return LogReader(filename)

    def write(self, data):
        """
        Write some data to the file.
        """
        if self.shouldRotate():
            self.flush()
            self.rotate()
        self._file.write(data)
        # Guard against a corner case where time.time()
        # could potentially run backwards to yesterday.
        # Primarily due to network time.
        self.lastDate = max(self.lastDate, self.toDate())
        return self.name

    def flush(self):
        """
        Flush the file
        """

        self._file.flush()

    def rotate(self):
        """Rotate the file and create a new one.
        If it's not possible to open new logfile, this will fail silently,
        and continue logging to old logfile.
        """
        if not (os.access(self.directory, os.W_OK) and os.access(self.path, os.W_OK)):
            return

        logs = self.listLogs()
        if (self.maxRotatedFiles is not None) and (len(logs)>=self.maxRotatedFiles):
            for i in range(len(logs)-self.maxRotatedFiles):
                os.remove("%s" % (os.path.join(self.directory, logs[i])))

        self.name = self.dateFile(self.toDate())
        newpath = "%s" % (os.path.join(self.directory, self.name))
        self._file.close()
        self.path = newpath
        self._openFile()

    def listLogs(self):
        """
        Return sorted list of integers - the old logs' identifiers.
        """
        result = []
        files = filter(os.path.isfile, glob.glob(self.directory + "*"))
        files.sort(key=lambda x: os.path.getmtime(x))
        for name in files:
            try:
                result.append(name.split('/')[-1])
            except ValueError:
                pass
        return result


    def __getstate__(self):
        state = BaseLogFile.__getstate__(self)
        del state["lastDate"]
        return state
