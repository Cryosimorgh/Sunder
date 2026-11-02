@echo off
rem Defaults to 1K / 600 frames for regression; pass --count N and physics flags to override.
call "%~dp0LAUNCH_G7_CAPABILITIES_DEMO.cmd" --render-bench --frames 600 %*
exit /b %errorlevel%
