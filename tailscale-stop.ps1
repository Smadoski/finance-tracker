$cmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
$exe = if ($cmd) { $cmd.Source } else { "C:\Program Files\Tailscale\tailscale.exe" }
if (-not (Test-Path $exe)) { throw "Tailscale CLI not found." }
& $exe serve --https=8443 off
