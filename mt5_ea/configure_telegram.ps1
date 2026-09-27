$ErrorActionPreference = "Stop"
$token = Read-Host "Telegram Bot Token"
if ([string]::IsNullOrWhiteSpace($token)) { throw "Token is empty." }
$updates = Invoke-RestMethod ("https://api.telegram.org/bot{0}/getUpdates" -f $token)
$msg = $updates.result | Where-Object { $_.message.chat.id } | Select-Object -Last 1 -ExpandProperty message
if (-not $msg) { throw "Chat ID not found. Send a message to the bot and run again." }
$chatId = [string]$msg.chat.id
[Environment]::SetEnvironmentVariable("EA_TELEGRAM_BOT_TOKEN",$token,"User")
[Environment]::SetEnvironmentVariable("EA_TELEGRAM_CHAT_ID",$chatId,"User")
$env:EA_TELEGRAM_BOT_TOKEN=$token
$env:EA_TELEGRAM_CHAT_ID=$chatId
$body = @{chat_id=$chatId;text="Hybrid EA Telegram connection OK"}
Invoke-RestMethod -Method Post -Uri ("https://api.telegram.org/bot{0}/sendMessage" -f $token) -Body $body | Out-Null
Write-Host "Telegram configured and test message sent."