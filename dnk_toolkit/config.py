import json
import os

DEFAULT_CONFIG = {
    "prompt": "dnk> ",
    "history_length": 1000,
    "log_level": "INFO"
}

_current_config = {}

def load_config(config_file_path: str) -> dict:
    global _current_config
    _current_config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r') as f:
                user_config = json.load(f)
                _current_config.update(user_config)
            print(f"[*] 설정 파일 '{config_file_path}' 로드 완료.")
        except json.JSONDecodeError:
            print(f"[!] 경고: 설정 파일 '{config_file_path}'이(가) 손상되었거나 형식이 올바르지 않습니다. 기본 설정을 사용합니다.")
        except Exception as e:
            print(f"[!] 경고: 설정 파일 로드 중 오류 발생: {e}. 기본 설정을 사용합니다.")
    return _current_config

def save_config(config_file_path: str):
    global _current_config
    try:
        with open(config_file_path, 'w') as f:
            json.dump(_current_config, f, indent=4)
        print(f"[*] 설정 파일 '{config_file_path}' 저장 완료.")
    except Exception as e:
        print(f"[!] 오류: 설정 파일 '{config_file_path}' 저장 실패: {e}")

def get_config(key: str = None):
    global _current_config
    if key:
        return _current_config.get(key)
    return _current_config

def set_config(key: str, value: str):
    global _current_config
    if value.lower() == 'true':
        _current_config[key] = True
    elif value.lower() == 'false':
        _current_config[key] = False
    elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
        _current_config[key] = int(value)
    elif value.replace('.', '', 1).isdigit():
         _current_config[key] = float(value)
    else:
        _current_config[key] = value
    print(f"[*] 설정 변경: '{key}' = '{_current_config[key]}'")

def print_config(key: str = None):
    global _current_config
    if key:
        val = get_config(key)
        if val is not None:
            print(f"{key}: {val}")
        else:
            print(f"오류: '{key}' 키를 찾을 수 없습니다.")
    else:
        print("\n--- 현재 설정 ---")
        for k, v in _current_config.items():
            print(f"{k}: {v}")
        print("-----------------\n")
