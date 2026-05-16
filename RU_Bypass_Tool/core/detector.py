import subprocess
import socket
import re
import requests
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProviderInfo:
    name: str
    ttl: int
    ttl_youtube: int
    repeats: int
    city: str = ""
    ip: str = ""

# База провайдеров по IP диапазонам и ASN
PROVIDER_DATABASE = {
    "КГТС": ProviderInfo(
        name="КГТС (Кострома)",
        ttl=7,
        ttl_youtube=7,
        repeats=10,
        city="Кострома"
    ),
    "Ростелеком": ProviderInfo(
        name="Ростелеком",
        ttl=4,
        ttl_youtube=6,
        repeats=8,
        city=""
    ),
    "МТС": ProviderInfo(
        name="МТС",
        ttl=3,
        ttl_youtube=5,
        repeats=8,
        city=""
    ),
    "Билайн": ProviderInfo(
        name="Билайн",
        ttl=5,
        ttl_youtube=7,
        repeats=10,
        city=""
    ),
    "Мегафон": ProviderInfo(
        name="Мегафон",
        ttl=4,
        ttl_youtube=6,
        repeats=8,
        city=""
    ),
    "Неизвестный": ProviderInfo(
        name="Неизвестный провайдер",
        ttl=4,
        ttl_youtube=7,
        repeats=10,
        city=""
    ),
}

class ProviderDetector:
    def __init__(self, log_callback=None):
        self.log = log_callback or print

    def get_external_ip(self) -> str:
        """Получить внешний IP адрес"""
        try:
            r = requests.get("https://api.ipify.org", timeout=5)
            return r.text.strip()
        except:
            try:
                r = requests.get("https://ifconfig.me/ip", timeout=5)
                return r.text.strip()
            except:
                return ""

    def get_provider_by_ip(self, ip: str) -> str:
        """Определить провайдера по IP через ipinfo.io"""
        try:
            r = requests.get(
                f"https://ipinfo.io/{ip}/json",
                timeout=5
            )
            data = r.json()
            org = data.get("org", "").lower()
            city = data.get("city", "")

            self.log(f"IP: {ip}, Org: {org}, City: {city}")

            # Определяем провайдера по названию организации
            if any(x in org for x in ["kgts", "костром", "46.42"]):
                return "КГТС"
            elif any(x in org for x in ["rostelecom", "ростелеком", "rtk"]):
                return "Ростелеком"
            elif any(x in org for x in ["mts", "мтс", "mobile telesystems"]):
                return "МТС"
            elif any(x in org for x in ["beeline", "билайн", "vimpelcom"]):
                return "Билайн"
            elif any(x in org for x in ["megafon", "мегафон"]):
                return "Мегафон"
            else:
                return "Неизвестный"
        except Exception as e:
            self.log(f"Ошибка определения провайдера: {e}")
            return "Неизвестный"

    def traceroute(self, host: str, max_hops: int = 15) -> list:
        """Трассировка маршрута"""
        hops = []
        try:
            result = subprocess.run(
                ["tracert", "-d", "-h", str(max_hops), "-w", "1000", host],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="cp866",
                errors="ignore"
            )
            lines = result.stdout.split("\n")
            for line in lines:
                match = re.search(
                    r"(\d+)\s+(?:(\d+)\s+ms|\*)\s+(?:(\d+)\s+ms|\*)\s+(?:(\d+)\s+ms|\*)\s+(\S+)",
                    line
                )
                if match:
                    hop_num = int(match.group(1))
                    ip = match.group(5)
                    is_timeout = "*" in line
                    hops.append({
                        "hop": hop_num,
                        "ip": ip if not is_timeout else "*",
                        "timeout": is_timeout
                    })
        except Exception as e:
            self.log(f"Ошибка трассировки: {e}")
        return hops

    def find_ttl(self, host: str = "youtube.com") -> int:
        """Найти TTL до DPI блокировки"""
        self.log(f"Трассировка до {host}...")
        hops = self.traceroute(host)

        # Ищем первый хоп со звёздочкой
        for hop in hops:
            if hop["timeout"]:
                ttl = hop["hop"] - 1
                self.log(f"DPI обнаружен на хопе {hop['hop']}, TTL = {ttl}")
                return max(1, ttl)

        # Если звёздочек нет — берём количество хопов
        if hops:
            ttl = len(hops) - 2
            self.log(f"Звёздочек нет, TTL = {ttl}")
            return max(1, ttl)

        self.log("Трассировка не дала результатов, TTL = 4 (по умолчанию)")
        return 4

    def detect(self) -> ProviderInfo:
        """Полное определение провайдера"""
        self.log("Получение внешнего IP...")
        ip = self.get_external_ip()

        if not ip:
            self.log("Не удалось получить IP, использую параметры по умолчанию")
            return PROVIDER_DATABASE["Неизвестный"]

        self.log(f"Внешний IP: {ip}")

        provider_name = self.get_provider_by_ip(ip)
        self.log(f"Провайдер: {provider_name}")

        provider = PROVIDER_DATABASE.get(
            provider_name,
            PROVIDER_DATABASE["Неизвестный"]
        )
        provider.ip = ip

        # Уточняем TTL через трассировку
        self.log("Определение TTL через трассировку...")
        real_ttl = self.find_ttl("youtube.com")

        if real_ttl > 0:
            provider.ttl_youtube = real_ttl
            provider.ttl = max(1, real_ttl - 1)
            self.log(f"TTL YouTube: {real_ttl}, TTL игры: {provider.ttl}")

        return provider