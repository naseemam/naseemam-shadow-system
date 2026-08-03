import pathlib
import unittest


class FrontendShellMessagesTests(unittest.TestCase):
    def test_shell_renders_conversation_messages_into_the_main_area(self):
        shell_path = pathlib.Path(__file__).resolve().parents[1] / '09_Assets' / 'web' / 'modules' / 'shell.js'
        content = shell_path.read_text(encoding='utf-8')

        self.assertIn('renderMessages', content)
        self.assertIn('messageArea', content)
        self.assertIn('convo.messages', content)
        self.assertIn('executionProgress', content)
        self.assertIn('executionResult', content)
        self.assertIn('replaceLastSystemMessage', content)
        self.assertIn('openPage', content)


if __name__ == '__main__':
    unittest.main()
