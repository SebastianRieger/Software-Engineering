New-Item -ItemType Directory -Force -Path ".\Kiosk_Image_Files\images" | Out-Null
New-Item -ItemType Directory -Force -Path ".\Kiosk_Image_Files\logs"  | Out-Null
docker compose up --build
