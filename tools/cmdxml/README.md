cmdxml
======

Generate JunitXML output from executing shell commands.
Based on `pytest`.


Description
-----------

This script allows generating xml reports for the execution of different shell
commands. The goal is allow command execution to produce a parseable JunitXML
report for a continuous integration server like Jenkins.

It is implemented around `pytest` to use our specifically crafted files.


Usage
-----

```
Usage: cmdxml [--command CMD] [--script SCRIPT] [...]

custom options:
  --command=command     Command to test, can be specified multiple times
  --script=script       Script to test, can be specified multiple times

other options from pytest
```

Examples:
---------

Execute two commands and one script

```
cmdxml --command 'date' --command 'test -f hello' --script 'script.sh'
============================= test session starts ==============================
......
collected 4 items / 1 deselected

cmdxml.py::test_command[date] PASSED                                     [ 33%]
cmdxml.py::test_command[test -f hello] FAILED                            [ 66%]
cmdxml.py::test_script[script.sh] PASSED                                 [100%]

=================================== FAILURES ===================================
_________________________ test_command[test -f hello] __________________________
cmdxml.py:25: in test_command
    assert _execute_command(command) == 0
E   AssertionError: assert 1 == 0
E    +  where 1 = _execute_command('test -f hello')
----------------------------- Captured stderr call -----------------------------
+ test -f hello
 generated xml file: .../report.xml
=============== 1 failed, 2 passed, 1 deselected in 0.05 seconds ===============
```


Integration in RIOT
-------------------

The integration is done through a global goal so must be used alone.

    RIOT_MAKEFILES_GLOBAL_PRE=${THIS_DIR}/clean_all.mk.pre make -C tests/bloom_bytes/ cmdxml-clean-all
