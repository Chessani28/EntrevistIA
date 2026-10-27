$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$bundled = Join-Path $projectRoot 'storage/runtime/ollama-0.40.6/ollama.exe'
if (Test-Path -LiteralPath $bundled) { $ollama = $bundled }
else {
    $command = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $command) { throw 'Ollama is not installed or not available in PATH.' }
    $ollama = $command.Source
}
$settings = @{
    OLLAMA_HOST = '127.0.0.1:11434'
    OLLAMA_MODELS = (Join-Path $projectRoot 'storage/models')
    OLLAMA_NO_CLOUD = '1'
    OLLAMA_CONTEXT_LENGTH = '2048'
    OLLAMA_NUM_PARALLEL = '1'
    OLLAMA_MAX_LOADED_MODELS = '1'
    OLLAMA_MAX_QUEUE = '1'
    OLLAMA_KEEP_ALIVE = '30s'
    OLLAMA_LOAD_TIMEOUT = '120s'
}
$previous = @{}
try {
    foreach ($key in $settings.Keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }
    & $ollama serve
} finally {
    foreach ($key in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
    }
}
