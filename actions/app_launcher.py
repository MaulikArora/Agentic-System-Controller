import subprocess
import webbrowser
import os

APP_MAP = {

    # Browsers
    "chrome":           {"type": "shell", "cmd": "chrome"},
    "google chrome":    {"type": "shell", "cmd": "chrome"},
    "firefox":          {"type": "shell", "cmd": "firefox"},
    "edge":             {"type": "shell", "cmd": "msedge"},
    "microsoft edge":   {"type": "shell", "cmd": "msedge"},
    "brave":            {"type": "shell", "cmd": "brave"},

    # Dev tools
    "vscode":           {"type": "shell", "cmd": "code"},
    "vs code":          {"type": "shell", "cmd": "code"},
    "visual studio code": {"type": "shell", "cmd": "code"},
    "terminal":         {"type": "shell", "cmd": "wt"},
    "powershell":       {"type": "shell", "cmd": "powershell"},
    "cmd":              {"type": "shell", "cmd": "cmd"},
    "notepad":          {"type": "shell", "cmd": "notepad"},
    "notepad++":        {"type": "shell", "cmd": "notepad++"},
    "git bash":         {"type": "shell", "cmd": "git-bash"},
    "postman":          {"type": "shell", "cmd": "postman"},

    # Productivity
    "word":             {"type": "shell", "cmd": "winword"},
    "excel":            {"type": "shell", "cmd": "excel"},
    "powerpoint":       {"type": "shell", "cmd": "powerpnt"},
    "outlook":          {"type": "shell", "cmd": "outlook"},
    "onenote":          {"type": "shell", "cmd": "onenote"},
    "teams":            {"type": "shell", "cmd": "ms-teams:"},
    "microsoft teams":  {"type": "shell", "cmd": "ms-teams:"},
    "slack":            {"type": "shell", "cmd": "slack"},
    "notion":           {"type": "shell", "cmd": "notion"},
    "obsidian":         {"type": "shell", "cmd": "obsidian"},

    # Media
    "spotify":          {"type": "shell", "cmd": "spotify"},
    "vlc":              {"type": "shell", "cmd": "vlc"},

    # System / utilities
    "calculator":       {"type": "shell", "cmd": "calc"},
    "calc":             {"type": "shell", "cmd": "calc"},
    "windows calculator": {"type": "shell", "cmd": "calc"},
    "calendar":         {"type": "shell", "cmd": "outlookcal:"},
    "file explorer":    {"type": "shell", "cmd": "explorer"},
    "explorer":         {"type": "shell", "cmd": "explorer"},
    "task manager":     {"type": "shell", "cmd": "taskmgr"},
    "settings":         {"type": "shell", "cmd": "ms-settings:"},
    "paint":            {"type": "shell", "cmd": "mspaint"},
    "snipping tool":    {"type": "shell", "cmd": "snippingtool"},
    "discord":          {"type": "shell", "cmd": "discord"},
    "zoom":             {"type": "shell", "cmd": "zoom"},
    "whatsapp":         {"type": "shell", "cmd": "whatsapp:"},
    "telegram":         {"type": "shell", "cmd": "telegram"},

    # ── Web: Video & Entertainment ─────────────────────────────────────────────
    "youtube":          {"type": "web", "cmd": "https://youtube.com"},
    "netflix":          {"type": "web", "cmd": "https://netflix.com"},
    "prime video":      {"type": "web", "cmd": "https://primevideo.com"},
    "amazon prime":     {"type": "web", "cmd": "https://primevideo.com"},
    "hotstar":          {"type": "web", "cmd": "https://hotstar.com"},
    "disney plus":      {"type": "web", "cmd": "https://disneyplus.com"},
    "twitch":           {"type": "web", "cmd": "https://twitch.tv"},

    # ── Web: Social Media ──────────────────────────────────────────────────────
    "twitter":          {"type": "web", "cmd": "https://twitter.com"},
    "x":                {"type": "web", "cmd": "https://x.com"},
    "instagram":        {"type": "web", "cmd": "https://instagram.com"},
    "facebook":         {"type": "web", "cmd": "https://facebook.com"},
    "linkedin":         {"type": "web", "cmd": "https://linkedin.com"},
    "reddit":           {"type": "web", "cmd": "https://reddit.com"},
    "pinterest":        {"type": "web", "cmd": "https://pinterest.com"},
    "snapchat":         {"type": "web", "cmd": "https://snapchat.com"},
    "tiktok":           {"type": "web", "cmd": "https://tiktok.com"},

    # ── Web: Search Engines ────────────────────────────────────────────────────
    "google":           {"type": "web", "cmd": "https://google.com"},
    "bing":             {"type": "web", "cmd": "https://bing.com"},
    "duckduckgo":       {"type": "web", "cmd": "https://duckduckgo.com"},

    # ── Web: Productivity & Docs ───────────────────────────────────────────────
    "gmail":            {"type": "web", "cmd": "https://mail.google.com"},
    "google drive":     {"type": "web", "cmd": "https://drive.google.com"},
    "google docs":      {"type": "web", "cmd": "https://docs.google.com"},
    "google sheets":    {"type": "web", "cmd": "https://sheets.google.com"},
    "google slides":    {"type": "web", "cmd": "https://slides.google.com"},
    "google calendar":  {"type": "web", "cmd": "https://calendar.google.com"},
    "google meet":      {"type": "web", "cmd": "https://meet.google.com"},
    "meet":             {"type": "web", "cmd": "https://meet.google.com"},
    "google maps":      {"type": "web", "cmd": "https://maps.google.com"},
    "maps":             {"type": "web", "cmd": "https://maps.google.com"},

    # ── Web: Dev & Tech ────────────────────────────────────────────────────────
    "github":           {"type": "web", "cmd": "https://github.com"},
    "stackoverflow":    {"type": "web", "cmd": "https://stackoverflow.com"},
    "stack overflow":   {"type": "web", "cmd": "https://stackoverflow.com"},
    "chatgpt":          {"type": "web", "cmd": "https://chatgpt.com"},
    "claude":           {"type": "web", "cmd": "https://claude.ai"},
    "vercel":           {"type": "web", "cmd": "https://vercel.com"},
    "replit":           {"type": "web", "cmd": "https://replit.com"},

    # ── Web: Shopping ──────────────────────────────────────────────────────────
    "amazon":           {"type": "web", "cmd": "https://amazon.in"},
    "flipkart":         {"type": "web", "cmd": "https://flipkart.com"},
    "meesho":           {"type": "web", "cmd": "https://meesho.com"},

    # ── Web: News ──────────────────────────────────────────────────────────────
    "bbc":              {"type": "web", "cmd": "https://bbc.com"},
    "bbc news":         {"type": "web", "cmd": "https://bbc.com/news"},
    "the hindu":        {"type": "web", "cmd": "https://thehindu.com"},
    "times of india":   {"type": "web", "cmd": "https://timesofindia.com"},

    # ── Web: Finance ───────────────────────────────────────────────────────────
    "zerodha":          {"type": "web", "cmd": "https://kite.zerodha.com"},
    "groww":            {"type": "web", "cmd": "https://groww.in"},
    "moneycontrol":     {"type": "web", "cmd": "https://moneycontrol.com"},
}


class AppLauncher:

    def open(self, target: str) -> str:
        if not target:
            return "No app target provided."

        target_clean = target.strip().lower()

        app = APP_MAP.get(target_clean)

        if not app:
            for key, val in APP_MAP.items():
                if target_clean in key or key in target_clean:
                    app = val
                    break

        if not app:
            return f"Couldn't find app: '{target}'"

        try:

            if app["type"] == "web":
                webbrowser.open(app["cmd"])
                return f"Opened {target} in browser."

            elif app["type"] == "shell":
                subprocess.Popen(
                    f'start "" "{app["cmd"]}"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"Opened {target}."

            elif app["type"] == "path":
                if not os.path.exists(app["cmd"]):
                    return f"Couldn't find app at path: {app['cmd']}"
                subprocess.Popen(
                    app["cmd"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"Opened {target}."

        except Exception as e:
            return f"Failed to open '{target}': {e}"
