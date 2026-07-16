import re
import subprocess


class SystemController:
    def handle(self, target: str) -> str:
        target_clean = target.strip().lower()

        if not target_clean:
            return "No system action provided."

        if "cancel" in target_clean and "shutdown" in target_clean:
            return self._run_shell(["shutdown", "/a"], "Cancelled scheduled shutdown.")

        if "lock" in target_clean:
            return self._run_shell(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                "Locked the computer."
            )

        if "sleep" in target_clean:
            return self._run_shell(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                "Putting the computer to sleep."
            )

        if "restart" in target_clean or "reboot" in target_clean:
            return self._run_shell(
                ["shutdown", "/r", "/t", "30"],
                "Restart scheduled in 30 seconds."
            )

        if "shutdown" in target_clean or "shut down" in target_clean:
            return self._run_shell(
                ["shutdown", "/s", "/t", "30"],
                "Shutdown scheduled in 30 seconds."
            )

        if "mute" in target_clean:
            return self._press_volume_key("volume mute", "Muted or unmuted volume.")

        volume_level_match = re.search(r"\bvolume\s+(\d{1,3})\b", target_clean)
        if volume_level_match:
            level = max(0, min(100, int(volume_level_match.group(1))))
            return self._set_volume(level)

        if "volume up" in target_clean or "increase volume" in target_clean:
            return self._press_volume_key("volume up", "Increased volume.")

        if "volume down" in target_clean or "decrease volume" in target_clean:
            return self._press_volume_key("volume down", "Decreased volume.")

        if "brightness" in target_clean:
            return self._set_brightness(target_clean)

        return f"System control action not supported: {target}"

    def _run_shell(self, command, success_message: str) -> str:
        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return success_message
        except Exception as exc:
            return f"System control failed: {exc}"

    def _press_volume_key(self, key_name: str, success_message: str) -> str:
        key_map = {
            "volume mute": 0xAD,
            "volume down": 0xAE,
            "volume up": 0xAF,
        }
        key_code = key_map[key_name]
        script = (
            "$signature = '[DllImport(\"user32.dll\")]public static extern void keybd_event"
            "(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);';"
            "$type = Add-Type -MemberDefinition $signature -Name Keyboard -Namespace Win32 -PassThru;"
            f"$type::keybd_event({key_code},0,0,[UIntPtr]::Zero);"
            f"$type::keybd_event({key_code},0,2,[UIntPtr]::Zero);"
        )

        return self._run_shell(
            ["powershell", "-NoProfile", "-Command", script],
            success_message
        )

    def _set_volume(self, level: int) -> str:
        scalar = level / 100
        script = f"""
$code = @'
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume
{{
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out uint pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, Guid pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, Guid pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute(bool bMute, Guid pguidEventContext);
    int GetMute(out bool pbMute);
    int GetVolumeStepInfo(out uint pnStep, out uint pnStepCount);
    int VolumeStepUp(Guid pguidEventContext);
    int VolumeStepDown(Guid pguidEventContext);
    int QueryHardwareSupport(out uint pdwHardwareSupportMask);
    int GetVolumeRange(out float pflVolumeMindB, out float pflVolumeMaxdB, out float pflVolumeIncrementdB);
}}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice
{{
    int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, out IAudioEndpointVolume ppInterface);
}}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator
{{
    int NotImpl1();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject {{ }}

public class AudioVolume
{{
    public static void Set(float level)
    {{
        IMMDeviceEnumerator enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice device;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out device));
        Guid endpointVolumeGuid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume endpointVolume;
        Marshal.ThrowExceptionForHR(device.Activate(ref endpointVolumeGuid, 23, IntPtr.Zero, out endpointVolume));
        Marshal.ThrowExceptionForHR(endpointVolume.SetMasterVolumeLevelScalar(level, Guid.Empty));
    }}
}}
'@
Add-Type -TypeDefinition $code
[AudioVolume]::Set({scalar})
"""

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return f"Set volume to {level} percent."
        except Exception as exc:
            return f"Volume control failed: {exc}"

    def _set_brightness(self, target: str) -> str:
        match = re.search(r"\b(\d{1,3})\b", target)
        if not match:
            return "Please specify a brightness percentage."

        level = max(0, min(100, int(match.group(1))))
        script = (
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
            f".WmiSetBrightness(1,{level})"
        )

        return self._run_shell(
            ["powershell", "-NoProfile", "-Command", script],
            f"Set brightness to {level} percent."
        )
