from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from bol.config import BOLConfig
from bol.modules.m3_visual.cortex import VisualCortex

class TestNativeBrowser(unittest.TestCase):
    def test_cortex_capture_region_when_enabled(self):
        config = BOLConfig()
        config.browser_window_enabled = True
        config.browser_window_x = 100
        config.browser_window_y = 150
        config.browser_window_width = 800
        config.browser_window_height = 600

        with patch('bol.modules.m3_visual.capture.ScreenCapturePipeline.capture_region') as mock_capture_region:
            mock_capture_region.return_value = (MagicMock(), MagicMock())
            cortex = VisualCortex(config)
            cortex.capture_current_state()
            
            # Should have called capture_region with the configured dimensions
            mock_capture_region.assert_called_once()
            region_arg = mock_capture_region.call_args[0][0]
            self.assertEqual(region_arg.left, 100)
            self.assertEqual(region_arg.top, 150)
            self.assertEqual(region_arg.width, 800)
            self.assertEqual(region_arg.height, 600)

if __name__ == "__main__":
    unittest.main()
