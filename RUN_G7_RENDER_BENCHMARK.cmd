@echo off
rem Defaults to 1K / 600 frames for regression; pass --count N and physics flags to override.
echo Automated render benchmark: fixed number of frames, exits after the test.
 echo For an editable graphical window use RUN_G7_VISUAL_BENCHMARK.cmd.
call "%~dp0LAUNCH_G7_CAPABILITIES_DEMO.cmd" --render-bench --frames 600 %*
exit /b %errorlevel%
