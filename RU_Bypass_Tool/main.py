import customtkinter as ctk
import threading
import os
import sys
import time
import subprocess
from core.detector import ProviderDetector, ProviderInfo, PROVIDER_DATABASE
from core.generator import BatGenerator
from core.zapret import ZapretManager
from ui.pages.bat_manager import BatManagerPage

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Иконка окна приложения
        try:
            if getattr(sys, "frozen", False):
                # Скомпилированный EXE
                icon_path = os.path.join(
                    os.path.dirname(sys.executable),
                    "assets", "icon.ico"
                )
            else:
                # Режим разработки
                icon_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "assets", "icon.ico"
                )
    
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            pass  # Если иконка не найдена — используем стандартную

        self.title("RU Bypass Tool")
        self.geometry("900x650")
        self.resizable(False, False)

        self.provider: ProviderInfo = None
        self.zapret_path = self._find_zapret()
        self.zapret = ZapretManager(log_callback=self._log)
        self.zapret.on_status_change = self._on_status_change
        self.bat_path = None
        self.detecting = False

        self.service_vars = {
            "youtube": ctk.BooleanVar(value=True),
            "discord": ctk.BooleanVar(value=True),
            "apex":    ctk.BooleanVar(value=True),
            "general": ctk.BooleanVar(value=True),
        }

        self._build_ui()
        self._check_zapret_path()

        if self.zapret.is_running():
            self._on_status_change(True)

    def _find_zapret(self) -> str:
        """Найти папку zapret"""
    
        # Для скомпилированного EXE используем папку где лежит EXE
        if getattr(sys, "frozen", False):
            # PyInstaller — берём папку где лежит EXE
            exe_dir = os.path.dirname(sys.executable)
        else:
            # Режим разработки — папка с main.py
            exe_dir = os.path.dirname(os.path.abspath(__file__))
    
        candidates = [
            exe_dir,
            os.path.join(exe_dir, ".."),
            os.path.join(exe_dir, "..", ".."),
            "C:\\zapret",
            "C:\\zapret-win-bundle",
        ]
    
        for path in candidates:
            path = os.path.abspath(path)
            if os.path.exists(os.path.join(path, "bin", "winws.exe")):
                return path
    
        # Если не нашли — возвращаем папку с EXE
        return exe_dir

    def _build_ui(self):
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="🛡️ RU Bypass Tool",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=20, pady=12)

        # Статус в заголовке
        self.header_status = ctk.CTkLabel(
            header,
            text="⭕ Остановлен",
            font=ctk.CTkFont(size=12),
            text_color="#f44336"
        )
        self.header_status.pack(side="right", padx=20)

        # Вкладки
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#0d1117",
            segmented_button_fg_color="#16213e",
            segmented_button_selected_color="#0d47a1",
            segmented_button_selected_hover_color="#1565c0",
            segmented_button_unselected_color="#16213e",
            segmented_button_unselected_hover_color="#1a2744",
            text_color="white",
            text_color_disabled="#666"
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(8, 0))

        # Создаём вкладки
        self.tabview.add("🏠 Главная")
        self.tabview.add("📂 BAT файлы")
        self.tabview.add("📋 Логи")

        # Строим содержимое вкладок
        self._build_home_tab()
        self._build_bat_tab()
        self._build_logs_tab()

        # Нижняя панель
        self._build_bottom_panel()

    # ==================== ВКЛАДКА ГЛАВНАЯ ====================

    def _build_home_tab(self):
        tab = self.tabview.tab("🏠 Главная")

        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=5, pady=5)

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self._build_provider_card(left)
        self._build_status_card(left)
        self._build_services_card(right)

    def _build_provider_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color="#16213e", corner_radius=12)
        card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="📡 Провайдер",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888"
        ).pack(anchor="w", padx=15, pady=(12, 4))

        self.provider_label = ctk.CTkLabel(
            card,
            text="Нажми 'Определить'",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        self.provider_label.pack(anchor="w", padx=15)

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(4, 8))

        self.ttl_label = ctk.CTkLabel(
            info_frame,
            text="TTL: —",
            font=ctk.CTkFont(size=12),
            text_color="#4fc3f7"
        )
        self.ttl_label.pack(side="left")

        self.ip_label = ctk.CTkLabel(
            info_frame,
            text="IP: —",
            font=ctk.CTkFont(size=12),
            text_color="#666"
        )
        self.ip_label.pack(side="left", padx=(12, 0))

        self.detect_btn = ctk.CTkButton(
            card,
            text="🔍 Определить провайдера",
            command=self._start_detection,
            fg_color="#0d47a1",
            hover_color="#1565c0",
            height=34,
            font=ctk.CTkFont(size=13)
        )
        self.detect_btn.pack(fill="x", padx=15, pady=(0, 8))

        manual = ctk.CTkFrame(card, fg_color="transparent")
        manual.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(
            manual,
            text="Вручную:",
            font=ctk.CTkFont(size=11),
            text_color="#666"
        ).pack(side="left")

        self.provider_combo = ctk.CTkComboBox(
            manual,
            values=list(PROVIDER_DATABASE.keys()),
            command=self._on_provider_manual_select,
            width=180,
            font=ctk.CTkFont(size=12)
        )
        self.provider_combo.pack(side="right")
        self.provider_combo.set("КГТС")

    def _build_status_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color="#16213e", corner_radius=12)
        card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="⚡ Статус",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888"
        ).pack(anchor="w", padx=15, pady=(12, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 12))

        self.status_indicator = ctk.CTkLabel(
            row,
            text="⭕",
            font=ctk.CTkFont(size=22)
        )
        self.status_indicator.pack(side="left")

        self.status_label = ctk.CTkLabel(
            row,
            text="Остановлен",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f44336"
        )
        self.status_label.pack(side="left", padx=(8, 0))

        # Текущий bat файл
        self.current_bat_label = ctk.CTkLabel(
            card,
            text="Конфиг: не выбран",
            font=ctk.CTkFont(size=11),
            text_color="#555"
        )
        self.current_bat_label.pack(anchor="w", padx=15, pady=(0, 12))

    def _build_services_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color="#16213e", corner_radius=12)
        card.pack(fill="both", expand=True, pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="🎯 Сервисы",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888"
        ).pack(anchor="w", padx=15, pady=(12, 8))

        services = [
            ("youtube", "▶️ YouTube",       "#ff0000"),
            ("discord", "💬 Discord",        "#5865f2"),
            ("apex",    "🎮 Apex Legends",   "#ff6600"),
            ("general", "🌐 Все сайты РКН", "#4caf50"),
        ]

        for key, label, color in services:
            row = ctk.CTkFrame(card, fg_color="#1a1a2e", corner_radius=8)
            row.pack(fill="x", padx=15, pady=3)

            ctk.CTkSwitch(
                row,
                text=label,
                variable=self.service_vars[key],
                font=ctk.CTkFont(size=13),
                progress_color=color,
                button_color=color,
                button_hover_color=color,
            ).pack(side="left", padx=10, pady=8)

        # Кнопка генерации
        ctk.CTkButton(
            card,
            text="⚙️ Сгенерировать конфиг",
            command=self._generate_bat,
            fg_color="#4a148c",
            hover_color="#6a1b9a",
            height=34,
            font=ctk.CTkFont(size=13)
        ).pack(fill="x", padx=15, pady=(12, 15))

    # ==================== ВКЛАДКА BAT ФАЙЛЫ ====================

    def _build_bat_tab(self):
        tab = self.tabview.tab("📂 BAT файлы")
        self.bat_manager = BatManagerPage(
            tab,
            zapret_path=self.zapret_path,
            log_callback=self._log
        )
        self.bat_manager.pack(fill="both", expand=True)

    # ==================== ВКЛАДКА ЛОГИ ====================

    def _build_logs_tab(self):
        tab = self.tabview.tab("📋 Логи")

        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=(5, 0))

        ctk.CTkLabel(
            header,
            text="Журнал событий",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888"
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="🗑 Очистить",
            command=self._clear_logs,
            width=100,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#37474f",
            hover_color="#455a64"
        ).pack(side="right")

        self.log_box = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0d1117",
            text_color="#c9d1d9",
            corner_radius=8,
            state="disabled"
        )
        self.log_box.pack(fill="both", expand=True, padx=5, pady=8)

    # ==================== НИЖНЯЯ ПАНЕЛЬ ====================

    def _build_bottom_panel(self):
        panel = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=0)
        panel.pack(fill="x", side="bottom")

        btn_frame = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame.pack(padx=15, pady=10)

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶ Запустить",
            command=self._start_zapret,
            fg_color="#2e7d32",
            hover_color="#388e3c",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹ Остановить",
            command=self._stop_zapret,
            fg_color="#c62828",
            hover_color="#d32f2f",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        self.restart_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Перезапуск",
            command=self._restart_zapret,
            fg_color="#e65100",
            hover_color="#f57c00",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.restart_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="📁 Папка",
            command=lambda: os.startfile(self.zapret_path),
            fg_color="#37474f",
            hover_color="#455a64",
            width=80,
            height=40,
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=5)

    # ==================== ЛОГИКА ====================

    def _log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_logs(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _check_zapret_path(self):
        winws = os.path.join(self.zapret_path, "bin", "winws.exe")
        # ВРЕМЕННО — показываем где ищем
        self._log(f"Ищу bat файлы в: {self.zapret_path}")
        self._log(f"winws.exe: {'найден' if os.path.exists(winws) else 'НЕ НАЙДЕН'}")
        
        # Показываем все bat файлы которые видит программа
        try:
            all_files = os.listdir(self.zapret_path)
            bat_files = [f for f in all_files if f.endswith(".bat")]
            self._log(f"Bat файлов найдено: {len(bat_files)}")
            for f in bat_files:
                self._log(f"  - {f}")
        except Exception as e:
            self._log(f"Ошибка чтения папки: {e}")

        if os.path.exists(winws):
            self._log(f"✅ zapret найден: {self.zapret_path}")
        else:
            self._log(f"⚠️ winws.exe не найден: {self.zapret_path}")

    def _start_detection(self):
        if self.detecting:
            return
        self.detecting = True
        self.detect_btn.configure(text="⏳ Определяю...", state="disabled")
        self.provider_label.configure(text="Определяю...")
        self._log("Определение провайдера...")

        def detect_thread():
            detector = ProviderDetector(log_callback=self._log)
            provider = detector.detect()
            self.after(0, lambda: self._on_detection_complete(provider))

        threading.Thread(target=detect_thread, daemon=True).start()

    def _on_detection_complete(self, provider: ProviderInfo):
        self.provider = provider
        self.detecting = False
        self.provider_label.configure(text=provider.name)
        self.ttl_label.configure(
            text=f"TTL: {provider.ttl} / YT: {provider.ttl_youtube}"
        )
        self.ip_label.configure(text=f"IP: {provider.ip}")
        self.detect_btn.configure(
            text="🔍 Определить провайдера",
            state="normal"
        )
        self._log(f"✅ Провайдер: {provider.name}")
        self._generate_bat()

    def _on_provider_manual_select(self, choice: str):
        self.provider = PROVIDER_DATABASE.get(choice)
        if self.provider:
            self.provider_label.configure(text=self.provider.name)
            self.ttl_label.configure(
                text=f"TTL: {self.provider.ttl} / YT: {self.provider.ttl_youtube}"
            )
            self._log(f"Провайдер выбран: {self.provider.name}")
            self._generate_bat()

    def _generate_bat(self):
        if not self.provider:
            self.provider = PROVIDER_DATABASE["КГТС"]

        services = {k: v.get() for k, v in self.service_vars.items()}

        try:
            generator = BatGenerator(self.zapret_path)
            self.bat_path = generator.save(self.provider, services)
            self._log(f"✅ Конфиг сгенерирован: zapret_generated.bat")
            self.current_bat_label.configure(
                text=f"Конфиг: zapret_generated.bat"
            )
            # Обновляем список в менеджере
            self.bat_manager.refresh_bat_list()
        except Exception as e:
            self._log(f"❌ Ошибка генерации: {e}")

    def _start_zapret(self):
        if not self.bat_path:
            if not self.provider:
                self.provider = PROVIDER_DATABASE["КГТС"]
            self._generate_bat()

        if not self.bat_path:
            self._log("❌ Нет конфига для запуска!")
            return

        self._log("▶ Запуск zapret...")

        def start_thread():
            success = self.zapret.start(self.bat_path)
            if not success:
                self.after(0, lambda: self._log("❌ Не удалось запустить!"))

        threading.Thread(target=start_thread, daemon=True).start()

    def _stop_zapret(self):
        self._log("⏹ Остановка zapret...")
        self.zapret.stop()

    def _restart_zapret(self):
        self._log("🔄 Перезапуск zapret...")
        self._generate_bat()

        def restart_thread():
            self.zapret.restart(self.bat_path)

        threading.Thread(target=restart_thread, daemon=True).start()

    def _on_status_change(self, running: bool):
        if running:
            self.status_indicator.configure(text="🟢")
            self.status_label.configure(
                text="Работает",
                text_color="#4caf50"
            )
            self.header_status.configure(
                text="🟢 Работает",
                text_color="#4caf50"
            )
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.restart_btn.configure(state="normal")
        else:
            self.status_indicator.configure(text="⭕")
            self.status_label.configure(
                text="Остановлен",
                text_color="#f44336"
            )
            self.header_status.configure(
                text="⭕ Остановлен",
                text_color="#f44336"
            )
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.restart_btn.configure(state="disabled")

    def _check_status_loop(self):
        running = self.zapret.is_running()
        if running != self.zapret._running:
            self.zapret._running = running
            self._on_status_change(running)
        self.after(3000, self._check_status_loop)


if __name__ == "__main__":
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join(sys.argv), None, 1
        )
        sys.exit()

    app = App()
    app._check_status_loop()
    app.mainloop()