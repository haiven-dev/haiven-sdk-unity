using Haiven.Sdk;
using NUnit.Framework;
using System.Threading;
using UnityEditor.PackageManager;

namespace Haiven.Tests
{
    public class ProtocolTests
    {
        [Test] public void LocalPackageLoads()
        {
            var package = System.Array.Find(PackageInfo.GetAllRegisteredPackages(), p => p.name == "com.haiven.sdk");
            Assert.That(package, Is.Not.Null);
            Assert.That(package.source, Is.EqualTo(PackageSource.Local));
        }
        [Test] public void RefusedReplyPreservesPresence()
        {
            var frame = ServerFrame.Parse("{\"type\":\"ping\",\"success\":false,\"requestId\":\"\"}");
            Assert.That(frame.IsReply, Is.True);
            Assert.That(frame.Success, Is.False);
            Assert.That(frame.RequestId, Is.EqualTo(""));
        }
        [Test] public void EventHasNoSuccessOrRequestId()
        {
            var frame = ServerFrame.Parse("{\"type\":\"chat.message\",\"payload\":{\"id\":\"m1\"}}");
            Assert.That(frame.IsReply, Is.False);
            Assert.That(frame.Success, Is.Null);
            Assert.That(frame.RequestId, Is.Null);
        }
        [Test] public void HandoffDispatcherRunsOnUnityThread()
        {
            var unityThread = System.Environment.CurrentManagedThreadId;
            var callbackThread = -1;
            new UnityHandoffDispatcher()
                .RunAsync(() => callbackThread = System.Environment.CurrentManagedThreadId, CancellationToken.None)
                .GetAwaiter().GetResult();
            Assert.That(callbackThread, Is.EqualTo(unityThread));
        }
    }
}
