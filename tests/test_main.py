import os
import sys
import unittest
from unittest.mock import MagicMock

# Add the project root to sys.path so we can import main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import is_moderator


def make_interaction(manage_messages=False, administrator=False):
    interaction = MagicMock()
    interaction.user.guild_permissions.manage_messages = manage_messages
    interaction.user.guild_permissions.administrator = administrator
    return interaction


class TestIsModerator(unittest.TestCase):
    def test_manage_messages_permission_counts_as_moderator(self):
        interaction = make_interaction(manage_messages=True)
        self.assertTrue(is_moderator(interaction))

    def test_administrator_permission_counts_as_moderator(self):
        interaction = make_interaction(administrator=True)
        self.assertTrue(is_moderator(interaction))

    def test_both_permissions_counts_as_moderator(self):
        interaction = make_interaction(manage_messages=True, administrator=True)
        self.assertTrue(is_moderator(interaction))

    def test_no_permissions_is_not_moderator(self):
        interaction = make_interaction()
        self.assertFalse(is_moderator(interaction))


if __name__ == "__main__":
    unittest.main()
