from typing import Literal
import logging
import traceback
import time

from dls_logform.functions import flatten_exception_message
from dls_logform.functions import list_exception_causes
from dls_logform.functions import format_exception_causes

# --------------------------------------------------------------------
class DlsLogform(logging.Formatter):
    """
    This class implements a python logging.Formatter object
    """

    # -----------------------------------------------------------------
    def __init__(
        self,
        type: Literal["bare", "short", "long", "dls"] = "long",
    ):

        #
        """
        Constructor,

        Args:
            type (Literal["bare", "dls", "short", "long"], optional): the desired format.
                Defaults to "long".

                - bare: just the message part, no date/time/process/source.
                    Typically used for console output to non-technical users.

                - short: message, includes level and source, but not date/time/process.
                    Typically used during debugging to the console from single-process applications.

                - long: full length formatted message.
                    Typically used for files written to log.

                - dls: same as "long" but adds some index-ready attributes to the record.
                    Typically used with a logging server such as Graylog or Logstash.

        """
        super().__init__(None, None, "%")

        self.type = type

        self._time_zero = None
        self._time_last = None

        self._last_log_record_created = None
        self.__last_formatted_message = None

        self.type_info = {
            "bare": {"indent": "\n"},
            "dls": {"indent": "\n" + " " * 77},
            "short": {"indent": "\n" + " " * 18},
            "long": {"indent": "\n" + " " * 77},
        }

    # -----------------------------------------------------------------
    def format(self, log_record: logging.LogRecord) -> str:
        """
        Override base method to provide the custom formatting on the given record.

        See https://docs.python.org/3/library/logging.html
        """

        # Being asked to format same record again?
        if log_record.created == self._last_log_record_created:
            return str(self.__last_formatted_message)
        self._last_log_record_created = log_record.created

        # Compute delta time since last message.
        zero_delta, last_delta = self.__sample_instant(log_record.created)

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

        formatted_exception = self.formatException(log_record.exc_info)

        formatted_stack = self.formatStack(log_record.stack_info)

        # We want short format?
        if self.type == "bare":
            pass

        # We want short format?
        elif self.type == "short":
            # Pretty up the filename as a module.
            module2 = self.__parse_module_from_filename(pathname)
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

        # We want separate indices for a database such as graylog.
        if self.type == "dls":
            log_record.dls = True
            log_record.dls_pathname = pathname
            log_record.dls_funcname = funcname
            log_record.dls_lineno = lineno
            log_record.dls_message = formatted_message
            log_record.dls_message_plus_exception = (
                formatted_message + formatted_exception
            )
            log_record.dls_process = log_record.process
            log_record.dls_process_name = log_record.processName
            log_record.dls_thread_name = log_record.threadName
            log_record.dls_levelname = log_record.levelname
            log_record.dls_exception = formatted_exception
            log_record.dls_stack = formatted_stack

        formatted_message = str(formatted_message) + formatted_exception

        formatted_message = str(formatted_message) + formatted_stack

        self.__last_formatted_message = formatted_message
        return formatted_message

    # -----------------------------------------------------------------
    def formatTime(self, log_record, datefmt=None):
        """
        Override base method to provide the custom date formatting on the given record.

        Ignores datefmt argument.  Always uses Y-m-d H:M:s.microseconds.
        """
        return time.strftime(
            "%Y-%m-%d %H:%M:%S.", time.localtime(log_record.created)
        ) + ("%06d" % (int(log_record.msecs * 1000.0)))

    # -----------------------------------------------------------------
    def formatException(self, exc_info):
        """
        Override base method to provide the custom date formatting on the given record.

        The exc_info is standard triple (type, value, traceback).

        Format the exception type and message,
        with all tracebacks and chained exceptions.

        Return as one string with newline characters in it.
        Put an indent of some spaces on subsequent lines after the first.
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
            module2 = self.__parse_module_from_filename(frame_summary.filename)

            lines.append(self.__format_frame_summary(module2, frame_summary))

        # Also append any chained exception.
        if exception.__cause__ is not None:
            lines.extend(self._format_exception_lines(exception.__cause__))
        elif exception.__context__ is not None:
            lines.extend(self._format_exception_lines(exception.__context__))

        return lines

    # -----------------------------------------------------------------
    def formatStack(self, stack_info):
        """
        Override base method to provide the custom stack formatting on the given record.

        Skips uninteresting stack frames.
        """

        if stack_info is None:
            return ""

        output_lines = [""]

        stack_summary = traceback.extract_stack()
        first = True
        for frame_summary in reversed(stack_summary):

            # Pretty up the filename as a module.
            module2 = self.__parse_module_from_filename(frame_summary.filename)

            # Skip boring stack entries.
            if "/dls_logform.py" in frame_summary.filename:
                continue
            if module2.startswith("logging."):
                continue

            # Stop when we hit the interpreter.
            if module2.startswith("_pytest."):
                break
            if module2.startswith("python3."):
                break

            if not first:
                output_lines.append(self.__format_frame_summary(module2, frame_summary))

            first = False

        return self.type_info[self.type]["indent"].join(output_lines)

    # -----------------------------------------------------------------
    def __parse_module_from_filename(self, filename: str) -> str:
        """
        _summary_

        Args:
            filename (str): name of the source file.

        Returns:
            str: the parsed module name derived from the filename.
        """

        # Remove backslashes put there from a Windows filesystem.
        module2 = filename.replace("\\", "/")

        # Keep just last two parts of the path.
        module2_parts = module2.split("/")
        if len(module2_parts) > 1:
            module2_parts = module2_parts[-2:]

        # Join path parts with a dot.
        module2 = ".".join(module2_parts)

        # Chop off the .py at the end.
        if module2.endswith(".py"):
            module2 = module2[:-3]

        return module2

    # -----------------------------------------------------------------
    def __format_frame_summary(
        self, module2: str, frame_summary: traceback.FrameSummary
    ) -> str:
        """
        Format a single StackSummary to look nice as a single line in the output.

        Args:
            module2 (str): parsed name of the module
            frame_summary (traceback.FrameSummary):
                the FrameSummary from traceback.extract_tb to be formatted

        Returns:
            str: line of output according to the formatting type we are doing.
        """

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
    def __sample_instant(self, created):
        """
        Give deltas from this record since the past record.
        The value of created is the time when the LogRecord was created
        (as returned by time.time()).
        This is only accurate if log records are being produced on the same computer.
        """

        if self._time_zero is None:
            self._time_zero = created

        if self._time_last is None:
            self._time_last = created

        zero_delta = int((created - self._time_zero) * 1000.0)
        last_delta = int((created - self._time_last) * 1000.0)

        self._time_last = created

        return zero_delta, last_delta
