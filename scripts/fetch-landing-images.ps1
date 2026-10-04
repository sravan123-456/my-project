$dir = Join-Path $PSScriptRoot "..\app\static\images\landing"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$images = [ordered]@{
    "india-01-taj-mahal.jpg" = "Taj_Mahal.jpg"
    "india-02-golden-temple.jpg" = "Golden_Temple_India.jpg"
    "india-03-india-gate.jpg" = "India_Gate%2C_New_Delhi.jpg"
    "india-04-hawa-mahal.jpg" = "Hawa_Mahal_Jaipur.jpg"
    "india-05-gateway-of-india.jpg" = "Gateway_of_India.jpg"
    "india-06-mysore-palace.jpg" = "Mysore_Palace_Night.jpg"
    "india-07-charminar.jpg" = "Charminar_Hyderabad_1.jpg"
    "india-08-red-fort.jpg" = "Red_Fort_in_Delhi_03-2016_img1.jpg"
    "india-09-qutub-minar.jpg" = "Qutub_Minar_in_the_monsoons.jpg"
    "india-10-ladakh.jpg" = "Pangong_Lake%2C_Ladakh.jpg"
    "india-11-kerala-backwaters.jpg" = "Backwaters%2C_Kerala.jpg"
    "india-12-varanasi-ghats.jpg" = "Varanasi_Ghats.jpg"
    "india-13-meenakshi-temple.jpg" = "Meenakshi_Amman_Temple.jpg"
    "india-14-konark-sun-temple.jpg" = "Konark_Sun_Temple_-_Front_View.jpg"
    "india-15-ajanta-caves.jpg" = "Ajanta_caves.jpg"
    "india-16-victoria-memorial.jpg" = "Victoria_Memorial%2C_Kolkata.jpg"
}

foreach ($entry in $images.GetEnumerator()) {
    $out = Join-Path $dir $entry.Key
    $url = "https://commons.wikimedia.org/wiki/Special:FilePath/$($entry.Value)?width=960"
    curl.exe -L -s -A "DanSetu/1.0 (landing images; contact@indukuru.online)" -o $out $url
    $size = (Get-Item $out).Length
    if ($size -lt 5000) {
        Write-Error "Failed download for $($entry.Key) ($size bytes) from $url"
        exit 1
    }
    Write-Host "$($entry.Key): $size bytes"
}

Write-Host "Downloaded $($images.Count) landing images."
