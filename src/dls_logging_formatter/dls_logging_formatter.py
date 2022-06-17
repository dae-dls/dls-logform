import multiprocessing
import logging
import os
import traceback
import time
import re

# ------------------------------------------------------------------------
ansi_colors_regex = re.compile(
    r"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])"
)


def flatten_exception_message(exception):
    """
    Remove newlines from exception message.
    """

    # Get the informative part of a tango exception.
    if type(exception).__name__ in [
        "DevFailed",
        "ConnectionFailed",
        "CommunicationFailed",
    ]:
        try:
            message = exception.args[0].desc.rstrip().replace("\n", " ")
        except:
            message = str(exception)
    elif type(exception).__name__ in ["CellExecutionError"]:
        cell_line = None
        # Jupyter ExecutePreprocessor provides its internal traceback as a multi-line string.
        lines = exception.traceback.split("\n")
        for line in lines:
            # Remove colorization that jupyter puts in these messages.
            line = ansi_colors_regex.sub("", line)
            # This is the line in the traceback telling which cell had the error?
            if line.startswith("Input In ["):
                cell_line = line
                break

        # Be tolerant of traceback not providing the cell.
        if cell_line is None:
            message = "%s %s" % (exception.ename, exception.evalue)
        else:
            message = "%s in %s: %s" % (exception.ename, cell_line, exception.evalue)
    else:
        message = str(exception)

    return message


# ------------------------------------------------------------------------
def list_exception_causes(exception):
    """
    Make an array by appending the exception message with the causing exceptions messages.
    """

    # Remove newlines from exception message.
    message = flatten_exception_message(exception)

    cause_list = ["%s: %s" % (type(exception).__name__, message)]
    if exception.__cause__ is not None:
        cause_list.extend(list_exception_causes(exception.__cause__))
    elif exception.__context__ is not None:
        cause_list.extend(list_exception_causes(exception.__context__))

    return cause_list


# ------------------------------------------------------------------------
def format_exception_causes(exception, join_string="... "):
    """
    Make a single string by joining the exception message with the causing exceptions messages.
    """

    return join_string.join(list_exception_causes(exception))


# --------------------------------------------------------------------
class DlsLoggingFormatter(logging.Formatter):
    """
    Our custom logging formatter.
    """

    # -----------------------------------------------------------------
    def __init__(
        self, fmt=None, datefmt=None, style="%", type="long", log_settings=None
    ):
        super().__init__(fmt, datefmt, style)

        self.type = type

        self._time_zero = None
        self._time_last = None

        self._last_log_record_created = None
        self._last_formatted_message = None

        self.type_info = {
            "bare": {"indent": "\n"},
            "short": {"indent": "\n" + " " * 18},
            "long": {"indent": "\n" + " " * 77},
        }

    # -----------------------------------------------------------------
    def format(self, log_record):
        """
        Override base format method to provide the custom formatting.
        """

        # Being asked to format same record again?
        if log_record.created == self._last_log_record_created:
            return self._last_formatted_message
        self._last_log_record_created = log_record.created

        # Compute delta time since last message.
        zero_delta, last_delta = self.sample_instant(log_record.created)

        # Format the message using the args provided on the log call.
        if log_record.args is None or len(log_record.args) == 0:
            formatted_message = log_record.msg
        else:
            formatted_message = log_record.msg % log_record.args

        # Allow the method who make the log call to specify what shall be reported.
        pathname = log_record.pathname
        if hasattr(log_record, "caller_pathname"):
            pathname = log_record.caller_pathname

        funcname = log_record.funcName
        if hasattr(log_record, "caller_funcname"):
            funcname = log_record.caller_funcname

        lineno = log_record.lineno
        if hasattr(log_record, "caller_lineno"):
            lineno = log_record.caller_lineno

        # We want short format?
        if self.type == "bare":
            pass
        # We want short format?
        elif self.type == "short":
            # Pretty up the filename as a module.
            module2 = self.parse_module_from_filename(pathname)
            formatted_message = "%8d %8d %-9s %s::%s[%d] %s" % (
                zero_delta,
                last_delta,
                log_record.levelname,
                module2,
                funcname,
                lineno,
                formatted_message,
            )
        # We want long format?
        else:
            formatted_message = "%s %5d %-12s %-12s %8d %8d %-9s %s[%d] %s" % (
                self.formatTime(log_record),
                log_record.process,
                # Truncate process and thread names if longer than 12.
                log_record.processName[:12],
                log_record.threadName[:12],
                zero_delta,
                last_delta,
                log_record.levelname,
                pathname,
                lineno,
                formatted_message,
            )

        # Bring this back maybe in the future.
        # formatted_message = self.wrap(formatted_message)

        formatted_message = str(formatted_message) + self.formatException(
            log_record.exc_info
        )

        formatted_message = formatted_message + self.formatStack(log_record.stack_info)

        self._last_formatted_message = formatted_message
        return formatted_message

    # -----------------------------------------------------------------
    def formatTime(self, log_record, datefmt=None):
        return time.strftime(
            "%Y-%m-%d %H:%M:%S.", time.localtime(log_record.created)
        ) + ("%06d" % (int(log_record.msecs * 1000.0)))

    # -----------------------------------------------------------------
    def formatException(self, exc_info):
        """
        The exc_info is standard triple (type, value, traceback).
        Format the exception type and message, with all tracebacks and chained exceptions.
        Return as one string with newline characters in it.
        """
        if exc_info is None:
            return ""
        if isinstance(exc_info, bool):
            return ""

        # In the case of "bare", we don't print any stack trace.
        if self.type == "bare":
            return ""

        # First line shall be indented as well as the rest.
        lines = [""]

        # Format the exception into lines list.
        lines.extend(self._format_exception_lines(exc_info[1]))

        # Return as single string, with the lines indented according to the formatting type.
        return self.type_info[self.type]["indent"].join(lines)

    # -----------------------------------------------------------------
    def _format_exception_lines(self, exception):
        """
        Format the exception type and message on one line.
        In addition, format the traceback on additional lines.
        Recursively format lines from the exception's chained cause or context.
        """

        # Remove newlines from exception message.
        message = flatten_exception_message(exception)

        lines = []
        lines.append("%-9s %s: %s" % ("EXCEPTION", type(exception).__name__, message))

        # Make the stack from the exception's traceback.
        stack_summary = traceback.extract_tb(exception.__traceback__)

        # Interate over the frames in the stack.
        for frame_summary in stack_summary:

            # Pretty up the filename as a module.
            module2 = self.parse_module_from_filename(frame_summary.filename)

            lines.append(self.format_frame_summary(module2, frame_summary))

        # Also append any chained exception.
        if exception.__cause__ is not None:
            lines.extend(self._format_exception_lines(exception.__cause__))
        elif exception.__context__ is not None:
            lines.extend(self._format_exception_lines(exception.__context__))

        return lines

    # -----------------------------------------------------------------
    def formatStack(self, stack_info):
        if stack_info is None:
            return ""

        output_lines = [""]

        stack_summary = traceback.extract_stack()
        first = True
        for frame_summary in reversed(stack_summary):

            # Pretty up the filename as a module.
            module2 = self.parse_module_from_filename(frame_summary.filename)

            # Skip boring stack entries.
            if "/dls_logging_formatter.py" in frame_summary.filename:
                continue
            if module2.startswith("logging."):
                continue

            # Stop when we hit the interpreter.
            if module2.startswith("_pytest."):
                break
            if module2.startswith("python3."):
                break

            if not first:
                output_lines.append(self.format_frame_summary(module2, frame_summary))

            first = False

        return self.type_info[self.type]["indent"].join(output_lines)

    # -----------------------------------------------------------------
    def wrap(self, line):
        max = 224
        level = "..."

        # Whole line fits?
        if len(line) < max:
            return line

        cut = line.rfind(" ", 0, max)
        if cut == -1:
            cut = max

        output_lines = [line[:cut]]
        while True:
            line = line[cut + 1 :]

            if len(line) < max:
                output_lines.append("%-9s %s" % (level, line))
                break

            cut = line.rfind(" ", 0, max)
            if cut == -1:
                cut = max

            output_lines.append("%-9s %s" % (level, line[:cut]))

        return self.type_info[self.type]["indent"].join(output_lines)

    # -----------------------------------------------------------------
    def parse_module_from_filename(self, filename):

        # Remove backslashes put there from a Windows filesystem.
        module2 = filename.replace("\\", "/")

        # Keep just last two parts of the path.
        module2 = module2.split("/")
        if len(module2) > 1:
            module2 = module2[-2:]

        # Join path parts with a dot.
        module2 = ".".join(module2)

        # Chop off the .py at the end.
        if module2.endswith(".py"):
            module2 = module2[:-3]

        return module2

    # -----------------------------------------------------------------
    def format_frame_summary(self, module2, frame_summary):

        if self.type == "short":
            return "%-9s %s::%s[%d] %s" % (
                "TRACEBACK",
                module2,
                frame_summary.name,
                frame_summary.lineno,
                frame_summary.line,
            )
        else:
            return "%-9s %s[%d] %s" % (
                "TRACEBACK",
                frame_summary.filename,
                frame_summary.lineno,
                frame_summary.line,
            )

    # -----------------------------------------------------------------
    def reset_times(self):
        """
        Reset the time zero point used for reporting elapsed time in log messages.
        """

        now = time.time()

        self._time_zero = now

        self._time_last = now

    # -----------------------------------------------------------------
    def sample_instant(self, created):
        """
        Give deltas from this record since the past record.
        The value of created is the time when the LogRecord was created (as returned by time.time()).
        """

        if self._time_zero is None:
            self._time_zero = created

        if self._time_last is None:
            self._time_last = created

        zero_delta = int((created - self._time_zero) * 1000.0)
        last_delta = int((created - self._time_last) * 1000.0)

        self._time_last = created

        return zero_delta, last_delta
