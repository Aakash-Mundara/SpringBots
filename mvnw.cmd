@echo off
where mvn >nul 2>nul
if %errorlevel%==0 (
  mvn -f "%~dp0backend\pom.xml" %*
  exit /b %errorlevel%
)
echo Maven is not installed. Install Maven 3.9+ or use WSL/Git Bash with ./mvnw.
exit /b 1
