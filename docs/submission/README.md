# Submission files

| File | What it is |
|---|---|
| `ABSA_Project_Report.docx` / `.pdf` | The project report with appendices: full results, baseline comparison, error analysis, transfer study |
| `ABSA_Presentation.pptx` / `.pdf` | The presentation, 18 slides including four screenshots |

These are built from `docs/report.md` and `docs/slides.md`, which are
themselves generated from the evaluation outputs. Do not edit the files in this
folder by hand: a later export overwrites them. To change wording, edit
`backend/training/report.py`; to change layout, edit `backend/training/export.py`.

## Rebuild

From `backend/`, with the development requirements installed
(`pip install -r requirements-dev.txt`):

```powershell
python -m training.report      # docs/report.md, docs/slides.md
python -m training.export      # the .docx and the .pptx
```

The PDFs are made from those two files with Word and PowerPoint
(File, Export, Create PDF), or from PowerShell:

```powershell
$dir = (Resolve-Path ..\docs\submission).Path
$word = New-Object -ComObject Word.Application
$doc = $word.Documents.Open("$dir\ABSA_Project_Report.docx", $false, $true)
$doc.ExportAsFixedFormat("$dir\ABSA_Project_Report.pdf", 17); $doc.Close($false); $word.Quit()
$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Open("$dir\ABSA_Presentation.pptx", $true, $false, $false)
$pres.SaveAs("$dir\ABSA_Presentation.pdf", 32); $pres.Close(); $ppt.Quit()
```

Screenshots come from `frontend/scripts/browser-checks.mjs`, run against the
application with the trained models loaded.

## Before submitting

- The slides use PowerPoint's default design. Apply the required template, if
  there is one, in PowerPoint and save a copy under another name.
- Add the names, roll numbers, course and supervisor on the title page and the
  title slide: none of that is in the repository, so it is not in these files.
- Read both documents once: they were generated and checked for content, not
  proofread for layout.
