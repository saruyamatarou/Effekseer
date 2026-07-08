# Build warning baseline

This document records the current warning baseline for the Effekseer fork while working on the Automation Bridge spike.

## Collection commands

Primary command:

```powershell
$env:PATH = 'C:\Program Files\CMake\bin;' + $env:PATH
py -3.12 build.py
```

The `py -3.12 build.py` run reached the CMake/MSBuild native build and then failed during the final `dotnet build` step because a running `Effekseer.exe` process was holding `Dev/release/EffekseerCore.dll`.

To capture the managed C# warning baseline without stopping the running editor, the C# projects were rebuilt to a temporary output directory:

```powershell
dotnet build Dev/Editor/Effekseer/Effekseer.csproj --no-restore -t:Rebuild -p:OutputPath=../../../build/codex-warning-baseline-check/
```

## Summary

| Area | Count | Notes |
| --- | ---: | --- |
| CMake dev warnings | 5 | CMake configure warnings from policy/install metadata. |
| MSB8065 | 1 | ResourceData custom build output marker warning. |
| EffekseerCore warnings | 12 | Existing C# warnings in `Dev/Editor/EffekseerCore`. |
| EffekseerCoreGUI warnings | 9 | Existing C# warnings in `Dev/Editor/EffekseerCoreGUI`. |
| Effekseer warnings | 1 | Existing C# warning in `Dev/Editor/Effekseer`. |
| AutomationBridge.cs direct warnings | 0 | No warning line references `Dev/Editor/Effekseer/AutomationBridge.cs`. |

## CMake dev warnings

| Code / kind | File | Detail |
| --- | --- | --- |
| CMP0148 | `CMakeLists.txt:520` | `FindPythonInterp` and `FindPythonLibs` policy warning. |
| CMake dev install | `Dev/Cpp/EffekseerRendererCommon/CMakeLists.txt:89` | `EffekseerRendererCommon` has `PUBLIC_HEADER` files but no `PUBLIC_HEADER DESTINATION`. |
| CMake dev install | `Dev/Cpp/EffekseerRendererLLGI/CMakeLists.txt:56` | `EffekseerRendererLLGI` has `PUBLIC_HEADER` files but no `PUBLIC_HEADER DESTINATION`. |
| CMake dev install | `Dev/Cpp/EffekseerRendererDX11/CMakeLists.txt:56` | `EffekseerRendererDX11` has `PUBLIC_HEADER` files but no `PUBLIC_HEADER DESTINATION`. |
| CMake dev install | `Dev/Cpp/EffekseerRendererDX12/CMakeLists.txt:59` | `EffekseerRendererDX12` has `PUBLIC_HEADER` files but no `PUBLIC_HEADER DESTINATION`. |

## MSB8065

| Code | Project / file | Detail |
| --- | --- | --- |
| MSB8065 | `build/ResourceData.vcxproj` | Custom build for `ResourceData.dummy.rule` succeeds but the expected `build/resourcedata.dummy` output is not created, which can affect incremental builds. |

## EffekseerCore warnings

| Code | File | Detail |
| --- | --- | --- |
| CS8981 | `Dev/Editor/EffekseerCore/Script/Compiler.cs:10` | Type name `sh` contains only lowercase ASCII characters. |
| CS8981 | `Dev/Editor/EffekseerCore/Script/Compiler.cs:11` | Type name `ph` contains only lowercase ASCII characters. |
| CS8981 | `Dev/Editor/EffekseerCore/Script/Compiler.cs:12` | Type name `pr` contains only lowercase ASCII characters. |
| CS0659 | `Dev/Editor/EffekseerCore/Data/Value/Gradient.cs:27` | `Gradient.State` overrides `Equals` but not `GetHashCode`. |
| SYSLIB0021 | `Dev/Editor/EffekseerCore/IO/EfkPkg.cs:525` | `MD5CryptoServiceProvider` is obsolete. |
| CS0067 | `Dev/Editor/EffekseerCore/Data/Value/Vector3DWithRandom.cs:56` | Event `Vector3DWithRandom.OnChanged` is never used. |
| CS0067 | `Dev/Editor/EffekseerCore/Data/NodeBase.cs:442` | Event `NodeBaseValues.OnChanged` is never used. |
| CS0067 | `Dev/Editor/EffekseerCore/Data/Value/Vector3D.cs:43` | Event `Vector3D.OnChanged` is never used. |
| CS0649 | `Dev/Editor/EffekseerCore/InternalScript/Compiler.cs:40` | Field `Operator.Type` is never assigned and keeps its default value. |
| CS0067 | `Dev/Editor/EffekseerCore/Data/Value/Vector4D.cs:48` | Event `Vector4D.OnChanged` is never used. |
| CS0067 | `Dev/Editor/EffekseerCore/Data/Value/IntWithInifinite.cs:34` | Event `IntWithInifinite.OnChanged` is never used. |
| CA2200 | `Dev/Editor/EffekseerCore/Data/Value/Path.cs:149` | Rethrowing a caught exception changes stack information. |

## EffekseerCoreGUI warnings

| Code | File | Detail |
| --- | --- | --- |
| CS0660 | `Dev/Editor/EffekseerCoreGUI/IO/mqoToEffekseerModelConverter/Color.cs:9` | `Color` defines `==` or `!=` but does not override `Equals`. |
| CS0661 | `Dev/Editor/EffekseerCoreGUI/IO/mqoToEffekseerModelConverter/Color.cs:9` | `Color` defines `==` or `!=` but does not override `GetHashCode`. |
| CS0660 | `Dev/Editor/EffekseerCoreGUI/IO/mqoToEffekseerModelConverter/Vector2D.cs:9` | `Vector2D` defines `==` or `!=` but does not override `Equals`. |
| CS0661 | `Dev/Editor/EffekseerCoreGUI/IO/mqoToEffekseerModelConverter/Vector2D.cs:9` | `Vector2D` defines `==` or `!=` but does not override `GetHashCode`. |
| CS0168 | `Dev/Editor/EffekseerCoreGUI/GUI/Dock/FileBrowser.cs:602` | Variable `e` is declared but never used. |
| CS0168 | `Dev/Editor/EffekseerCoreGUI/GUI/Dock/FileBrowser.cs:615` | Variable `e` is declared but never used. |
| CS0162 | `Dev/Editor/EffekseerCoreGUI/GUI/Dock/FCurves.cs:2407` | Unreachable code detected. |
| CS0414 | `Dev/Editor/EffekseerCoreGUI/GUI/BindableComponent/ParameterList.cs:34` | Field `ParameterList.isFirstUpdate` is assigned but never used. |
| CS0414 | `Dev/Editor/EffekseerCoreGUI/GUI/BindableComponent/ParameterList.cs:105` | Field `ParameterList.TypeRowCollection.controlEnabled` is assigned but never used. |

## Effekseer warnings

| Code | File | Detail |
| --- | --- | --- |
| SYSLIB0032 | `Dev/Editor/Effekseer/Program.cs:16` | `HandleProcessCorruptedStateExceptionsAttribute` is obsolete and ignored. |

## Automation Bridge warning check

No collected warning directly references `Dev/Editor/Effekseer/AutomationBridge.cs`.

The current Automation Bridge files therefore do not add a direct build warning in this baseline. Future changes should compare new warning output against the tables above and treat any warning in `Dev/Editor/Effekseer/AutomationBridge.cs` as new unless this document is intentionally updated.

## Transient warnings excluded from baseline

The `py -3.12 build.py` run also emitted repeated `MSB3026` warnings and final `MSB3027` / `MSB3021` errors while copying `EffekseerCore.dll` into `Dev/release`. These were caused by an already running `Effekseer.exe` process locking the output DLL. They are environment/state dependent and are not counted as source warning baseline entries.
