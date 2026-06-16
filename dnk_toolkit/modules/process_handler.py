
import subprocess
import os
import socket
import threading
import time
import sys

class ProcessBase:
    def __init__(self):
        self.connected = False
        self.output_buffer = b''
        self.interactive_thread = None
        self.stop_event = threading.Event()

    def send(self, data: bytes):
        raise NotImplementedError

    def _read_from_source(self, timeout=0.1):
        raise NotImplementedError

    def recv(self, num_bytes: int = 4096, timeout: float = 0.1) -> bytes:
        while self.connected and len(self.output_buffer) < num_bytes:
            data = self._read_from_source(timeout)
            if data:
                self.output_buffer += data
            else:
                break
        
        if len(self.output_buffer) >= num_bytes:
            result = self.output_buffer[:num_bytes]
            self.output_buffer = self.output_buffer[num_bytes:]
            return result
        elif self.output_buffer:
            result = self.output_buffer
            self.output_buffer = b''
            return result
        return b''

    def recvline(self, timeout: float = 0.1) -> bytes:
        while self.connected:
            if b'\n' in self.output_buffer:
                line, self.output_buffer = self.output_buffer.split(b'\n', 1)
                return line + b'\n'
            
            data = self._read_from_source(timeout)
            if data:
                self.output_buffer += data
            else:
                if self.output_buffer:
                    line = self.output_buffer
                    self.output_buffer = b''
                    return line
                break
        return b''

    def recvall(self, timeout: float = 0.1) -> bytes:
        all_data = b''
        while self.connected:
            data = self._read_from_source(timeout)
            if data:
                all_data += data
            else:
                if not data and not self.connected:
                    break
                time.sleep(0.01)
        return self.output_buffer + all_data

    def _interactive_reader(self):
        while not self.stop_event.is_set() and self.connected:
            try:
                output = self._read_from_source(timeout=0.05)
                if output:
                    sys.stdout.buffer.write(output)
                    sys.stdout.flush()
                if not self.connected:
                    break
            except Exception as e:
                if self.connected:
                    print(f"오류: 인터랙티브 리더 중 오류 발생: {e}", file=sys.stderr)
                self.connected = False
                break

    def interactive(self):
        if not self.connected:
            print("[!] 연결되지 않았거나 프로세스가 실행 중이지 않습니다.", file=sys.stderr)
            return

        print("\n[*] 인터랙티브 모드 시작 (Ctrl+C로 종료).")
        print("    출력된 데이터는 즉시 표시됩니다.")
        
        self.stop_event.clear()
        self.interactive_thread = threading.Thread(target=self._interactive_reader)
        self.interactive_thread.daemon = True
        self.interactive_thread.start()

        try:
            while self.connected:
                line = sys.stdin.readline()
                if not line:
                    break
                self.send(line.encode('utf-8'))
        except KeyboardInterrupt:
            print("\n[*] 인터랙티브 모드 종료 (Ctrl+C).")
        except EOFError:
            print("\n[*] 인터랙티브 모드 종료 (EOF).")
        finally:
            self.stop_event.set()
            if self.interactive_thread and self.interactive_thread.is_alive():
                self.interactive_thread.join(timeout=1)
            self.close()

    def close(self):
        self.connected = False
        self.stop_event.set()
        if self.interactive_thread and self.interactive_thread.is_alive():
            self.interactive_thread.join(timeout=1)

class LocalProcess(ProcessBase):
    def __init__(self, binary_path: str, args: list = None):
        super().__init__()
        if not os.path.exists(binary_path):
            print(f"오류: 바이너리 파일 '{binary_path}'을(를) 찾을 수 없습니다.", file=sys.stderr)
            self.connected = False
            return
        
        cmd = [binary_path] + (args if args else [])
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                preexec_fn=os.setsid
            )
            self.connected = True
            print(f"[*] 로컬 프로세스 실행됨: '{' '.join(cmd)}' (PID: {self.process.pid})")
        except Exception as e:
            print(f"오류: 로컬 프로세스 실행 실패: {e}", file=sys.stderr)
            self.connected = False

    def send(self, data: bytes):
        if self.connected and self.process and self.process.stdin:
            try:
                self.process.stdin.write(data)
                self.process.stdin.flush()
            except BrokenPipeError:
                self.connected = False
                print("[*] 프로세스가 종료되었습니다.")
            except Exception as e:
                print(f"오류: 데이터 전송 실패: {e}", file=sys.stderr)
                self.connected = False

    def _read_from_source(self, timeout=0.1):
        if self.connected and self.process and self.process.stdout:
            try:
                if self.process.poll() is not None:
                    self.connected = False
                    remaining_output = self.process.stdout.read()
                    return remaining_output
                
                import select
                ready_to_read, _, _ = select.select([self.process.stdout], [], [], timeout)
                if ready_to_read:
                    return self.process.stdout.read(4096)
            except ValueError:
                self.connected = False
            except Exception as e:
                print(f"오류: 데이터 수신 실패: {e}")
                self.connected = False
        return b''

    def close(self):
        super().close()
        if hasattr(self, 'process') and self.process:
            if self.process.poll() is None:
                try:
                    os.killpg(os.getpgid(self.process.pid), 9)
                except Exception as e:
                    print(f"경고: 프로세스 종료 중 오류 발생: {e}")
            self.process = None

class RemoteProcess(ProcessBase):
    def __init__(self, host: str, port: int):
        super().__init__()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.socket.settimeout(0.1)
            self.connected = True
            print(f"[*] 원격 호스트에 연결됨: {host}:{port}")
        except ConnectionRefusedError:
            print(f"오류: {host}:{port} 연결 거부됨. 서버가 실행 중인지 확인하세요.")
            self.connected = False
        except socket.timeout:
            print(f"오류: {host}:{port} 연결 시간 초과.")
            self.connected = False
        except Exception as e:
            print(f"오류: 원격 연결 실패: {e}")
            self.connected = False

    def send(self, data: bytes):
        if self.connected and self.socket:
            try:
                self.socket.sendall(data)
            except BrokenPipeError:
                self.connected = False
                print("[*] 소켓 연결이 끊어졌습니다.")
            except Exception as e:
                print(f"오류: 데이터 전송 실패: {e}")
                self.connected = False

    def _read_from_source(self, timeout=0.1):
        if self.connected and self.socket:
            try:
                import select
                ready_to_read, _, _ = select.select([self.socket], [], [], timeout)
                if ready_to_read:
                    data = self.socket.recv(4096)
                    if not data:
                        self.connected = False
                    return data
            except socket.timeout:
                pass
            except Exception as e:
                print(f"오류: 데이터 수신 실패: {e}")
                self.connected = False
        return b''

    def close(self):
        super().close()