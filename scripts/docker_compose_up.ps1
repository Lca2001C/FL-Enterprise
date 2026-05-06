# Sobe os servicos com Docker Compose sem usar proxy do ambiente (evita falha de DNS em proxys internos).
# Uso: .\scripts\docker_compose_up.ps1
#      .\scripts\docker_compose_up.ps1 build
#      .\scripts\docker_compose_up.ps1 up -d

$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:http_proxy = ""
$env:https_proxy = ""
$env:ALL_PROXY = ""
$env:all_proxy = ""

if ($args.Count -eq 0) {
    docker compose up --build
} else {
    docker compose @args
}
