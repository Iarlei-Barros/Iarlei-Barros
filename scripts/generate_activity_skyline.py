import os
import json
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = "Iarlei-Barros"
OUTPUT_FILE = "assets/activity-skyline.svg"

DAYS = 180
TOWERS = 18


# ============================================================
# TOKYO NIGHT
# ============================================================

BG = "#1a1b26"
BG_DARK = "#16161e"
BG_LIGHT = "#24283b"

BORDER = "#565f89"
GRID = "#292e42"

TEXT = "#c0caf5"
TEXT_SECONDARY = "#9aa5ce"

BLUE = "#7aa2f7"
CYAN = "#7dcfff"
PURPLE = "#bb9af7"
PINK = "#f7768e"
YELLOW = "#e0af68"


# ============================================================
# GITHUB API
# ============================================================

def github_query():
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN não encontrado.")

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS - 1)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "login": USERNAME,
        "from": f"{start}T00:00:00Z",
        "to": f"{today}T23:59:59Z"
    }

    data = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME
        },
        method="POST"
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]["user"]["contributionsCollection"]


# ============================================================
# ORGANIZA OS DADOS
# ============================================================

def get_contributions():
    collection = github_query()
    calendar = collection["contributionCalendar"]

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })

    days = sorted(days, key=lambda x: x["date"])

    # Garante exatamente os últimos 180 dias
    days = days[-DAYS:]

    total = sum(day["count"] for day in days)
    active_days = sum(1 for day in days if day["count"] > 0)

    return days, total, active_days


# ============================================================
# TORRES
# ============================================================

def create_towers(days):
    towers = []

    chunk_size = len(days) / TOWERS

    for i in range(TOWERS):
        start = int(i * chunk_size)
        end = int((i + 1) * chunk_size)

        chunk = days[start:end]

        value = sum(day["count"] for day in chunk)

        towers.append(value)

    return towers


def tower_color(value, maximum):
    if value == 0:
        return {
            "front": "#292e42",
            "side": "#1f2335",
            "top": "#3b4261"
        }

    ratio = value / maximum if maximum else 0

    if ratio < 0.25:
        return {
            "front": BLUE,
            "side": "#3d59a1",
            "top": "#9db8ff"
        }

    if ratio < 0.50:
        return {
            "front": CYAN,
            "side": "#2b7f91",
            "top": "#a8e8f5"
        }

    if ratio < 0.75:
        return {
            "front": PURPLE,
            "side": "#7052a8",
            "top": "#d1b9ff"
        }

    return {
        "front": PINK,
        "side": "#a33e5f",
        "top": "#ff9db2"
    }


# ============================================================
# SVG
# ============================================================

def tower_svg(x, base_y, width, height, depth, colors):
    x2 = x + width

    top_y = base_y - height

    # perspectiva
    dx = depth
    dy = depth * 0.55

    front = (
        f"{x},{top_y} "
        f"{x2},{top_y} "
        f"{x2},{base_y} "
        f"{x},{base_y}"
    )

    side = (
        f"{x2},{top_y} "
        f"{x2 + dx},{top_y - dy} "
        f"{x2 + dx},{base_y - dy} "
        f"{x2},{base_y}"
    )

    top = (
        f"{x},{top_y} "
        f"{x2},{top_y} "
        f"{x2 + dx},{top_y - dy} "
        f"{x + dx},{top_y - dy}"
    )

    return f"""
    <polygon points="{side}"
        fill="{colors['side']}"
        stroke="{GRID}"
        stroke-width="1"/>

    <polygon points="{top}"
        fill="{colors['top']}"
        stroke="{GRID}"
        stroke-width="1"/>

    <polygon points="{front}"
        fill="{colors['front']}"
        stroke="{GRID}"
        stroke-width="1"/>
    """


def generate_svg(days, total, active_days, towers):
    width = 900
    height = 320

    maximum = max(towers) if towers else 1
    peak = maximum

    # --------------------------------------------------------
    # Fundo
    # --------------------------------------------------------

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}">

    <defs>

        <linearGradient id="background"
            x1="0" y1="0"
            x2="0" y2="1">

            <stop offset="0%"
                stop-color="{BG}"/>

            <stop offset="100%"
                stop-color="{BG_DARK}"/>

        </linearGradient>

        <linearGradient id="floor"
            x1="0" y1="0"
            x2="0" y2="1">

            <stop offset="0%"
                stop-color="{BG_LIGHT}"/>

            <stop offset="100%"
                stop-color="{BG_DARK}"/>

        </linearGradient>

        <filter id="softGlow">

            <feGaussianBlur
                stdDeviation="5"
                result="blur"/>

            <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>

        </filter>

    </defs>


    <!-- BACKGROUND -->

    <rect
        width="900"
        height="320"
        fill="url(#background)"/>


    <!-- ESTRELAS -->

    <g fill="{TEXT_SECONDARY}" opacity="0.75">

        <circle cx="250" cy="28" r="1"/>
        <circle cx="355" cy="54" r="1"/>
        <circle cx="438" cy="25" r="1"/>
        <circle cx="520" cy="70" r="1"/>
        <circle cx="612" cy="38" r="1"/>
        <circle cx="695" cy="60" r="1"/>
        <circle cx="815" cy="35" r="1"/>

    </g>


    <!-- TÍTULO -->

    <text
        x="28"
        y="28"
        fill="{BLUE}"
        font-family="Arial, sans-serif"
        font-size="16"
        font-weight="bold">

        Contribution Skyline

    </text>


    <text
        x="28"
        y="47"
        fill="{PURPLE}"
        font-family="monospace"
        font-size="8"
        letter-spacing="3">

        180 DAYS · IARLEI-BARROS

    </text>


    <!-- ÁREA DO GRÁFICO -->

    <path
        d="M20 268 L510 268 L545 250 L545 75"
        fill="none"
        stroke="{GRID}"
        stroke-width="1"/>


    <path
        d="M20 268 L510 268 L545 250"
        fill="url(#floor)"
        stroke="{GRID}"
        stroke-width="1"/>


    <!-- LINHA DE HORIZONTE -->

    <line
        x1="20"
        y1="268"
        x2="545"
        y2="268"
        stroke="{BORDER}"
        stroke-width="1"
        opacity="0.7"/>


    <!-- TORRES -->
"""

    # --------------------------------------------------------
    # Torres
    # --------------------------------------------------------

    start_x = 48
    base_y = 258

    width_tower = 34
    gap = 7

    max_height = 145

    for i, value in enumerate(towers):

        x = start_x + i * (width_tower + gap)

        if maximum:
            tower_height = 18 + (value / maximum) * max_height
        else:
            tower_height = 18

        colors = tower_color(value, maximum)

        svg += tower_svg(
            x=x,
            base_y=base_y,
            width=width_tower,
            height=tower_height,
            depth=9,
            colors=colors
        )

    # --------------------------------------------------------
    # PAINEL DIREITO
    # --------------------------------------------------------

    svg += f"""

    <!-- DIVISÓRIA -->

    <line
        x1="565"
        y1="38"
        x2="565"
        y2="250"
        stroke="{GRID}"
        stroke-width="1"/>


    <!-- ACTIVITY -->

    <text
        x="592"
        y="62"
        fill="{PURPLE}"
        font-family="monospace"
        font-size="9"
        letter-spacing="3">

        — ACTIVITY

    </text>


    <rect x="592" y="85"
        width="11" height="11"
        rx="1"
        fill="{BLUE}"/>

    <text
        x="615"
        y="94"
        fill="{TEXT}"
        font-family="monospace"
        font-size="9">

        low · activity

    </text>


    <rect x="592" y="106"
        width="11" height="11"
        rx="1"
        fill="{CYAN}"/>

    <text
        x="615"
        y="115"
        fill="{TEXT}"
        font-family="monospace"
        font-size="9">

        mid · activity

    </text>


    <rect x="592" y="127"
        width="11" height="11"
        rx="1"
        fill="{PURPLE}"/>

    <text
        x="615"
        y="136"
        fill="{TEXT}"
        font-family="monospace"
        font-size="9">

        high · activity

    </text>


    <rect x="592" y="148"
        width="11"
        height="11"
        rx="1"
        fill="{PINK}"/>

    <text
        x="615"
        y="157"
        fill="{TEXT}"
        font-family="monospace"
        font-size="9">

        peak · activity

    </text>


    <!-- SEPARADOR -->

    <line
        x1="592"
        y1="177"
        x2="820"
        y2="177"
        stroke="{GRID}"
        stroke-width="1"/>


    <!-- PROFILE -->

    <text
        x="592"
        y="201"
        fill="{PURPLE}"
        font-family="monospace"
        font-size="9"
        letter-spacing="3">

        — PROFILE

    </text>


    <text
        x="592"
        y="224"
        fill="{TEXT}"
        font-family="monospace"
        font-size="9">

        contributions

    </text>

    <text
        x="815"
        y="224"
        fill="{CYAN}"
        font-family="monospace"
        font-size="10"
        font-weight="bold"
        text-anchor="end">

        {total}

    </text>


    <text
        x="592"
        y="242"
        fill="{TEXT}"
        font-family="monospace"
        font-size="9">

        active days

    </text>

    <text
        x="815"
        y="242"
        fill="{PINK}"
        font-family="monospace"
        font-size="10"
        font-weight="bold"
        text-anchor="end">

        {active_days}

    </text>


    <!-- RODAPÉ -->

    <text
        x="28"
        y="298"
        fill="{TEXT_SECONDARY}"
        opacity="0.7"
        font-family="monospace"
        font-size="7"
        letter-spacing="2">

        IARLEI-BARROS · CONTRIBUTION SKYLINE

    </text>


    <text
        x="815"
        y="298"
        fill="{BLUE}"
        font-family="monospace"
        font-size="7"
        font-weight="bold"
        letter-spacing="2"
        text-anchor="end">

        TOKYO NIGHT

    </text>

</svg>
"""

    return svg


# ============================================================
# MAIN
# ============================================================

def main():
    days, total, active_days = get_contributions()

    towers = create_towers(days)

    svg = generate_svg(
        days,
        total,
        active_days,
        towers
    )

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(svg)

    print("Skyline atualizado!")
    print(f"Usuário: {USERNAME}")
    print(f"Contribuições: {total}")
    print(f"Dias ativos: {active_days}")
    print(f"Pico: {max(towers) if towers else 0}")


if __name__ == "__main__":
    main()
