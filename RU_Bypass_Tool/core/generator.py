import os
from core.detector import ProviderInfo

class BatGenerator:
    def __init__(self, zapret_path: str):
        self.zapret_path = zapret_path
        self.bin_path = os.path.join(zapret_path, "bin")
        self.lists_path = os.path.join(zapret_path, "lists")

    def generate(self, provider: ProviderInfo, services: dict) -> str:
        """
        Генерация bat файла под провайдера
        services = {
            "youtube": True,
            "discord": True,
            "apex": True,
            "general": True
        }
        """
        bin = self.bin_path + "\\"
        lists = self.lists_path + "\\"
        ttl = provider.ttl
        ttl_yt = provider.ttl_youtube
        rep = provider.repeats

        lines = []
        lines.append("@echo off")
        lines.append("chcp 65001 > nul")
        lines.append("")
        lines.append(f'cd /d "{self.zapret_path}"')
        lines.append("call service.bat status_zapret")
        lines.append("call service.bat check_updates")
        lines.append("call service.bat load_game_filter")
        lines.append("call service.bat load_user_lists")
        lines.append("echo:")
        lines.append("")
        lines.append(f'set "BIN={bin}"')
        lines.append(f'set "LISTS={lists}"')
        lines.append("")

        # Формируем команду запуска winws
        cmd_parts = []
        cmd_parts.append(f'start "zapret" /min "%BIN%winws.exe"')

        # WinDivert фильтры
        tcp_ports = "80,443,2053,2083,2087,2096,8443,%GameFilterTCP%"
        udp_ports = "443,19294-19344,50000-50100,%GameFilterUDP%"

        if services.get("apex"):
            udp_ports += ",1024-1124,10000-65535"

        cmd_parts.append(f"--wf-tcp={tcp_ports}")
        cmd_parts.append(f"--wf-udp={udp_ports}")

        # Блок Apex (первым — без ipset)
        if services.get("apex"):
            cmd_parts.append("--new")
            cmd_parts.append("--filter-udp=1024-1124,10000-65535")
            cmd_parts.append("--dpi-desync=fake")
            cmd_parts.append("--dpi-desync-any-protocol=1")
            cmd_parts.append(f"--dpi-desync-autottl={ttl}")
            cmd_parts.append("--dpi-desync-cutoff=n2")
            cmd_parts.append(f'--dpi-desync-fake-unknown-udp="%BIN%quic_initial_www_google_com.bin"')
            cmd_parts.append(f"--dpi-desync-repeats={rep}")

        # Блок YouTube QUIC
        if services.get("youtube"):
            cmd_parts.append("--new")
            cmd_parts.append("--filter-udp=443")
            cmd_parts.append(f'--hostlist="%LISTS%list-youtube.txt"')
            cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude.txt"')
            cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude-user.txt"')
            cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
            cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
            cmd_parts.append("--dpi-desync=fake")
            cmd_parts.append(f"--dpi-desync-autottl={ttl_yt}")
            cmd_parts.append("--dpi-desync-repeats=12")
            cmd_parts.append(f'--dpi-desync-fake-quic="%BIN%quic_initial_www_google_com.bin"')

        # Блок Discord UDP
        if services.get("discord"):
            cmd_parts.append("--new")
            cmd_parts.append("--filter-udp=19294-19344,50000-50100")
            cmd_parts.append("--dpi-desync=fake")
            cmd_parts.append("--dpi-desync-any-protocol=1")
            cmd_parts.append(f"--dpi-desync-autottl={ttl}")
            cmd_parts.append("--dpi-desync-cutoff=n2")
            cmd_parts.append(f'--dpi-desync-fake-unknown-udp="%BIN%quic_initial_www_google_com.bin"')
            cmd_parts.append(f"--dpi-desync-repeats={rep}")

        # Блок Discord TCP
        if services.get("discord"):
            cmd_parts.append("--new")
            cmd_parts.append("--filter-tcp=2053,2083,2087,2096,8443,443")
            cmd_parts.append("--hostlist-domains=discord.com,discordapp.com,discord.media,discordapp.net,discord.gg")
            cmd_parts.append("--dpi-desync=fake,multisplit")
            cmd_parts.append("--dpi-desync-split-seqovl=681")
            cmd_parts.append("--dpi-desync-split-pos=1")
            cmd_parts.append("--dpi-desync-fooling=ts")
            cmd_parts.append(f"--dpi-desync-autottl={ttl}")
            cmd_parts.append(f"--dpi-desync-repeats={rep}")
            cmd_parts.append(f'--dpi-desync-split-seqovl-pattern="%BIN%tls_clienthello_www_google_com.bin"')
            cmd_parts.append(f'--dpi-desync-fake-tls="%BIN%tls_clienthello_www_google_com.bin"')

        # Блок YouTube TCP
        if services.get("youtube"):
            cmd_parts.append("--new")
            cmd_parts.append("--filter-tcp=443")
            cmd_parts.append(f'--hostlist="%LISTS%list-youtube.txt"')
            cmd_parts.append(f'--hostlist="%LISTS%list-google.txt"')
            cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude.txt"')
            cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude-user.txt"')
            cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
            cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
            cmd_parts.append("--dpi-desync=fake,multisplit")
            cmd_parts.append("--dpi-desync-split-seqovl=681")
            cmd_parts.append("--dpi-desync-split-pos=1")
            cmd_parts.append("--dpi-desync-fooling=ts")
            cmd_parts.append(f"--dpi-desync-autottl={ttl_yt}")
            cmd_parts.append(f"--dpi-desync-repeats={rep}")
            cmd_parts.append(f'--dpi-desync-split-seqovl-pattern="%BIN%tls_clienthello_www_google_com.bin"')
            cmd_parts.append(f'--dpi-desync-fake-tls="%BIN%tls_clienthello_www_google_com.bin"')

        # Блок общий TCP 80/443
        if services.get("general"):
            cmd_parts.append("--new")
            cmd_parts.append("--filter-tcp=80,443")
            cmd_parts.append(f'--hostlist="%LISTS%list-general.txt"')
            cmd_parts.append(f'--hostlist="%LISTS%list-general-user.txt"')
            cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude.txt"')
            cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude-user.txt"')
            cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
            cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
            cmd_parts.append("--dpi-desync=fake,multisplit")
            cmd_parts.append("--dpi-desync-split-seqovl=664")
            cmd_parts.append("--dpi-desync-split-pos=1")
            cmd_parts.append("--dpi-desync-fooling=ts")
            cmd_parts.append(f"--dpi-desync-autottl={ttl}")
            cmd_parts.append(f"--dpi-desync-repeats={rep}")
            cmd_parts.append(f'--dpi-desync-split-seqovl-pattern="%BIN%tls_clienthello_max_ru.bin"')
            cmd_parts.append(f'--dpi-desync-fake-tls="%BIN%tls_clienthello_max_ru.bin"')
            cmd_parts.append(f'--dpi-desync-fake-http="%BIN%tls_clienthello_max_ru.bin"')

        # Блок ipset UDP
        cmd_parts.append("--new")
        cmd_parts.append("--filter-udp=443")
        cmd_parts.append(f'--ipset="%LISTS%ipset-all.txt"')
        cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude.txt"')
        cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude-user.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
        cmd_parts.append("--dpi-desync=fake")
        cmd_parts.append(f"--dpi-desync-autottl={ttl}")
        cmd_parts.append("--dpi-desync-repeats=12")
        cmd_parts.append(f'--dpi-desync-fake-quic="%BIN%quic_initial_www_google_com.bin"')

        # Блок ipset TCP
        cmd_parts.append("--new")
        cmd_parts.append("--filter-tcp=80,443,8443")
        cmd_parts.append(f'--ipset="%LISTS%ipset-all.txt"')
        cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude.txt"')
        cmd_parts.append(f'--hostlist-exclude="%LISTS%list-exclude-user.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
        cmd_parts.append("--dpi-desync=fake,multisplit")
        cmd_parts.append("--dpi-desync-split-seqovl=664")
        cmd_parts.append("--dpi-desync-split-pos=1")
        cmd_parts.append("--dpi-desync-fooling=ts")
        cmd_parts.append(f"--dpi-desync-autottl={ttl}")
        cmd_parts.append(f"--dpi-desync-repeats={rep}")
        cmd_parts.append(f'--dpi-desync-split-seqovl-pattern="%BIN%tls_clienthello_max_ru.bin"')
        cmd_parts.append(f'--dpi-desync-fake-tls="%BIN%tls_clienthello_max_ru.bin"')
        cmd_parts.append(f'--dpi-desync-fake-http="%BIN%tls_clienthello_max_ru.bin"')

        # Блок GameFilter TCP
        cmd_parts.append("--new")
        cmd_parts.append("--filter-tcp=%GameFilterTCP%")
        cmd_parts.append(f'--ipset="%LISTS%ipset-all.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
        cmd_parts.append("--dpi-desync=fake,multisplit")
        cmd_parts.append("--dpi-desync-any-protocol=1")
        cmd_parts.append(f"--dpi-desync-autottl={ttl}")
        cmd_parts.append("--dpi-desync-cutoff=n4")
        cmd_parts.append("--dpi-desync-split-seqovl=664")
        cmd_parts.append("--dpi-desync-split-pos=1")
        cmd_parts.append("--dpi-desync-fooling=ts")
        cmd_parts.append(f"--dpi-desync-repeats={rep}")
        cmd_parts.append(f'--dpi-desync-split-seqovl-pattern="%BIN%tls_clienthello_max_ru.bin"')
        cmd_parts.append(f'--dpi-desync-fake-tls="%BIN%tls_clienthello_max_ru.bin"')
        cmd_parts.append(f'--dpi-desync-fake-http="%BIN%tls_clienthello_max_ru.bin"')

        # Блок GameFilter UDP
        cmd_parts.append("--new")
        cmd_parts.append("--filter-udp=%GameFilterUDP%")
        cmd_parts.append(f'--ipset="%LISTS%ipset-all.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude.txt"')
        cmd_parts.append(f'--ipset-exclude="%LISTS%ipset-exclude-user.txt"')
        cmd_parts.append("--dpi-desync=fake")
        cmd_parts.append("--dpi-desync-any-protocol=1")
        cmd_parts.append(f"--dpi-desync-autottl={ttl}")
        cmd_parts.append("--dpi-desync-cutoff=n2")
        cmd_parts.append("--dpi-desync-repeats=10")
        cmd_parts.append(f'--dpi-desync-fake-unknown-udp="%BIN%quic_initial_www_google_com.bin"')

        # Собираем команду в одну строку
        full_cmd = " ".join(cmd_parts)
        lines.append(full_cmd)
        lines.append("")
        lines.append("echo:")
        lines.append("echo [OK] zapret zapushchen")
        lines.append("pause")

        return "\n".join(lines)

    def save(self, provider: ProviderInfo, services: dict,
             filename: str = "zapret_generated.bat") -> str:
        """Сохранить сгенерированный bat файл"""
        content = self.generate(provider, services)
        path = os.path.join(self.zapret_path, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path