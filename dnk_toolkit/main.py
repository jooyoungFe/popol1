###`dnk_toolkit/main.py`

import argparse
import sys
import os
import shlex
import readline
import atexit

from utils.ascii_art import print_logo
from utils.data_converters import p32, p64, u32, u64
from modules.payload_generator import create_nop_sled, create_padding, generate_shellcode_placeholder
from modules.process_handler import LocalProcess, RemoteProcess
from modules.binary_analyzer import check_binary_mitigations, rop_gadget_finder_placeholder, memory_leak_analyzer_placeholder
from config import load_config, save_config, get_config, set_config, print_config

CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.dnk_config.json')
HISTORY_FILE = os.path.join(os.path.expanduser('~'), '.dnk_history')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def setup_readline(parser_instance):
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)
    atexit.register(readline.write_history_file, HISTORY_FILE)
    readline.set_history_length(get_config('history_length'))

    def completer(text, state):
        line_buffer = readline.get_line_buffer()
        
        try:
            parts = shlex.split(line_buffer)
        except ValueError:
            parts = line_buffer.split()

        if line_buffer.endswith(' ') or not parts:
            current_word_to_complete = ''
            current_context_parts = parts
        else:
            current_word_to_complete = parts[-1]
            current_context_parts = parts[:-1]

        suggestions = []

        if not current_context_parts:
            all_main_commands = list(parser_instance.choices.keys()) + ['clear', 'exit', 'quit', 'help']
            suggestions = [cmd for cmd in all_main_commands if cmd.startswith(current_word_to_complete)]
        elif len(current_context_parts) == 1:
            main_cmd = current_context_parts[0]
            if main_cmd in parser_instance.choices:
                subparser = parser_instance.choices[main_cmd]
                if hasattr(subparser, 'choices') and subparser.choices:
                    sub_commands = list(subparser.choices.keys())
                    suggestions = [cmd for cmd in sub_commands if cmd.startswith(current_word_to_complete)]
            elif main_cmd == 'config':
                config_sub_commands = ['get', 'set']
                suggestions = [cmd for cmd in config_sub_commands if cmd.startswith(current_word_to_complete)]
        elif len(current_context_parts) == 2 and current_context_parts[0] == 'config' and current_context_parts[1] == 'set':
            all_config_keys = list(get_config().keys())
            suggestions = [key for key in all_config_keys if key.startswith(current_word_to_complete)]
        
        suggestions.sort()

        if state < len(suggestions):
            return suggestions[state]
        else:
            return None

    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")

def set_and_save_config_wrapper(key: str, value: str):
    set_config(key, value)
    save_config(CONFIG_FILE)

def debugger_placeholder(pid_or_binary, breakpoint_addr=None):
    print(f"[+] Debugger: Attaching to {pid_or_binary}...")
    if breakpoint_addr:
        print(f"[+] Debugger: Setting breakpoint at 0x{breakpoint_addr:x}...")
    print("[+] Debugger: (Not implemented) This would launch a debugger session.")
    print("[+] Debugger: Use 'gdb -p <pid>' or 'lldb -p <pid>' manually for now.")
    print("[+] Debugger: Or 'gdb <binary>' / 'lldb <binary>'")


def main():
    load_config(CONFIG_FILE)
    
    clear_screen()
    print_logo()

    parser = argparse.ArgumentParser(
        description="""
        DN.K - 파이썬 CLI 툴킷 (Pwntools inspired)
        
        이 도구는 시스템 해킹 학습 및 분석을 위한 기초적인 기능을 제공합니다.
        실제 공격 도구가 아니며, 교육적 목적으로 사용합니다.
        """,
        formatter_class=argparse.RawTextHelpFormatter,
        prog="dnk"
    )

    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')

    payload_parser = subparsers.add_parser('payload', help='메모리 오염 및 페이로드 생성 관련 기능')
    payload_subparsers = payload_parser.add_subparsers(dest='payload_cmd', help='페이로드 기능')

    p32_parser = payload_subparsers.add_parser('p32', help='정수를 4바이트 리틀 엔디언 바이트로 변환')
    p32_parser.add_argument('value', type=lambda x: int(x, 0), help='변환할 정수 (10진수 또는 0x 접두사 16진수)')
    p32_parser.set_defaults(func=lambda args: print(f"p32({hex(args.value)}): {p32(args.value)}"))

    p64_parser = payload_subparsers.add_parser('p64', help='정수를 8바이트 리틀 엔디언 바이트로 변환')
    p64_parser.add_argument('value', type=lambda x: int(x, 0), help='변환할 정수 (10진수 또는 0x 접두사 16진수)')
    p64_parser.set_defaults(func=lambda args: print(f"p64({hex(args.value)}): {p64(args.value)}"))

    u32_parser = payload_subparsers.add_parser('u32', help='4바이트 리틀 엔디언 바이트를 정수로 변환 (예: "\\xef\\xbe\\xad\\xde")')
    u32_parser.add_argument('value_str', help='변환할 바이트 문자열 (예: "\\xef\\xbe\\xad\\xde")')
    u32_parser.set_defaults(func=lambda args: print("u32({}): {}".format(args.value_str, u32(eval('b\"' + args.value_str + '\"')))))

    u64_parser = payload_subparsers.add_parser('u64', help='8바이트 리틀 엔디언 바이트를 정수로 변환 (예: "\\xef\\xbe\\xad\\xde\\xef\\xbe\\xad\\xde")')
    u64_parser.add_argument('value_str', help='변환할 바이트 문자열 (예: "\\xef\\xbe\\xad\\xde\\xef\\xbe\\xad\\xde")')
    u64_parser.set_defaults(func=lambda args: print("u64({}): {}".format(args.value_str, u64(eval('b\"' + args.value_str + '\"')))))

    nop_parser = payload_subparsers.add_parser('nop', help='지정된 크기의 NOP sled 생성')
    nop_parser.add_argument('size', type=int, help='생성할 NOP sled의 크기 (바이트)')
    nop_parser.set_defaults(func=lambda args: print(f"NOP Sled ({args.size} bytes):\n{create_nop_sled(args.size)}"))

    padding_parser = payload_subparsers.add_parser('padding', help='지정된 크기의 패딩 바이트 생성')
    padding_parser.add_argument('--size', type=int, required=True, help='패딩의 크기 (바이트)')
    padding_parser.add_argument('--char', type=str, default='A', help='패딩에 사용할 문자 (기본값: "A")')
    padding_parser.set_defaults(func=lambda args: print(f"Padding ({args.size} bytes with '{args.char}'):\n{create_padding(args.size, args.char.encode('latin-1'))}"))

    shellcode_parser = payload_subparsers.add_parser('shellcode', help='아키텍처 및 OS별 셸코드 생성 (플레이스홀더)')
    shellcode_parser.add_argument('arch', type=str, help='대상 아키텍처 (예: x64, arm)')
    shellcode_parser.add_argument('os', type=str, help='대상 운영체제 (예: linux, windows, macos)')
    shellcode_parser.add_argument('type', type=str, help='셸코드 유형 (예: execve, reverse_shell)')
    shellcode_parser.set_defaults(func=lambda args: generate_shellcode_placeholder(args.arch, args.os, args.type))

    process_parser = subparsers.add_parser('process', help='로컬 프로세스 또는 원격 서버와 상호작용')
    process_subparsers = process_parser.add_subparsers(dest='process_cmd', help='프로세스 상호작용 기능')

    local_parser = process_subparsers.add_parser('local', help='로컬 프로세스 실행 및 상호작용')
    local_parser.add_argument('binary', type=str, help='실행할 바이너리 경로')
    local_parser.add_argument('args', nargs=argparse.REMAINDER, help='바이너리에 전달할 인자들')
    local_parser.set_defaults(func=lambda args: LocalProcess(args.binary, args.args).interactive())

    remote_parser = process_subparsers.add_parser('remote', help='원격 서버에 연결 및 상호작용')
    remote_parser.add_argument('host', type=str, help='원격 서버 호스트 주소')
    remote_parser.add_argument('port', type=int, help='원격 서버 포트 번호')
    remote_parser.set_defaults(func=lambda args: RemoteProcess(args.host, args.port).interactive())

    analyze_parser = subparsers.add_parser('analyze', help='바이너리 파일 분석 기능')
    analyze_subparsers = analyze_parser.add_subparsers(dest='analyze_cmd', help='바이너리 분석 기능')

    checksec_parser = analyze_subparsers.add_parser('checksec', help='바이너리 보안 완화 기술 확인 (ASLR, DEP, PIE 등)')
    checksec_parser.add_argument('binary', type=str, help='분석할 바이너리 경로')
    checksec_parser.set_defaults(func=lambda args: print(check_binary_mitigations(args.binary)))

    rop_parser = analyze_subparsers.add_parser('rop', help='바이너리에서 ROP 가젯 탐색 (플레이스홀더)')
    rop_parser.add_argument('binary', type=str, help='분석할 바이너리 경로')
    rop_parser.set_defaults(func=lambda args: print(rop_gadget_finder_placeholder(args.binary)))

    leak_parser = analyze_subparsers.add_parser('leak', help='메모리 릭 분석 (플레이스홀더)')
    leak_parser.add_argument('binary', type=str, help='분석할 바이너리 경로')
    leak_parser.add_argument('--address', type=lambda x: int(x, 0), help='릭될 것으로 예상되는 주소 (10진수 또는 0x 접두사 16진수)')
    leak_parser.set_defaults(func=lambda args: print(memory_leak_analyzer_placeholder(args.binary, args.address)))

    debugger_parser = subparsers.add_parser('debug', help='디버거 연동 (플레이스홀더)')
    debugger_parser.add_argument('target', type=str, help='디버깅할 PID 또는 바이너리 경로')
    debugger_parser.add_argument('--bp', type=lambda x: int(x, 0), help='설정할 브레이크포인트 주소 (10진수 또는 0x 접두사 16진수)')
    debugger_parser.set_defaults(func=lambda args: debugger_placeholder(args.target, args.bp))

    config_parser = subparsers.add_parser('config', help='설정 관리 (예: config get <key>, config set <key> <value>)')
    config_subparsers = config_parser.add_subparsers(dest='config_cmd', help='설정 기능')

    config_get_parser = config_subparsers.add_parser('get', help='설정 값 조회')
    config_get_parser.add_argument('key', nargs='?', help='조회할 설정 키 (생략 시 모든 설정 출력)')
    config_get_parser.set_defaults(func=lambda args: print_config(args.key))

    config_set_parser = config_subparsers.add_parser('set', help='설정 값 변경')
    config_set_parser.add_argument('key', help='설정할 키')
    config_set_parser.add_argument('value', help='설정할 값')
    config_set_parser.set_defaults(func=lambda args: set_and_save_config_wrapper(args.key, args.value))

    print("\n[*] Interactive 모드 시작. 'exit' 또는 'quit' 입력 시 종료.")
    print("    도움말은 'help' 또는 각 명령어 뒤에 '--help'를 입력하세요.")
    
    setup_readline(parser)

    while True:
        try:
            command_line = input(get_config("prompt")).strip()
            
            if not command_line:
                continue
            if command_line.lower() in ['exit', 'quit']:
                print("[*] Interactive 모드 종료.")
                break
            if command_line.lower() == 'clear':
                clear_screen()
                continue

            command_args = shlex.split(command_line)
            
            try:
                args = parser.parse_args(command_args)

                if hasattr(args, 'func'):
                    args.func(args)
                else:
                    if args.command and args.command in subparsers.choices:
                        subparsers.choices[args.command].print_help()
                    else:
                        parser.print_help()
            except SystemExit as e:
                if e.code == 2:
                    print(f"[!] 명령어 파싱 오류 또는 잘못된 사용법: '{command_line}'", file=sys.stderr)
            except Exception as e:
                print(f"[!] 오류 발생: {e}", file=sys.stderr)

        except KeyboardInterrupt:
            print("\n[*] Interactive 모드 종료 (Ctrl+C).")
            break
        except EOFError:
            print("\n[*] Interactive 모드 종료 (EOF).")
            break


if __name__ == "__main__":
    main()