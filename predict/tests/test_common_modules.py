"""Unit tests for common utility modules"""
import unittest
from unittest.mock import Mock, patch, mock_open
import os
import tempfile
from common.io import (
    get_match_up_output_html_path,
    find_output_folder,
    find_credential_folder,
    find_configs_folder,
    find_root_folder,
    get_file_content_from_crendential_folder,
    get_single_line_string_from_file
)
from common.styling import get_table_css


class TestIOModule(unittest.TestCase):
    """Test cases for common.io module"""

    @patch('common.io.find_output_folder')
    def test_get_match_up_output_html_path(self, mock_output):
        """Test HTML output path generation"""
        mock_output.return_value = '/output'
        result = get_match_up_output_html_path(123, 5)
        self.assertEqual(result, '/output/123_5.html')

    @patch('common.io.find_root_folder')
    def test_find_output_folder(self, mock_root):
        """Test finding output folder"""
        mock_root.return_value = '/root'
        result = find_output_folder()
        self.assertEqual(result, '/root/output')

    @patch('common.io.find_root_folder')
    def test_find_credential_folder(self, mock_root):
        """Test finding credentials folder"""
        mock_root.return_value = '/root'
        result = find_credential_folder()
        self.assertEqual(result, '/root/credentials')

    @patch('common.io.find_root_folder')
    def test_find_configs_folder(self, mock_root):
        """Test finding configs folder"""
        mock_root.return_value = '/root'
        result = find_configs_folder()
        self.assertEqual(result, '/root/configs')

    @patch('os.getcwd')
    def test_find_root_folder_found(self, mock_cwd):
        """Test finding root folder when path exists"""
        mock_cwd.return_value = '/home/user/projects/fantasy_basketball_tools/src'
        result = find_root_folder()
        self.assertTrue(result.endswith('fantasy_basketball_tools'))

    @patch('os.getcwd')
    def test_find_root_folder_not_found(self, mock_cwd):
        """Test finding root folder raises exception when not found"""
        mock_cwd.return_value = '/some/other/path'
        with self.assertRaises(Exception) as context:
            find_root_folder()
        self.assertIn('fatasy_basketball_tools', str(context.exception))

    @patch('common.io.get_single_line_string_from_file')
    @patch('common.io.find_credential_folder')
    def test_get_file_content_from_credential_folder(self, mock_cred_folder, mock_read):
        """Test reading file from credential folder"""
        mock_cred_folder.return_value = '/creds'
        mock_read.return_value = 'secret_value'
        
        result = get_file_content_from_crendential_folder('test.txt')
        self.assertEqual(result, 'secret_value')
        mock_read.assert_called_once()

    def test_get_single_line_string_from_file(self):
        """Test reading single line from file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('line1\nline2\nline3')
            temp_path = f.name
        
        try:
            result = get_single_line_string_from_file(temp_path)
            self.assertEqual(result, 'line1')
        finally:
            os.unlink(temp_path)

    def test_get_single_line_string_from_file_with_whitespace(self):
        """Test reading single line with surrounding whitespace"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('  line1  \nline2')
            temp_path = f.name
        
        try:
            result = get_single_line_string_from_file(temp_path)
            self.assertEqual(result, 'line1')
        finally:
            os.unlink(temp_path)


class TestStylingModule(unittest.TestCase):
    """Test cases for common.styling module"""

    def test_get_table_css_returns_string(self):
        """Test get_table_css returns a string"""
        result = get_table_css()
        self.assertIsInstance(result, str)

    def test_get_table_css_contains_css_link(self):
        """Test get_table_css contains CSS link tag"""
        result = get_table_css()
        self.assertIn('<link', result)
        self.assertIn('rel="stylesheet"', result)
        self.assertIn('css', result)

    def test_get_table_css_contains_main_css(self):
        """Test get_table_css references main.css"""
        result = get_table_css()
        self.assertIn('main.css', result)


if __name__ == '__main__':
    unittest.main()
