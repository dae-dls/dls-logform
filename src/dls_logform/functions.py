from typing import Literal, List
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


def flatten_exception_message(exception: BaseException) -> str:
    """
    Remove newlines from certain package exception messages to make them look a little nicer.

    This function knows how to flatten error messages from certain external packages.

    Currently these are: PyTango and Jupyter nbconvert.

    Does not import these packages, insteads bases discovery on class type.
    """

    # Get the informative part of a tango exception.
    if type(exception).__name__ in [
        "DevFailed",
        "ConnectionFailed",
        "CommunicationFailed",
    ]:
        try:
            message = exception.args[0].desc.rstrip().replace("\n", " ")
        except Exception as exception2:
            message = str(exception2)

    # Get the informative part of a particular Jupyter nbconvert error.
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
def list_exception_causes(exception: BaseException) -> List[str]:
    """
    Recurse through the cause chain, making
    an array of lines by appending the exception message
    with the causing exceptions' messages.

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
def format_exception_causes(exception: BaseException, join_string="... ") -> str:
    """
    Make a single string by joining the exception message with the causing exceptions' messages.

    Typically used when a the message is intended for a
    display mechanism known not to show a multiline message very well,
    such as some Tango's Jive and other MsgBox type dialogs.
    """

    return join_string.join(list_exception_causes(exception))
