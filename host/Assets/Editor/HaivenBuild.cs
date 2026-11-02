using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class HaivenBuild
{
    public static void WebGL()
    {
        if (Application.unityVersion != "6000.0.52f1") throw new Exception("Unexpected Unity version: " + Application.unityVersion);
        if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.WebGL, BuildTarget.WebGL)) throw new Exception("WebGL module missing");
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        new GameObject("Haiven smoke").AddComponent<WebGlSmoke>();
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), "Assets/Smoke.unity");
        PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.WebGL, ManagedStrippingLevel.High);
        PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
        PlayerSettings.runInBackground = true;
        var output = Environment.GetEnvironmentVariable("HAIVEN_WEBGL_OUTPUT");
        if (String.IsNullOrEmpty(output)) throw new Exception("HAIVEN_WEBGL_OUTPUT is required");
        Directory.CreateDirectory(output);
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Smoke.unity" }, locationPathName = output,
            target = BuildTarget.WebGL, options = BuildOptions.None
        });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("WebGL build failed: " + report.summary.result);
        File.WriteAllText(Path.Combine(output, "haiven-build.json"), "{\"unity\":\"6000.0.52f1\",\"stripping\":\"High\",\"result\":\"Succeeded\"}");
    }
}
