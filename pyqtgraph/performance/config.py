"""
Performance Configuration Presets for PyQtGraph

This module provides pre-configured settings optimized for different
use cases, particularly high-frequency trading applications.
"""

import pyqtgraph as pg
from typing import Dict, Any, Optional


class PerformanceConfig:
    """Base class for performance configuration presets."""
    
    def __init__(self):
        self._config = {}
    
    def apply(self) -> None:
        """Apply the configuration to PyQtGraph."""
        for key, value in self._config.items():
            pg.setConfigOption(key, value)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the configuration dictionary."""
        return self._config.copy()


class TradingViewConfig(PerformanceConfig):
    """
    Optimized configuration for trading applications similar to TradingView.
    
    Features:
    - OpenGL acceleration enabled
    - Antialiasing disabled for performance
    - Mouse rate limiting for smooth interaction
    - Optimized for high-frequency updates
    """
    
    def __init__(self, 
                 enable_opengl: bool = True,
                 mouse_rate_limit: int = 120,
                 enable_antialiasing: bool = False,
                 enable_cupy: bool = False,
                 enable_numba: bool = True):
        super().__init__()
        
        self._config = {
            'useOpenGL': enable_opengl,
            'antialias': enable_antialiasing,
            'mouseRateLimit': mouse_rate_limit,
            'useCupy': enable_cupy,
            'useNumba': enable_numba,
            'segmentedLineMode': 'on',  # Always use segmented lines for performance
            'exitCleanup': True,
            'crashWarning': False,  # Disable warnings for performance
            'enableExperimental': True,  # Enable experimental optimizations
        }


class HighFrequencyConfig(PerformanceConfig):
    """
    Configuration optimized for extremely high-frequency data updates.
    
    Trades off some visual quality for maximum performance.
    """
    
    def __init__(self):
        super().__init__()
        
        self._config = {
            'useOpenGL': True,
            'antialias': False,
            'mouseRateLimit': 60,  # Lower rate for max performance
            'useCupy': True,  # Enable GPU acceleration if available
            'useNumba': True,
            'segmentedLineMode': 'on',
            'exitCleanup': True,
            'crashWarning': False,
            'enableExperimental': True,
            'background': 'k',  # Dark background reduces GPU load
            'foreground': 'w',
        }


class QualityConfig(PerformanceConfig):
    """
    Configuration optimized for visual quality with reasonable performance.
    
    Good for detailed analysis views where visual fidelity is important.
    """
    
    def __init__(self):
        super().__init__()
        
        self._config = {
            'useOpenGL': True,
            'antialias': True,  # Enable antialiasing for quality
            'mouseRateLimit': 100,
            'useCupy': False,
            'useNumba': True,
            'segmentedLineMode': 'auto',  # Auto-decide based on conditions
            'exitCleanup': True,
            'crashWarning': True,
            'enableExperimental': False,
        }


class ConfigManager:
    """
    Manager for applying and switching between different performance configurations.
    """
    
    PRESETS = {
        'trading': TradingViewConfig,
        'high_frequency': HighFrequencyConfig,
        'quality': QualityConfig,
        'default': PerformanceConfig,
    }
    
    def __init__(self):
        self._current_config = None
        self._original_config = {}
    
    def save_current_config(self) -> None:
        """Save current PyQtGraph configuration for restoration."""
        config_options = [
            'useOpenGL', 'antialias', 'mouseRateLimit', 'useCupy', 'useNumba',
            'segmentedLineMode', 'exitCleanup', 'crashWarning', 'enableExperimental',
            'background', 'foreground'
        ]
        
        for option in config_options:
            try:
                self._original_config[option] = pg.getConfigOption(option)
            except KeyError:
                pass  # Option might not exist in this version
    
    def apply_preset(self, preset_name: str, **kwargs) -> None:
        """
        Apply a performance preset configuration.
        
        Parameters:
        -----------
        preset_name : str
            Name of the preset ('trading', 'high_frequency', 'quality', 'default')
        **kwargs
            Additional arguments to pass to the configuration constructor
        """
        if preset_name not in self.PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(self.PRESETS.keys())}")
        
        if self._current_config is None:
            self.save_current_config()
        
        config_class = self.PRESETS[preset_name]
        self._current_config = config_class(**kwargs)
        self._current_config.apply()
    
    def restore_original(self) -> None:
        """Restore the original PyQtGraph configuration."""
        if self._original_config:
            for key, value in self._original_config.items():
                pg.setConfigOption(key, value)
            self._current_config = None
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the current configuration if one is applied."""
        if self._current_config:
            return self._current_config.get_config()
        return None


# Convenience functions for easy access
def apply_trading_config(**kwargs) -> None:
    """Apply trading-optimized configuration."""
    config = TradingViewConfig(**kwargs)
    config.apply()


def apply_high_frequency_config() -> None:
    """Apply high-frequency optimized configuration."""
    config = HighFrequencyConfig()
    config.apply()


def apply_quality_config() -> None:
    """Apply quality-optimized configuration."""
    config = QualityConfig()
    config.apply()