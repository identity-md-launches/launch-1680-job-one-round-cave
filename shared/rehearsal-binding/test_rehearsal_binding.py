import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rehearsal_binding


class RehearsalBindingTests(unittest.TestCase):
    def test_real_zto_demo_binds_offline(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(rehearsal_binding.main(['demo']), 0)
        result = json.loads(stream.getvalue())
        self.assertEqual(result['verdict'], 'bound')
        self.assertEqual(result['plan']['call']['to'],
                         '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e')


if __name__ == '__main__':
    unittest.main()
