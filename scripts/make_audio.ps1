<#
.SYNOPSIS
  Render DealerWatch synthetic call transcripts to WAV with Windows SAPI (System.Speech).
.DESCRIPTION
  Default mode runs scripts/make_audio.py, which picks the calls (leak, injection and small-talk calls in
  planted lookback windows plus 3 innocent ones, or every call with -All), stitches one 16 kHz mono WAV per
  call into data/generated/audio/<call_id>.wav and rewrites each call JSON with the real utterance offsets
  and audio_file.
  Worker mode (-Manifest <json>) is used by make_audio.py: it renders each {text, voice, out} entry to its
  own 16 kHz mono 16-bit WAV. Dealers speak with Microsoft David, everyone else with Microsoft Zira.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/make_audio.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/make_audio.ps1 -All
#>
param(
    [string]$Manifest,
    [string]$DataDir,
    [switch]$All
)
$ErrorActionPreference = "Stop"

if ($Manifest) {
    Add-Type -AssemblyName System.Speech
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,
        [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $installed = @($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })
    try {
        foreach ($item in @(Get-Content -Raw -Encoding UTF8 $Manifest | ConvertFrom-Json)) {
            $voice = $installed | Where-Object { $_ -like "$($item.voice)*" } | Select-Object -First 1
            if ($voice) {
                $synth.SelectVoice($voice)
            } elseif ($item.voice -like "*David*") {
                $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male)
            } else {
                $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female)
            }
            $synth.SetOutputToWaveFile([string]$item.out, $format)
            $synth.Speak([string]$item.text)
            $synth.SetOutputToNull()
        }
    } finally {
        $synth.Dispose()
    }
    exit 0
}

$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$pyArgs = @((Join-Path $PSScriptRoot "make_audio.py"))
if ($DataDir) { $pyArgs += @("--data-dir", $DataDir) }
if ($All) { $pyArgs += "--all" }
& $py @pyArgs
exit $LASTEXITCODE
