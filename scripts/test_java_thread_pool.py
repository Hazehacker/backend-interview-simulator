#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references" / "java-coding-challenges.md"


def find_java_tools() -> tuple[str, str] | None:
    candidates: list[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin")

    path_javac = shutil.which("javac")
    path_java = shutil.which("java")
    if path_javac and path_java:
        candidates.append(Path(path_javac).parent)

    candidates.extend(Path("/Library/Java/JavaVirtualMachines").glob(
        "*/Contents/Home/bin"
    ))
    candidates.extend((Path.home() / "Library/Java/JavaVirtualMachines").glob(
        "*/Contents/Home/bin"
    ))
    candidates.extend(Path("/Applications").glob(
        "*.app/Contents/jbr/Contents/Home/bin"
    ))
    candidates.extend(Path("/usr/lib/jvm").glob("*/bin"))

    seen: set[Path] = set()
    for directory in candidates:
        if directory in seen:
            continue
        seen.add(directory)
        javac = directory / "javac"
        java = directory / "java"
        if not javac.is_file() or not java.is_file():
            continue
        probe = subprocess.run(
            [str(javac), "-version"],
            text=True,
            capture_output=True,
        )
        if probe.returncode == 0:
            return str(javac), str(java)
    return None


def extract_thread_pool() -> str:
    text = SOURCE.read_text(encoding="utf-8")
    section = text.split("### 1.3 实现一个简易线程池", 1)[1].split(
        "\n---", 1
    )[0]
    answer = section.split("**参考解答**：", 1)[1]
    blocks = re.findall(r"```java\n(.*?)```", answer, re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError(
            f"expected one Java reference implementation, found {len(blocks)}"
        )
    return blocks[0].strip() + "\n"


class JavaThreadPoolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = extract_thread_pool()

    def test_teaching_contract_is_explicit(self) -> None:
        required = (
            "enum State",
            "RUNNING",
            "SHUTDOWN",
            "TERMINATED",
            "ThreadFactory",
            "RejectedExecutionException",
            "void shutdown()",
            "boolean awaitTermination(",
            "IllegalArgumentException",
            "catch (RuntimeException taskFailure)",
            "catch (RuntimeException | Error constructionFailure)",
            "List<Thread> startedWorkers",
            "finishConstructionRollback(startedWorkers)",
        )
        for marker in required:
            self.assertIn(marker, self.source)
        self.assertRegex(
            self.source,
            r"finally\s*\{[^{}]*workers\.remove",
            "worker removal must be protected by finally",
        )

    def test_harness(self) -> None:
        tools = find_java_tools()
        if tools is None:
            self.skipTest("no working javac/java pair found")
        javac, java = tools

        harness = r"""
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

public class SimpleThreadPoolHarness {
    public static void main(String[] args) throws Exception {
        testGracefulShutdownAndRuntimeFailure();
        testConstructionRollbackOnStartFailure();
        testConstructionRollbackOnFactoryError();
        testFatalErrorShutsDownAndDrains();
        System.out.println("PASS java thread-pool harness");
    }

    private static void testGracefulShutdownAndRuntimeFailure() throws Exception {
        AtomicInteger completed = new AtomicInteger();
        CountDownLatch blocker = new CountDownLatch(1);
        SimpleThreadPool pool = new SimpleThreadPool(2, 8);

        pool.execute(completed::incrementAndGet);
        pool.execute(() -> { throw new IllegalStateException("expected task failure"); });
        pool.execute(() -> {
            try {
                blocker.await();
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                throw new AssertionError(ex);
            }
            completed.incrementAndGet();
        });
        pool.execute(completed::incrementAndGet);

        pool.shutdown();
        boolean rejected = false;
        try {
            pool.execute(() -> {});
        } catch (RejectedExecutionException expected) {
            rejected = true;
        }
        if (!rejected) {
            throw new AssertionError("submit after shutdown was accepted");
        }

        blocker.countDown();
        if (!pool.awaitTermination(Duration.ofSeconds(5))) {
            throw new AssertionError("awaitTermination timed out");
        }
        if (completed.get() != 3) {
            throw new AssertionError("queued work did not drain: " + completed.get());
        }
        if (!pool.isTerminated()) {
            throw new AssertionError("pool did not reach TERMINATED");
        }

        SimpleThreadPool survivor = new SimpleThreadPool(1, 2);
        CountDownLatch failureRan = new CountDownLatch(1);
        CountDownLatch laterRan = new CountDownLatch(1);
        survivor.execute(() -> {
            failureRan.countDown();
            throw new RuntimeException("expected");
        });
        survivor.execute(laterRan::countDown);
        if (!failureRan.await(5, TimeUnit.SECONDS)
                || !laterRan.await(5, TimeUnit.SECONDS)) {
            throw new AssertionError("unchecked failure poisoned worker accounting");
        }
        survivor.shutdown();
        if (!survivor.awaitTermination(Duration.ofSeconds(5))) {
            throw new AssertionError("survivor pool did not terminate");
        }
    }

    private static void testConstructionRollbackOnStartFailure() {
        AtomicInteger created = new AtomicInteger();
        AtomicReference<Thread> firstWorker = new AtomicReference<>();
        IllegalStateException expected = new IllegalStateException(
                "injected start failure");
        ThreadFactory factory = task -> {
            int index = created.incrementAndGet();
            if (index == 2) {
                return new Thread(task, "start-failure-worker") {
                    @Override
                    public synchronized void start() {
                        throw expected;
                    }
                };
            }
            Thread thread = new Thread(task, "rollback-worker-" + index) {
                @Override
                public void interrupt() {
                    throw new SecurityException("injected interrupt failure");
                }

                @Override
                public void run() {
                    super.run();
                    try {
                        Thread.sleep(250);
                    } catch (InterruptedException ignored) {
                        // Delay only makes a missing constructor join deterministic.
                    }
                }
            };
            firstWorker.set(thread);
            return thread;
        };

        Throwable actual = null;
        try {
            new SimpleThreadPool(2, 2, factory);
        } catch (RuntimeException | Error failure) {
            actual = failure;
        }
        if (actual != expected) {
            throw new AssertionError("constructor did not rethrow start failure", actual);
        }
        if (firstWorker.get() == null || firstWorker.get().isAlive()) {
            throw new AssertionError("started worker survived constructor rollback");
        }
    }

    private static void testConstructionRollbackOnFactoryError() {
        AtomicInteger created = new AtomicInteger();
        AtomicReference<Thread> firstWorker = new AtomicReference<>();
        AssertionError expected = new AssertionError("injected factory error");
        ThreadFactory factory = task -> {
            if (created.incrementAndGet() == 2) {
                throw expected;
            }
            Thread thread = delayedExitThread(task, "factory-error-worker");
            firstWorker.set(thread);
            return thread;
        };

        Throwable actual = null;
        try {
            new SimpleThreadPool(2, 2, factory);
        } catch (RuntimeException | Error failure) {
            actual = failure;
        }
        if (actual != expected) {
            throw new AssertionError("constructor did not rethrow factory Error", actual);
        }
        if (firstWorker.get() == null || firstWorker.get().isAlive()) {
            throw new AssertionError("worker survived factory Error rollback");
        }
    }

    private static Thread delayedExitThread(Runnable task, String name) {
        return new Thread(task, name) {
            @Override
            public void run() {
                super.run();
                try {
                    Thread.sleep(250);
                } catch (InterruptedException ignored) {
                    // Delay only makes a missing constructor join deterministic.
                }
            }
        };
    }

    private static void testFatalErrorShutsDownAndDrains() throws Exception {
        AtomicInteger uncaughtErrors = new AtomicInteger();
        CountDownLatch fatalObserved = new CountDownLatch(1);
        ThreadFactory factory = task -> {
            Thread thread = new Thread(task, "fatal-policy-worker");
            thread.setUncaughtExceptionHandler((ignored, failure) -> {
                if (failure instanceof AssertionError
                        && "fatal task".equals(failure.getMessage())) {
                    uncaughtErrors.incrementAndGet();
                    fatalObserved.countDown();
                }
            });
            return thread;
        };
        SimpleThreadPool pool = new SimpleThreadPool(2, 4, factory);
        CountDownLatch fatalStarted = new CountDownLatch(1);
        CountDownLatch releaseFatal = new CountDownLatch(1);
        CountDownLatch survivorStarted = new CountDownLatch(1);
        CountDownLatch releaseSurvivor = new CountDownLatch(1);
        AtomicInteger drained = new AtomicInteger();

        pool.execute(() -> {
            fatalStarted.countDown();
            await(releaseFatal);
            throw new AssertionError("fatal task");
        });
        pool.execute(() -> {
            survivorStarted.countDown();
            await(releaseSurvivor);
        });
        if (!fatalStarted.await(5, TimeUnit.SECONDS)
                || !survivorStarted.await(5, TimeUnit.SECONDS)) {
            throw new AssertionError("fatal test workers did not start");
        }
        pool.execute(drained::incrementAndGet);
        releaseFatal.countDown();
        releaseSurvivor.countDown();

        if (!fatalObserved.await(5, TimeUnit.SECONDS)) {
            throw new AssertionError("fatal Error did not reach uncaught handler");
        }
        boolean rejected = false;
        try {
            pool.execute(() -> {});
        } catch (RejectedExecutionException expected) {
            rejected = true;
        }
        if (!rejected) {
            throw new AssertionError("fatal Error did not reject later submissions");
        }
        if (!pool.awaitTermination(Duration.ofSeconds(5))) {
            pool.shutdown();
            throw new AssertionError("fatal Error did not terminate the pool");
        }
        if (drained.get() != 1) {
            throw new AssertionError("surviving worker did not drain queued work");
        }
        if (uncaughtErrors.get() != 1) {
            throw new AssertionError(
                    "fatal Error was swallowed or reported more than once: "
                            + uncaughtErrors.get());
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new RuntimeException(interrupted);
        }
    }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "SimpleThreadPool.java").write_text(
                self.source, encoding="utf-8"
            )
            (directory / "SimpleThreadPoolHarness.java").write_text(
                harness, encoding="utf-8"
            )
            env = dict(os.environ)
            compile_result = subprocess.run(
                [
                    javac,
                    "-encoding",
                    "UTF-8",
                    "SimpleThreadPool.java",
                    "SimpleThreadPoolHarness.java",
                ],
                cwd=directory,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(
                0,
                compile_result.returncode,
                compile_result.stdout + compile_result.stderr,
            )
            run_result = subprocess.run(
                [java, "-ea", "-cp", str(directory), "SimpleThreadPoolHarness"],
                cwd=directory,
                env=env,
                text=True,
                capture_output=True,
                timeout=15,
            )
            self.assertEqual(
                0, run_result.returncode, run_result.stdout + run_result.stderr
            )
            self.assertIn("PASS java thread-pool harness", run_result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
