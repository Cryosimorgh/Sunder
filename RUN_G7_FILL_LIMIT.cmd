@echo off
rem Native physics-only capacity ramp. No arbitrary population cap; GPU resources and validation stop admission.
call "%~dp0LAUNCH_G7_CAPABILITIES_DEMO.cmd" --fill-until-limit %*
exit /b %errorlevel%
