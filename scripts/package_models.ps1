<#
.SYNOPSIS
  Package the three deployed models for teammates, or check and unpack a package.

.EXAMPLE
  .\scripts\package_models.ps1                         # writes absa-models.zip and absa-models.zip.sha256
  .\scripts\package_models.ps1 -Install absa-models.zip   # verifies the hash, then unpacks into models\

  Nothing is deleted. -Install refuses to unpack over a model folder that holds
  anything but the placeholder, and refuses an archive it cannot verify.
#>
param(
    [string]$Install,
    [string]$Output = "absa-models.zip",
    # Install even though no .sha256 file is next to the archive (not recommended).
    [switch]$SkipHashCheck,
    # Package the historical material instead: earlier models, the record of the
    # training run and the old log. Writes absa-history.zip. Not needed to run
    # the application; kept because the earlier models cannot be recreated.
    [switch]$History
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$models = Join-Path $root "models"
$names = "aspect_extraction", "sentiment", "overall_sentiment"

if ($History) {
    $target = Join-Path $root "absa-history.zip"
    if (Test-Path $target) { throw "$target already exists. Move or rename it first." }
    # Files are read in place and written straight into the archive: nothing is
    # copied, moved or removed.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::Open($target, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        $files = @()
        foreach ($item in "previous", "sentiment_joint_backup", "candidates\eval", "candidates\logs") {
            $source = Join-Path $models $item
            if (Test-Path $source) { $files += Get-ChildItem $source -Recurse -File } else { Write-Warning "models\$item not found, skipped" }
        }
        foreach ($file in "train_sentiment_aspect.log", "evaluation_report.json", "baseline_report.json", "laptops_only_report.json") {
            $source = Join-Path $models $file
            if (Test-Path $source) { $files += Get-Item $source }
        }
        foreach ($f in $files) {
            $entry = $f.FullName.Substring($models.Length + 1).Replace("\", "/")
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, $entry, [System.IO.Compression.CompressionLevel]::Fastest) | Out-Null
        }
    } finally {
        $zip.Dispose()
    }
    $hash = (Get-FileHash $target -Algorithm SHA256).Hash
    "$hash  absa-history.zip" | Set-Content "$target.sha256" -Encoding ascii
    Write-Host ("Wrote {0} ({1:N2} GB)`nSHA256 {2}" -f $target, ((Get-Item $target).Length / 1GB), $hash)
    return
}

if ($Install) {
    $expectedFile = "$Install.sha256"
    $actual = (Get-FileHash $Install -Algorithm SHA256).Hash
    if (Test-Path $expectedFile) {
        $expected = (Get-Content $expectedFile -Raw).Trim().Split(" ")[0]
        if ($actual -ne $expected) { throw "Hash mismatch: the archive is damaged or not the one that was shared.`n expected $expected`n actual   $actual" }
        Write-Host "Hash verified: $actual"
    } elseif ($SkipHashCheck) {
        Write-Warning "Hash not checked. SHA256 of this archive: $actual"
    } else {
        throw "No $expectedFile next to the archive, so it cannot be verified. Get that file from the sender, or pass -SkipHashCheck. SHA256 of this archive: $actual"
    }
    foreach ($name in $names) {
        $folder = Join-Path $models $name
        $content = @(Get-ChildItem $folder -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' })
        if ($content.Count -gt 0) {
            throw "models\$name is not empty. Move it away first (docs/model_recovery.md); nothing was unpacked."
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
