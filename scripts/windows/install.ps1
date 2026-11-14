# =====================================================================
#  GymPro DZ - Installation Windows (sans Docker)
#  Lancez INSTALLER.bat (double-clic) : il exécute ce script.
# =====================================================================
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root

function Title($t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "    OK  $t" -ForegroundColor Green }
function Fail($t) { Write-Host ""; Write-Host "ERREUR : $t" -ForegroundColor Red; Read-Host "Appuyez sur Entrée pour fermer"; exit 1 }

Write-Host "=============================================" -ForegroundColor Green
Write-Host "        GymPro DZ - Installation"             -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# ---------------------------------------------------------------- 1. Python
Title "1/6  Vérification de Python"
function Find-Python {
    foreach ($c in @("py -3.12", "py -3.13", "py -3.11", "py -3", "python")) {
        try {
            $parts = $c.Split(" ")
            $v = & $parts[0] $parts[1..9] -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v -match "^3\.(1[0-9])$") { return $c }
        } catch {}
    }
    return $null
}
$Py = Find-Python
if (-not $Py) {
    Write-Host "    Python n'est pas installé. Installation automatique (winget)..." -ForegroundColor Yellow
    try {
        winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $Py = Find-Python
    } catch {}
}
if (-not $Py) {
    Start-Process "https://www.python.org/downloads/windows/"
    Fail "Installez Python 3.12 depuis python.org (cochez 'Add python.exe to PATH'), puis relancez INSTALLER.bat"
}
Ok "Python trouvé ($Py)"

# ---------------------------------------------------------------- 2. venv + packages
Title "2/6  Installation des composants (2-5 minutes, Internet requis)"
$parts = $Py.Split(" ")
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $parts[0] $parts[1..9] -m venv .venv
    if ($LASTEXITCODE -ne 0) { Fail "Impossible de créer l'environnement Python (.venv)" }
}
$VPy = Join-Path $Root ".venv\Scripts\python.exe"
$VPyw = Join-Path $Root ".venv\Scripts\pythonw.exe"
& $VPy -m pip install --upgrade pip --quiet --disable-pip-version-check
& $VPy -m pip install -r requirements.txt --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Fail "L'installation des paquets a échoué. Vérifiez la connexion Internet." }
Ok "Composants installés"

# ---------------------------------------------------------------- 3. .env (Supabase)
Title "3/6  Configuration de la base de données Supabase"
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "    Collez l'URL de connexion Supabase (Project > Connect > 'Session pooler')." -ForegroundColor Yellow
    Write-Host "    Exemple : postgresql://postgres.abcd:MOTDEPASSE@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    Write-Host "    (Laissez vide pour utiliser une base locale SQLite - mode hors-ligne / démo)"
    $DbUrl = Read-Host "    URL Supabase"
    $Lan = Read-Host "    Autoriser les autres appareils du Wi-Fi (tablette, téléphone) ? (o/N)"
    $HostIp = if ($Lan -match "^[oOyY]") { "0.0.0.0" } else { "127.0.0.1" }
    $Secret = & $VPy -c "import secrets; print(secrets.token_urlsafe(50))"
    @"
# GymPro DZ configuration
SECRET_KEY=$Secret
DEBUG=false
DATABASE_URL=$DbUrl
HOST=$HostIp
PORT=8000
ALLOWED_HOSTS=*
DEFAULT_LANGUAGE=fr
APP_WINDOW=true
"@ | Set-Content -Path ".env" -Encoding UTF8
    Ok ".env créé"
} else {
    Ok ".env existe déjà (conservé)"
}

# ---------------------------------------------------------------- 4. database
Title "4/6  Préparation de la base de données"
& $VPy manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { Fail "Connexion à la base impossible. Vérifiez DATABASE_URL dans le fichier .env (mot de passe, Internet)." }
& $VPy manage.py collectstatic --noinput | Out-Null
Ok "Base de données prête"

# ---------------------------------------------------------------- 5. owner account
Title "5/6  Compte du propriétaire"
& $VPy manage.py setup_gym
if ($LASTEXITCODE -ne 0) { Fail "Création du compte impossible" }

# ---------------------------------------------------------------- 6. shortcuts
Title "6/6  Création de l'icône sur le Bureau"
$Icon = Join-Path $Root "gym\static\gym\img\gympro.ico"
$Launcher = Join-Path $Root "launcher.pyw"
$Shell = New-Object -ComObject WScript.Shell
function New-Shortcut($path, $extra) {
    $s = $Shell.CreateShortcut($path)
    $s.TargetPath = $VPyw
    $s.Arguments = ("`"$Launcher`" " + $extra).Trim()
    $s.WorkingDirectory = $Root
    $s.IconLocation = $Icon
    $s.Description = "GymPro DZ - Gestion de salle de sport"
    $s.Save()
}
$Desktop = [Environment]::GetFolderPath("Desktop")
New-Shortcut (Join-Path $Desktop "GymPro DZ.lnk") ""
$StartMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "GymPro DZ.lnk"
New-Shortcut $StartMenu ""
Ok "Icône 'GymPro DZ' créée sur le Bureau et dans le menu Démarrer"

$Auto = Read-Host "    Démarrer le serveur automatiquement avec Windows ? (O/n)"
if ($Auto -notmatch "^[nN]") {
    New-Shortcut (Join-Path ([Environment]::GetFolderPath("Startup")) "GymPro DZ (serveur).lnk") "--server-only"
    Ok "Démarrage automatique activé"
}

if ((Get-Content .env | Select-String "HOST=0.0.0.0")) {
    try {
        New-NetFirewallRule -DisplayName "GymPro DZ" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private -ErrorAction Stop | Out-Null
        Ok "Pare-feu ouvert sur le port 8000 (réseau privé)"
    } catch { Write-Host "    (Pare-feu : lancez INSTALLER.bat en administrateur pour ouvrir le port 8000 aux autres appareils)" -ForegroundColor Yellow }
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
    Write-Host "    Sur les autres appareils du Wi-Fi, ouvrez : http://$($ip):8000" -ForegroundColor Green
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Installation terminée !" -ForegroundColor Green
Write-Host "  Double-cliquez sur l'icône 'GymPro DZ' du Bureau." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
$open = Read-Host "Ouvrir l'application maintenant ? (O/n)"
if ($open -notmatch "^[nN]") { Start-Process $VPyw -ArgumentList "`"$Launcher`"" -WorkingDirectory $Root }
