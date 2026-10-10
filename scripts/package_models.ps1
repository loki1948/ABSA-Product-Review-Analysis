<#
.SYNOPSIS
  Package the three deployed models for teammates, or check and unpack a package.

.EXAMPLE
  .\scripts\package_models.ps1                         # writes absa-models.zip and absa-models.zip.sha256
  .\scripts\package_models.ps1 -Install absa-models.zip   # verifies the hash, then unpacks into models\

  Nothing is deleted. -Install refuses to overwrite a model folder that already
  holds a model; move it away first (see docs/model_recovery.md).
#>
param(
    [string]$Install,
    [string]$Output = "absa-models.zip"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$models = Join-Path $root "models"
$names = "aspect_extraction", "sentiment", "overall_sentiment"

if ($Install) {
    $expectedFile = "$Install.sha256"
    $actual = (Get-FileHash $Install -Algorithm SHA256).Hash
    if (Test-Path $expectedFile) {
        $expected = (Get-Content $expectedFile -Raw).Trim().Split(" ")[0]
        if ($actual -ne $expected) { throw "Hash mismatch: the archive is damaged or not the one that was shared.`n expected $expected`n actual   $actual" }
        Write-Host "Hash verified: $actual"
    } else {
        Write-Warning "No $expectedFile next to the archive; compare this hash with the one the sender posted: $actual"
    }
    foreach ($name in $names) {
        if (Test-Path (Join-Path $models "$name\config.json")) {
            throw "models\$name already holds a model. Move it away first (docs/model_recovery.md)."
        }
    }
    Expand-Archive $Install -DestinationPath $models -Force
    Write-Host "Installed. Now run, from backend\:  python -m pytest -m model"
    return
}

foreach ($name in $names) {
    foreach ($file in "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "training_log.json") {
        if (-not (Test-Path (Join-Path $models "$name\$file"))) { throw "models\$name\$file is missing: nothing packaged." }
    }
}
$target = Join-Path $root $Output
if (Test-Path $target) { throw "$target already exists. Move or rename it first." }
Compress-Archive -Path ($names | ForEach-Object { Join-Path $models $_ }) -DestinationPath $target -CompressionLevel Fastest
$hash = (Get-FileHash $target -Algorithm SHA256).Hash
"$hash  $Output" | Set-Content "$target.sha256" -Encoding ascii
Write-Host ("Wrote {0} ({1:N2} GB)`nSHA256 {2}`nShare both files." -f $target, ((Get-Item $target).Length / 1GB), $hash)
