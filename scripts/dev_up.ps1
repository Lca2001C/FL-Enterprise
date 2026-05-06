# Sobe Redis para desenvolvimento local (requer Docker).
docker compose up -d redis
if ($LASTEXITCODE -ne 0) { docker-compose up -d redis }
Write-Host "Redis iniciado. Copie .env.example para .env e rode: uvicorn motopay.interfaces.api.main:app --reload"
