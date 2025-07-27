class SystemException(Exception):
    """시스템 관련 기본 예외"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ConfigurationException(SystemException):
    """설정 오류"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, code="CONFIG_ERROR")
        if config_key:
            self.details['config_key'] = config_key


class ComponentInitializationException(SystemException):
    """컴포넌트 초기화 오류"""
    def __init__(self, component_name: str, message: str):
        full_message = f"Failed to initialize {component_name}: {message}"
        super().__init__(full_message, code="INIT_ERROR")
        self.details['component'] = component_name