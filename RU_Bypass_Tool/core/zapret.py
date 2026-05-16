import subprocess
import psutil
import os
import time
import threading

class ZapretManager:
    def __init__(self, log_callback=None):
        self.process = None
        self.bat_path = None
        self.log = log_callback or print
        self._running = False
        self.on_status_change = None

    def is_running(self) -> bool:
        """Проверить запущен ли winws.exe"""
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] == "winws.exe":
                    return True
            except:
                pass
        return False

    def start(self, bat_path: str) -> bool:
        """Запустить zapret"""
        if self.is_running():
            self.log("zapret уже запущен")
            return True

        try:
            self.bat_path = bat_path
            self.log(f"Запуск: {bat_path}")

            self.process = subprocess.Popen(
                [bat_path],
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # Ждём запуска winws.exe
            for i in range(10):
                time.sleep(1)
                if self.is_running():
                    self._running = True
                    self.log("zapret успешно запущен!")
                    if self.on_status_change:
                        self.on_status_change(True)
                    return True

            self.log("Ошибка: winws.exe не запустился")
            return False

        except Exception as e:
            self.log(f"Ошибка запуска: {e}")
            return False

    def stop(self) -> bool:
        """Остановить zapret"""
        try:
            stopped = False
            for proc in psutil.process_iter(["name", "pid"]):
                try:
                    if proc.info["name"] in ["winws.exe", "winws"]:
                        proc.kill()
                        stopped = True
                        self.log(f"Процесс winws.exe остановлен (PID: {proc.info['pid']})")
                except:
                    pass

            if self.process:
                self.process.kill()
                self.process = None

            self._running = False
            if self.on_status_change:
                self.on_status_change(False)

            if stopped:
                self.log("zapret остановлен")
            return True

        except Exception as e:
            self.log(f"Ошибка остановки: {e}")
            return False

    def restart(self, bat_path: str = None) -> bool:
        """Перезапустить zapret"""
        self.log("Перезапуск zapret...")
        self.stop()
        time.sleep(2)
        return self.start(bat_path or self.bat_path)