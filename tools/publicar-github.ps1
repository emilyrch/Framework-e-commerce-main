$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$remoteUrl = 'https://github.com/emilyrch/LPS-Ecommerce.git'
$gitCommand = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCommand) {
    throw 'Git nao encontrado neste terminal. Instale/ative Git for Windows e reabra o terminal; este script nao instala ferramentas.'
}
$gitExe = $gitCommand.Source
function Invoke-ProjectGit {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $gitExe -C $repoRoot @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Git falhou. Nenhum push forcado ou limpeza sera realizado.' }
}

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.git'))) {
    Invoke-ProjectGit init -b main
}
$currentBranch = & $gitExe -C $repoRoot branch --show-current
if ($currentBranch -ne 'main') { throw 'A branch atual nao e main. Confira antes de publicar.' }

$remotes = @(Invoke-ProjectGit remote)
$origin = if ($remotes -contains 'origin') { Invoke-ProjectGit remote get-url origin } else { $null }
if ($origin -and $origin.TrimEnd('/') -notin @($remoteUrl, 'https://github.com/emilyrch/LPS-Ecommerce')) {
    throw 'Origin aponta para outro repositorio. Nada foi sobrescrito.'
}
if (-not $origin) { Invoke-ProjectGit remote add origin $remoteUrl }

$candidateFiles = @(& $gitExe -C $repoRoot ls-files --cached --others --exclude-standard)
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel listar os arquivos.' }
$credentialPatterns = @(
    '(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'AKIA[0-9A-Z]{16}',
    '\bsk-(proj-)?[A-Za-z0-9_-]{40,}'
)
foreach ($relative in $candidateFiles) {
    if ($relative -match '(^|/)(\.local|\.venv|node_modules|var|tmp)/|\.(sqlite|db|pem|key|p12|pfx)$|(^|/)\.env$') {
        throw "Arquivo privado encontrado: $relative. Publicacao interrompida."
    }
    $fullPath = Join-Path $repoRoot $relative
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) { continue }
    $file = Get-Item -LiteralPath $fullPath
    if ($file.Length -gt 50MB) { throw "Arquivo maior que 50 MB: $relative" }
    if ($file.Extension -in @('.py','.ts','.tsx','.js','.json','.md','.yaml','.yml','.html','.txt','.example')) {
        $content = Get-Content -LiteralPath $fullPath -Raw -Encoding UTF8
        foreach ($pattern in $credentialPatterns) {
            if ($content -match $pattern) { throw "Possivel credencial em $relative. Conteudo ocultado; revise antes de publicar." }
        }
    }
}

Invoke-ProjectGit add --all
& $gitExe -C $repoRoot diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    $authorName = & $gitExe -C $repoRoot config user.name
    $authorEmail = & $gitExe -C $repoRoot config user.email
    if (-not $authorName -or -not $authorEmail) {
        throw 'Configure user.name e user.email no Git e execute novamente. Use seu email privado noreply do GitHub, se desejar.'
    }
    Invoke-ProjectGit commit -m 'Publish academic e-commerce software product line'
} elseif ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel verificar o indice.' }

Invoke-ProjectGit push -u origin main
Write-Host 'Envio concluido: https://github.com/emilyrch/LPS-Ecommerce'
Write-Host 'Abra o link e confirme que o README e as pastas aparecem. Isso nao homologa funcionalidades pendentes.'
