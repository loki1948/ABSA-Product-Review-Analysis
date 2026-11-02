# Let Word fill in the table of contents of the template report and export a PDF copy.
# Run from the repository root after to_docx.py:
#   powershell -ExecutionPolicy Bypass -File docs\report_site\update_toc.ps1
$ErrorActionPreference = "Stop"
$sub = (Resolve-Path "$PSScriptRoot\..\submission").Path
$docx = Join-Path $sub "ABSA_Project_Report_Template.docx"
$pdf = Join-Path $sub "ABSA_Project_Report_Template.pdf"
function Log($m) { Write-Output ("{0:HH:mm:ss} {1}" -f (Get-Date), $m) }
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    Log "opening"
    $doc = $word.Documents.Open($docx)
    Log ("pages: " + $doc.ComputeStatistics(2))
    $doc.TablesOfContents.Item(1).Update()
    $doc.Fields.Update() | Out-Null
    Log "fields updated"
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)
    Log "pdf exported"
    $doc.Close($false)
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
