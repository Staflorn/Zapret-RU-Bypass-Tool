import subprocess
import sys
import os
import time

def test():
    print("=" * 50)
    print("ДИАГНОСТИКА v3")
    print("=" * 50)
    print()

    import ctypes
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    print(f"[1] Права: {'✅ Администратор' if is_admin else '❌ НЕТ ПРАВ'}")
    print()

    # Тест New-Service
    print("[2] Тест New-Service + sc delete...")
    cmd_exe = os.path.join(
        os.environ.get("SystemRoot", "C:\\Windows"),
        "System32", "cmd.exe"
    )
    svc_name = "zapret_test_v3"

    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"New-Service -Name '{svc_name}' "
         f"-DisplayName 'Zapret Test v3' "
         f"-BinaryPathName '{cmd_exe} /c echo test' "
         f"-StartupType Manual -ErrorAction Stop"],
        capture_output=True, text=True,
        encoding="utf-8", errors="ignore", timeout=15
    )
    if r.returncode == 0:
        print(f"    ✅ New-Service: OK")
    else:
        print(f"    ❌ New-Service: {r.stderr[:80]}")

    # Удаляем через sc.exe с bytes
    r2 = subprocess.run(
        ["sc.exe", "delete", svc_name],
        capture_output=True, timeout=10
    )
    out = r2.stdout.decode("cp866", errors="ignore").strip()
    print(f"    sc delete код: {r2.returncode} | {out[:60]}")
    if r2.returncode == 0:
        print("    ✅ sc delete: OK")
    else:
        print("    ❌ sc delete не сработал")
    print()

    # Тест ServiceManager
    print("[3] Полный тест ServiceManager...")
    try:
        sys.path.insert(
            0, os.path.dirname(os.path.abspath(__file__))
        )
        from core.service_manager import ServiceManager

        # Ищем bat файл
        bat_path = None
        excluded = {
            "service.bat", "install_service.bat",
            "uninstall_service.bat", "install.bat",
            "blockcheck.bat", "get_if_list.bat"
        }
        search_dirs = [
            os.path.dirname(os.path.abspath(__file__)),
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), ".."
            )
        ]
        for d in search_dirs:
            try:
                for f in sorted(os.listdir(d)):
                    if (f.endswith(".bat")
                            and f.lower() not in excluded
                            and not f.startswith("_")):
                        bat_path = os.path.join(d, f)
                        break
            except:
                pass
            if bat_path:
                break

        if not bat_path:
            print("    ⚠️ Bat файл не найден!")
        else:
            print(f"    Файл: {os.path.basename(bat_path)}")

            sm = ServiceManager(
                zapret_path=os.path.dirname(bat_path),
                log_callback=lambda m: print(f"    LOG: {m}")
            )

            name = sm._bat_to_service_name(bat_path)
            print(f"    Имя сервиса: {name}")

            status = sm.get_service_status(bat_path)
            print(f"    Начальный статус: {status}")

            print()
            print("    --- Установка ---")
            ok, msg = sm.install_service(bat_path)
            print(f"    Результат: {'✅' if ok else '❌'} {msg}")

            if ok:
                time.sleep(1)
                s = sm.get_service_status(bat_path)
                print(f"    Статус: {s}")

                print()
                print("    --- Запуск ---")
                ok2, msg2 = sm.start_service(bat_path)
                print(f"    Результат: {'✅' if ok2 else '❌'} {msg2}")

                time.sleep(2)
                s2 = sm.get_service_status(bat_path)
                print(f"    Статус: {s2}")

                if s2 == "running":
                    print()
                    print("    --- Остановка ---")
                    ok3, msg3 = sm.stop_service(bat_path)
                    print(f"    Результат: {'✅' if ok3 else '❌'} {msg3}")

                print()
                print("    --- Удаление ---")
                ok4, msg4 = sm.uninstall_service(bat_path)
                print(f"    Результат: {'✅' if ok4 else '❌'} {msg4}")

                time.sleep(1)
                s3 = sm.get_service_status(bat_path)
                print(f"    Статус после удаления: {s3}")

    except Exception as e:
        import traceback
        print(f"    ❌ Исключение: {e}")
        traceback.print_exc()

    print()
    print("=" * 50)
    print("Готово!")
    print("=" * 50)
    input()

test()