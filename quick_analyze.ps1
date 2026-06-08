# Quick PE Analysis
$exePath = Get-ChildItem -Path "D:\*\Documents\Downloads\*.exe" | Select-Object -First 1 -ExpandProperty FullName
$bytes = [IO.File]::ReadAllBytes($exePath)

Write-Host "=== QUICK TECH STACK DETECT ==="

# Check for PyInstaller
if ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('PyInstaller')) {
    Write-Host "Tech: PyInstaller (Python)"
} elseif ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('python')) {
    Write-Host "Tech: Python (possibly py2exe)"
} elseif ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('node.exe')) {
    Write-Host "Tech: Electron (Node.js)"
} elseif ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('Go Build')) {
    Write-Host "Tech: Go"
} elseif ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('rustc')) {
    Write-Host "Tech: Rust"
} else {
    Write-Host "Tech: Likely C/C++ (Native Win32)"
}

# Check for MSVC
if ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('MSVCR')) {
    Write-Host "Runtime: MSVC Runtime detected"
}

# Check for .NET
if ([System.Text.Encoding]::ASCII.GetString($bytes).Contains('mscorlib')) {
    Write-Host "Tech: .NET (C#/VB.NET)"
}

Write-Host "`n=== UI FRAMEWORK ==="
$str = [System.Text.Encoding]::ASCII.GetString($bytes)
if ($str -match 'MFC|AFX') { Write-Host "UI: MFC (Microsoft Foundation Classes)" }
if ($str -match 'Qt|QtCore') { Write-Host "UI: Qt Framework" }
if ($str -match 'GTK|gtk') { Write-Host "UI: GTK+" }
if ($str -match 'wxWidgets') { Write-Host "UI: wxWidgets" }
if ($str -match 'DialogEx|CreateWindow') { Write-Host "UI: Win32 API Dialog" }
if ($str -match 'Electron|Chrome') { Write-Host "UI: Electron" }

Write-Host "`n=== KEY STRINGS (sample) ==="
$matches = [regex]::Matches([System.Text.Encoding]::ASCII.GetString($bytes), '[\x20-\x7E]{10,80}')
$seen = @{}
$count = 0
foreach ($m in $matches) {
    $s = $m.Value
    if ($s -match '[A-Za-z]{4,}' -and !$seen.ContainsKey($s)) {
        Write-Host $s
        $seen[$s] = $true
        $count++
        if ($count -ge 50) { break }
    }
}
