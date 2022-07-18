dls-logform
===========

Summary
-------
Version 5.0.32

Styles Python log messages by override of the Python logging.Formatter
class.

The programmer needs to use the standard Python logging to produce info,
debug and exception message for both users, developers and logstash to
use. It is not trivial to format messages with the correct information
which suits all three consumers. This class provides the programmer with
a no-code solution for consistent log formatting.

This is a Python class which derives from logging.Formatter, adding
formatting to include timestamp, origination, and traceback for both
human readable and grokable.

Usage
-----

.. code:: python

   import logging

   from dls_logform.dls_logform import DlsLogform
   from dls_logform.dls_logform import format_exception_causes

   # Make handler which writes the logs to console.
   handler = logging.StreamHandler()

   # Make the formatter from the MaxIV library.
   maxiv_formatter = DlsLogform()

   # Let handler write custom formatted messages.
   handler.setFormatter(maxiv_formatter)

   # Let root logger use the file handler.
   root_logger = logging.getLogger()
   root_logger.addHandler(handler)

   # Log level for all modules.
   root_logger.setLevel("DEBUG")

   # Log something.
   root_logger.info("this is something")

   # Cause an exception chain to be logged.
   try:
       one()

   except Exception as exception:
       logger.exception(
           "exception in main %s" % (format_exception_causes(exception)),
           exc_info=exception,
       )


   def one():
       try:
           two()
       except:
           raise RuntimeError("badness in one while calling two")
       
   def two():
       raise RuntimeError("badness in two")

description
-----------

-  a library to enable enhanced log formatting
-  foundation for even more improvements to log formatting

use cases
---------

-  developer wishes to see debug output with more useful information
   than standard logging
-  many developers working on many programs and device servers want to
   unify output format
-  operations person running a pipeline with multiple running processes
   needs to combine logs using same format

implementation
--------------

-  use python standard logging
-  custom formatter overrides logging.Formatter to give time, process,
   source file and message

example log output
------------------

::

   2020-02-23 09:09:10.635885 30048 det-viz-00   worker-main      1390      149 INFO     /root/workspace/lib-maxiv-daqcluster/lib_maxiv_daqcluster/worker.py@69 worker process det-viz-00 started
   2020-02-23 09:09:10.811396 30034 liveprep-00  worker-main      1566      405 DEBUG    /root/workspace/lib-maxiv-valkyrie-python/lib_maxiv_valkyrie/zmq_pubsub/writer.py@48 server to tcp://*:19108 binding
   2020-02-23 09:09:10.896064 30044 fai1d-viz    MainThread       1651      430 INFO     /root/workspace/lib-maxiv-daqcluster/lib_maxiv_daqcluster/liveview.py@57 liveview process fai1d-viz starting
   2020-02-23 09:09:10.988101 29972 MainProcess  daq              1743      432 INFO     /root/workspace/lib-maxiv-daqcluster/lib_maxiv_daqcluster/orchestrator.py@58 ScanSettingsKeywords.WORKER_COUNT is 1
   2020-02-23 09:09:11.039062 30048 det-viz-00   worker-main      1793      403 DEBUG    /root/workspace/lib-maxiv-valkyrie-python/lib_maxiv_valkyrie/zmq_pubsub/reader.py@50 client to tcp://localhost:19108 connecting
   2020-02-23 09:09:11.056322 30098 worker000    worker-main      1811       68 INFO     /root/workspace/lib-maxiv-daqcluster/lib_maxiv_daqcluster/worker.py@69 worker process worker000 started

change log
----------

2020-08-18 2.0.1 fixes bug in time format, current format of this
version is now being used by logstash grok filter for b-v-log-1.
2020-11-23 2.0.3 fixes README example program 2021-02-08 2.1.0 adds
format_exception_causes() and list_exception_causes()
