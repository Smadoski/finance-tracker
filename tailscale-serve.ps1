$ErrorActionPreference = "Stop"
$cmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
$exe = if ($cmd) { $cmd.Source } else { "C:\Program Files\Tailscale\tailscale.exe" }
if (-not (Test-Path $exe)) { throw "Tailscale CLI not found. Install Tailscale and sign in first." }
& $exe serve --bg --https=8443 127.0.0.1:8080
& $exe serve status
