# ...existing code...
# Load MaxMind license key from file (geoip_license.txt) or environment variable GEOIP_LICENSE.
# Do NOT store the key in this script.
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$licenseFile = Join-Path $scriptRoot "geoip_license.txt"

$license = $null

# 1) Try environment variable first
if ($env:GEOIP_LICENSE -and $env:GEOIP_LICENSE.Trim() -ne "") {
    $license = $env:GEOIP_LICENSE.Trim()
}

# 2) Fallback to file if env var not set
if (-not $license -and (Test-Path $licenseFile)) {
    try {
        $lines = Get-Content -Path $licenseFile -ErrorAction Stop | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
        if ($lines.Count -ge 1) {
            $license = $lines[0]
        }
    } catch {
        Write-Error "Failed reading license file ${licenseFile}: $($_)"
        exit 1
    }
}

if (-not $license) {
    Write-Error "GeoIP license not found. Create geoip_license.txt containing the license key (first non-empty line) or set GEOIP_LICENSE environment variable."
    exit 1
}

# ...existing code continues unchanged...
$url = "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=$license&suffix=tar.gz"
$destDir = "C:\inetpub\aquaponics\geoip"
New-Item -Path $destDir -ItemType Directory -Force | Out-Null
$tarGz = Join-Path $destDir "GeoLite2-City.tar.gz"

try {
    Invoke-WebRequest -Uri $url -OutFile $tarGz -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
} catch {
    $err = $_
    Write-Error "Download failed: $($err.Exception.Message)"
    try {
        $resp = $err.Exception.Response
        if ($resp -ne $null) {
            $stream = $resp.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $body = $reader.ReadToEnd()
            Write-Error "Server response body (first 2000 chars):"
            Write-Error $body.Substring(0,[math]::Min(2000,$body.Length))
        }
    } catch {
        Write-Error "Unable to read response body: $($_.Exception.Message)"
    }
    Remove-Item $tarGz -ErrorAction SilentlyContinue
    exit 1
}

try {
    tar -xzf $tarGz -C $destDir
} catch {
    Write-Error "Failed to extract ${tarGz}: $($_)"
    Remove-Item $tarGz -ErrorAction SilentlyContinue
    exit 1
}

Get-ChildItem -Path $destDir -Recurse -Filter "GeoLite2-City.mmdb" | ForEach-Object {
  Move-Item -Path $_.FullName -Destination (Join-Path $destDir "GeoLite2-City.mmdb") -Force
}

Remove-Item $tarGz -Force
// ...existing code...