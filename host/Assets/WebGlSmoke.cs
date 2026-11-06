// Copyright 2026 Haiven
// SPDX-License-Identifier: Apache-2.0

using System;
using System.Collections;
using Haiven.Sdk;
using UnityEngine;

public class WebGlSmoke : MonoBehaviour
{
#if UNITY_WEBGL && !UNITY_EDITOR
    private WebGlSocket socket;
    private IEnumerator Start()
    {
        bool ready = false, echoed = false;
        var uri = new Uri(Application.absoluteURL);
        socket = new WebGlSocket("ws://" + uri.Authority + "/socket");
        socket.Received += text => {
            if (text == "haiven-π") echoed = true;
            else if (ServerFrame.Parse(text).Type == "ready") ready = true;
        };
        float deadline = Time.realtimeSinceStartup + 20;
        while (!ready && Time.realtimeSinceStartup < deadline) yield return null;
        if (!ready) { Debug.LogError("HAIVEN_WEBGL_FAIL ready"); yield break; }
        socket.Send("haiven-π");
        while (!echoed && Time.realtimeSinceStartup < deadline) yield return null;
        if (!echoed) { Debug.LogError("HAIVEN_WEBGL_FAIL echo"); yield break; }
        var refused = ServerFrame.Parse("{\"type\":\"ping\",\"success\":false}");
        var notification = ServerFrame.Parse("{\"type\":\"chat.message\"}");
        if (!refused.IsReply || notification.IsReply) { Debug.LogError("HAIVEN_WEBGL_FAIL protocol"); yield break; }

        var mainThread = System.Environment.CurrentManagedThreadId;
        var tokens = new MemoryHandoffTokenStore();
        var browser = new RecordingBrowser();
        var coordinator = new HandoffCoordinator(
            new HandoffOptions(
                new Uri("http://" + uri.Authority + "/connect/game"),
                new Uri("http://" + uri.Authority + "/v0/auth/handoff/exchange"),
                "webgl-smoke",
                new Uri("http://" + uri.Authority + "/callback?mode=login")),
            browser,
            new MemoryHandoffTransactionStore(),
            tokens,
            new UnityHandoffHttpTransport(),
            new UnityHandoffDispatcher());
        var completedThread = -1;
        string failure = null;
        coordinator.Completed += _ => completedThread = System.Environment.CurrentManagedThreadId;
        coordinator.Failed += error => failure = error.ToString();
        var handoff = coordinator.BeginLogin();
        _ = coordinator.HandleCallbackAsync(new Uri(
            "http://" + uri.Authority + "/callback?mode=login&code=webgl-code&state=" + handoff.State));
        deadline = Time.realtimeSinceStartup + 20;
        while (tokens.Credential == null && failure == null && Time.realtimeSinceStartup < deadline) yield return null;
        if (failure != null) { Debug.LogError("HAIVEN_WEBGL_FAIL handoff " + failure); yield break; }
        if (tokens.Credential == null) { Debug.LogError("HAIVEN_WEBGL_FAIL handoff timeout"); yield break; }
        if (tokens.Credential.AccessToken != "webgl-access" || completedThread != mainThread)
        { Debug.LogError("HAIVEN_WEBGL_FAIL handoff completion"); yield break; }
        if (browser.Opened != handoff.AuthorizationUri)
        { Debug.LogError("HAIVEN_WEBGL_FAIL handoff browser"); yield break; }
        socket.Dispose();
        Debug.Log("HAIVEN_WEBGL_PASS");
    }
    private void OnDestroy() { socket?.Dispose(); }

    private sealed class RecordingBrowser : IHandoffBrowser
    {
        public Uri Opened { get; private set; }
        public void Open(Uri uri) { Opened = uri; }
    }
#endif
}
