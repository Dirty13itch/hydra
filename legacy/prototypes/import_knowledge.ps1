$LETTA_URL = 'http://192.168.1.244:8283'
$AGENT_ID = 'agent-b3fb1747-1a5b-4c94-b713-11d6403350bf'
$knowledgeDir = 'C:\Users\shaun\projects\hydra\knowledge'

$files = Get-ChildItem -Path $knowledgeDir -Filter '*.md'
Write-Host "Found $($files.Count) knowledge files to import"
Write-Host ('-' * 50)

$success = 0
$failed = 0

foreach ($file in $files) {
    Write-Host "Importing: $($file.Name)... " -NoNewline

    try {
        $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
        $text = "[HYDRA KNOWLEDGE FILE: $($file.Name)]`n`n$content"

        $body = @{ text = $text } | ConvertTo-Json -Depth 10 -Compress

        $response = Invoke-RestMethod -Uri "$LETTA_URL/v1/agents/$AGENT_ID/archival-memory/" -Method Post -Body $body -ContentType 'application/json; charset=utf-8' -TimeoutSec 120

        Write-Host "SUCCESS" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host ('-' * 50)
Write-Host "Import complete! Success: $success, Failed: $failed"
