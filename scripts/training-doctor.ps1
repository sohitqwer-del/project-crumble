param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.:-]+$')][string]$HostName,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z_][A-Za-z0-9_.-]*$')][string]$UserName,
    [Parameter(Mandatory=$true)][string]$IdentityFile,
    [ValidatePattern('^[A-Za-z0-9_./-]+$')][string]$PythonPath = 'python3'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) { throw 'SSH identity file does not exist.' }
$crumbleProbe = @'
import json, sys
result = {'python': sys.version.split()[0]}
try:
    import torch
    result.update(torch=torch.__version__, cuda_available=torch.cuda.is_available())
    if result['cuda_available']:
        result.update(gpu_count=torch.cuda.device_count(), device=torch.cuda.get_device_name(0))
except ImportError:
    result.update(torch=None, cuda_available=False)
print(json.dumps(result, indent=2))
'@
$crumbleProbe | ssh -o BatchMode=yes -o ConnectTimeout=20 -i $IdentityFile "$UserName@$HostName" "$PythonPath -"
if ($LASTEXITCODE -ne 0) { throw 'Training host capability check failed.' }
