"""Tests for error visualizer."""
import imp
from os import path
from collections import namedtuple

from EasyClangComplete.plugin.error_vis import popup_error_vis
from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.settings import settings_storage
from EasyClangComplete.plugin.popups import popups
from EasyClangComplete.plugin import view_config
from EasyClangComplete.plugin import tools

from EasyClangComplete.tests import gui_test_wrapper


imp.reload(gui_test_wrapper)
imp.reload(popup_error_vis)
imp.reload(settings_manager)
imp.reload(settings_storage)
imp.reload(view_config)
imp.reload(popups)
imp.reload(tools)

ActionRequest = tools.ActionRequest
PopupErrorVis = popup_error_vis.PopupErrorVis
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper
SettingsManager = settings_manager.SettingsManager
SettingsStorage = settings_storage.SettingsStorage
ViewConfigManager = view_config.ViewConfigManager
Popup = popups.Popup

test_file = namedtuple('test_file', 'name')
test_cursor = namedtuple('test_cursor', 'file line')
test_extent = namedtuple('test_extent', 'start end')


class TestErrorVis:
    """Test error visualization."""

    def set_up_completer(self):
        """Set up a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        settings.use_libclang = self.use_libclang

        view_config_manager = ViewConfigManager()
        view_config = view_config_manager.load_for_view(self.view, settings)
        completer = view_config.completer
        return completer, settings

    def tear_down_completer(self):
        """Tear down a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        view_config_manager = ViewConfigManager()
        view_config_manager.clear_for_view(self.view.buffer_id())

    def test_popups_init(self):
        """Test that setup view correctly sets up the popup."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer, _ = self.set_up_completer()
        self.assertIsNotNone(completer.error_vis)
        self.assertTrue(isinstance(completer.error_vis, PopupErrorVis))
        self.tear_down_completer()
        self.tear_down()

    def test_generate_errors(self):
        """Test that errors get correctly generated and cleared."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer, _ = self.set_up_completer()
        self.assertIsNotNone(completer.error_vis)
        err_dict = completer.error_vis.err_regions
        v_id = self.view.buffer_id()
        self.assertTrue(v_id in err_dict)
        self.assertEqual(len(err_dict[v_id]), 1)
        self.assertTrue(10 in err_dict[v_id])
        self.assertEqual(len(err_dict[v_id][10]), 1)
        self.assertEqual(err_dict[v_id][10][0]['row'], '10')
        self.assertEqual(err_dict[v_id][10][0]['col'], '3')
        expected_error = "expected unqualified-id"
        self.assertTrue(expected_error in err_dict[v_id][10][0]['error'])

        # not clear errors:
        completer.error_vis.clear(self.view)
        err_dict = completer.error_vis.err_regions
        self.assertFalse(v_id in err_dict)

        # cleanup
        self.tear_down_completer()
        self.tear_down()

    def test_get_text_by_extent_multifile(self):
        """Test getting text from multifile extent."""
        file1 = test_file('file1.c')
        file2 = test_file('file2.c')
        cursor1 = test_cursor(file1, 1)
        cursor2 = test_cursor(file2, 6)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), None)

    def test_get_text_by_extent_oneline(self):
        """Test getting text from oneline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 8)
        cursor2 = test_cursor(file1, 8)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), '  A a;\n')

    def test_get_text_by_extent_multiline(self):
        """Test getting text from multiline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 8)
        cursor2 = test_cursor(file1, 9)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), '  A a;\n  a.\n')

    def test_error(self):
        """Test getting text from multiline extent."""
        error_popup = Popup.error("error_text")
        md_text = error_popup.as_markdown()
        expected_error = """!!! panel-error "ECC: Error"
    error_text
"""
        self.assertEqual(md_text, expected_error)

    def test_warning(self):
        """Test getting text from multiline extent."""
        error_popup = Popup.warning("warning_text")
        md_text = error_popup.as_markdown()
        expected_error = """!!! panel-warning "ECC: Warning"
    warning_text
"""
        self.assertEqual(md_text, expected_error)

    def test_info(self):
        """Test that info message is generated correctly."""
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8), "  a.")
        pos = self.view.text_point(8, 4)
        action_request = ActionRequest(self.view, pos)
        completer.info(action_request, settings)


class TestErrorVisBin(TestErrorVis, GuiTestWrapper):
    """Test class for the binary based completer."""
    use_libclang = False


class TestErrorVisLib(TestErrorVis, GuiTestWrapper):
    """Test class for the binary based completer."""
    use_libclang = True
