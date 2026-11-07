"""Production saves layout and explicit database isolation, using temporary roots."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.paths import SAVE_DB, SAVE_DIR, save_db
from app.service import Service
from app.storage import Store
from app.web import create_app


class SavePathsTests(unittest.TestCase):
    def test_production_layout_keeps_story_packages_at_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = Service(Store(save_db(root)), root)
            self.assertEqual(service.runtime.library, root / 'StoryPackage')
            self.assertEqual(service.runtime.character_directory, root / 'character_packages')
            self.assertEqual(SAVE_DB.parent, SAVE_DIR)
            self.assertFalse((root / 'data').exists())

    def test_old_data_path_is_an_explicit_isolated_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / 'data' / 'textiledream.sqlite3')
            service = Service(store, root)
            self.assertEqual(service.runtime.library, store.path.parent / 'StoryPackage')
            self.assertFalse((root / 'saves').exists())

    def test_web_default_and_explicit_database_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch('app.web.ROOT', Path(tmp)):
            (Path(tmp) / 'app' / 'static').mkdir(parents=True)
            (Path(tmp) / 'assets' / 'maps').mkdir(parents=True)
            default = create_app().state.service
            explicit = create_app(Path(tmp) / 'sandbox' / 'test.sqlite3').state.service
            self.assertEqual(default.store.path, save_db(Path(tmp)))
            self.assertEqual(default.runtime.library, Path(tmp) / 'StoryPackage')
            self.assertEqual(explicit.runtime.library, Path(tmp) / 'sandbox' / 'StoryPackage')
            self.assertFalse((Path(tmp) / 'data').exists())
