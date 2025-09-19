#!/usr/bin/env pwsh
# Convert all files from CRLF to LF line endings
# This script recursively processes all files in the project and converts line endings

param(
    [string]$Path = ".",
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

# File extensions to process (add more as needed)
$FileExtensions = @(
    "*.py", "*.js", "*.ts", "*.tsx", "*.json", "*.md", "*.txt", "*.yml", "*.yaml",
    "*.sql", "*.sh", "*.ps1", "*.html", "*.css", "*.scss", "*.sass", "*.less",
    "*.xml", "*.toml", "*.ini", "*.cfg", "*.conf", "*.env", "*.gitignore",
    "*.dockerfile", "*.dockerignore", "*.eslintrc*", "*.prettierrc*"
)

# Directories to exclude
$ExcludeDirectories = @(
    "node_modules", ".git", "__pycache__", ".pytest_cache", "dist", "build",
    "coverage", ".coverage", "venv", "env", ".venv", ".env", "target",
    "bin", "obj", ".vs", ".vscode", ".idea", "*.egg-info"
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Test-ShouldExcludeDirectory {
    param([string]$DirectoryPath)
    
    foreach ($excludePattern in $ExcludeDirectories) {
        if ($DirectoryPath -like "*$excludePattern*") {
            return $true
        }
    }
    return $false
}

function Convert-FileToLF {
    param(
        [string]$FilePath,
        [bool]$DryRun,
        [bool]$Verbose
    )
    
    try {
        # Read file content as bytes to detect line endings
        $content = [System.IO.File]::ReadAllBytes($FilePath)
        
        # Check if file contains CRLF (0x0D 0x0A)
        $hasCRLF = $false
        for ($i = 0; $i -lt $content.Length - 1; $i++) {
            if ($content[$i] -eq 0x0D -and $content[$i + 1] -eq 0x0A) {
                $hasCRLF = $true
                break
            }
        }
        
        if (-not $hasCRLF) {
            if ($Verbose) {
                Write-Log "File already has LF endings: $FilePath" "DEBUG"
            }
            return $false
        }
        
        if ($DryRun) {
            Write-Log "Would convert: $FilePath" "DRY-RUN"
            return $true
        }
        
        # Read file as text and convert line endings
        $textContent = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
        
        # Remove BOM if present
        $textContent = $textContent.TrimStart([char]0xFEFF)
        
        # Convert line endings
        $convertedContent = $textContent -replace "`r`n", "`n"
        
        # Write back to file without BOM
        [System.IO.File]::WriteAllText($FilePath, $convertedContent, [System.Text.UTF8Encoding]::new($false))
        
        Write-Log "Converted: $FilePath" "SUCCESS"
        return $true
        
    } catch {
        Write-Log "Error processing file $FilePath`: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Process-Directory {
    param(
        [string]$DirectoryPath,
        [bool]$DryRun,
        [bool]$Verbose
    )
    
    if (Test-ShouldExcludeDirectory $DirectoryPath) {
        if ($Verbose) {
            Write-Log "Skipping excluded directory: $DirectoryPath" "DEBUG"
        }
        return
    }
    
    try {
        # Process files in current directory
        foreach ($extension in $FileExtensions) {
            $files = Get-ChildItem -Path $DirectoryPath -Filter $extension -File -ErrorAction SilentlyContinue
            
            foreach ($file in $files) {
                $converted = Convert-FileToLF -FilePath $file.FullName -DryRun $DryRun -Verbose $Verbose
                if ($converted) {
                    $script:ConvertedCount++
                }
                $script:ProcessedCount++
            }
        }
        
        # Recursively process subdirectories
        $subdirs = Get-ChildItem -Path $DirectoryPath -Directory -ErrorAction SilentlyContinue
        foreach ($subdir in $subdirs) {
            Process-Directory -DirectoryPath $subdir.FullName -DryRun $DryRun -Verbose $Verbose
        }
        
    } catch {
        Write-Log "Error processing directory $DirectoryPath`: $($_.Exception.Message)" "ERROR"
    }
}

# Main execution
Write-Log "Starting LF conversion process..." "INFO"
Write-Log "Path: $Path" "INFO"
Write-Log "Dry run: $DryRun" "INFO"
Write-Log "Verbose: $Verbose" "INFO"

$script:ProcessedCount = 0
$script:ConvertedCount = 0

$startTime = Get-Date

# Resolve the path to absolute
$ResolvedPath = Resolve-Path -Path $Path -ErrorAction Stop

if (-not (Test-Path -Path $ResolvedPath -PathType Container)) {
    Write-Log "Error: Path '$ResolvedPath' is not a valid directory" "ERROR"
    exit 1
}

Process-Directory -DirectoryPath $ResolvedPath -DryRun $DryRun -Verbose $Verbose

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Log "Conversion process completed!" "INFO"
Write-Log "Files processed: $($script:ProcessedCount)" "INFO"
Write-Log "Files converted: $($script:ConvertedCount)" "INFO"
Write-Log "Duration: $($duration.TotalSeconds.ToString('F2')) seconds" "INFO"

if ($DryRun) {
    Write-Log "This was a dry run. Use without -DryRun to actually convert files." "INFO"
}
