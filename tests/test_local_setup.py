import multiprocessing

from crumble.util import writer_lock


def _hold(path, acquired, release):
    with writer_lock(path):
        acquired.set()
        release.wait(15)


def test_writer_lock_serialises_spawned_processes(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    first, second, release_first, release_second = [ctx.Event() for _ in range(4)]
    path = str(tmp_path / "writer.lock")
    a = ctx.Process(target=_hold, args=(path, first, release_first))
    b = ctx.Process(target=_hold, args=(path, second, release_second))
    try:
        a.start()
        assert first.wait(10)
        b.start()
        assert not second.wait(0.3)
        release_first.set()
        assert second.wait(10)
        release_second.set()
        a.join(10)
        b.join(10)
        assert a.exitcode == b.exitcode == 0
    finally:
        release_first.set()
        release_second.set()
        for p in (a, b):
            if p.pid is not None:
                p.join(3)
                if p.is_alive():
                    p.terminate()
                    p.join(3)
