import multiprocessing as mp
from pathlib import Path
import tempfile
import unittest
from journal import Journal


def owner(path, pipe, recover):
    j=Journal(path)
    with j.locked():
        if j.stage() is None: j.transition(None,'prepared')
        pipe.send('locked'); pipe.recv()
        j.transition('prepared','aborted' if recover else 'started')
        pipe.send('transitioned')
        pipe.recv()


def follower(path, pipe, recover):
    j=Journal(path)
    try:
        with j.locked(nonblocking=True): pass
    except BlockingIOError: pipe.send('blocked')
    else: pipe.send('unexpected'); return
    with j.locked():
        try: j.transition('prepared','aborted' if recover else 'started')
        except ValueError: pipe.send('refused')
        else: pipe.send('accepted')

class JournalTests(unittest.TestCase):
    def scenario(self, first_recovery=False, kill=False):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/'receipt'); ctx=mp.get_context('spawn')
            a,b=ctx.Pipe(); c,e=ctx.Pipe()
            p=ctx.Process(target=owner,args=(path,b,first_recovery))
            q=ctx.Process(target=follower,args=(path,e,not first_recovery))
            try:
                p.start(); self.assertTrue(a.poll(10)); self.assertEqual(a.recv(),'locked')
                q.start(); self.assertTrue(c.poll(10)); self.assertEqual(c.recv(),'blocked')
                a.send('continue'); self.assertTrue(a.poll(10)); self.assertEqual(a.recv(),'transitioned')
                if kill: p.kill()
                else: a.send('finish')
                p.join(10); self.assertFalse(p.is_alive())
                self.assertTrue(c.poll(10)); self.assertEqual(c.recv(),'refused')
                q.join(10); self.assertEqual(q.exitcode,0)
                self.assertEqual(Journal(path).stage(),'aborted' if first_recovery else 'started')
            finally:
                for child in (p,q):
                    if child.pid and child.is_alive(): child.kill(); child.join(5)
                for conn in (a,b,c,e): conn.close()
    def test_add_wins(self): self.scenario()
    def test_recovery_wins(self): self.scenario(first_recovery=True)
    def test_started_owner_killed_no_retry(self): self.scenario(kill=True)

if __name__=='__main__': unittest.main()
