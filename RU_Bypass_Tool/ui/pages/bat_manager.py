# ui/pages/bat_manager.py
import customtkinter as ctk
import os
import subprocess
import threading
import time
import psutil
import socket

try:
    import requests
except ImportError:
    requests = None

from core.service_manager import ServiceManager

class ServiceDialog(ctk.CTkToplevel):

    def __init__(self, parent, bat_path: str,
                 service_manager: ServiceManager,
                 log_callback=None):
        super().__init__(parent)

        self.bat_path = bat_path
        self.sm = service_manager
        self.log = log_callback or print
        self.filename = os.path.basename(bat_path)

        self.title(f"Автозапуск — {self.filename}")
        self.geometry("480x470")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._build_ui()
        self.after(100, self._start_status_loop)

    def _build_ui(self):
        # Заголовок
        header = ctk.CTkFrame(
            self, fg_color="#1a1a2e", corner_radius=0
        )
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="⚙️ Автозапуск с Windows",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4fc3f7"
        ).pack(padx=15, pady=12)

        # Инфо
        info = ctk.CTkFrame(
            self, fg_color="#16213e", corner_radius=10
        )
        info.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(
            info,
            text=f"📄 {self.filename}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        task_name = self.sm._bat_to_service_name(self.bat_path)
        ctk.CTkLabel(
            info,
            text=f"Имя задачи: {task_name}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#555"
        ).pack(anchor="w", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            info,
            text="Использует Планировщик задач Windows\n"
                 "Bat файл запускается автоматически при старте системы",
            font=ctk.CTkFont(size=11),
            text_color="#666",
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # Статус
        status_frame = ctk.CTkFrame(
            self, fg_color="#16213e", corner_radius=10
        )
        status_frame.pack(fill="x", padx=15, pady=6)

        status_row = ctk.CTkFrame(
            status_frame, fg_color="transparent"
        )
        status_row.pack(fill="x", padx=12, pady=12)

        ctk.CTkLabel(
            status_row,
            text="Статус:",
            font=ctk.CTkFont(size=12),
            text_color="#888"
        ).pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_row,
            text="⏳ Проверяю...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffd700"
        )
        self.status_label.pack(side="left", padx=8)

        # Кнопки
        btns = ctk.CTkFrame(
            self, fg_color="#16213e", corner_radius=10
        )
        btns.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(
            btns,
            text="Управление:",
            font=ctk.CTkFont(size=11),
            text_color="#666"
        ).pack(anchor="w", padx=12, pady=(10, 4))

        # Установить
        self.install_btn = ctk.CTkButton(
            btns,
            text="📥 Добавить в автозапуск",
            command=self._on_install,
            fg_color="#1a237e",
            hover_color="#283593",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled"
        )
        self.install_btn.pack(fill="x", padx=12, pady=3)

        # Запустить сейчас
        self.start_btn = ctk.CTkButton(
            btns,
            text="▶ Запустить сейчас",
            command=self._on_start,
            fg_color="#2e7d32",
            hover_color="#388e3c",
            height=36,
            font=ctk.CTkFont(size=12),
            state="disabled"
        )
        self.start_btn.pack(fill="x", padx=12, pady=3)

        # Остановить
        self.stop_btn = ctk.CTkButton(
            btns,
            text="⏹ Остановить",
            command=self._on_stop,
            fg_color="#c62828",
            hover_color="#d32f2f",
            height=36,
            font=ctk.CTkFont(size=12),
            state="disabled"
        )
        self.stop_btn.pack(fill="x", padx=12, pady=3)

        # Удалить из автозапуска
        self.uninstall_btn = ctk.CTkButton(
            btns,
            text="🗑 Убрать из автозапуска",
            command=self._on_uninstall,
            fg_color="#37474f",
            hover_color="#455a64",
            height=36,
            font=ctk.CTkFont(size=12),
            state="disabled"
        )
        self.uninstall_btn.pack(fill="x", padx=12, pady=(3, 12))

        # Лог
        self.mini_log = ctk.CTkTextbox(
            self,
            height=80,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="#0d1117",
            text_color="#c9d1d9",
            corner_radius=8,
            state="disabled"
        )
        self.mini_log.pack(
            fill="x", padx=15, pady=(6, 15)
        )

    def _log(self, msg: str):
        try:
            ts = time.strftime("%H:%M:%S")
            self.mini_log.configure(state="normal")
            self.mini_log.insert("end", f"[{ts}] {msg}\n")
            self.mini_log.see("end")
            self.mini_log.configure(state="disabled")
        except:
            pass
        self.log(msg)

    def _refresh_status(self):
        def check():
            try:
                import psutil
    
                winws_running = any(
                    p.info["name"] == "winws.exe"
                    for p in psutil.process_iter(["name"])
                )
    
                task_status = self.sm.get_task_status(self.bat_path)
    
                if task_status == "not_installed":
                    final = "not_installed"
                elif winws_running:
                    final = "running"
                else:
                    final = "stopped"
    
                # Проверяем что окно ещё существует перед обновлением
                def safe_apply(s):
                    try:
                        if self.winfo_exists():
                            self._apply_status(s)
                    except:
                        pass
    
                try:
                    self.after(0, lambda s=final: safe_apply(s))
                except:
                    pass
    
            except Exception as e:
                def safe_error():
                    try:
                        if self.winfo_exists():
                            self._log(f"❌ Ошибка: {e}")
                            self._apply_status("not_installed")
                    except:
                        pass
                try:
                    self.after(0, safe_error)
                except:
                    pass
    
        threading.Thread(target=check, daemon=True).start()


    def _apply_status(self, status: str):
        self._current_status = status
    
        status_map = {
            "not_installed": (
                "⚫ Не добавлен в автозапуск",
                "#666666"
            ),
            "stopped": (
                "🔴 Добавлен в автозапуск, сейчас не запущен",
                "#f44336"
            ),
            "running": (
                "🟢 Работает (winws.exe запущен)",
                "#4caf50"
            ),
            "starting": (
                "🟡 Запускается...",
                "#ffd700"
            ),
        }
    
        text, color = status_map.get(
            status, ("❓ Неизвестно", "#888")
        )
        self.status_label.configure(text=text, text_color=color)
    
        # Обновляем кнопки
        for btn in [
            self.install_btn, self.start_btn,
            self.stop_btn, self.uninstall_btn
        ]:
            btn.configure(state="disabled")
    
        if status == "not_installed":
            self.install_btn.configure(state="normal")
        elif status == "stopped":
            self.start_btn.configure(state="normal")
            self.uninstall_btn.configure(state="normal")
        elif status == "running":
            self.stop_btn.configure(state="normal")
            self.uninstall_btn.configure(state="normal")
    
        self._log(f"Статус: {text}")

    def _start_status_loop(self):
        """Обновлять статус каждые 3 секунды"""
        self._refresh_status()
        try:
            # Проверяем что окно ещё открыто
            if self.winfo_exists():
                self.after(3000, self._start_status_loop)
        except:
            pass

    def _run_action(self, name: str, fn, *args):
        for btn in [
            self.install_btn, self.start_btn,
            self.stop_btn, self.uninstall_btn
        ]:
            btn.configure(state="disabled")
    
        self._log(f"⏳ {name}...")
    
        def thread():
            try:
                ok, msg = fn(*args)
                icon = "✅" if ok else "❌"
    
                def on_done():
                    try:
                        if self.winfo_exists():
                            self._log(f"{icon} {msg}")
                    except:
                        pass
    
                def on_refresh():
                    try:
                        if self.winfo_exists():
                            self._refresh_status()
                    except:
                        pass
    
                try:
                    self.after(0, on_done)
                    self.after(1500, on_refresh)
                except:
                    pass
    
            except Exception as e:
                def on_error():
                    try:
                        if self.winfo_exists():
                            self._log(f"❌ {e}")
                    except:
                        pass
    
                def on_refresh_err():
                    try:
                        if self.winfo_exists():
                            self._refresh_status()
                    except:
                        pass
    
                try:
                    self.after(0, on_error)
                    self.after(1500, on_refresh_err)
                except:
                    pass
    
        threading.Thread(target=thread, daemon=True).start()

    def _on_install(self):
        self._run_action(
            "Добавление в автозапуск",
            self.sm.install_as_task,
            self.bat_path
        )

    def _on_start(self):
        self._run_action(
            "Запуск",
            self.sm.start_task,
            self.bat_path
        )

    def _on_stop(self):
        self._run_action(
            "Остановка",
            self.sm.stop_task,
            self.bat_path
        )

    def _on_uninstall(self):
        confirm = ctk.CTkToplevel(self)
        confirm.title("Подтверждение")
        confirm.geometry("320x130")
        confirm.resizable(False, False)
        confirm.grab_set()
        confirm.lift()

        ctk.CTkLabel(
            confirm,
            text=f"Убрать из автозапуска?\n{self.filename}",
            font=ctk.CTkFont(size=13),
            justify="center"
        ).pack(pady=18)

        row = ctk.CTkFrame(confirm, fg_color="transparent")
        row.pack()

        def do_it():
            confirm.destroy()
            self._run_action(
                "Удаление из автозапуска",
                self.sm.uninstall_task,
                self.bat_path
            )

        ctk.CTkButton(
            row, text="✅ Убрать",
            command=do_it,
            fg_color="#c62828", width=130
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            row, text="❌ Отмена",
            command=confirm.destroy,
            fg_color="#37474f", width=130
        ).pack(side="left", padx=6)

class BatManagerPage(ctk.CTkFrame):
    def __init__(self, parent, zapret_path: str, log_callback=None):
        super().__init__(parent, fg_color="transparent")

        self.zapret_path = zapret_path
        self.log = log_callback or print
        self.bat_cards = {}

        self.service_manager = ServiceManager(
            zapret_path=zapret_path,
            log_callback=log_callback
        )

        self._build_ui()
        self.refresh_bat_list()

    def _build_ui(self):
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12)
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            header,
            text="📂 Менеджер BAT файлов",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        ).pack(side="left", padx=15, pady=12)

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=15, pady=8)

        ctk.CTkButton(
            btn_frame,
            text="🔄 Обновить",
            command=self.refresh_bat_list,
            width=110, height=32,
            fg_color="#0d47a1",
            hover_color="#1565c0",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="📁 Открыть папку",
            command=self._open_folder,
            width=130, height=32,
            fg_color="#37474f",
            hover_color="#455a64",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=4)

        # Легенда
        legend = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12)
        legend.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            legend,
            text="Статус сервиса:",
            font=ctk.CTkFont(size=11),
            text_color="#666"
        ).pack(side="left", padx=12, pady=6)

        for icon, text in [
            ("⚫", "Не установлен"),
            ("🔴", "Остановлен"),
            ("🟢", "Работает"),
        ]:
            ctk.CTkLabel(
                legend,
                text=f"{icon} {text}",
                font=ctk.CTkFont(size=11),
                text_color="#888"
            ).pack(side="left", padx=10, pady=6)

        # Поиск
        filter_frame = ctk.CTkFrame(
            self, fg_color="#16213e", corner_radius=12
        )
        filter_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            filter_frame,
            text="🔍",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(12, 4), pady=8)

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_bat_list())

        ctk.CTkEntry(
            filter_frame,
            textvariable=self.search_var,
            placeholder_text="Поиск bat файлов...",
            width=220,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", pady=8)

        self.count_label = ctk.CTkLabel(
            filter_frame,
            text="Файлов: 0",
            font=ctk.CTkFont(size=12),
            text_color="#666"
        )
        self.count_label.pack(side="right", padx=15)

        # Список
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#0d1117",
            corner_radius=12
        )
        self.scroll_frame.pack(fill="both", expand=True)

    def refresh_bat_list(self):
        """Обновить список bat файлов"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.bat_cards.clear()

        bat_files = self._find_bat_files()

        search = self.search_var.get().lower()
        if search:
            bat_files = [
                f for f in bat_files
                if search in os.path.basename(f).lower()
            ]

        self.count_label.configure(text=f"Файлов: {len(bat_files)}")

        if not bat_files:
            ctk.CTkLabel(
                self.scroll_frame,
                text="😔 BAT файлы не найдены",
                font=ctk.CTkFont(size=14),
                text_color="#666"
            ).pack(pady=40)
            return

        for bat_path in bat_files:
            self._create_bat_card(bat_path)

    def _find_bat_files(self) -> list:
        excluded = {
            "service.bat",
            "install_service.bat",
            "uninstall_service.bat",
            "get_if_list.bat",
            "blockcheck.bat",
            "install.bat",
        }
        result = []
        try:
            for file in sorted(os.listdir(self.zapret_path)):
                if (file.lower().endswith(".bat")
                        and file.lower() not in excluded
                        and not file.startswith("_svc_")):
                    result.append(
                        os.path.join(self.zapret_path, file)
                    )
        except Exception as e:
            self.log(f"Ошибка: {e}")
        return result

    def _get_card_color(self, filename: str) -> str:
        name = filename.lower()
        if "apex" in name:      return "#ff6600"
        if "discord" in name:   return "#5865f2"
        if "youtube" in name:   return "#ff0000"
        if "general" in name:   return "#4caf50"
        if "generated" in name: return "#4fc3f7"
        if "alt" in name:       return "#ffd700"
        return "#888888"

    def _create_bat_card(self, bat_path: str):
        """Создать карточку для bat файла"""
        filename = os.path.basename(bat_path)
        filesize = os.path.getsize(bat_path)
        mod_time = os.path.getmtime(bat_path)
        mod_str = time.strftime(
            "%d.%m.%Y %H:%M", time.localtime(mod_time)
        )
        color = self._get_card_color(filename)

        # Получаем статус сервиса в фоне
        svc_status = "checking"

        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="#16213e",
            corner_radius=10
        )
        card.pack(fill="x", padx=8, pady=4)

        # Верхняя строка — название
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            top_row,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color=color,
            width=20
        ).pack(side="left")

        ctk.CTkLabel(
            top_row,
            text=filename,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
            anchor="w"
        ).pack(side="left", padx=(4, 0))

        # Статус сервиса (справа)
        svc_status_label = ctk.CTkLabel(
            top_row,
            text="⚫ Проверяю...",
            font=ctk.CTkFont(size=11),
            text_color="#555"
        )
        svc_status_label.pack(side="right")

        # Метаданные
        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.pack(fill="x", padx=12, pady=(0, 2))

        ctk.CTkLabel(
            meta_row,
            text=f"📅 {mod_str}  📦 {filesize} байт",
            font=ctk.CTkFont(size=11),
            text_color="#555"
        ).pack(side="left")

        result_label = ctk.CTkLabel(
            meta_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        )
        result_label.pack(side="left", padx=(10, 0))

        # Прогресс-бар
        progress = ctk.CTkProgressBar(
            card, height=3,
            fg_color="#1a1a2e",
            progress_color="#4fc3f7"
        )

        # Кнопки
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 10))

        # Кнопка Проверить
        test_btn = ctk.CTkButton(
            btn_row,
            text="🧪 Проверить",
            width=105, height=30,
            fg_color="#1a237e",
            hover_color="#283593",
            font=ctk.CTkFont(size=11)
        )
        test_btn.configure(
            command=lambda p=bat_path, r=result_label,
                           pr=progress, b=test_btn:
                self._run_test(p, r, pr, b)
        )
        test_btn.pack(side="left", padx=(0, 4))

        # Кнопка Запустить
        ctk.CTkButton(
            btn_row,
            text="▶ Запустить",
            command=lambda p=bat_path: self._launch_bat(p),
            width=100, height=30,
            fg_color="#2e7d32",
            hover_color="#388e3c",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=4)

        # Кнопка Сервис
        svc_btn = ctk.CTkButton(
            btn_row,
            text="⚙️ Сервис",
            width=95, height=30,
            fg_color="#1a237e",
            hover_color="#283593",
            font=ctk.CTkFont(size=11)
        )
        svc_btn.configure(
            command=lambda p=bat_path,
                           sl=svc_status_label,
                           sb=svc_btn:
                self._open_service_dialog(p, sl, sb)
        )
        svc_btn.pack(side="left", padx=4)

        # Кнопка Открыть
        ctk.CTkButton(
            btn_row,
            text="📝 Открыть",
            command=lambda p=bat_path: self._open_bat(p),
            width=90, height=30,
            fg_color="#37474f",
            hover_color="#455a64",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=4)

        # Кнопка Удалить
        ctk.CTkButton(
            btn_row,
            text="🗑",
            command=lambda p=bat_path, c=card:
                self._delete_bat(p, c),
            width=34, height=30,
            fg_color="#b71c1c",
            hover_color="#c62828",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=4)

        self.bat_cards[bat_path] = {
            "card": card,
            "result": result_label,
            "progress": progress,
            "test_btn": test_btn,
            "svc_btn": svc_btn,
            "svc_status_label": svc_status_label,
        }

        # Загружаем статус сервиса в фоне
        self._update_service_badge(bat_path, svc_status_label, svc_btn)

    def _open_service_dialog(self, bat_path: str,
                             svc_status_label,
                             svc_btn=None):
        """Открыть диалог управления сервисом"""
        dialog = ServiceDialog(
            parent=self,
            bat_path=bat_path,
            service_manager=self.service_manager,
            log_callback=self.log
        )

        def on_close():
            dialog.destroy()
            self._update_service_badge(
                bat_path, svc_status_label, svc_btn
            )

        dialog.protocol("WM_DELETE_WINDOW", on_close)

    def _update_service_badge(self, bat_path: str,
                              svc_status_label,
                              svc_btn=None):
        """Проверяем статус задачи планировщика"""
        def check():
            try:
                # Используем get_task_status вместо get_service_status
                status = self.service_manager.get_task_status(bat_path)
    
                svc_icons = {
                    "running":       "🟢 Автозапуск работает",
                    "stopped":       "🔴 Автозапуск добавлен",
                    "not_installed": "⚫ Нет автозапуска",
                }
                svc_colors = {
                    "running":       "#4caf50",
                    "stopped":       "#f44336",
                    "not_installed": "#555555",
                }
    
                def update_ui():
                    try:
                        svc_status_label.configure(
                            text=svc_icons.get(status, "❓"),
                            text_color=svc_colors.get(status, "#888")
                        )
                        if svc_btn:
                            btn_color = (
                                "#2e7d32"
                                if status == "running"
                                else "#1a237e"
                            )
                            svc_btn.configure(fg_color=btn_color)
                    except Exception:
                        pass
    
                self.after(0, update_ui)
            except Exception:
                pass
    
        threading.Thread(target=check, daemon=True).start()

    # ==================== ТЕСТ ====================

    def _run_test(self, bat_path, result_label,
                  progress, test_btn):
        filename = os.path.basename(bat_path)
        self.log(f"🧪 Тест: {filename}")

        test_btn.configure(
            text="⏳ Тест...",
            state="disabled",
            fg_color="#555"
        )
        result_label.configure(
            text="⏳ Тестирование...",
            text_color="#ffd700"
        )
        progress.pack(fill="x", padx=12, pady=(0, 6))
        progress.set(0)
        progress.start()

        def test_thread():
            results = self._perform_test(bat_path, progress)
            self.after(0, lambda: self._show_test_results(
                results, result_label, progress, test_btn
            ))

        threading.Thread(target=test_thread, daemon=True).start()

    def _perform_test(self, bat_path: str, progress) -> dict:
        results = {
            "winws_running": False,
            "youtube": False,
            "discord": False,
            "apex_ping": False,
            "general": False,
            "error": None
        }
        test_process = None
        try:
            self.after(0, lambda: progress.set(0.1))
            test_process = subprocess.Popen(
                [bat_path], shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            time.sleep(3)

            self.after(0, lambda: progress.set(0.2))
            for _ in range(8):
                if self._is_winws_running():
                    results["winws_running"] = True
                    break
                time.sleep(1)

            if not results["winws_running"]:
                results["error"] = "winws.exe не запустился"
                return results

            time.sleep(2)
            self.after(0, lambda: progress.set(0.4))
            results["youtube"] = self._test_youtube()

            self.after(0, lambda: progress.set(0.6))
            results["discord"] = self._test_discord()

            self.after(0, lambda: progress.set(0.8))
            results["apex_ping"] = self._test_apex()

            self.after(0, lambda: progress.set(0.9))
            results["general"] = self._test_general()

        except Exception as e:
            results["error"] = str(e)
        finally:
            self.after(0, lambda: progress.set(1.0))
            self._stop_winws()
            if test_process:
                try:
                    test_process.kill()
                except:
                    pass
        return results

    def _is_winws_running(self) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] == "winws.exe":
                    return True
            except:
                pass
        return False

    def _stop_winws(self):
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] == "winws.exe":
                    proc.kill()
            except:
                pass

    def _test_youtube(self) -> bool:
        if requests is None:
            return False
        try:
            r = requests.get(
                "https://www.youtube.com",
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            return r.status_code == 200
        except:
            return False

    def _test_discord(self) -> bool:
        if requests is None:
            return False
        try:
            r = requests.get(
                "https://discord.com/api/v10/gateway",
                timeout=8
            )
            return r.status_code in [200, 401]
        except:
            return False

    def _test_apex(self) -> bool:
        for host, port in [
            ("ea.com", 443),
            ("accounts.ea.com", 443)
        ]:
            try:
                sock = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                )
                sock.settimeout(5)
                if sock.connect_ex((host, port)) == 0:
                    sock.close()
                    return True
                sock.close()
            except:
                pass
        return False

    def _test_general(self) -> bool:
        if requests is None:
            return False
        for site in [
            "https://instagram.com",
            "https://facebook.com"
        ]:
            try:
                r = requests.get(
                    site, timeout=6,
                    headers={"User-Agent": "Mozilla/5.0"},
                    allow_redirects=True
                )
                if r.status_code < 500:
                    return True
            except:
                pass
        return False

    def _show_test_results(self, results, result_label,
                           progress, test_btn):
        progress.stop()
        progress.pack_forget()
        test_btn.configure(
            text="🧪 Проверить",
            state="normal",
            fg_color="#1a237e"
        )

        if results.get("error"):
            result_label.configure(
                text=f"❌ {results['error']}",
                text_color="#f44336"
            )
            return

        if not results["winws_running"]:
            result_label.configure(
                text="❌ winws.exe не запустился",
                text_color="#f44336"
            )
            return

        icons = (
            f"▶️{'✅' if results['youtube'] else '❌'} "
            f"💬{'✅' if results['discord'] else '❌'} "
            f"🎮{'✅' if results['apex_ping'] else '❌'} "
            f"🌐{'✅' if results['general'] else '❌'}"
        )
        passed = sum([
            results["youtube"], results["discord"],
            results["apex_ping"], results["general"]
        ])

        if passed == 4:
            color, status = "#4caf50", "Всё работает!"
        elif passed >= 2:
            color, status = "#ffd700", f"Частично ({passed}/4)"
        else:
            color, status = "#f44336", f"Не работает ({passed}/4)"

        result_label.configure(
            text=f"{status}  {icons}",
            text_color=color
        )
        self.log(
            f"Тест завершён: {status} | "
            f"YT={'✅' if results['youtube'] else '❌'} "
            f"DC={'✅' if results['discord'] else '❌'} "
            f"Apex={'✅' if results['apex_ping'] else '❌'} "
            f"РКН={'✅' if results['general'] else '❌'}"
        )

    # ==================== ДЕЙСТВИЯ ====================

    def _launch_bat(self, bat_path: str):
        self.log(f"▶ Запуск: {os.path.basename(bat_path)}")
        try:
            subprocess.Popen(
                [bat_path], shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")

    def _open_bat(self, bat_path: str):
        try:
            subprocess.Popen(["notepad.exe", bat_path])
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")

    def _delete_bat(self, bat_path: str, card):
        filename = os.path.basename(bat_path)
        dialog = ctk.CTkToplevel(self)
        dialog.title("Удаление")
        dialog.geometry("340x130")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"Удалить файл?\n{filename}",
            font=ctk.CTkFont(size=13),
            justify="center"
        ).pack(pady=18)

        row = ctk.CTkFrame(dialog, fg_color="transparent")
        row.pack()

        def confirm():
            try:
                os.remove(bat_path)
                card.destroy()
                self.log(f"🗑 Удалён: {filename}")
                dialog.destroy()
            except Exception as e:
                self.log(f"❌ Ошибка: {e}")
                dialog.destroy()

        ctk.CTkButton(
            row, text="✅ Удалить",
            command=confirm,
            fg_color="#c62828", width=130
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            row, text="❌ Отмена",
            command=dialog.destroy,
            fg_color="#37474f", width=130
        ).pack(side="left", padx=6)

    def _open_folder(self):
        os.startfile(self.zapret_path)