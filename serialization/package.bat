@echo off
setlocal enabledelayedexpansion

:: Package files into a .node zip file
:: Usage: package_to_node.bat <output_name> <file1> [file2] [file3] ...
:: Example: package_to_node.bat my_package file.txt folder\

if "%~1"=="" (
    echo Usage: %~nx0 ^<output_name^> ^<file1^> [file2] [file3] ...
    echo.
    echo Creates a .node file ^(zip format^) containing the specified files/folders
    echo.
    echo Examples:
    echo   %~nx0 my_package file.txt
    echo   %~nx0 my_package file1.txt file2.txt folder\
    echo   %~nx0 my_package *.txt
    exit /b 1
)

set "output_name=%~1"
shift

if /i "%output_name:~-5%"==".node" (
    set "output_name=%output_name:~0,-5%"
)

set "node_file=%output_name%.node"

if exist "%node_file%" (
    echo Warning: %node_file% already exists. It will be overwritten.
    del "%node_file%" 2>nul
)

set "files_to_add="
set "file_count=0"

:collect_files
if "%~1"=="" goto create_package

if exist "%~1" (
    set "files_to_add=!files_to_add!'%~1',"
    set /a file_count+=1
    echo Adding: %~1
) else (
    echo Warning: '%~1' not found, skipping...
)

shift
goto collect_files

:create_package
if %file_count%==0 (
    echo Error: No valid files or folders found to package.
    exit /b 1
)

set "files_to_add=%files_to_add:~0,-1%"

echo.
echo Creating %node_file%...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$files = @(%files_to_add%); " ^
    "if (Test-Path '%node_file%') { Remove-Item '%node_file%' -Force }; " ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem; " ^
    "$zip = [System.IO.Compression.ZipFile]::Open('%CD%\%node_file%', 'Create'); " ^
    "$hashData = @(); " ^
    "foreach ($file in $files) { " ^
        "if (Test-Path $file) { " ^
            "if ((Get-Item $file).PSIsContainer) { " ^
                "$folderName = Split-Path $file -Leaf; " ^
                "Get-ChildItem $file -Recurse | ForEach-Object { " ^
                    "if (-not $_.PSIsContainer) { " ^
                        "$relativePath = $_.FullName.Substring((Resolve-Path $file).Path.Length + 1); " ^
                        "$entryName = $folderName + '/' + $relativePath.Replace('\', '/'); " ^
                        "[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entryName) | Out-Null; " ^
                        "$fileHash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash; " ^
                        "$hashData += $entryName + ':' + $fileHash; " ^
                    "} " ^
                "}; " ^
            "} else { " ^
                "$fileName = Split-Path $file -Leaf; " ^
                "[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, (Resolve-Path $file).Path, $fileName) | Out-Null; " ^
                "$fileHash = (Get-FileHash (Resolve-Path $file).Path -Algorithm SHA256).Hash; " ^
                "$hashData += $fileName + ':' + $fileHash; " ^
            "} " ^
        "} " ^
    "}; " ^
    "$sortedHashData = $hashData | Sort-Object; " ^
    "$combinedHash = ($sortedHashData -join '|'); " ^
    "$finalHash = [System.Security.Cryptography.HashAlgorithm]::Create('SHA256').ComputeHash([System.Text.Encoding]::UTF8.GetBytes($combinedHash)); " ^
    "$hashString = [System.BitConverter]::ToString($finalHash).Replace('-', '').ToLower(); " ^
    "$configEntry = $zip.CreateEntry('.config'); " ^
    "$configStream = $configEntry.Open(); " ^
    "$configBytes = [System.Text.Encoding]::UTF8.GetBytes('hash=' + $hashString + [Environment]::NewLine + 'created=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ') + [Environment]::NewLine); " ^
    "$configStream.Write($configBytes, 0, $configBytes.Length); " ^
    "$configStream.Close(); " ^
    "$zip.Dispose(); " ^
    "Write-Host 'Content hash: ' $hashString;"

if exist "%node_file%" (
    echo.
    echo Successfully created: %node_file%
    
    for %%A in ("%node_file%") do (
        echo File size: %%~zA bytes
    )
    
    echo.
    echo Contents:
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Add-Type -AssemblyName System.IO.Compression.FileSystem; " ^
        "$zip = [System.IO.Compression.ZipFile]::OpenRead('%CD%\%node_file%'); " ^
        "$zip.Entries | ForEach-Object { '  ' + $_.FullName + ' (' + $_.Length + ' bytes)' }; " ^
        "$zip.Dispose();"
        
    echo.
    echo Package created successfully!
) else (
    echo.
    echo Error: Failed to create %node_file%
    exit /b 1
)

endlocal
