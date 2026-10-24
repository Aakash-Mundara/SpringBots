$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root 'local/logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Weed = Join-Path $Root 'local/bin/weed.exe'
if (!(Test-Path $Weed)) { $Weed = (Get-Command weed -ErrorAction SilentlyContinue).Source }
$Elastic = Join-Path $Root 'local/bin/elasticmq-server-all.jar'
if (!$Weed) { throw 'Put weed.exe in local/bin or add weed to PATH.' }
if (!(Test-Path $Elastic)) { throw 'Put ElasticMQ standalone jar at local/bin/elasticmq-server-all.jar.' }
if (!(Get-Command java -ErrorAction SilentlyContinue)) { throw 'Java 21+ is required.' }
if (!(Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node 20+ and npm are required.' }
Start-Process -FilePath $Weed -ArgumentList @('server', "-dir=$(Join-Path $Root 'local/seaweed')", '-s3') -RedirectStandardOutput (Join-Path $LogDir 'seaweed.log') -RedirectStandardError (Join-Path $LogDir 'seaweed.err.log')
Start-Process -FilePath 'java' -ArgumentList @("-Dconfig.file=$(Join-Path $Root 'local/elasticmq.conf')", '-jar', $Elastic) -RedirectStandardOutput (Join-Path $LogDir 'elasticmq.log') -RedirectStandardError (Join-Path $LogDir 'elasticmq.err.log')
Start-Sleep -Seconds 3
Start-Process -FilePath (Join-Path $Root 'mvnw.cmd') -ArgumentList @('-q','-DskipTests','spring-boot:run') -WorkingDirectory $Root -RedirectStandardOutput (Join-Path $LogDir 'backend.log') -RedirectStandardError (Join-Path $LogDir 'backend.err.log')
$Frontend = Join-Path $Root 'frontend'
if (!(Test-Path (Join-Path $Frontend 'node_modules'))) { Start-Process npm -ArgumentList @('install') -WorkingDirectory $Frontend -Wait }
Start-Process npm -ArgumentList @('run','dev') -WorkingDirectory $Frontend -RedirectStandardOutput (Join-Path $LogDir 'frontend.log') -RedirectStandardError (Join-Path $LogDir 'frontend.err.log')
Write-Host 'OnboardIQ starting: http://localhost:5173 | API http://localhost:8080/api/v1/health | Swagger http://localhost:8080/swagger-ui.html | ElasticMQ stats http://localhost:9325'
