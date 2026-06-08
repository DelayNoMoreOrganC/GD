# PE File Analyzer
# Analyzes Windows executable to extract metadata and dependencies

$exePath = Get-ChildItem -Path "D:\*\Documents\Downloads\*.exe" | Select-Object -First 1 -ExpandProperty FullName

try {
    $file = Get-Item $exePath
    Write-Host "=== BASIC INFO ==="
    Write-Host "Size: $($file.Length / 1MB) MB"
    Write-Host "Created: $($file.CreationTime)"

    Write-Host "`n=== PE SIGNATURE ==="
    $bytes = [System.IO.File]::ReadAllBytes($exePath)
    $mz = [char]$bytes[0] + [char]$bytes[1]
    Write-Host "MZ Signature: $mz"

    # PE offset at 0x3C
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    Write-Host "PE Offset: 0x$($peOffset.ToString('X'))"

    if ($peOffset -lt $bytes.Length - 4) {
        $peSig = [char]$bytes[$peOffset] + [char]$bytes[$peOffset+1] + [char]$bytes[$peOffset+2] + [char]$bytes[$peOffset+3]
        Write-Host "PE Signature: $peSig"

        # Machine type at PE offset + 4
        $machine = [BitConverter]::ToInt16($bytes, $peOffset + 4)
        Write-Host "Machine Type: 0x$($machine.ToString('X'))"

        # Number of sections
        $sections = [BitConverter]::ToInt16($bytes, $peOffset + 6)
        Write-Host "Sections: $sections"

        # Characteristics
        $chars = [BitConverter]::ToInt16($bytes, $peOffset + 22)
        Write-Host "Characteristics: 0x$($chars.ToString('X'))"
        Write-Host "  -> $(if ($chars -band 0x2000) { 'DLL' } else { 'EXE' })"
        Write-Host "  -> $(if ($chars -band 0x0100) { '32-bit' } elseif ($chars -band 0x0200) { '64-bit' } else { 'Unknown' })"
    }

    Write-Host "`n=== STRING SEARCH KEYWORDS ==="
    $keywords = @('dll', 'python', 'file', 'system', 'window', 'error', 'visual', 'basic', 'c++', 'mingw', 'msvc', 'gtk', 'qt', 'framework', 'electron')
    $strAll = [System.Text.Encoding]::ASCII.GetString($bytes)
    foreach ($kw in $keywords) {
        if ($strAll -like "*$kw*") {
            Write-Host "Found: $kw"
        }
    }

    Write-Host "`n=== IMPORT DLL HINTS ==="
    $dllStrings = $strAll -split '[\x00-\x1F]' | Where-Object { $_ -match '\.dll$' -and $_.Length -lt 50 }
    $dllStrings | Select-Object -First 20 | ForEach-Object { Write-Host $_ }

    Write-Host "`n=== LONGER READABLE STRINGS ==="
    $longStrings = $strAll -split '[\x00-\x1F]' | Where-Object { $_.Length -gt 15 -and $_.Length -lt 100 -and $_ -match '^[a-zA-Z0-9 ./\\:_-]{4,}$' }
    $longStrings | Select-Object -First 30 | ForEach-Object { Write-Host $_ }

} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
