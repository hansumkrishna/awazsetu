// AwazSetu launcher for the MSIX package.
//
// An AppxManifest entry point must be an .exe and cannot carry arguments, so
// "pythonw.exe app\run.py" is not expressible there. This is that argument,
// compiled. It is built by scripts/build_msix.py with csc.exe from the .NET
// Framework that ships with Windows, so producing the installer needs no
// toolchain the machine does not already have.
//
// It does four things the .bat cannot:
//   * picks a free port when 5000 is taken, instead of failing invisibly
//   * a single instance -- a second launch reopens the tab rather than starting
//     a second server on a second port
//   * ties the Python process to a Job Object, so closing the app can never
//     leave a two-gigabyte interpreter running with no window to close it from
//   * shows a real message box when the package is incomplete, because an MSIX
//     app has no console to print to
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

static class AwazSetu
{
    const string MUTEX = @"Local\AwazSetu.SingleInstance";

    // ---- Job Object: the child dies with us, however we die ----------------
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern IntPtr CreateJobObject(IntPtr a, string name);
    [DllImport("kernel32.dll")]
    static extern bool SetInformationJobObject(IntPtr job, int infoClass, IntPtr info, uint len);
    [DllImport("kernel32.dll")]
    static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

    [StructLayout(LayoutKind.Sequential)]
    struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)]
    struct IO_COUNTERS
    {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)]
    struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit, JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed, PeakJobMemoryUsed;
    }

    static IntPtr MakeKillOnCloseJob()
    {
        IntPtr job = CreateJobObject(IntPtr.Zero, null);
        if (job == IntPtr.Zero) return IntPtr.Zero;
        var ext = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
        ext.BasicLimitInformation.LimitFlags = 0x2000;   // KILL_ON_JOB_CLOSE
        int len = Marshal.SizeOf(ext);
        IntPtr p = Marshal.AllocHGlobal(len);
        Marshal.StructureToPtr(ext, p, false);
        SetInformationJobObject(job, 9, p, (uint)len);   // ExtendedLimitInformation
        Marshal.FreeHGlobal(p);
        return job;
    }

    static int FreePort(int preferred)
    {
        if (IsFree(preferred)) return preferred;
        for (int p = preferred + 1; p < preferred + 40; p++) if (IsFree(p)) return p;
        return 0;                                        // let the OS choose nothing; we fail loudly
    }

    static bool IsFree(int port)
    {
        try
        {
            var l = new TcpListener(IPAddress.Loopback, port);
            l.Start(); l.Stop(); return true;
        }
        catch (SocketException) { return false; }
    }

    static void Fail(string msg)
    {
        MessageBox.Show(msg, "AwazSetu", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }

    [STAThread]
    static int Main(string[] args)
    {
        string home = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        string py = Path.Combine(home, @"runtime\python\pythonw.exe");
        string runpy = Path.Combine(home, @"app\run.py");

        if (!File.Exists(py) || !File.Exists(runpy))
        {
            Fail("This installation is incomplete.\n\nMissing:\n  " +
                 (File.Exists(py) ? "" : py + "\n  ") +
                 (File.Exists(runpy) ? "" : runpy) +
                 "\n\nReinstall the package.");
            return 1;
        }

        // A second launch should reopen the tab, not start a second server.
        bool isFirst;
        using (var mutex = new Mutex(true, MUTEX, out isFirst))
        {
            if (!isFirst)
            {
                string existing = Environment.GetEnvironmentVariable("AWAZ_URL")
                                  ?? "http://127.0.0.1:5000";
                try { Process.Start(new ProcessStartInfo(existing) { UseShellExecute = true }); }
                catch { }
                return 0;
            }

            int port = FreePort(5000);
            if (port == 0) { Fail("No free network port could be found for the local server."); return 1; }
            string url = "http://127.0.0.1:" + port + "/";

            var psi = new ProcessStartInfo(py, "\"" + runpy + "\"")
            {
                WorkingDirectory = home,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            // Everything the app needs, exactly as AwazSetu.bat sets it. The data
            // location is deliberately NOT forced: app/paths.py probes for a
            // writable folder, which is right for both an MSIX install (read-only)
            // and this same launcher run from an ordinary folder.
            var e = psi.EnvironmentVariables;
            e["AWAZ_HOME"] = home;
            e["AWAZ_MODELS_DIR"] = Path.Combine(home, "models");
            e["AWAZ_BIN_DIR"] = Path.Combine(home, @"runtime\bin");
            e["AWAZ_LLM_DIR"] = Path.Combine(home, @"models\llm");
            e["HF_HOME"] = Path.Combine(home, @"models\hf-cache");
            e["HF_HUB_OFFLINE"] = "1";
            e["TRANSFORMERS_OFFLINE"] = "1";
            e["AWAZ_OFFLINE"] = "1";
            e["AWAZ_PORT"] = port.ToString();
            e["PYTHONIOENCODING"] = "utf-8";
            e["PYTHONDONTWRITEBYTECODE"] = "1";
            e["PATH"] = Path.Combine(home, @"runtime\bin") + ";" + e["PATH"];

            Process proc;
            try { proc = Process.Start(psi); }
            catch (Exception ex) { Fail("Could not start AwazSetu.\n\n" + ex.Message); return 1; }

            IntPtr job = MakeKillOnCloseJob();
            if (job != IntPtr.Zero) { try { AssignProcessToJobObject(job, proc.Handle); } catch { } }
            AppDomain.CurrentDomain.ProcessExit += (s, a) =>
            { try { if (!proc.HasExited) proc.Kill(); } catch { } };

            // Wait for the port to answer rather than sleeping a fixed time: on a
            // cold first run loading the settings takes longer than any guess.
            for (int i = 0; i < 120 && !proc.HasExited; i++)
            {
                if (!IsFree(port)) break;                // something is listening
                Thread.Sleep(250);
            }
            if (proc.HasExited)
            {
                Fail("AwazSetu stopped while starting up.\n\nRun AwazSetu-Check to see what is wrong.");
                return 1;
            }
            try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); }
            catch { }

            proc.WaitForExit();
            return proc.ExitCode;
        }
    }
}
