# Windows 7 / PowerShell 2 compatible LabVIEW VI Server relay.
param([string]$TokenFile = "$env:LOCALAPPDATA\LabVIEWBridge\token.txt", [string]$AllowedRoot = "$env:USERPROFILE\Documents\LabVIEW Data\Codex", [int]$Port = 18765)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Web.Extensions
$serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
$serializer.MaxJsonLength = 1048576
$token = (Get-Content -LiteralPath $TokenFile -ErrorAction Stop | Select-Object -First 1).Trim()
$root = [IO.Path]::GetFullPath($AllowedRoot).TrimEnd('\') + '\'
[IO.Directory]::CreateDirectory($root) | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Send-Response($writer, $response) {
    $json = $serializer.Serialize($response)
    $line = [Convert]::ToBase64String($utf8.GetBytes($json))
    $writer.WriteLine($line)
    $writer.Flush()
}
function Safe-ViPath([string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($full) -ine '.vi') { throw 'VI must be inside the configured Codex workspace and have a .vi extension.' }
    if (-not [IO.File]::Exists($full)) { throw 'VI does not exist.' }
    return $full
}
while ($true) {
    $client = $null; $reader = $null; $writer = $null
    try {
        $client = New-Object Net.Sockets.TcpClient
        $client.ReceiveTimeout = 30000; $client.SendTimeout = 30000
        $client.Connect('10.0.2.2', $Port)
        $stream = $client.GetStream()
        $reader = New-Object IO.StreamReader($stream, $utf8)
        $writer = New-Object IO.StreamWriter($stream, $utf8)
        $line = $reader.ReadLine()
        if (-not $line -or $line.Length -gt 1048576) { throw 'Invalid request.' }
        $request = $serializer.DeserializeObject($utf8.GetString([Convert]::FromBase64String($line)))
        if (-not $request.ContainsKey('token') -or $request['token'] -cne $token) { throw 'Authentication failed.' }
        if ($request['op'] -eq 'ping') {
            $result = @{ ok = $true; result = @{ agent = 'labview-2017-powershell'; powershell = $PSVersionTable.PSVersion.ToString() } }
        } elseif ($request['op'] -eq 'version') {
            $app = New-Object -ComObject LabVIEW.Application
            $result = @{ ok = $true; result = @{ version = [string]$app.GetType().InvokeMember('Version', [Reflection.BindingFlags]::GetProperty, $null, $app, $null) } }
        } elseif ($request['op'] -eq 'get_control') {
            $path = Safe-ViPath ([string]$request['path'])
            $app = New-Object -ComObject LabVIEW.Application
            $vi = $app.GetType().InvokeMember('GetVIReference', [Reflection.BindingFlags]::InvokeMethod, $null, $app, [object[]]@($path))
            $value = $vi.GetType().InvokeMember('GetControlValue', [Reflection.BindingFlags]::InvokeMethod, $null, $vi, [object[]]@([string]$request['control']))
            $result = @{ ok = $true; result = @{ path = $path; control = [string]$request['control']; value = $value } }
        } else { throw 'Unknown operation.' }
        Send-Response $writer $result
    } catch {
        if ($writer) { try { Send-Response $writer @{ ok = $false; error = [string]$_.Exception.Message } } catch {} }
    } finally {
        if ($reader) { $reader.Close() }
        if ($writer) { $writer.Close() }
        if ($client) { $client.Close() }
    }
    Start-Sleep -Seconds 3
}
