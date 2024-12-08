"""配置文件处理模块"""
import yaml
import os
from typing import Dict

class Config:
    _instance = None
    _config = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.reload()
            
    def _get_project_root(self):
        """获取项目根目录"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def reload(self):
        config_path = os.path.join(self._get_project_root(), 'config', 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
    
    def save(self):
        config_path = os.path.join(self._get_project_root(), 'config', 'config.yaml')
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, sort_keys=False)
    
    @property
    def bilibili(self) -> Dict:
        return self._config['bilibili']
    
    @property
    def monitor(self) -> Dict:
        return self._config['monitor']
    
    @property
    def danmaku(self) -> Dict:
        return self._config['danmaku']

# 创建全局配置实例
config = Config.get_instance() 