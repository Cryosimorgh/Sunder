@echo off
rem Full 1K population is admitted before measuring 600 rendered frames.
call "%~dp0LAUNCH_G7_CAPABILITIES_DEMO.cmd" --render-bench --frames 600 %*
exit /b %errorlevel%
