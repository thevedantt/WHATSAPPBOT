param(
    [string]$AuthToken = "33jvteMdVtyhQr6O0FMD1lzlxQn_3Mzpb976boSSeQBAqvnqr",
    [int]$Port = 5000
)

Write-Host "Configuring ngrok authtoken..."
ngrok config add-authtoken $AuthToken

Write-Host "Starting ngrok http tunnel on port $Port..."
ngrok http $Port
