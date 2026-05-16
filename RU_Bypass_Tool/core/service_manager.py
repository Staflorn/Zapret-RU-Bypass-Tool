import subprocess
import os
import time
import re
import winreg
from typing import Optional, Callable, Tuple


class ServiceManager:

    SERVICE_PREFIX = "zapret_"

    def __init__(self, zapret_path: str,
                 log_callback: Optional[Callable] = None):
        self.zapret_path = zapret_path
        self.log = log_callback or print

    # ==================== УТИЛИТЫ ====================

    def _bat_to_service_name(self, bat_path: str) -> str:
        filename = os.path.basename(bat_path)
        name = os.path.splitext(filename)[0]
        safe = "".join(
            c if (c.isalnum() or c == "_") else "_"
            for c in name
        )
        return f"{self.SERVICE_PREFIX}{safe[:60]}"

    def _bat_to_display_name(self, bat_path: str) -> str:
        filename = os.path.basename(bat_path)
        name = os.path.splitext(filename)[0]
        return f"Zapret [{name}]"

    def _check_admin(self) -> bool:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except:
            return False

    def _run_powershell(self, command: str,
                        timeout: int = 30) -> Tuple[int, str, str]:
        """Запустить команду через PowerShell"""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle", "Hidden",
                    "-ExecutionPolicy", "Bypass",
                    "-Command", command
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return (
                result.returncode,
                result.stdout.strip(),
                result.stderr.strip()
            )
        except subprocess.TimeoutExpired:
            self.log("PowerShell: таймаут!")
            return -1, "", "timeout"
        except Exception as e:
            self.log(f"PowerShell ошибка: {e}")
            return -1, "", str(e)

    def _run_sc(self, args: list,
                timeout: int = 30) -> Tuple[int, str, str]:
        """sc.exe с правильной кодировкой cp866"""
        try:
            result = subprocess.run(
                ["sc.exe"] + args,
                capture_output=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout = result.stdout.decode(
                "cp866", errors="ignore"
            ).strip()
            stderr = result.stderr.decode(
                "cp866", errors="ignore"
            ).strip()
            self.log(
                f"sc {' '.join(str(a) for a in args[:2])}: "
                f"code={result.returncode}"
                + (f" | {stdout[:60]}" if stdout else "")
            )
            return result.returncode, stdout, stderr
        except Exception as e:
            return -1, "", str(e)

    # ==================== ПАРСИНГ BAT ФАЙЛА ====================

    def _extract_winws_args(self, bat_path: str) -> Optional[str]:
        """
        Извлечь аргументы winws.exe из bat файла.
        Ищем строку с winws.exe и берём все параметры после неё.
        """
        try:
            with open(bat_path, "r",
                      encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Убираем переносы строк с ^
            content_joined = content.replace("^\n", " ").replace("^ \n", " ")

            # Ищем строку с winws.exe
            # Паттерн: что-то winws.exe <аргументы>
            pattern = r'winws\.exe["\s]+(.*?)(?:\n|$)'
            match = re.search(
                pattern, content_joined,
                re.IGNORECASE | re.DOTALL
            )

            if match:
                args = match.group(1).strip()
                # Убираем лишние пробелы и переносы
                args = " ".join(args.split())
                self.log(
                    f"Извлечены аргументы winws: "
                    f"{args[:80]}..."
                )
                return args

            self.log("Аргументы winws.exe не найдены в bat файле")
            return None

        except Exception as e:
            self.log(f"Ошибка парсинга bat файла: {e}")
            return None

    def _get_winws_path(self) -> Optional[str]:
        """Найти winws.exe"""
        candidates = [
            os.path.join(self.zapret_path, "bin", "winws.exe"),
            os.path.join(self.zapret_path, "winws.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _resolve_bat_variables(self, bat_path: str,
                                args: str) -> str:
        """
        Заменить переменные %BIN% и %LISTS% на реальные пути
        """
        bin_path = os.path.join(self.zapret_path, "bin") + "\\"
        lists_path = os.path.join(self.zapret_path, "lists") + "\\"

        args = args.replace("%BIN%", bin_path)
        args = args.replace("%LISTS%", lists_path)

        # Убираем незаменённые переменные bat
        # (GameFilterTCP, GameFilterUDP и т.д.)
        args = re.sub(r"%\w+%", "", args)

        # Убираем двойные пробелы
        args = " ".join(args.split())

        return args

    # ==================== СТАТУС ====================

    def get_service_status(self, bat_path: str) -> str:
        service_name = self._bat_to_service_name(bat_path)
        return self._get_status_by_name(service_name)

    def _get_status_by_name(self, service_name: str) -> str:
        code, out, err = self._run_powershell(
            f"(Get-Service -Name '{service_name}' "
            f"-ErrorAction SilentlyContinue).Status"
        )
        status_str = out.strip().lower()

        if not status_str:
            return "not_installed"
        elif "running" in status_str:
            return "running"
        elif "stopped" in status_str:
            return "stopped"
        elif "startpending" in status_str:
            return "starting"
        elif "stoppending" in status_str:
            return "stopping"
        else:
            return "not_installed"

    def _is_service_installed(self, service_name: str) -> bool:
        return self._get_status_by_name(service_name) != "not_installed"

    # ==================== УСТАНОВКА ====================

    def install_as_task(self, bat_path: str) -> Tuple[bool, str]:
        """
        Установить через Планировщик задач Windows.
        Надёжнее чем сервис для bat файлов с WinDivert.
        """
        if not self._check_admin():
            return False, "Нет прав администратора!"
    
        if not os.path.exists(bat_path):
            return False, f"Файл не найден: {bat_path}"
    
        task_name = self._bat_to_service_name(bat_path)
        display_name = self._bat_to_display_name(bat_path)
        filename = os.path.basename(bat_path)
    
        self.log(f"Создание задачи планировщика: {task_name}")
    
        # Удаляем старую задачу если есть
        self._run_powershell(
            f"Unregister-ScheduledTask -TaskName '{task_name}' "
            f"-Confirm:$false -ErrorAction SilentlyContinue"
        )
    
        # XML описание задачи
        xml = f"""<?xml version="1.0" encoding="UTF-16"?>
    <Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
      <RegistrationInfo>
        <Description>Zapret DPI bypass: {filename}</Description>
        <URI>\\{task_name}</URI>
      </RegistrationInfo>
      <Triggers>
        <BootTrigger>
          <Enabled>true</Enabled>
          <Delay>PT5S</Delay>
        </BootTrigger>
      </Triggers>
      <Principals>
        <Principal id="Author">
          <UserId>S-1-5-18</UserId>
          <RunLevel>HighestAvailable</RunLevel>
        </Principal>
      </Principals>
      <Settings>
        <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
        <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
        <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
        <AllowHardTerminate>true</AllowHardTerminate>
        <StartWhenAvailable>true</StartWhenAvailable>
        <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
        <IdleSettings>
          <StopOnIdleEnd>false</StopOnIdleEnd>
          <RestartOnIdle>false</RestartOnIdle>
        </IdleSettings>
        <AllowStartOnDemand>true</AllowStartOnDemand>
        <Enabled>true</Enabled>
        <Hidden>false</Hidden>
        <RunOnlyIfIdle>false</RunOnlyIfIdle>
        <WakeToRun>false</WakeToRun>
        <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
        <Priority>4</Priority>
      </Settings>
      <Actions Context="Author">
        <Exec>
          <Command>cmd.exe</Command>
          <Arguments>/c "{bat_path}"</Arguments>
          <WorkingDirectory>{self.zapret_path}</WorkingDirectory>
        </Exec>
      </Actions>
    </Task>"""
    
        # Сохраняем XML во временный файл
        xml_path = os.path.join(
            os.environ.get("TEMP", "C:\\Temp"),
            f"{task_name}.xml"
        )
        try:
            with open(xml_path, "w", encoding="utf-16") as f:
                f.write(xml)
        except Exception as e:
            return False, f"Ошибка создания XML: {e}"
    
        # Регистрируем задачу
        code, out, err = self._run_powershell(
            f"Register-ScheduledTask "
            f"-TaskName '{task_name}' "
            f"-Xml (Get-Content '{xml_path}' -Raw) "
            f"-Force -ErrorAction Stop",
            timeout=30
        )
    
        # Удаляем временный XML
        try:
            os.remove(xml_path)
        except:
            pass
    
        if code == 0:
            self.log(f"✅ Задача создана: {task_name}")
            return True, f"Задача '{display_name}' создана!\nАвтозапуск при входе в систему включён."
        else:
            short_err = err.split("\n")[0] if err else out
            return False, f"Ошибка создания задачи: {short_err[:100]}"
    
    def start_task(self, bat_path: str) -> Tuple[bool, str]:
        """Запустить задачу планировщика"""
        task_name = self._bat_to_service_name(bat_path)
    
        code, out, err = self._run_powershell(
            f"Start-ScheduledTask -TaskName '{task_name}' "
            f"-ErrorAction Stop"
        )
    
        if code == 0:
            return True, "Задача запущена!"
        else:
            return False, f"Ошибка: {err.split(chr(10))[0][:100]}"
    
    def stop_task(self, bat_path: str) -> Tuple[bool, str]:
        """Остановить задачу планировщика"""
        task_name = self._bat_to_service_name(bat_path)
    
        code, out, err = self._run_powershell(
            f"Stop-ScheduledTask -TaskName '{task_name}' "
            f"-ErrorAction Stop"
        )
    
        # Также убиваем winws.exe
        self._run_powershell(
            "Get-Process winws -ErrorAction SilentlyContinue "
            "| Stop-Process -Force"
        )
    
        if code == 0:
            return True, "Задача остановлена!"
        else:
            return False, f"Ошибка: {err.split(chr(10))[0][:100]}"
    
    def uninstall_task(self, bat_path: str) -> Tuple[bool, str]:
        """Удалить задачу планировщика"""
        task_name = self._bat_to_service_name(bat_path)
    
        # Сначала останавливаем
        self.stop_task(bat_path)
        time.sleep(1)
    
        code, out, err = self._run_powershell(
            f"Unregister-ScheduledTask -TaskName '{task_name}' "
            f"-Confirm:$false -ErrorAction Stop"
        )
    
        if code == 0:
            return True, "Задача удалена!"
        else:
            return False, f"Ошибка: {err.split(chr(10))[0][:100]}"
    
    def get_task_status(self, bat_path: str) -> str:
        """Статус задачи планировщика"""
        task_name = self._bat_to_service_name(bat_path)
    
        code, out, err = self._run_powershell(
            f"(Get-ScheduledTask -TaskName '{task_name}' "
            f"-ErrorAction SilentlyContinue).State"
        )
    
        state = out.strip().lower()
        if not state:
            return "not_installed"
        elif "running" in state:
            return "running"
        elif "ready" in state:
            return "stopped"
        elif "disabled" in state:
            return "stopped"
        else:
            return "not_installed"